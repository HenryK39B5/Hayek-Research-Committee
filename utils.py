# utils.py: 通用帮助函数模块
import os
import json
import requests
import re
from typing import List
import PyPDF2
from ebooklib import epub
import ebooklib  # 导入 ebooklib 以访问 ITEM_DOCUMENT
from dotenv import load_dotenv  # 新增：加载 .env 文件

# 常量（如果需要，可以移到单独的 config.py，但现在简单点）
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
MODEL_NAME = 'deepseek-chat'
TEMPERATURE = 0.7
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Helper function to extract text from PDF
def extract_text_from_pdf(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            for page in reader.pages:
                text += page.extract_text() + '\n'
            return text
    except Exception as e:
        raise ValueError(f"Error reading PDF {file_path}: {e}")

# Helper function to extract text from EPUB
def extract_text_from_epub(file_path: str) -> str:
    try:
        book = epub.read_epub(file_path)
        text = ''
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            text += item.get_content().decode('utf-8') + '\n'
        return text
    except Exception as e:
        raise ValueError(f"Error reading EPUB {file_path}: {e}")

# Recursive text splitter: split into paragraphs, then sentences, then chunks
def recursive_split_text(text: str, max_chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    def split_into_paragraphs(t: str) -> List[str]:
        return [p.strip() for p in t.split('\n\n') if p.strip()]

    def split_into_sentences(p: str) -> List[str]:
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', p)
        return [s.strip() for s in sentences if s.strip()]

    chunks = []
    paragraphs = split_into_paragraphs(text)
    for para in paragraphs:
        if len(para) <= max_chunk_size:
            chunks.append(para)
        else:
            sentences = split_into_sentences(para)
            current_chunk = ''
            for sent in sentences:
                if len(current_chunk) + len(sent) <= max_chunk_size:
                    current_chunk += sent + ' '
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sent[-overlap:] + sent if len(sent) > overlap else sent
            if current_chunk:
                chunks.append(current_chunk.strip())
    return chunks

# Helper function for DeepSeek API call
def call_deepseek_api(prompt: str, system_prompt: str = "") -> str:
    load_dotenv()  # 新增：加载 .env 文件（确保 API key 被读取）
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set in environment variables or .env file.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_NAME,
        "temperature": TEMPERATURE,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"DeepSeek API error: {e}")