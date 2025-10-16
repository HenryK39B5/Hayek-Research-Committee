# indexing.py: 处理文档向量化与 FAISS 索引构建/加载（使用 Ollama embedding）
import os
import json
import faiss
import numpy as np
import ollama
from utils import extract_text_from_pdf, extract_text_from_epub, recursive_split_text  # 导入 utils 中的函数

# 常量
INDEX_FILE = 'hayek_index.faiss'
METADATA_FILE = 'hayek_metadata.json'
EMBEDDING_MODEL = 'embeddinggemma:300m-qat-q4_0'
PARENT_CHUNK_SIZE = 2000  # 父块大小
SUB_CHUNK_SIZE = 500      # 子块大小
MIN_CHUNK_LENGTH = 100    # 已有的最小长度

# Function to build index
def build_index() -> tuple:
    data_dir = 'data/test'
    processed_dir = 'data/processed'  # 保存提取文本的目录
    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir)  # 创建目录如果不存在
    
    if not os.path.exists(data_dir):
        raise ValueError(f"'{data_dir}' folder not found in the current directory.")
    
    all_files = os.listdir(data_dir)
    # print(f"Found {len(all_files)} files in '{data_dir}': {all_files[:5]}...")  
    
    documents = [f for f in all_files if f.lower().endswith(('.pdf', '.epub'))]
    if not documents:
        raise ValueError(f"No PDF or EPUB documents found in '{data_dir}' folder.")

    all_parent_chunks = []  # list of {'text': str, 'metadata': dict}
    all_sub_chunks = []     # list of {'text': str, 'metadata': dict, 'parent_id': int}
    global_parent_id = 0
    global_sub_id = 0

    for doc in documents:
        full_path = os.path.join(data_dir, doc)
        if doc.lower().endswith('.pdf'):
            text = extract_text_from_pdf(full_path)
        elif doc.lower().endswith('.epub'):
            text = extract_text_from_epub(full_path)
        else:
            continue
        
        # 保存提取的文本到 txt
        txt_filename = os.path.splitext(doc)[0] + '.txt'  # e.g., book.pdf -> book.txt
        txt_path = os.path.join(processed_dir, txt_filename)
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        print(f"Saved extracted text to {txt_path}")
        
        # 先分父块（大段落）
        parent_chunks = recursive_split_text(text, max_chunk_size=PARENT_CHUNK_SIZE, overlap=100)  # 用大 size
        filtered_parents = [p for p in parent_chunks if len(p) >= MIN_CHUNK_LENGTH * 2]  # 父块至少大点
        
        for local_parent_id, parent_text in enumerate(filtered_parents):
            global_parent_id += 1
            parent_metadata = {
                'source_file': doc,
                'chunk_id': f"parent_{global_parent_id:04d}",
                'page_estimate': local_parent_id + 1
            }
            all_parent_chunks.append({'text': parent_text, 'metadata': parent_metadata})
            
            # 从父块分子块
            sub_chunks = recursive_split_text(parent_text, max_chunk_size=SUB_CHUNK_SIZE, overlap=50)
            filtered_subs = [s for s in sub_chunks if len(s) >= MIN_CHUNK_LENGTH]
            
            for sub_text in filtered_subs:
                global_sub_id += 1
                sub_metadata = {
                    'source_file': doc,
                    'chunk_id': f"sub_{global_sub_id:04d}",
                    'page_estimate': local_parent_id + 1,
                    'parent_id': global_parent_id  # 链接到父
                }
                all_sub_chunks.append({'text': sub_text, 'metadata': sub_metadata})
    
    if not all_sub_chunks:
        raise ValueError("No sub-chunks extracted.")

    # Embed chunks using Ollama
    print("Starting embedding sub-chunks with Ollama...")
    embeddings = []
    for i, sub_dict in enumerate(all_sub_chunks):
        chunk_text = sub_dict['text']
        try:
            emb_response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=chunk_text)
            embeddings.append(emb_response['embedding'])
            if (i + 1) % 100 == 0:
                print(f"Embedded {i + 1}/{len(all_sub_chunks)} chunks")
        except Exception as e:
            raise ValueError(f"Ollama embedding error for chunk {i}: {e}.")
    
    embeddings = np.array(embeddings, dtype=np.float32)
    dim = embeddings.shape[1]
    
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

   # 保存：分开存 parent 和 sub
    metadata = {'parents': all_parent_chunks, 'subs': all_sub_chunks}
    faiss.write_index(index, INDEX_FILE)
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False)
    
    print(f"Index built... Total parents: {len(all_parent_chunks)}, subs: {len(all_sub_chunks)}")
    return index, metadata  # 返回 dict

# Function to load existing index
def load_index() -> tuple:
    if not os.path.exists(INDEX_FILE) or not os.path.exists(METADATA_FILE):
        print("Index not found, building new one...")
        return build_index()
    index = faiss.read_index(INDEX_FILE)
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    parents = metadata['parents']
    subs = metadata['subs']
    print("Index loaded: parents and subs")
    return index, parents, subs  # 返回 index, parents, subs

# 如果单独运行这个文件，就构建索引（测试用）
if __name__ == "__main__":
    build_index()  # 或 load_index()，根据需要