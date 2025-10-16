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
pip install requests numpy faiss-cpu sentence-transformers ollama python-dotenv PyPDF2 ebooklib
```
注意：FAISS用CPU版（faiss-cpu）；如果有GPU，可用faiss-gpu。

### 文档准备
- 将Hayek的PDF/EPUB文件放入`data/raw/`文件夹（或测试用`data/test/`）。
- 首次运行`python indexing.py`构建索引（生成`hayek_index.faiss`和`hayek_metadata.json`）。

## 使用方式
1. 启动Ollama服务器：`ollama serve`（新终端）。
2. 运行应用：`python main.py`。
3. 输入中文问题，按Enter提交；输入`quit`退出。
4. 系统输出报告，包括“用户提问”和“委员会意见”（200-400字分析+免责声明）。

示例输出：
```
用户提问：哈耶克如何看待中央计划经济？
委员会意见：...（AI生成的总结、引用和启示）
This is AI-generated inspiration based on Hayek's works, not authoritative interpretation.
```

## 技术实现细节
项目采用模块化设计，分成多个Python文件，便于维护和扩展。核心是RAG系统：文档向量化存储在FAISS向量数据库中，查询时检索相关块，再用LLM生成报告。以下是详细说明。

### 文件结构与模块说明
- **utils.py**：通用工具函数。
  - 提取文本：`extract_text_from_pdf`（用PyPDF2）和`extract_text_from_epub`（用ebooklib）。
  - 文本拆分：`recursive_split_text`（递归拆分成~500字符块，支持段落/句子级，带重叠）。
  - API调用：`call_deepseek_api`（POST到DeepSeek chat API，model: deepseek-chat, temperature: 0.7；用`python-dotenv`加载.env中的API key）。
  - 常量：API URL、模型名、chunk大小等。

- **indexing.py**：文档向量化与FAISS索引管理（离线步骤）。
  - `build_index()`：扫描`data/raw/`（或自定义路径）中的PDF/EPUB文件，提取文本，拆分成chunks，用Ollama（模型: mxbai-embed-large）生成embeddings（向量），构建FAISS IndexFlatL2（L2距离近似余弦相似度），保存索引和元数据（chunks列表）。
  - `load_index()`：加载现成索引；若不存在，自动调用build_index。
  - 注意：embedding用本地Ollama，避免API依赖；支持调试打印进度。构建一次后，重复使用。

- **query_handler.py**：查询处理核心。
  - `refine_query()`：用DeepSeek API精炼中文问题，输出英文查询和3-5关键词（prompt指定精确格式）。
  - `retrieve_chunks()`：用Ollama embedding英文查询，在FAISS中搜索top-5相关chunks（返回文本块）。
  - `generate_report()`：用DeepSeek API生成中文报告（prompt包括原问题+检索上下文；结构：用户提问 + 委员会意见（总结、引用、分析、启示） + 免责声明）。
  - `handle_query()`：整合以上步骤，返回完整报告。

- **main.py**：应用入口。
  - 命令行交互循环：读取用户输入，调用`handle_query`，打印报告。
  - 错误处理：捕获异常，提供友好提示。

### 工作流程
1. **索引构建（离线）**：运行`indexing.py`，读取文档 → 拆分chunks → Ollama embedding → FAISS索引保存。
2. **查询处理（在线）**：
   - 精炼：DeepSeek API转中文问题为英文查询/关键词。
   - 检索：Ollama embedding查询 → FAISS cosine搜索top-5 chunks。
   - 生成：DeepSeek API用上下文生成报告（强调Hayek概念，中性启发）。
3. **输出**：结构化中文报告。

### 关键技术点
- **Embedding与检索**：Ollama本地模型（mxbai-embed-large，1024维）确保隐私/无费用；FAISS高效向量搜索（IndexFlatL2）。
- **LLM集成**：DeepSeek-chat用于精炼和报告生成（temperature 0.7平衡创造性）；prompt工程确保输出格式严格。
- **错误处理**：每个函数有try-except，检查API key、Ollama运行、文件存在。
- **扩展性**：模块化设计；易换embedding模型（e.g., 回sentence-transformers）或LLM；支持大文档（chunk重叠避免信息丢失）。
- **性能考虑**：索引构建耗时（大文档几分钟），但查询快（秒级）；测试用小文件夹加速调试。

## 内网穿透（Tunneling）
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
```

## 贡献与调整
欢迎fork/pull request！调整想法如加GUI（Streamlit/Tkinter）、优化prompt或支持更多LLM，随时讨论。联系：[你的联系方式]。

## 免责声明
此应用为AI生成灵感，非权威解读。基于Hayek公开作品，仅教育目的。