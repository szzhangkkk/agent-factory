"""Main orchestrator: ties all components together."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.core.doc_processor.converter import DocumentConverter
from src.core.doc_processor.chunker import Chunk, get_chunker
from src.core.vector_store.milvus_store import MilvusStore
from src.core.vector_store.memory_store import MemoryVectorStore
from src.core.retrieval.hybrid_search import HybridRetriever
from src.core.llm.client import LLMClient, EmbeddingClient
from src.core.llm.local_embedder import LocalEmbedder
from src.core.agent.generator import AgentGenerator, GeneratedAgent
from src.core.agent.tools import create_default_registry
from src.core.agent.runtime import AgentRuntime
from src.benchmark.testset_generator import TestSetGenerator
from src.benchmark.runner import BenchmarkRunner, PipelineConfig
from src.benchmark.metrics import LLMJudge


@dataclass
class CreateResult:
    agent: GeneratedAgent
    benchmark_report: str
    best_config: str
    benchmark_scores: dict
    output_dir: str


class Orchestrator:
    """Main entry point: orchestrates document processing, benchmarking, and agent generation."""

    def __init__(self, config_path: str = ""):
        self.config = self._load_config(config_path)
        self.llm_client = LLMClient(self.config.get("llm", {}))
        self.embedding_client = self._create_embedding_client()

    def _load_config(self, path: str) -> dict:
        if not path:
            config_dir = Path(__file__).parent.parent.parent / "config"
            active = config_dir / "active.yaml"
            default = config_dir / "default.yaml"
            path = str(active if active.exists() else default)
        p = Path(path)
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f)
        return {}

    def _create_embedding_client(self):
        """Create embedding client. Supports 'local' provider for offline use."""
        emb_cfg = self.config.get("embedding", {})
        provider = emb_cfg.get("provider", "")
        if provider == "local":
            model = emb_cfg.get("model", "BAAI/bge-small-zh-v1.5")
            print(f"  Using local embedding model: {model}")
            return LocalEmbedder(model_name=model)
        return EmbeddingClient(emb_cfg)

    def _create_vector_store(self):
        """Create vector store. Tries Milvus first, falls back to in-memory store."""
        vector_cfg = self.config.get("vector_db", {})
        if hasattr(self.embedding_client, "dimension"):
            dimension = self.embedding_client.dimension
        else:
            dimension = self.config.get("embedding", {}).get("dimension", 1024)
        collection = vector_cfg.get("collection", "agent_docs")
        store_type = vector_cfg.get("type", "memory")

        if store_type == "milvus":
            try:
                store = MilvusStore(
                    collection_name=collection,
                    dimension=dimension,
                    use_lite=False,
                    host=vector_cfg.get("host", "localhost"),
                    port=vector_cfg.get("port", 19530),
                )
                store.connect()
                print("  Using Milvus server")
                return store
            except Exception as e:
                print(f"  Milvus server unavailable ({e}), falling back to memory store")

        if store_type == "milvus_lite":
            try:
                store = MilvusStore(
                    collection_name=collection,
                    dimension=dimension,
                    use_lite=True,
                    lite_path=vector_cfg.get("path", "./data/vectordb"),
                )
                store.connect()
                print("  Using Milvus Lite")
                return store
            except Exception as e:
                print(f"  Milvus Lite unavailable ({e}), falling back to memory store")

        persist_path = vector_cfg.get("path", "./data/vectordb")
        print(f"  Using in-memory vector store (persist: {persist_path})")
        return MemoryVectorStore(
            collection_name=collection,
            dimension=dimension,
            persist_path=persist_path,
        )

    def create_agent(
        self,
        docs_path: str,
        agent_name: str = "",
        agent_description: str = "",
        user_requirement: str = "",
        output_dir: str = "./output",
        skip_benchmark: bool = False,
    ) -> CreateResult:
        print("[1/6] Converting documents...")
        converter = DocumentConverter()
        try:
            if Path(docs_path).is_dir():
                documents = converter.convert_directory(docs_path)
            else:
                documents = [converter.convert_file(docs_path)]
        except Exception as e:
            raise ValueError(f"文档转换失败: {e}")

        if not documents:
            raise ValueError(f"未找到可转换的文档，请检查路径: {docs_path}")

        print(f"  Converted {len(documents)} document(s)")

        print("[2/6] Chunking documents...")
        chunking_cfg = self.config.get("chunking", {})
        chunker = get_chunker(
            chunking_cfg.get("strategy", "semantic"),
            max_chunk_size=chunking_cfg.get("max_chunk_size", 1024),
            overlap=chunking_cfg.get("overlap", 128),
        )
        all_chunks: list[Chunk] = []
        for doc in documents:
            chunks = chunker.chunk(doc.markdown, metadata=doc.metadata)
            all_chunks.extend(chunks)

        if not all_chunks:
            raise ValueError("文档分块后内容为空，请检查文档是否包含可读取的文字内容")

        print(f"  Generated {len(all_chunks)} chunks")

        print("[3/6] Building vector store + BM25 index...")
        store = self._create_vector_store()
        store.create_collection()

        # Embed and insert
        print("  Embedding chunks...")
        texts = [c.content for c in all_chunks]
        embeddings = self.embedding_client.embed_batch(texts)
        store.insert_chunks(all_chunks, embeddings)

        # Build retriever
        retriever = HybridRetriever(
            vector_store=store,
            embed_fn=self.embedding_client.embed,
            top_k=self.config.get("retrieval", {}).get("top_k", 5),
            vector_weight=self.config.get("retrieval", {}).get("vector_weight", 0.7),
            bm25_weight=self.config.get("retrieval", {}).get("bm25_weight", 0.3),
        )
        retriever.build_bm25_index([
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "source": c.source,
                "heading_path": c.heading_path,
                "metadata": c.metadata,
            }
            for c in all_chunks
        ])

        best_config = "hybrid"
        benchmark_scores = {}
        benchmark_comparison = []

        if not skip_benchmark:
            print("[4/6] Running benchmark...")
            best_config, benchmark_scores, benchmark_comparison = self._run_benchmark(all_chunks, retriever, store)
        else:
            print("[4/6] Skipping benchmark (--skip-benchmark)")

        print("[5/6] Generating agent...")
        doc_summary = "\n\n".join(
            f"## {doc.metadata.get('filename', 'doc')}\n{doc.markdown[:1000]}"
            for doc in documents[:5]
        )
        if not user_requirement:
            user_requirement = agent_description or "根据文档内容回答用户问题"

        generator = AgentGenerator(self.llm_client)
        agent = generator.generate(
            doc_summary=doc_summary,
            user_requirement=user_requirement,
            agent_name=agent_name,
            agent_description=agent_description,
            retrieval_config={
                "strategy": best_config,
                "top_k": self.config.get("retrieval", {}).get("top_k", 5),
            },
        )

        # Update retriever strategy
        retriever.top_k = self.config.get("retrieval", {}).get("top_k", 5)

        print("[6/6] Saving agent artifacts...")
        base = Path(output_dir)
        base.mkdir(parents=True, exist_ok=True)
        agent_dir_name = agent.spec.name.replace(" ", "_").lower() if agent.spec.name else "agent"
        out = base / agent_dir_name
        out.mkdir(parents=True, exist_ok=True)

        (out / "agent.py").write_text(agent.code)
        (out / "config.yaml").write_text(yaml.dump(agent.config, allow_unicode=True, default_flow_style=False))
        (out / "test_cases.json").write_text(json.dumps(agent.test_cases, ensure_ascii=False, indent=2))
        (out / "spec.json").write_text(json.dumps({
            "name": agent.spec.name,
            "description": agent.spec.description,
            "reasoning_strategy": agent.spec.reasoning_strategy,
            "output_format": agent.spec.output_format,
            "tools": agent.spec.tools,
            "system_prompt": agent.spec.system_prompt,
        }, ensure_ascii=False, indent=2))
        # Save chunks for BM25 rebuild on chat()
        (out / "chunks.json").write_text(json.dumps([
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "source": c.source,
                "heading_path": c.heading_path,
                "metadata": c.metadata,
            }
            for c in all_chunks
        ], ensure_ascii=False, indent=2))

        benchmark_report = ""
        if benchmark_scores:
            benchmark_report = json.dumps(benchmark_scores, ensure_ascii=False, indent=2)
            (out / "benchmark_report.json").write_text(benchmark_report)
        if benchmark_comparison:
            (out / "benchmark_comparison.json").write_text(
                json.dumps(benchmark_comparison, ensure_ascii=False, indent=2)
            )

        print(f"\n✓ Agent '{agent.spec.name}' generated successfully!")
        print(f"  Output directory: {output_dir}")
        print(f"  Best retrieval strategy: {best_config}")

        return CreateResult(
            agent=agent,
            benchmark_report=benchmark_report,
            best_config=best_config,
            benchmark_scores=benchmark_scores,
            output_dir=str(out),
        )

    def _run_benchmark(
        self, chunks: list[Chunk], retriever: HybridRetriever, store
    ) -> tuple[str, dict]:
        print("  Generating test set...")
        test_gen = TestSetGenerator(self.llm_client, questions_per_doc=3)
        test_set = test_gen.generate_from_chunks([
            {"content": c.content, "source": c.source}
            for c in chunks[:30]
        ])
        print(f"  Generated {len(test_set.cases)} test cases")

        judge = LLMJudge(self.llm_client)
        runner = BenchmarkRunner(judge=judge)

        strategies = ["vector", "bm25", "hybrid", "hybrid_rerank"]
        for strategy in strategies:
            print(f"  Testing strategy: {strategy}...")
            config = PipelineConfig(name=strategy, retrieval_strategy=strategy)

            def retrieve_fn(q, s=strategy):
                result = retriever.retrieve(q, strategy=s)
                return result.chunks

            def generate_fn(q, contexts):
                ctx_texts = [c.content if hasattr(c, "content") else c for c in contexts]
                ctx_block = "\n\n".join(ctx_texts[:5])
                messages = [
                    {"role": "system", "content": "根据提供的参考文档回答用户问题。如果文档中没有相关信息，请如实说明。"},
                    {"role": "user", "content": f"参考文档：\n{ctx_block}\n\n问题：{q}"},
                ]
                return self.llm_client.chat_text(messages=messages)

            runner.run(config, test_set, retrieve_fn, generate_fn)

        report_df = runner.compare()
        print("\n  Benchmark Results:")
        print(report_df.to_string(index=False))

        best = runner.best_config()
        best_result = runner.results[best]
        scores = {
            "best_config": best,
            "overall_score": round(best_result.metrics.overall_score, 3),
            "recall": round(best_result.metrics.recall, 3),
            "precision": round(best_result.metrics.precision, 3),
            "mrr": round(best_result.metrics.mrr_score, 3),
            "faithfulness": round(best_result.metrics.faithfulness, 3),
            "relevance": round(best_result.metrics.relevance, 3),
            "correctness": round(best_result.metrics.correctness, 3),
        }

        # Save full per-strategy comparison
        comparison = []
        for name, result in runner.results.items():
            m = result.metrics
            comparison.append({
                "config": name,
                "recall": round(m.recall, 3),
                "precision": round(m.precision, 3),
                "mrr": round(m.mrr_score, 3),
                "faithfulness": round(m.faithfulness, 3),
                "relevance": round(m.relevance, 3),
                "overall": round(m.overall_score, 3),
                "latency": round(m.latency, 3),
            })
        comparison.sort(key=lambda x: x["overall"], reverse=True)

        return best, scores, comparison

    def chat(self, agent_dir: str, question: str) -> dict:
        """Chat with a generated agent using AgentRuntime, with persistent memory."""
        agent_path = Path(agent_dir)

        config_path = agent_path / "config.yaml"
        with open(config_path) as f:
            agent_config = yaml.safe_load(f)

        store = self._create_vector_store()

        retriever = HybridRetriever(
            vector_store=store,
            embed_fn=self.embedding_client.embed,
        )

        # Rebuild BM25 index from saved chunks
        chunks_file = agent_path / "chunks.json"
        if chunks_file.exists():
            saved_chunks = json.loads(chunks_file.read_text())
            retriever.build_bm25_index(saved_chunks)

        retrieval_strategy = agent_config.get("retrieval", {}).get("strategy", "hybrid")
        result = retriever.retrieve(question, strategy=retrieval_strategy)

        contexts = [c.content for c in result.chunks]
        context_block = "\n\n---\n\n".join(contexts) if contexts else ""
        sources = list({c.source for c in result.chunks})

        system_prompt = agent_config.get("system_prompt", "根据文档回答问题")
        reasoning_strategy = agent_config.get("agent", {}).get("reasoning_strategy", "direct")

        # Create tool registry and agent runtime
        custom_tools = agent_config.get("custom_tools", [])
        registry = create_default_registry(retriever=retriever, custom_tools=custom_tools)
        runtime = AgentRuntime(
            llm_client=self.llm_client,
            tool_registry=registry,
            system_prompt=system_prompt,
            reasoning_strategy=reasoning_strategy,
        )

        # Load conversation history from disk
        history_file = agent_path / "chat_history.json"
        if history_file.exists():
            try:
                saved = json.loads(history_file.read_text())
                runtime.history = saved[-20:]  # Keep last 20 turns
            except (json.JSONDecodeError, KeyError):
                pass

        agent_result = runtime.run(question, context=context_block)

        # Save updated history
        history_file.write_text(json.dumps(runtime.history, ensure_ascii=False, indent=2))

        return {
            "answer": agent_result.content,
            "sources": agent_result.sources or sources,
            "reasoning_steps": [s.to_dict() for s in agent_result.steps],
            "iterations": agent_result.iterations,
            "tool_calls_made": agent_result.total_tool_calls,
            "retrieval_strategy": retrieval_strategy,
            "retrieval_latency": result.latency,
            "chunks_used": len(contexts),
        }
