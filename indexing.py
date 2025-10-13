# indexing.py: 处理文档向量化与 FAISS 索引构建/加载（使用 Ollama embedding）
import os
import json
import faiss
import numpy as np
import ollama  # 需要 pip install ollama
from utils import extract_text_from_pdf, extract_text_from_epub, recursive_split_text  # 导入 utils 中的函数

# 常量
INDEX_FILE = 'hayek_index.faiss'
METADATA_FILE = 'hayek_metadata.json'
EMBEDDING_MODEL = 'embeddinggemma:300m-qat-q4_0'
# Function to build index
def build_index() -> tuple:
    # Find all PDF and EPUB files in 'data/raw' folder (根据你的输出调整路径)
    data_dir = 'data/raw'  # 如果用测试文件夹，改成 'data/test'
    if not os.path.exists(data_dir):
        raise ValueError(f"'{data_dir}' folder not found in the current directory.")
    
    all_files = os.listdir(data_dir)
    #print(f"Found {len(all_files)} files in '{data_dir}': {all_files[:5]}...")  # 只打印前5个，避免太长
    
    documents = [f for f in all_files if f.lower().endswith(('.pdf', '.epub'))]
    if not documents:
        raise ValueError(f"No PDF or EPUB documents found in '{data_dir}' folder.")

    all_chunks = []
    for doc in documents:
        full_path = os.path.join(data_dir, doc)
        if doc.lower().endswith('.pdf'):
            text = extract_text_from_pdf(full_path)
        elif doc.lower().endswith('.epub'):
            text = extract_text_from_epub(full_path)
        else:
            continue
        chunks = recursive_split_text(text)
        all_chunks.extend(chunks)
        print(f"Extracted {len(chunks)} chunks from {doc}")  # 调试：监控进度

    if not all_chunks:
        raise ValueError("No text chunks extracted from documents.")

    # Embed chunks using Ollama
    print("Starting embedding with Ollama...")
    embeddings = []
    for i, chunk in enumerate(all_chunks):
        try:
            emb_response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=chunk)
            embeddings.append(emb_response['embedding'])
            if (i + 1) % 100 == 0:  # 进度提示
                print(f"Embedded {i + 1}/{len(all_chunks)} chunks")
        except Exception as e:
            raise ValueError(f"Ollama embedding error for chunk {i}: {e}. Ensure 'ollama serve' is running and model is pulled.")

    embeddings = np.array(embeddings, dtype=np.float32)  # FAISS 需要 float32
    dim = embeddings.shape[1]

    # Build FAISS index (using L2 distance for cosine similarity approximation)
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Save index and metadata
    faiss.write_index(index, INDEX_FILE)
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False)

    print(f"Index built and saved to {INDEX_FILE} and {METADATA_FILE} using Ollama model {EMBEDDING_MODEL}")
    print(f"Total chunks: {len(all_chunks)}, Dimension: {dim}")
    return index, all_chunks

# Function to load existing index
def load_index() -> tuple:
    if not os.path.exists(INDEX_FILE) or not os.path.exists(METADATA_FILE):
        print("Index not found, building new one...")
        return build_index()
    index = faiss.read_index(INDEX_FILE)
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    print("Index loaded successfully")
    return index, chunks

# 如果单独运行这个文件，就构建索引（测试用）
if __name__ == "__main__":
    build_index()  # 或 load_index()，根据需要