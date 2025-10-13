# query_handler.py: 处理查询精炼、检索和报告生成
import ollama
import faiss
import numpy as np
from typing import List, Tuple
from utils import call_deepseek_api  # 导入 API 调用
from indexing import load_index, EMBEDDING_MODEL  # 导入索引加载和模型名

TOP_K = 5  # 检索 top-5 chunks

# Function to refine query
def refine_query(chinese_question: str) -> Tuple[str, List[str]]:
    system_prompt = "You are a query refiner for Hayek's works. Extract 3-5 English keywords and create a concise English query for retrieval."
    prompt = f"Given the Chinese question: '{chinese_question}'\nOutput in this exact format:\nRefined Query: [concise english query]\nKeywords: [kw1, kw2, kw3, ...]"
    response = call_deepseek_api(prompt, system_prompt)
    
    # Parse response
    try:
        query_line = [line for line in response.split('\n') if line.startswith('Refined Query:')][0]
        keywords_line = [line for line in response.split('\n') if line.startswith('Keywords:')][0]
        english_query = query_line.split(':', 1)[1].strip()
        keywords = [kw.strip() for kw in keywords_line.split(':', 1)[1].split(',')]
        return english_query, keywords
    except IndexError:
        raise ValueError("Invalid response format from query refinement.")

# Function to retrieve chunks
def retrieve_chunks(english_query: str, index: faiss.IndexFlatL2, chunks: List[str]) -> List[str]:
    # Embed query using Ollama
    try:
        query_emb_response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=english_query)
        query_emb = np.array([query_emb_response['embedding']], dtype=np.float32)
    except Exception as e:
        raise ValueError(f"Ollama embedding error for query: {e}. Ensure 'ollama serve' is running.")

    # Search FAISS index
    distances, indices = index.search(query_emb, TOP_K)
    retrieved = [chunks[i] for i in indices[0] if i < len(chunks)]
    print(f"Retrieved {len(retrieved)} chunks.")  # 调试输出
    return retrieved

# Function to generate report
def generate_report(chinese_question: str, retrieved_chunks: List[str]) -> str:
    context = '\n\n'.join(retrieved_chunks)
    system_prompt = "You are the Hayek Research Committee AI. Generate a structured Chinese report based on Hayek's views from the provided context. Be neutral, inspirational, emphasize spontaneous order, dispersed knowledge, price signals. End with implications. Include disclaimer."
    prompt = f"Original Question: {chinese_question}\n\nRetrieved Context:\n{context}\n\nGenerate report in Chinese:\n- Section 1: '用户提问' (repeat question)\n- Section 2: '委员会意见' (200-400 words summary, quotes/paraphrases, analysis, implications)\nDisclaimer at end: 'This is AI-generated inspiration based on Hayek's works, not authoritative interpretation.'"
    return call_deepseek_api(prompt, system_prompt)

# 主工作流函数（可供 main.py 调用）
def handle_query(chinese_question: str) -> str:
    # Load index
    index, chunks = load_index()
    
    # Refine query
    english_query, keywords = refine_query(chinese_question)
    print(f"Refined Query: {english_query}\nKeywords: {keywords}")  # 调试输出
    
    # Retrieve
    retrieved = retrieve_chunks(english_query, index, chunks)
    
    # Generate report
    report = generate_report(chinese_question, retrieved)
    
    return report

# 如果单独运行这个文件，就测试一个查询
if __name__ == "__main__":
    sample_question = "哈耶克如何看待中央计划经济？"
    report = handle_query(sample_question)
    print(report)