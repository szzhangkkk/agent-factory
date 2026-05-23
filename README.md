# AgentOS

从文档自动生成具备**工具调用、多步推理、记忆**能力的 AI Agent。

上传文档 → 自动分块向量化 → Benchmark 选出最优检索策略 → LLM 生成一个真正能用工具思考的 Agent。

## 它能做什么

一个普通的 RAG 聊天机器人只能"检索+回答"。AgentOS 生成的 Agent 可以：

- **调用工具** — 文档检索、数学计算、文本分析，LLM 自主决定何时用什么工具
- **多步推理** — ReAct 模式：思考 → 行动 → 观察，逐步解决复杂问题
- **规划执行** — Plan-Execute 模式：先拆解任务为步骤，再逐步执行
- **对话记忆** — 滑动窗口保持上下文连贯

## 快速开始

### 安装

```bash
cd agent-factory
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 配置

编辑 `config/active.yaml`：

```yaml
llm:
  provider: deepseek          # 支持 deepseek / qwen / zhipu / moonshot / openai / claude / ollama
  api_key: your-api-key
  base_url: https://api.deepseek.com/v1
  model: deepseek-chat

embedding:
  provider: local              # 本地离线 embedding，无需 API
  model: BAAI/bge-small-zh-v1.5
```

### CLI 使用

```bash
# 从文档创建 Agent
agent-factory create --docs ./uploads/manual.pdf --name "我的助手" --skip-benchmark

# 与 Agent 对话
agent-factory chat --agent ./output --question "退款政策是什么？"

# 测试连接
agent-factory test-connection

# 查看支持的 LLM 提供商
agent-factory providers
```

### Web 界面

```bash
# 启动后端（会同时提供前端页面）
uvicorn src.web.api.app:app --host 0.0.0.0 --port 8000

# 浏览器打开 http://localhost:8000
```

Web 界面包含 5 个页面：

| 页面 | 功能 |
|------|------|
| 配置 | 设置 LLM 和 Embedding 提供商，测试连接 |
| 文档 | 拖拽上传文档（PDF/Word/PPT/Excel/HTML 等 25+ 格式） |
| Agent | 填写需求，一键生成 Agent |
| 对话 | 与 Agent 对话，实时看到工具调用过程和推理步骤 |
| Benchmark | 查看不同检索策略的评测结果 |

## 架构

```
文档输入
  │
  ▼
DocumentConverter (markitdown, 25+ 格式)
  │
  ▼
Chunker (heading / sliding_window / semantic)
  │
  ▼
VectorStore + BM25 Index
  │
  ▼
BenchmarkRunner ── 4 种策略自动评测，选出最优
  │
  ▼
AgentGenerator ── LLM 设计 Agent 规格、选择工具和推理策略
  │
  ▼
生成的 Agent（agent.py + config.yaml + spec.json）
  │
  ▼
AgentRuntime ── 运行时引擎
  ├── 工具调用循环（ToolRegistry → LLM → 执行 → 反馈）
  ├── 推理策略（direct / react / plan_execute）
  └── 对话记忆（滑动窗口）
```

## 推理策略

| 策略 | 适用场景 | 工作方式 |
|------|---------|---------|
| `direct` | 简单问答 | 单轮工具调用，直接回答 |
| `react` | 多步推理 | Thought → Action → Observation 循环 |
| `plan_execute` | 复杂任务 | 先生成执行计划，再逐步执行 |

## 内置工具

| 工具 | 功能 |
|------|------|
| `document_retrieval` | 混合检索（向量 + BM25 + 重排序） |
| `calculator` | 安全数学计算（AST 解析，无代码注入风险） |
| `text_analyzer` | 关键词提取、字数统计 |

## 支持的 LLM 提供商

DeepSeek / 通义千问 / 智谱 GLM / Moonshot / Claude / OpenAI / Ollama / 自定义

## Docker 部署

```bash
cd deploy/docker
docker-compose up -d
```

包含 Milvus 向量数据库 + Agent 后端两个服务。

## 项目结构

```
src/
├── cli.py                          # CLI 入口
├── core/
│   ├── orchestrator.py             # 主流程编排
│   ├── agent/
│   │   ├── generator.py            # Agent 生成器
│   │   ├── runtime.py              # Agent 运行时（工具循环 + 推理策略）
│   │   └── tools.py                # 工具系统（Tool 基类 + 注册器 + 内置工具）
│   ├── doc_processor/
│   │   ├── converter.py            # 文档转 Markdown
│   │   └── chunker.py              # 分块策略
│   ├── llm/
│   │   ├── client.py               # 统一 LLM 客户端 + 工具调用循环
│   │   ├── local_embedder.py       # 离线 Embedding
│   │   └── providers.py            # LLM 提供商配置
│   ├── retrieval/
│   │   └── hybrid_search.py        # 混合检索（向量 + BM25 + 重排序）
│   └── vector_store/
│       ├── milvus_store.py         # Milvus 向量存储
│       └── memory_store.py         # 轻量内存向量存储
├── benchmark/
│   ├── metrics.py                  # RAG 评测指标
│   ├── runner.py                   # Benchmark 运行器
│   └── testset_generator.py        # 测试集生成
└── web/
    ├── api/app.py                  # FastAPI 后端
    └── frontend/                   # React 前端（Ant Design）
```

## License

MIT
