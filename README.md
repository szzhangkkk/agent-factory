# AgentOS

<p align="center">
  <strong>上传文档，自动生成一个能思考、会用工具的 AI Agent</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.10-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/format-25%2B-orange" alt="Supported Formats">
</p>

---

### 这是什么？

普通的 RAG 聊天机器人只能"搜一段文档 + 让 LLM 总结一下"。**AgentOS 更进一步**：它自动分析你的文档，生成一个带工具、会多步推理、有记忆的 AI Agent。

打个比方：

> **RAG 聊天机器人** = 图书管理员，你问什么它找什么
>
> **AgentOS 生成的 Agent** = 一个会翻书、会按计算器、会做文本分析，还会先想清楚再动手的助手

---

## 快速体验

```bash
# 1. 克隆
git clone git@github.com:szzhangkkk/agent-factory.git
cd agent-factory

# 2. 安装
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. 配置 LLM
# 编辑 config/active.yaml，填入你的 API key（支持 DeepSeek / 千问 / 智谱 / OpenAI / Claude 等）

# 4. 从文档生成 Agent
agent-factory create --docs ./uploads/manual.pdf --name "客服助手" --skip-benchmark

# 5. 和它对话
agent-factory chat --agent ./output --question "退款政策是什么？"
```

---

## 安装

### 环境要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.10 |
| pip | 最新即可 |

### 步骤

```bash
git clone git@github.com:szzhangkkk/agent-factory.git
cd agent-factory
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
```

### 验证安装

```bash
agent-factory test-connection   # 测试 LLM 连接是否正常
agent-factory providers         # 查看支持的 LLM 提供商
```

---

## 配置

编辑 `config/active.yaml`，最少只需要配两样：

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

支持的 LLM 提供商：**DeepSeek / 通义千问 / 智谱 GLM / Moonshot / Claude / OpenAI / Ollama / 自定义**

---

## 使用方式

### CLI

```bash
# 从文档创建 Agent
agent-factory create --docs ./uploads/manual.pdf --name "客服助手"

# 跳过 benchmark 评测（更快）
agent-factory create --docs ./uploads/manual.pdf --name "客服助手" --skip-benchmark

# 与生成的 Agent 对话
agent-factory chat --agent ./output --question "退款流程需要几天？"
```

### Web 界面

```bash
uvicorn src.web.api.app:app --host 0.0.0.0 --port 8000
```

浏览器打开 `http://localhost:8000`，你会看到 5 个页面：

| 页面 | 做什么 |
|------|--------|
| **配置** | 设置 LLM 和 Embedding，测试连接 |
| **文档** | 拖拽上传 PDF/Word/PPT/Excel 等 25+ 格式文件 |
| **Agent** | 填写需求，一键生成 Agent |
| **对话** | 和 Agent 聊天，实时看到它的思考过程和工具调用 |
| **Benchmark** | 对比不同检索策略的评分，选出最优 |

---

## 它是怎么工作的

```
你的文档
    │
    ▼
[格式转换]  →  PDF/Word/PPT/Excel/HTML…统一转 Markdown（25+ 格式）
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
Direct 模式                    ReAct 模式                   Plan-Execute 模式
─────────────                  ────────────                 ─────────────────
用户问 → 调工具 → 回答          用户问                       用户问
简单直给                        │                            │
                               思考 → 行动 → 观察           制定计划：
                                │         │                 ├─ 步骤1：检索文档
                                "我需要先查文档"              ├─ 步骤2：提取关键信息
                                     │                      └─ 步骤3：计算汇总
                                     ▼                         │
                                查到结果不符，再查一次           逐步执行 → 最终回答
                                     │
                                     ▼
                                满意了，回答用户
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
| `calculator` | 安全数学计算（AST 解析，不会执行任意代码） | "算一下 2 的 10 次方" |
| `text_analyzer` | 提取关键词、统计字数 | "这段话的关键词有哪些？" |

---

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest
```

---

## Docker 部署

```bash
cd deploy/docker
docker-compose up -d
```

包含两个服务：Milvus 向量数据库 + Agent 后端。

---

## 项目结构

```
agent-factory/
├── config/                          # 配置文件
│   └── active.yaml                  # 当前使用的配置
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
│   │   │   └── chunker.py           # 三种分块策略
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
├── output_agent/                    # 示例 Agent
│   ├── agent.py                     #   可独立运行的 Agent 脚本
│   ├── config.yaml                  #   Agent 配置
│   └── spec.json                    #   Agent 规格（工具、推理策略、提示词）
└── tests/
```

---

## License

MIT
