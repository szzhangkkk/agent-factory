# Agent Factory

<p align="center">
  <strong>上传文档，自动生成一个能思考、会用工具、可独立部署的 AI Agent</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.10-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/formats-22-orange" alt="Supported Formats">
</p>

---

## 目录

- [这是什么？](#这是什么)
- [快速体验](#快速体验)
- [安装](#安装)
- [配置](#配置)
- [CLI 命令](#cli-命令)
- [Web 界面](#web-界面)
- [核心功能](#核心功能)
- [独立部署 Agent](#独立部署-agent)
- [Docker 部署](#docker-部署)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [开发](#开发)
- [License](#license)

---

## 这是什么？

普通的 RAG 聊天机器人只能"搜一段文档 + 让 LLM 总结一下"。**Agent Factory 更进一步**：它自动分析你的文档，生成一个带工具、会多步推理、有记忆、可独立部署的 AI Agent。

> **RAG 聊天机器人** = 图书管理员，你问什么它找什么
>
> **Agent Factory 生成的 Agent** = 一个会翻书、会按计算器、会做文本分析，还会先想清楚再动手，并且可以打包带走的助手

---

## 快速体验

```bash
# 1. 克隆
git clone git@github.com:szzhangkkk/agent-factory.git
cd agent-factory

# 2. 安装
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .

# 3. 配置 LLM
cp config/active.example.yaml config/active.yaml
# 编辑 config/active.yaml，填入你的 API key

# 4. 启动 Web 界面
uvicorn src.web.api.app:app --host 0.0.0.0 --port 8000 &

# 5. 启动前端
cd src/web/frontend/frontend && npm install && npm run dev
# 浏览器打开 http://localhost:5173
```

或者用 CLI：

```bash
# 从文档生成 Agent
agent-factory create --docs ./uploads/manual.pdf --name "客服助手" --skip-benchmark

# 和它对话
agent-factory chat --agent ./output/客服助手 --question "退款政策是什么？"
```

---

## 安装

### 环境要求

| 依赖 | 最低版本 | 说明 |
|------|---------|------|
| Python | ≥ 3.10 | |
| Node.js | ≥ 18 | 前端构建（可选，仅 Web 界面需要） |
| RAM | 推荐 8GB+ | Embedding 模型约需 1.5GB |
| 磁盘 | 2GB+ | 含模型缓存 |

### 安装步骤

```bash
git clone git@github.com:szzhangkkk/agent-factory.git
cd agent-factory
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 前端（可选）
cd src/web/frontend/frontend && npm install && cd ../../..
```

> **注意**：首次运行时，Embedding 模型（`BAAI/bge-small-zh-v1.5`，约 400MB）会自动下载。国内用户建议：
> ```bash
> export HF_ENDPOINT=https://hf-mirror.com
> ```

---

## 配置

编辑 `config/active.yaml`（从 `config/active.example.yaml` 复制）：

```yaml
llm:
  provider: deepseek
  api_key: your-api-key
  base_url: https://api.deepseek.com/v1
  model: deepseek-chat

embedding:
  provider: local               # 本地 embedding，无需 API
  model: BAAI/bge-small-zh-v1.5
```

支持的 LLM 提供商：

| ID | 名称 | 需要 API Key |
|------|------|------|
| `deepseek` | DeepSeek | 是 |
| `qwen` | 通义千问 | 是 |
| `zhipu` | 智谱 GLM | 是 |
| `moonshot` | Moonshot (Kimi) | 是 |
| `claude` | Anthropic Claude | 是 |
| `openai` | OpenAI | 是 |
| `ollama` | Ollama (本地) | 否 |
| `custom` | 自定义（OpenAI 兼容） | 按需 |

---

## CLI 命令

| 命令 | 用途 | 示例 |
|------|------|------|
| `create` | 从文档创建 Agent | `agent-factory create --docs ./manual.pdf --name "助手"` |
| `chat` | 与生成的 Agent 对话 | `agent-factory chat --agent ./output/助手 -q "退款流程？"` |
| `providers` | 列出可用的 LLM 提供商 | `agent-factory providers` |
| `test-connection` | 检测 LLM 和 Embedding 连接 | `agent-factory test-connection` |

### create 参数

| 参数 | 必选 | 说明 |
|------|------|------|
| `--docs` | 是 | 文档路径（文件或目录） |
| `--name` | 否 | Agent 名称 |
| `--description` | 否 | Agent 描述 |
| `--requirement` | 否 | 对 Agent 的额外要求 |
| `--output` | 否 | 输出目录（默认 `./output`） |
| `--skip-benchmark` | 否 | 跳过自动评测（加速创建） |

---

## Web 界面

```bash
# 启动后端
uvicorn src.web.api.app:app --host 0.0.0.0 --port 8000

# 启动前端（另一个终端）
cd src/web/frontend/frontend && npm run dev
```

浏览器打开 `http://localhost:5173`，6 个页面：

| 页面 | 功能 |
|------|------|
| **模型配置** | 设置 LLM 和 Embedding，测试连接 |
| **文档管理** | 上传 PDF/Word/PPT/Excel 等文件 |
| **Agent 创建** | 填写需求，一键生成 Agent |
| **对话测试** | 和 Agent 聊天，查看推理过程和工具调用 |
| **Benchmark** | 对比不同检索策略的评测结果 |
| **Agent 管理** | 查看/删除/导出已创建的 Agent，管理自定义工具 |

---

## 核心功能

### 对话记忆

Agent 跨会话保持记忆。对话历史自动保存到 `chat_history.json`，下次对话时自动加载。

### 三种推理模式

| 模式 | 适合 | 怎么工作 |
|------|------|---------|
| `direct` | 简单问答 | 调一次工具，直接回答 |
| `react` | 多步推理 | 思考 → 行动 → 观察，循环直到满意 |
| `plan_execute` | 复杂任务 | 先拆解成步骤清单，再逐步执行 |

### 内置工具

| 工具 | 能干什么 |
|------|---------|
| `document_retrieval` | 混合检索知识库（向量 + BM25 + 重排序） |
| `calculator` | 安全数学计算（AST 解析） |
| `text_analyzer` | 提取关键词、统计字数 |

### 自定义工具

在 Agent 管理页面，可以为 Agent 添加自定义 HTTP API 工具。Agent 会在对话时自动判断是否调用。

### 自动 Benchmark

创建 Agent 时自动评测 4 种检索策略（vector / bm25 / hybrid / hybrid_rerank），选出最优配置。

### 支持的文档格式

共 **22 种**：`.pdf` `.docx` `.doc` `.pptx` `.xlsx` `.xls` `.epub` `.txt` `.md` `.html` `.csv` `.json` `.xml` `.jpg` `.png` `.gif` `.bmp` `.zip` `.wav` `.mp3` `.mp4`

---

## 独立部署 Agent

生成的 Agent 可以完全脱离 Agent Factory 独立运行。

### 导出

在 Web 界面的「Agent 管理」页面，点击导出按钮下载 zip 包。包含：

- `server.py` — 独立 FastAPI 服务器（使用完整的混合检索引擎）
- `src/core/` — 核心源码（检索、推理、工具系统）
- `data/` — Agent 配置和知识库数据
- `Dockerfile` + `docker-compose.yml` — 一键容器化部署
- `README.md` — 部署说明

### 部署方式

```bash
# 解压
unzip agent-xxx.zip && cd agent-xxx

# 方式一：直接运行
pip install -r requirements.txt
export LLM_API_KEY=your-key
python server.py

# 方式二：Docker
LLM_API_KEY=your-key docker compose up -d
```

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/chat` | `{"question": "..."}` |
| `DELETE` | `/history` | 清除对话记忆 |
| `GET` | `/health` | 健康检查 |

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | LLM API Key | （必填） |
| `LLM_BASE_URL` | LLM API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` |

---

## Docker 部署

### Agent Factory 平台

```bash
cd deploy/docker
docker-compose up -d
# 浏览器打开 http://localhost:8000
```

### 单个 Agent（导出后）

```bash
cd agent-xxx
LLM_API_KEY=your-key docker compose up -d
# API 在 http://localhost:8080
```

---

## 项目结构

```
agent-factory/
├── config/                          # 配置文件
│   ├── active.example.yaml          # 配置示例
│   └── default.yaml                 # 默认配置
├── src/
│   ├── cli.py                       # CLI 入口
│   ├── core/
│   │   ├── orchestrator.py          # 主流程编排 + 对话记忆
│   │   ├── agent/
│   │   │   ├── generator.py         # Agent 生成器
│   │   │   ├── runtime.py           # 运行时引擎（工具循环 + 推理策略）
│   │   │   └── tools.py             # 工具系统 + 自定义 HTTP 工具
│   │   ├── doc_processor/
│   │   │   ├── converter.py         # 文档转 Markdown
│   │   │   └── chunker.py           # 三种分块策略
│   │   ├── llm/
│   │   │   ├── client.py            # 统一 LLM 客户端
│   │   │   ├── local_embedder.py    # 离线 Embedding
│   │   │   └── providers.py         # 提供商配置
│   │   ├── retrieval/
│   │   │   └── hybrid_search.py     # 混合检索（向量 + BM25）
│   │   └── vector_store/
│   │       ├── milvus_store.py      # Milvus 向量存储
│   │       └── memory_store.py      # 轻量内存存储
│   ├── benchmark/                   # Benchmark 评测
│   └── web/
│       ├── api/app.py               # FastAPI 后端
│       └── frontend/                # React 前端
├── output/                          # Agent 输出目录
├── pyproject.toml
└── README.md
```

---

## 常见问题

<details>
<summary><strong>和 Dify / FastGPT / LangChain 有什么区别？</strong></summary>

这些平台需要你手动设计提示词、选工具、配流程。Agent Factory **只需要上传文档**，自动完成 Agent 设计（推理策略、工具配置、系统提示词），并支持一键导出为独立可部署的服务。
</details>

<details>
<summary><strong>生成的 Agent 可以单独部署吗？</strong></summary>

可以。在 Web 界面「Agent 管理」页面点击导出，会生成一个包含完整源码、Dockerfile 和部署说明的 zip 包。解压后 `python server.py` 或 `docker compose up -d` 即可运行，不依赖 Agent Factory。
</details>

<details>
<summary><strong>Agent 有记忆吗？</strong></summary>

有。对话历史自动持久化到 `chat_history.json`，下次对话自动加载最近 20 轮记录。在 Web 界面点击「清空对话」会同时清除服务端记忆。
</details>

<details>
<summary><strong>能给 Agent 添加自定义工具吗？</strong></summary>

可以。在「Agent 管理」页面选择一个 Agent，点击「添加工具」，填入 HTTP API 的名称、URL 和描述即可。Agent 会在对话时自动判断是否需要调用。
</details>

<details>
<summary><strong>支持多语言文档吗？</strong></summary>

支持。默认 Embedding 模型 `bge-small-zh-v1.5` 对中英文都有良好效果。英文为主可切换为 `BAAI/bge-small-en-v1.5`。
</details>

<details>
<summary><strong>Benchmark 很慢？</strong></summary>

Benchmark 需要对 4 种检索策略逐一做 LLM 评测，涉及多次 API 调用。如果不需要，创建 Agent 时勾选「跳过 Benchmark」即可。
</details>

<details>
<summary><strong>首次运行提示模型下载失败？</strong></summary>

国内用户设置镜像：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```
模型只需下载一次。
</details>

---

## 开发

```bash
pip install -e ".[dev]"
pytest
```

欢迎提交 Issue 和 Pull Request！

---

## License

MIT
