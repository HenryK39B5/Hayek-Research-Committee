# 哈耶克研究委员会 (Hayek Research Committee)

## 项目简介
这是一个基于RAG（Retrieval-Augmented Generation）的AI应用，模拟一个研究委员会，对Friedrich von Hayek的英文作品（PDF/EPUB文件）进行分析。用户输入中文问题（如“哈耶克如何看待中央计划经济？”），系统输出结构化的中文报告，包括Hayek观点总结、引用和启发性分析。报告强调Hayek的核心概念，如自发秩序、分散知识和价格信号。

## 安装与依赖
### 环境要求
- Python 3.8+（推荐使用Anaconda或虚拟环境）
- Ollama（本地运行，用于embedding模型）：下载并安装Ollama，运行`ollama serve`，并拉取模型如`ollama pull mxbai-embed-large`。
- DeepSeek API Key：存放在项目根目录的`.env`文件中，格式为`DEEPSEEK_API_KEY=your_key`（从DeepSeek官网获取）。

### 安装依赖库
在项目目录运行：
```
pip install requests numpy faiss-cpu ollama python-dotenv PyPDF2 ebooklib streamlit
```
注意：FAISS用CPU版（faiss-cpu）；如果有GPU，可用faiss-gpu。

### 文档准备
- 将Hayek的PDF/EPUB文件放入`data/raw/`文件夹（或测试用`data/test/`）。
- 首次运行`python indexing.py`构建索引（生成`hayek_index.faiss`和`hayek_metadata.json`）。

## 使用方式
1. 启动Ollama服务器：`ollama serve`（新终端）。
2. 启动 Web UI：streamlit run app.py

示例输出：
```
用户提问：哈耶克如何看待中央计划经济？
委员会意见：...（AI生成的总结、引用和启示）
This is AI-generated inspiration based on Hayek's works, not authoritative interpretation.
```

## 技术实现细节
项目采用模块化设计，分成多个Python文件，便于维护和扩展。核心是RAG系统：文档向量化存储在FAISS向量数据库中，查询时检索相关块，再用LLM生成报告。以下是详细说明。

### 文件结构与模块说明
- **utils.py**：通用工具与 I/O。
  - 文本提取：`extract_text_from_pdf(path)`（PyPDF2）与 `extract_text_from_epub(path)`（ebooklib）。
  - 文本拆分：`recursive_split_text(text, max_chunk_size=500, overlap=50)`（先按段落再按句子递归拆分，保留重叠）。
  - API 调用：`call_deepseek_api(prompt, system_prompt="")`（POST 到 DeepSeek chat API，model: `deepseek-chat`，temperature: 0.7；用 `python-dotenv` 从 `.env` 读取 `DEEPSEEK_API_KEY`）。
  - 文本清洗：`clean_text`（移除 HTML、规范空白）。
  - 常量：API URL、模型名、chunk 默认大小等均在该模块使用或导入。

- **indexing.py**：离线构建与加载 FAISS 索引（基于本地 Ollama embedding）。
  - 默认数据路径：`data/test/`（可修改）。提取后文本保存到 `data/processed/`。
  - `build_index()`：扫描 `data/test` 中的 PDF/EPUB → 提取文本 → 先分父块（PARENT_CHUNK_SIZE=2000）→ 再分子块（SUB_CHUNK_SIZE=500，最小长度过滤）→ 用 Ollama 生成 embeddings（EMBEDDING_MODEL = 'embeddinggemma:300m-qat-q4_0'）→ 构建 FAISS 索引（IndexFlatL2）→ 保存为 `hayek_index.faiss` 与 `hayek_metadata.json`（metadata 包含 parents/subs 列表和每块的 metadata）。
  - `load_index()`：若索引文件缺失则自动调用 `build_index()`，否则从磁盘读取索引与 metadata。
  - 输出文件：`hayek_index.faiss` 与 `hayek_metadata.json`。

- **query_handler.py**：查询流程与报告生成。
  - `refine_query(chinese_question)`：调用 DeepSeek（`call_deepseek_api`）将中文问题精炼成英文查询与 3-5 个关键词，并返回分析 / 适配建议（若问题不适合则返回空的英文查询）。
  - `retrieve_chunks(english_query, index, parents, subs)`：用 Ollama 对英文查询做 embedding，利用 FAISS 搜索 top-K（TOP_K=5），根据检索到的子块映射回父块并返回父块列表。
  - `generate_report(chinese_question, retrieved_chunks, analysis="")`：将检索上下文和（可选）精炼分析传给 DeepSeek API，生成结构化中文报告（包含“用户提问”与“委员会意见”与免责声明）。
  - `handle_query(chinese_question)`：整合以上步骤（精炼→检索→生成），返回报告与召回的父块及关键词（供 UI 显示）。

- **app.py**：Streamlit 前端（替代 main.py）。
  - 使用 `streamlit` 实现交互式 UI：输入问题、提交后调用 `handle_query`、在页面展示报告、关键词与来源 chunks（以 tabs 显示并高亮关键词）。
  - 会话状态保留历史查询，支持清空历史，chunks 阅读器显示 metadata（source_file、chunk_id、page_estimate）。

### 工作流程
1. **索引构建（离线）**：运行`indexing.py`，读取文档 → 拆分chunks → Ollama embedding → FAISS索引保存。
2. **查询处理（在线）**：
   - 精炼：DeepSeek API转中文问题为英文查询/关键词。
   - 检索：Ollama embedding查询 → FAISS cosine搜索top-5 chunks。
   - 生成：DeepSeek API用上下文生成报告（强调Hayek概念，中性启发）。
3. **输出**：结构化中文报告。

### 关键技术点
- Embedding 与检索
  - 本项目使用本地 Ollama 生成 embeddings（配置模型名在 `indexing.py`，当前为 `embeddinggemma:300m-qat-q4_0`）。请先运行 `ollama serve` 并确保已拉取所需 embedding 模型。
  - 向量索引采用 FAISS 的 IndexFlatL2（L2 距离用于近似余弦相似度检索的简单实现），索引与 metadata 分别保存为 `hayek_index.faiss` 与 `hayek_metadata.json`，可复用以加速查询。

- LLM / API 集成
  - 精炼与报告生成使用 DeepSeek Chat API（endpoint：`https://api.deepseek.com/v1/chat/completions`，model: `deepseek-chat`，temperature: 0.7）。API Key 从项目根目录 `.env` 中读取，键名为 `DEEPSEEK_API_KEY`。
  - 所有对 DeepSeek 的调用通过 `utils.call_deepseek_api` 统一封装，包含 basic error handling。

- 工作流（概览）
  1. 离线：运行 `python indexing.py`（或单独运行脚本中的 `build_index()`）→ 提取文本→ 拆分父/子块→ Ollama embedding→ 构建并保存 FAISS 索引与 metadata。
  2. 在线：确保 Ollama 服务运行（`ollama serve`），并设置 `.env` 的 `DEEPSEEK_API_KEY` → 运行前端 `streamlit run app.py` → 在页面输入中文问题→ 系统依次执行精炼（DeepSeek）→ 检索（Ollama + FAISS）→ 生成报告（DeepSeek）。

- 错误处理与提示
  - 每一步对常见错误（缺少 API key、Ollama 未运行、找不到数据目录或无文档、embedding 错误）有显式异常提示，UI 层在捕获异常时会展示友好信息。
  - 索引构建耗时（视文档大小），建议测试时先将样本放在 `data/test/` 并小规模运行。

- 可配置项（在代码中）
  - 数据路径（`indexing.py` 的 `data_dir`）、父/子块大小（PARENT_CHUNK_SIZE、SUB_CHUNK_SIZE）、embedding 模型名（EMBEDDING_MODEL）、FAISS 索引/metadata 文件名、DeepSeek 模型与 temperature（在 `utils.py` 中定义）。

## 内网穿透（Tunneling）：展示方式
### 使用 Ngrok 实现本地应用公网访问
Ngrok 可将 Streamlit 应用（默认端口 8501）暴露到公网，便于测试共享。适用于项目初期验证。

#### 步骤
1. **下载 Ngrok**：访问 [ngrok.com/download](https://ngrok.com/download)，下载 Windows 版（ngrok.exe），置于项目目录。
2. **注册与配置**（可选，推荐）：在 [dashboard.ngrok.com](https://dashboard.ngrok.com) 注册，获取 Authtoken，然后运行 `ngrok config add-authtoken YOUR_AUTHTOKEN`。
3. **启动应用**：运行 `streamlit run app.py`（确保 Ollama serve 运行）。
4. **启动穿透**：新终端运行 `ngrok http 8501`，获取公网 URL（如 `https://abc123.ngrok.io`）。
5. **测试**：用浏览器打开 URL，确认访问正常。分享 URL 给他人。
6. **停止**：Ctrl+C 关闭 Ngrok 和 Streamlit。

#### 注意
- 免费版 URL 临时；付费版支持固定域名。
- 安全：测试后关闭，避免暴露敏感数据。
- 备选：Frp 或 Cloudflare Tunnel（详见工具文档）。

#### 示例输出
```
Forwarding    https://abc123.ngrok.io -> http://localhost:8501
```

## 贡献与调整
欢迎fork/pull request！调整想法如加GUI（Streamlit/Tkinter）、优化prompt或支持更多LLM，随时讨论。联系：[你的联系方式]。

## 免责声明
此应用为AI生成灵感，非权威解读。基于Hayek公开作品，仅教育目的。