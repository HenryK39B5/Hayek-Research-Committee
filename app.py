# app.py: 哈耶克研究委员会 Streamlit 网页应用（优化阅读器交互）
import streamlit as st
from query_handler import handle_query
from dotenv import load_dotenv
import os
import re

# 加载 .env
load_dotenv()

# 页面配置
st.set_page_config(page_title="哈耶克研究委员会", page_icon="📚", layout="wide")

# 会话状态：保存历史记录
if "history" not in st.session_state:
    st.session_state.history = []

# 侧边栏：设置和帮助
with st.sidebar:
    st.title("设置")
    st.markdown("欢迎！输入中文问题，获取 Hayek 观点分析。")
    if st.button("清空历史"):
        st.session_state.history = []
        st.rerun()

# 主页面
st.title("哈耶克研究委员会")
st.markdown("请输入您的中文问题（例如：'哈耶克如何看待中央计划经济？'），然后点击提交。")

question = st.text_input("您的提问：", key="input")

if st.button("提交") and question:
    with st.spinner("委员会正在分析中...（这可能需要几秒钟）"):
        try:
            report, retrieved_chunks, keywords = handle_query(question)
            st.session_state.history.append({"question": question, "report": report, "chunks": retrieved_chunks, "keywords": keywords})
        except Exception as e:
            st.error(f"处理出错：{e}。请检查 Ollama 是否运行或 API key 是否有效。")

# 显示历史报告，并在每个报告底部加 chunks 阅读器（用 tabs 作为标签页）
for entry in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(f"**提问：** {entry['question']}")
    with st.chat_message("assistant"):
        # 在报告中展示关键词
        if entry.get("keywords"):
            keywords_str = ', '.join(entry["keywords"])
            st.markdown(f"**提取关键词：** {keywords_str}")
            st.markdown("---")
        st.markdown(entry['report'])
    
    # 底部 chunks 阅读器（用 tabs 标签页，每个 tab 一个 chunk，高亮关键词）
    chunks = entry.get("chunks", [])
    keywords = entry.get("keywords", [])
    
    if chunks:
        st.markdown("### 来源 Chunks 阅读器")
        st.caption("选择标签页查看不同文档内容（高亮关键词）")
        
        # CSS 美化：阅读 pane、高亮（莫兰迪浅灰蓝 #B0C4DE）
        st.markdown("""
            <style>
            .reading-content {
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                font-family: 'Georgia', serif;
                line-height: 1.6;
                overflow-y: auto;
                max-height: 400px;
            }
            .highlight {
                background-color: #B0C4DE;  /* 莫兰迪浅灰蓝 */
                padding: 2px 4px;
                border-radius: 3px;
                font-weight: bold;
                color: #333;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # 用 tabs 作为标签页（横向排列）
        tab_titles = [f"文档 {i+1}" for i in range(len(chunks))]
        tabs = st.tabs(tab_titles)
        
        for i, tab in enumerate(tabs):
            with tab:
                chunk = chunks[i]
                st.markdown(f"**来源：** {chunk['metadata']['source_file']} | **ID：** {chunk['metadata']['chunk_id']} | **页码估算：** {chunk['metadata']['page_estimate']}")
                
                # 高亮关键词
                chunk_text = chunk['text']
                for kw in keywords:
                    chunk_text = re.sub(rf'\b({re.escape(kw)})\b', r'<span class="highlight">\1</span>', chunk_text, flags=re.I)
                
                st.markdown(f'<div class="reading-content">{chunk_text}</div>', unsafe_allow_html=True)
    else:
        st.info("无召回 chunks。")
    
    st.markdown("---")  # 分隔历史 entry

# 底部提示
st.caption("This is AI-generated inspiration based on Hayek's works, not authoritative interpretation.")