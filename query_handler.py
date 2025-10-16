# query_handler.py: 处理查询精炼、检索和报告生成
import ollama
import faiss
import numpy as np
from typing import List, Tuple
from utils import call_deepseek_api  # 导入 API 调用
from indexing import load_index, EMBEDDING_MODEL  # 导入索引加载和模型名

TOP_K = 5  # 检索 top-5 chunks

# Function to refine query
def refine_query(chinese_question: str) -> Tuple[str, List[str], str]:
    system_prompt = "You are a query analyzer for Hayek's works. First, analyze if the question is suitable (related to economics, philosophy, spontaneous order, etc.). If too narrow/irrelevant, suggest expansion. Then, refine to English query and 3-5 keywords."
    prompt = f"Given the Chinese question: '{chinese_question}'\n\nStep 1: Analyze suitability (1-2 sentences): Is it relevant to Hayek? If not, suggest related topic. If shallow, suggest deeper angle.\nStep 2: Refined Query: [concise english query, or empty if unsuitable]\nStep 3: Keywords: [kw1, kw2, ...] (3-5 English keywords, or empty if unsuitable)\nOutput exactly in this format."
    response = call_deepseek_api(prompt, system_prompt)
    
    # Parse response
    try:
        lines = response.split('\n')
        analysis = ' '.join([line.strip() for line in lines if line.startswith('Step 1:')])[len('Step 1: '):].strip()
        query_line = [line for line in lines if line.startswith('Step 2:')][0]
        keywords_line = [line for line in lines if line.startswith('Step 3:')][0]
        
        english_query = query_line.split(':', 1)[1].strip() if ':' in query_line else ''
        keywords_str = keywords_line.split(':', 1)[1].strip() if ':' in keywords_line else ''
        keywords = [kw.strip() for kw in keywords_str.split(',')] if keywords_str else []
        
        return english_query, keywords, analysis  # 返回 analysis
    except IndexError:
        raise ValueError("Invalid response format from query refinement.")

# Function to retrieve chunks
def retrieve_chunks(english_query: str, index: faiss.IndexFlatL2, parents: List[dict], subs: List[dict]) -> List[dict]:
    # Embed query using Ollama
    try:
        query_emb_response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=english_query)
        query_emb = np.array([query_emb_response['embedding']], dtype=np.float32)
    except Exception as e:
        raise ValueError(f"Ollama embedding error for query: {e}. Ensure 'ollama serve' is running.")

    # Search FAISS index
    distances, indices = index.search(query_emb, TOP_K)
    sub_indices = [i for i in indices[0] if i < len(subs)]
    
    # 收集唯一 parent_ids
    parent_ids = set(subs[i]['metadata']['parent_id'] for i in sub_indices)
    retrieved = [parents[pid - 1] for pid in parent_ids if pid - 1 < len(parents)]  # ID 从1开始，list 从0
    
    print(f"Retrieved {len(retrieved)} parent chunks from {len(sub_indices)} subs.")
    return retrieved

# Function to generate report
def generate_report(chinese_question: str, retrieved_chunks: List[dict], analysis: str = "") -> str:
    context = '\n\n'.join([chunk['text'] for chunk in retrieved_chunks])
    system_prompt = "You are the Hayek Research Committee AI. Generate a structured Chinese report based on Hayek's views from the provided context. Be neutral, inspirational, emphasize spontaneous order, dispersed knowledge, price signals. End with implications. Include disclaimer. If analysis is provided, incorporate its insights to deepen the response."
    prompt = f"Original Question: {chinese_question}\n\nAnalysis (if any): {analysis}\n\nRetrieved Context:\n{context}\n\nGenerate report in Chinese:\n- Section 1: '用户提问' (repeat question)\n- Section 2: '委员会意见' (200-400 words summary, quotes/paraphrases, analysis, implications; reference the above analysis to make it more targeted)\nDisclaimer at end: 'This is AI-generated inspiration based on Hayek's works, not authoritative interpretation.'"
    return call_deepseek_api(prompt, system_prompt)

# 主工作流函数（可供 main.py 调用）
def handle_query(chinese_question: str) -> Tuple[str, List[dict]]:
    index, parents, subs = load_index()  # 解包 parents, subs
    english_query, keywords, analysis = refine_query(chinese_question)  # 解包 analysis
    
    print(f"Analysis: {analysis}\nRefined Query: {english_query}\nKeywords: {keywords}")
    
    if not english_query:  # 如果不适合，生成建议报告
        report = f"用户提问：{chinese_question}\n\n委员会意见：{analysis} 建议您调整问题以更好地匹配 Hayek 的观点，例如探讨自发秩序或知识分散。\n\nThis is AI-generated inspiration based on Hayek's works, not authoritative interpretation."
        return report, []  # 无 chunks
    
    retrieved_parents = retrieve_chunks(english_query, index, parents, subs)  # 传 parents, subs，返回 parents
    
    report = generate_report(chinese_question, retrieved_parents, analysis)  # 用 parents
    
    # 如果有分析建议，注入报告开头
    if analysis:
        report = f"分析建议：{analysis}\n\n" + report
    
    return report, retrieved_parents, keywords  # 返回父块

# 如果单独运行这个文件，就测试一个查询
if __name__ == "__main__":
    sample_question = "哈耶克如何看待中央计划经济？"
    report = handle_query(sample_question)
    print(report)