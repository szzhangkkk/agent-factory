"""FastAPI web application for AgentOS."""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="AgentOS", version="0.1.0", description="Auto-generate RAG agents from documents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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


CONFIG_PATH = "config/active.yaml"


def _get_orchestrator():
    from src.core.orchestrator import Orchestrator
    return Orchestrator(config_path=CONFIG_PATH)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/providers")
async def list_providers():
    from src.core.llm.providers import list_providers as lp
    return lp()


@app.post("/config")
async def update_config(update: ConfigUpdate):
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


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), target_dir: str = Form("./uploads")):
    dest = Path(target_dir)
    dest.mkdir(parents=True, exist_ok=True)
    file_path = dest / file.filename
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
