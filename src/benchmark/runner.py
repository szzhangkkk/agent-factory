"""Benchmark runner: compares multiple RAG configurations against a test set."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd

from src.benchmark.metrics import (
    LLMJudge,
    EvaluationResult,
    recall_at_k,
    precision_at_k,
    mrr,
)
from src.benchmark.testset_generator import TestSet, TestCase


@dataclass
class PipelineConfig:
    name: str
    chunking_strategy: str = "semantic"
    chunking_kwargs: dict = field(default_factory=dict)
    retrieval_strategy: str = "hybrid"
    retrieval_kwargs: dict = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    config_name: str
    metrics: EvaluationResult
    per_question: list[dict] = field(default_factory=list)


class BenchmarkRunner:
    """Runs a test set against multiple RAG pipeline configurations and compares results."""

    def __init__(self, judge: LLMJudge | None = None):
        self.judge = judge
        self.results: dict[str, BenchmarkResult] = {}

    def run(
        self,
        config: PipelineConfig,
        test_set: TestSet,
        retrieve_fn,
        generate_fn,
        top_k: int = 5,
    ) -> BenchmarkResult:
        """Run a single configuration against the full test set.

        Args:
            config: The pipeline configuration being tested.
            test_set: The test cases to evaluate against.
            retrieve_fn: Callable(question, strategy) -> list[str] (retrieved contexts).
            generate_fn: Callable(question, contexts) -> str (generated answer).
        """
        per_question = []
        total_recall, total_precision, total_mrr = 0.0, 0.0, 0.0
        total_faith, total_rel, total_corr = 0.0, 0.0, 0.0
        total_latency = 0.0
        n = len(test_set.cases)

        for case in test_set.cases:
            start = time.time()

            # Retrieve
            contexts = retrieve_fn(case.question, config.retrieval_strategy)

            # Generate
            answer = generate_fn(case.question, contexts)

            latency = time.time() - start
            total_latency += latency

            # Retrieval metrics
            ctx_texts = [c if isinstance(c, str) else c.content for c in contexts]
            gt_contexts = [case.ground_truth_context] if case.ground_truth_context else []

            r = recall_at_k(ctx_texts, gt_contexts, k=top_k)
            p = precision_at_k(ctx_texts, gt_contexts, k=top_k)
            m = mrr(ctx_texts, gt_contexts)
            total_recall += r
            total_precision += p
            total_mrr += m

            # LLM-as-Judge metrics
            faith, rel, corr = 0.0, 0.0, 0.0
            if self.judge:
                faith = self.judge.faithfulness(answer, ctx_texts)
                rel = self.judge.answer_relevance(case.question, answer)
                corr = self.judge.answer_correctness(answer, case.answer)
            total_faith += faith
            total_rel += rel
            total_corr += corr

            per_question.append({
                "question": case.question,
                "answer": answer,
                "ground_truth": case.answer,
                "recall": r,
                "precision": p,
                "mrr": m,
                "faithfulness": faith,
                "relevance": rel,
                "correctness": corr,
                "latency": latency,
            })

        metrics = EvaluationResult(
            recall=total_recall / n if n else 0,
            precision=total_precision / n if n else 0,
            mrr_score=total_mrr / n if n else 0,
            faithfulness=total_faith / n if n else 0,
            relevance=total_rel / n if n else 0,
            correctness=total_corr / n if n else 0,
            latency=total_latency / n if n else 0,
        )

        result = BenchmarkResult(
            config_name=config.name,
            metrics=metrics,
            per_question=per_question,
        )
        self.results[config.name] = result
        return result

    def compare(self) -> pd.DataFrame:
        """Generate a comparison DataFrame of all benchmark results."""
        rows = []
        for name, result in self.results.items():
            m = result.metrics
            rows.append({
                "config": name,
                "recall": round(m.recall, 3),
                "precision": round(m.precision, 3),
                "mrr": round(m.mrr_score, 3),
                "faithfulness": round(m.faithfulness, 3),
                "relevance": round(m.relevance, 3),
                "correctness": round(m.correctness, 3),
                "overall": round(m.overall_score, 3),
                "avg_latency_s": round(m.latency, 3),
            })
        df = pd.DataFrame(rows)
        return df.sort_values("overall", ascending=False).reset_index(drop=True)

    def best_config(self) -> str:
        """Return the name of the best-performing configuration."""
        if not self.results:
            return ""
        return max(self.results, key=lambda k: self.results[k].metrics.overall_score)
