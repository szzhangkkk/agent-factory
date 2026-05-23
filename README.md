# Agent Factory

<p align="center">
  <strong>上传文档，自动生成一个能思考、会用工具的 AI Agent</strong>
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
  - [环境要求](#环境要求)
  - [安装步骤](#安装步骤)
  - [验证安装](#验证安装)
- [配置](#配置)
- [CLI 命令](#cli-命令)
- [Web 界面](#web-界面)
- [它是怎么工作的](#它是怎么工作的)
- [三种推理模式](#三种推理模式)
- [内置工具](#内置工具)
- [支持的文档格式](#支持的文档格式)
- [Docker 部署](#docker-部署)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [开发](#开发)
- [License](#license)

---

### 这是什么？

普通的 RAG 聊天机器人只能"搜一段文档 + 让 LLM 总结一下"。**Agent Factory 更进一步**：它自动分析你的文档，生成一个带工具、会多步推理、有记忆的 AI Agent。

打个比方：

> **RAG 聊天机器人** = 图书管理员，你问什么它找什么
>
> **Agent Factory 生成的 Agent** = 一个会翻书、会按计算器、会做文本分析，还会先想清楚再动手的助手

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
# 复制示例配置 → 编辑 → 填入你的 API key
cp config/active.example.yaml config/active.yaml

# 4. 从文档生成 Agent
agent-factory create --docs ./uploads/manual.pdf --name "客服助手" --skip-benchmark

# 5. 和它对话
agent-factory chat --agent ./output --question "退款政策是什么？"
```

---

## 安装

### 环境要求

| 依赖 | 最低版本 | 说明 |
|------|---------|------|
| Python | ≥ 3.10 | |
| pip | 最新 | |
| RAM | 推荐 8GB+ | Embedding 模型约需 1.5GB，Milvus 向量数据库约需 2GB |
| 磁盘 | 2GB+ | 含模型缓存和向量数据 |

### 安装步骤

```bash
git clone git@github.com:szzhangkkk/agent-factory.git
cd agent-factory
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
```

> **注意**：首次运行时，Embedding 模型（`BAAI/bge-small-zh-v1.5`，约 400MB）会自动从 HuggingFace 下载。国内用户建议设置镜像加速：
> ```bash
> export HF_ENDPOINT=https://hf-mirror.com
> ```

### 验证安装

```bash
agent-factory test-connection   # 测试 LLM 连接是否正常
agent-factory providers         # 查看支持的 LLM 提供商
agent-factory --version         # 查看版本号
```

---

## 配置

编辑 `config/active.yaml`（从 `config/active.example.yaml` 复制而来），最少只需要配两样：

```yaml
llm:
  provider: deepseek            # 用什么模型
  api_key: your-api-key         # 你的 API key
  base_url: https://api.deepseek.com/v1
  model: deepseek-chat

embedding:
  provider: local               # 本地 embedding，不需 API，开箱即用
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

```bash
# 查看所有命令
agent-factory --help

# 查看版本
agent-factory --version
```

| 命令 | 用途 | 示例 |
|------|------|------|
| `create` | 从文档创建 Agent | `agent-factory create --docs ./manual.pdf --name "助手"` |
| `chat` | 与生成的 Agent 对话 | `agent-factory chat --agent ./output -q "退款流程？"` |
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
| `--config` | 否 | 指定配置文件路径 |
| `--skip-benchmark` | 否 | 跳过自动评测（加速创建） |

### chat 参数

| 参数 | 必选 | 说明 |
|------|------|------|
| `--agent` | 是 | Agent 输出目录路径 |
| `--question` / `-q` | 是 | 要问的问题 |
| `--show-sources` | 否 | 显示引用的文档来源 |
| `--config` | 否 | 指定配置文件路径 |

---

## Web 界面

```bash
uvicorn src.web.api.app:app --host 0.0.0.0 --port 8000
```

浏览器打开 `http://localhost:8000`，你会看到 5 个页面：

| 页面 | 做什么 |
|------|--------|
| **配置** | 设置 LLM 和 Embedding，测试连接 |
| **文档** | 拖拽上传 PDF/Word/PPT/Excel 等格式文件 |
| **Agent** | 填写需求，一键生成 Agent |
| **对话** | 和 Agent 聊天，实时看到思考过程和工具调用 |
| **Benchmark** | 对比不同检索策略的评分，选出最优 |

---

## 它是怎么工作的

```
你的文档
    │
    ▼
[格式转换]  →  22 种格式统一转 Markdown（基于 markitdown）
    │
    ▼
[智能分块]  →  按标题 / 滑动窗口 / 语义三种策略切分
    │
    ▼
[向量索引]  →  Embedding + BM25 混合存储
    │
    ▼
[自动评测]  →  4 种检索策略跑分，自动选最优
    │
    ▼
[生成 Agent] →  LLM 设计 Agent 规格：用什么工具、什么推理策略、系统提示词怎么写
    │
    ▼
[运行时引擎] →  工具调用循环 → 多步推理 → 对话记忆 → 输出结果
```

---

## 三种推理模式

同一个问题，Agent 可以用不同的方式解决。模式在创建 Agent 时自动选择，也支持手动指定。

```
Direct 模式                ReAct 模式                   Plan-Execute 模式
─────────────              ────────────                 ─────────────────
用户问 → 调工具 → 回答      用户问                       用户问
简单直给                    │                            │
                           思考 → 行动 → 观察           制定计划：
                            │         │                 ├─ 步骤1：检索文档
                           "我需要  查到结果不符，        ├─ 步骤2：提取关键信息
                           先查文档"  再查一次            └─ 步骤3：计算汇总
                                │         │                 │
                                └─────────┘            逐步执行 → 最终回答
                                     │
                                  满意了，
                                  回答用户
```

| 模式 | 适合 | 怎么工作 |
|------|------|---------|
| `direct` | 简单问答 | 调一次工具，直接回答 |
| `react` | 多步推理 | 思考 → 行动 → 观察，循环直到满意 |
| `plan_execute` | 复杂任务 | 先拆解成步骤清单，再逐步执行 |

---

## 内置工具

Agent 被创建后自带以下工具，LLM 会根据用户问题自动判断该用哪个：

| 工具 | 能干什么 | 举例 |
|------|---------|------|
| `document_retrieval` | 混合检索知识库（向量 + BM25 + 重排序） | "退款政策是什么？" |
| `calculator` | 安全数学计算（AST 解析，不执行任意代码） | "算一下 2 的 10 次方" |
| `text_analyzer` | 提取关键词、统计字数 | "这段话的关键词有哪些？" |

---

## 支持的文档格式

共支持 **22 种** 文件格式：

| 类别 | 格式 |
|------|------|
| **文档** | `.pdf` `.docx` `.doc` `.pptx` `.ppt` `.xlsx` `.xls` `.epub` |
| **文本** | `.txt` `.md` `.html` `.htm` `.csv` `.json` `.xml` |
| **图片** | `.jpg` `.jpeg` `.png` `.gif` `.bmp` |
| **压缩** | `.zip` |
| **音视频** | `.wav` `.mp3` `.mp4` |

---

## Docker 部署

前置条件：安装 [Docker](https://docs.docker.com/get-docker/) 和 [Docker Compose](https://docs.docker.com/compose/install/)。

```bash
# 1. 进入部署目录
cd deploy/docker

# 2. 配置（如果不使用默认 config/active.yaml）
# 编辑 docker-compose.yml，设置环境变量或挂载自定义配置

# 3. 启动
docker-compose up -d

# 4. 查看日志（等待 embedding 模型下载完成）
docker-compose logs -f

# 5. 验证
curl http://localhost:8000/health
```

包含两个服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| `milvus` | 19530 | Milvus 向量数据库 |
| `agent-backend` | 8000 | Agent 后端 API |

---

## 项目结构

```
agent-factory/
├── config/                          # 配置文件
│   ├── active.example.yaml          # 配置示例（可复制为 active.yaml）
│   └── active.yaml                  # 当前生效的配置（不入库）
├── src/
│   ├── cli.py                       # CLI 入口（Click）
│   ├── core/
│   │   ├── orchestrator.py          # 主流程编排
│   │   ├── agent/
│   │   │   ├── generator.py         # Agent 生成器
│   │   │   ├── runtime.py           # 运行时引擎（工具循环 + 推理策略）
│   │   │   └── tools.py             # 工具系统（基类 + 注册器 + 内置工具）
│   │   ├── doc_processor/
│   │   │   ├── converter.py         # 文档转 Markdown（基于 markitdown）
│   │   │   ├── chunker.py           # 三种分块策略
│   │   │   └── pipeline.py          # 文档处理管线
│   │   ├── llm/
│   │   │   ├── client.py            # 统一 LLM 客户端 + 工具调用循环
│   │   │   ├── local_embedder.py    # 离线 Embedding（无需 API）
│   │   │   └── providers.py         # LLM 提供商配置
│   │   ├── retrieval/
│   │   │   └── hybrid_search.py     # 混合检索（向量 + BM25 + 重排序）
│   │   └── vector_store/
│   │       ├── milvus_store.py      # Milvus 向量存储
│   │       └── memory_store.py      # 轻量内存向量存储
│   ├── benchmark/
│   │   ├── metrics.py               # RAG 评测指标
│   │   ├── runner.py                # Benchmark 运行器
│   │   └── testset_generator.py     # 测试集生成
│   └── web/
│       ├── api/app.py               # FastAPI 后端
│       └── frontend/                # React 前端（Ant Design）
├── output/                          # Agent 输出目录
├── tests/                           # 测试
├── pyproject.toml                   # 项目配置
└── README.md
```

---

## 常见问题

<details>
<summary><strong>和 Dify / FastGPT / LangChain 有什么区别？</strong></summary>

这些平台提供的是通用的 RAG + Agent 编排框架，你需要手动设计提示词、选工具、配流程。Agent Factory 更进一步：**你只需要上传文档，它会自动分析内容，生成一个专门为这份文档定制的 Agent**，包括推理策略选择、工具配置和系统提示词，全部自动完成。
</details>

<details>
<summary><strong>生成的 Agent 可以单独部署吗？</strong></summary>

可以。每个生成的 Agent 保存在 `output/` 目录下，包含完整的 `spec.json`（工具、推理策略、提示词）和 `config.yaml`。你可以把它带到任何兼容的 Agent 运行时中运行。
</details>

<details>
<summary><strong>支持多语言文档吗？</strong></summary>

支持。Embedding 模型 `bge-small-zh-v1.5` 对中英文都有良好效果。如果主要处理英文文档，可以切换为 `BAAI/bge-small-en-v1.5`。
</details>

<details>
<summary><strong>上传大型文档会怎样？</strong></summary>

大文档会自动分块，默认 chunk size 为 512 tokens。建议单个文档不超过 100MB。如果文档非常大，可以使用滑动窗口分块策略提高检索质量。
</details>

<details>
<summary><strong>能不能不用 Milvus？</strong></summary>

可以。Agent 默认使用轻量级内存向量存储（`memory_store.py`），适合开发和小规模使用。Milvus 是可选的，适合生产环境和大规模数据。
</details>

<details>
<summary><strong>如何切换 LLM 提供商？</strong></summary>

编辑 `config/active.yaml` 中的 `llm.provider` 字段，改为 `qwen`、`zhipu`、`claude` 等。运行 `agent-factory providers` 查看所有可用选项及其默认配置。
</details>

<details>
<summary><strong>首次运行提示模型下载失败？</strong></summary>

国内用户可能无法直接访问 HuggingFace。设置镜像：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```
然后再运行命令。模型只需下载一次，之后会缓存。
</details>

---

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest
```

欢迎提交 Issue 和 Pull Request！

---

## License

MIT
