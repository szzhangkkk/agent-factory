"""FastAPI web application for Agent Factory."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Agent Factory", version="0.1.0", description="Auto-generate RAG agents from documents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DIST_DIR = Path(__file__).parent.parent.parent / "web" / "frontend" / "frontend" / "dist"


class ChatRequest(BaseModel):
    agent_dir: str
    question: str
    show_sources: bool = False


class ToolCallInfo(BaseModel):
    tool_name: str
    arguments: str = "{}"
    result: str = ""
    error: str = ""

class ReasoningStep(BaseModel):
    tool_calls: list[ToolCallInfo] = []
    content: str = ""

class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []
    reasoning_steps: list[ReasoningStep] = []
    iterations: int = 0
    tool_calls_made: int = 0
    retrieval_strategy: str = ""
    retrieval_latency: float = 0.0
    chunks_used: int = 0


class CreateRequest(BaseModel):
    docs_path: str
    agent_name: str = ""
    agent_description: str = ""
    user_requirement: str = ""
    skip_benchmark: bool = False


class CreateResponse(BaseModel):
    agent_name: str
    output_dir: str
    best_config: str
    reasoning_strategy: str = "direct"
    tools: list[dict] = []
    benchmark_scores: dict = {}


class ConfigUpdate(BaseModel):
    llm: dict | None = None
    embedding: dict | None = None
    vector_db: dict | None = None
    chunking: dict | None = None
    retrieval: dict | None = None


class CustomToolRequest(BaseModel):
    name: str
    description: str = ""
    parameters: dict = {"type": "object", "properties": {}}
    url: str
    method: str = "POST"
    headers: dict | None = None


CONFIG_PATH = "config/active.yaml"

_orchestrator = None


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from src.core.orchestrator import Orchestrator
        _orchestrator = Orchestrator(config_path=CONFIG_PATH)
    return _orchestrator


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/providers")
async def list_providers():
    from src.core.llm.providers import list_providers as lp
    return lp()


@app.post("/config")
async def update_config(update: ConfigUpdate):
    global _orchestrator
    config_path = Path(CONFIG_PATH)
    existing = {}
    if config_path.exists():
        with open(config_path) as f:
            existing = yaml.safe_load(f) or {}

    for key in ["llm", "embedding", "vector_db", "chunking", "retrieval"]:
        val = getattr(update, key)
        if val is not None:
            existing[key] = val

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(existing, f, allow_unicode=True)

    _orchestrator = None
    return {"status": "ok", "config": existing}


@app.post("/test-connection")
async def test_connection():
    results = {}

    # Test LLM separately
    try:
        orch = _get_orchestrator()
        resp = orch.llm_client.chat_text(
            messages=[{"role": "user", "content": "Say OK"}], max_tokens=10
        )
        results["llm"] = {"status": "ok", "response": resp.strip()}
    except Exception as e:
        results["llm"] = {"status": "error", "error": str(e)}

    # Test Embedding separately
    try:
        orch2 = _get_orchestrator()
        emb_client = orch2.embedding_client
        if hasattr(emb_client, 'api_key') and not emb_client.api_key and not hasattr(emb_client, '_model'):
            results["embedding"] = {"status": "error", "error": "Embedding API Key 未配置"}
        else:
            emb = emb_client.embed("test")
            results["embedding"] = {"status": "ok", "dimension": len(emb)}
    except Exception as e:
        results["embedding"] = {"status": "error", "error": str(e)}

    return results


@app.post("/agents/create", response_model=CreateResponse)
async def create_agent(request: CreateRequest):
    orch = _get_orchestrator()
    try:
        result = orch.create_agent(
            docs_path=request.docs_path,
            agent_name=request.agent_name,
            agent_description=request.agent_description,
            user_requirement=request.user_requirement,
            skip_benchmark=request.skip_benchmark,
        )
        return CreateResponse(
            agent_name=result.agent.spec.name,
            output_dir=result.output_dir,
            best_config=result.best_config,
            reasoning_strategy=result.agent.spec.reasoning_strategy,
            tools=result.agent.spec.tools,
            benchmark_scores=result.benchmark_scores,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    orch = _get_orchestrator()
    try:
        result = orch.chat(request.agent_dir, request.question)
        # Convert reasoning steps dicts to Pydantic models
        steps = []
        for step in result.get("reasoning_steps", []):
            tool_calls = [
                ToolCallInfo(
                    tool_name=tc.get("tool_name", ""),
                    arguments=str(tc.get("arguments", "{}")),
                    result=tc.get("result", ""),
                    error=tc.get("error", ""),
                )
                for tc in step.get("tool_calls", [])
            ]
            steps.append(ReasoningStep(tool_calls=tool_calls, content=step.get("content", "")))
        return ChatResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            reasoning_steps=steps,
            iterations=result.get("iterations", 0),
            tool_calls_made=result.get("tool_calls_made", 0),
            retrieval_strategy=result.get("retrieval_strategy", ""),
            retrieval_latency=result.get("retrieval_latency", 0.0),
            chunks_used=result.get("chunks_used", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/agents/chat/history")
async def clear_chat_history(agent_dir: str = "./output"):
    history_file = Path(agent_dir) / "chat_history.json"
    if history_file.exists():
        history_file.unlink()
    return {"status": "ok"}


@app.get("/agents/{agent_name}/tools")
async def get_custom_tools(agent_name: str, output_dir: str = "./output"):
    agent_path = Path(output_dir) / agent_name
    config_path = agent_path / "config.yaml"
    if not config_path.exists():
        return {"tools": []}
    config = yaml.safe_load(config_path.read_text())
    return {"tools": config.get("custom_tools", [])}


@app.post("/agents/{agent_name}/tools")
async def add_custom_tool(agent_name: str, tool: CustomToolRequest, output_dir: str = "./output"):
    agent_path = Path(output_dir) / agent_name
    config_path = agent_path / "config.yaml"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Agent 不存在")
    config = yaml.safe_load(config_path.read_text())
    tools = config.setdefault("custom_tools", [])
    tools.append(tool.model_dump(exclude_none=True))
    config_path.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False))
    return {"status": "ok", "tools": tools}


@app.delete("/agents/{agent_name}/tools/{tool_name}")
async def delete_custom_tool(agent_name: str, tool_name: str, output_dir: str = "./output"):
    agent_path = Path(output_dir) / agent_name
    config_path = agent_path / "config.yaml"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Agent 不存在")
    config = yaml.safe_load(config_path.read_text())
    tools = config.get("custom_tools", [])
    config["custom_tools"] = [t for t in tools if t.get("name") != tool_name]
    config_path.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False))
    return {"status": "ok"}


OUTPUT_DIR = Path("./output")


@app.get("/agents/list")
async def list_agents(output_dir: str = "./output"):
    agents = []
    out = Path(output_dir)
    if not out.exists():
        return {"agents": []}
    for d in sorted(out.iterdir()):
        if d.is_dir() and (d / "config.yaml").exists():
            config = yaml.safe_load((d / "config.yaml").read_text())
            agents.append({
                "name": d.name,
                "path": str(d),
                "agent_name": config.get("agent", {}).get("name", d.name),
                "description": config.get("agent", {}).get("description", ""),
                "reasoning_strategy": config.get("agent", {}).get("reasoning_strategy", "direct"),
                "strategy": config.get("retrieval", {}).get("strategy", "hybrid"),
                "has_benchmark": (d / "benchmark_comparison.json").exists(),
                "has_history": (d / "chat_history.json").exists(),
            })
    return {"agents": agents}


@app.delete("/agents/{agent_name}")
async def delete_agent(agent_name: str, output_dir: str = "./output"):
    import shutil
    agent_path = Path(output_dir) / agent_name
    if not agent_path.exists():
        raise HTTPException(status_code=404, detail="Agent 不存在")
    shutil.rmtree(agent_path)
    return {"status": "ok"}


@app.get("/agents/{agent_name}/export")
async def export_agent(agent_name: str, output_dir: str = "./output"):
    import zipfile
    import io
    from fastapi.responses import StreamingResponse

    agent_path = Path(output_dir) / agent_name
    if not agent_path.exists():
        raise HTTPException(status_code=404, detail="Agent 不存在")

    config = yaml.safe_load((agent_path / "config.yaml").read_text())
    spec = json.loads((agent_path / "spec.json").read_text()) if (agent_path / "spec.json").exists() else {}

    agent_name_display = spec.get("name", agent_name)
    system_prompt = config.get("system_prompt", "根据文档回答问题")
    reasoning = config.get("agent", {}).get("reasoning_strategy", "direct")
    strategy = config.get("retrieval", {}).get("strategy", "hybrid")

    project_root = Path(__file__).parent.parent.parent.parent

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Agent data
        for f in ["config.yaml", "spec.json", "chunks.json", "agent.py", "test_cases.json"]:
            fp = agent_path / f
            if fp.exists():
                zf.write(fp, f"data/{f}")

        # 2. Core source code (the real retrieval engine, tools, runtime)
        core_src = project_root / "src" / "core"
        for py_file in core_src.rglob("*.py"):
            rel = py_file.relative_to(project_root / "src")
            zf.write(py_file, f"src/{rel}")

        # 3. __init__.py files
        for init_dir in [core_src, core_src / "agent", core_src / "llm",
                         core_src / "retrieval", core_src / "vector_store"]:
            init = init_dir / "__init__.py"
            if not init.exists():
                zf.writestr(f"src/core/{init_dir.relative_to(core_src)}/__init__.py", "")

        # 4. Standalone server using the real engine
        server_code = f'''"""Standalone Agent Server - exported from Agent Factory"""
"""Uses the real hybrid retrieval engine (vector + BM25 + reranking)."""
import json, os, sys
from pathlib import Path

# Add src to path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yaml

from src.core.llm.client import LLMClient, EmbeddingClient
from src.core.retrieval.hybrid_search import HybridRetriever
from src.core.vector_store.memory_store import MemoryVectorStore
from src.core.agent.tools import create_default_registry
from src.core.agent.runtime import AgentRuntime

app = FastAPI(title="{agent_name_display}")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_DIR = Path(__file__).parent / "data"
config = yaml.safe_load((DATA_DIR / "config.yaml").read_text())

# --- LLM & Embedding (configure via env vars) ---
llm_client = LLMClient({{"provider": "custom", "api_key": os.environ.get("LLM_API_KEY", ""),
    "base_url": os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1"),
    "model": os.environ.get("LLM_MODEL", "deepseek-chat")}})

emb_cfg = config.get("embedding", {{}})
emb_provider = emb_cfg.get("provider", "local")
if emb_provider == "local":
    from src.core.llm.local_embedder import LocalEmbedder
    emb_client = LocalEmbedder(emb_cfg.get("model", "BAAI/bge-small-zh-v1.5"))
else:
    emb_client = EmbeddingClient(emb_cfg)

# --- Retrieval engine (vector + BM25) ---
store = MemoryVectorStore()
retriever = HybridRetriever(vector_store=store, embed_fn=emb_client.embed)

# Load saved chunks into BM25 index
chunks_file = DATA_DIR / "chunks.json"
if chunks_file.exists():
    saved_chunks = json.loads(chunks_file.read_text())
    retriever.build_bm25_index(saved_chunks)

# --- Agent runtime ---
system_prompt = config.get("system_prompt", "根据文档回答问题")
reasoning = config.get("agent", {{}}).get("reasoning_strategy", "direct")
custom_tools = config.get("custom_tools", [])
registry = create_default_registry(retriever=retriever, custom_tools=custom_tools)
runtime = AgentRuntime(llm_client=llm_client, tool_registry=registry,
    system_prompt=system_prompt, reasoning_strategy=reasoning)

# Load conversation memory
history_file = DATA_DIR / "chat_history.json"
if history_file.exists():
    try:
        runtime.history = json.loads(history_file.read_text())[-20:]
    except Exception:
        pass

retrieval_strategy = config.get("retrieval", {{}}).get("strategy", "hybrid")

class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
async def chat(req: ChatRequest):
    result = retriever.retrieve(req.question, strategy=retrieval_strategy)
    contexts = [c.content for c in result.chunks]
    context_block = "\\n\\n---\\n\\n".join(contexts) if contexts else ""
    sources = list({{c.source for c in result.chunks}})

    agent_result = runtime.run(req.question, context=context_block)

    history_file.write_text(json.dumps(runtime.history, ensure_ascii=False, indent=2))

    return {{
        "answer": agent_result.content,
        "sources": agent_result.sources or sources,
        "reasoning_steps": [s.to_dict() for s in agent_result.steps],
        "iterations": agent_result.iterations,
        "tool_calls_made": agent_result.total_tool_calls,
        "retrieval_strategy": retrieval_strategy,
        "retrieval_latency": result.latency,
        "chunks_used": len(contexts),
    }}

@app.delete("/history")
async def clear_history():
    runtime.history.clear()
    if history_file.exists():
        history_file.unlink()
    return {{"status": "ok"}}

@app.get("/health")
async def health():
    return {{"status": "ok", "agent": "{agent_name_display}", "reasoning": reasoning}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
'''
        zf.writestr("server.py", server_code)

        # 5. requirements.txt
        zf.writestr("requirements.txt", "\n".join([
            "fastapi>=0.110.0", "uvicorn>=0.29.0", "openai>=1.0.0",
            "anthropic>=0.30.0", "pyyaml>=6.0", "numpy>=1.24.0",
            "jieba>=0.42.1", "rank-bm25>=0.2.2", "sentence-transformers>=2.0.0",
        ]))

        # 6. Dockerfile
        zf.writestr("Dockerfile", f"""FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "server.py"]
""")

        # 7. docker-compose.yml
        zf.writestr("docker-compose.yml", f"""version: "3.8"
services:
  agent:
    build: .
    ports:
      - "8080:8080"
    environment:
      - LLM_API_KEY=${{LLM_API_KEY}}
      - LLM_BASE_URL=${{LLM_BASE_URL:-https://api.deepseek.com/v1}}
      - LLM_MODEL=${{LLM_MODEL:-deepseek-chat}}
    restart: unless-stopped
""")

        # 8. README
        zf.writestr("README.md", f"""# {agent_name_display}

独立部署的 AI Agent — 从 Agent Factory 导出。

包含完整的混合检索引擎（向量检索 + BM25）、多步推理（{reasoning}）和工具调用能力。

## 快速启动

```bash
pip install -r requirements.txt

# 设置环境变量
export LLM_API_KEY=your-api-key
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_MODEL=deepseek-chat

python server.py
```

## Docker 部署

```bash
# 一键启动
LLM_API_KEY=your-key docker compose up -d

# 或手动构建
docker build -t {agent_name} .
docker run -p 8080:8080 -e LLM_API_KEY=your-key {agent_name}
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 发送消息 `{{"question": "..."}}` |
| DELETE | `/history` | 清除对话记忆 |
| GET | `/health` | 健康检查 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | LLM API Key | (必填) |
| `LLM_BASE_URL` | LLM API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` |
""")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=agent-{agent_name}.zip"},
    )


@app.get("/agents/benchmark")
async def get_benchmark(agent_dir: str = "./output"):
    agent_path = Path(agent_dir)
    comparison_file = agent_path / "benchmark_comparison.json"
    if not comparison_file.exists():
        return {"data": [], "message": "Benchmark 数据不存在，请先创建 Agent"}
    data = json.loads(comparison_file.read_text())
    return {"data": data}


UPLOAD_BASE = Path("./uploads").resolve()


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), target_dir: str = Form("./uploads")):
    dest = (UPLOAD_BASE / target_dir).resolve()
    if not str(dest).startswith(str(UPLOAD_BASE)):
        raise HTTPException(status_code=400, detail="无效的上传目录")
    dest.mkdir(parents=True, exist_ok=True)

    filename = Path(file.filename).name
    if not filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="无效的文件名")
    file_path = dest / filename
    if not str(file_path.resolve()).startswith(str(dest)):
        raise HTTPException(status_code=400, detail="无效的文件路径")

    content = await file.read()
    file_path.write_bytes(content)
    return {"status": "ok", "path": str(file_path)}


# Serve frontend static files
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(DIST_DIR / "index.html"))
