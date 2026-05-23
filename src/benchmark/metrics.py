"""RAG evaluation metrics."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.core.llm.client import LLMClient


@dataclass
class MetricResult:
    name: str
    value: float
    details: dict = field(default_factory=dict)


def _tokenize(text: str) -> set[str]:
    """Extract meaningful tokens from text (Chinese chars + English words)."""
    text = text.lower()
    chinese = set(re.findall(r"[一-鿿]", text))
    english = set(re.findall(r"[a-z]+", text))
    return chinese | english


def _token_overlap_score(text_a: str, text_b: str) -> float:
    """Calculate token-based overlap between two texts (0-1)."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = tokens_a & tokens_b
    return len(overlap) / min(len(tokens_a), len(tokens_b))


def recall_at_k(retrieved_contexts: list[str], ground_truth_contexts: list[str], k: int = 5) -> float:
    """What fraction of relevant documents appear in top-K results."""
    if not ground_truth_contexts:
        return 1.0
    retrieved = retrieved_contexts[:k]
    hits = 0
    for gt in ground_truth_contexts:
        if any(_token_overlap_score(gt, r) >= 0.5 for r in retrieved):
            hits += 1
    return hits / len(ground_truth_contexts)


def precision_at_k(retrieved_contexts: list[str], ground_truth_contexts: list[str], k: int = 5) -> float:
    """What fraction of top-K results are relevant."""
    if not retrieved_contexts:
        return 0.0
    retrieved = retrieved_contexts[:k]
    hits = 0
    for r in retrieved:
        if any(_token_overlap_score(gt, r) >= 0.5 for gt in ground_truth_contexts):
            hits += 1
    return hits / min(k, len(retrieved_contexts))


def mrr(retrieved_contexts: list[str], ground_truth_contexts: list[str]) -> float:
    """Mean Reciprocal Rank: 1/rank of first relevant result."""
    for i, ctx in enumerate(retrieved_contexts):
        for gt in ground_truth_contexts:
            if _token_overlap_score(gt, ctx) >= 0.5:
                return 1.0 / (i + 1)
    return 0.0


class LLMJudge:
    """Uses an LLM to evaluate answer quality (faithfulness, relevance, correctness)."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def faithfulness(self, answer: str, contexts: list[str]) -> float:
        """Is the answer supported by the retrieved context? (0-1)"""
        context_text = "\n---\n".join(contexts[:5])
        prompt = f"""你是一个严格的评估专家。请判断以下回答是否忠实于给定的上下文信息。

上下文：
{context_text}

回答：
{answer}

评估标准：
- 1.0: 回答完全基于上下文，没有编造信息
- 0.8: 回答大部分基于上下文，有极少量推测
- 0.6: 回答部分基于上下文，有一些编造
- 0.4: 回答有较多编造内容
- 0.2: 回答基本不是基于上下文
- 0.0: 回答完全编造

请只输出一个 0 到 1 之间的数字（精确到小数点后一位）："""
        return self._get_score(prompt)

    def answer_relevance(self, question: str, answer: str) -> float:
        """Does the answer actually address the question? (0-1)"""
        prompt = f"""你是一个严格的评估专家。请判断以下回答是否真正回答了用户的问题。

问题：{question}

回答：{answer}

评估标准：
- 1.0: 完美回答了问题
- 0.8: 基本回答了问题，有小的偏差
- 0.6: 部分回答了问题
- 0.4: 回答和问题相关但没有正面回答
- 0.2: 回答和问题关系不大
- 0.0: 完全没有回答问题

请只输出一个 0 到 1 之间的数字（精确到小数点后一位）："""
        return self._get_score(prompt)

    def answer_correctness(self, answer: str, ground_truth: str) -> float:
        """How well does the answer match the ground truth? (0-1)"""
        prompt = f"""你是一个严格的评估专家。请判断以下回答与标准答案的吻合程度。

标准答案：{ground_truth}

待评估回答：{answer}

评估标准：
- 1.0: 与标准答案完全一致
- 0.8: 核心信息一致，表述略有不同
- 0.6: 包含了部分关键信息
- 0.4: 有少量正确信息
- 0.2: 基本不一致
- 0.0: 完全错误

请只输出一个 0 到 1 之间的数字（精确到小数点后一位）："""
        return self._get_score(prompt)

    def _get_score(self, prompt: str) -> float:
        try:
            response = self.llm.chat_text(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10,
            )
            score_str = response.strip()
            import re
            match = re.search(r"(\d+\.?\d*)", score_str)
            if match:
                return min(1.0, max(0.0, float(match.group(1))))
            return 0.0
        except Exception:
            return 0.0


@dataclass
class EvaluationResult:
    recall: float = 0.0
    precision: float = 0.0
    mrr_score: float = 0.0
    faithfulness: float = 0.0
    relevance: float = 0.0
    correctness: float = 0.0
    latency: float = 0.0
    details: dict = field(default_factory=dict)

    @property
    def overall_score(self) -> float:
        weights = {
            "recall": 0.2,
            "precision": 0.15,
            "mrr": 0.15,
            "faithfulness": 0.2,
            "relevance": 0.15,
            "correctness": 0.15,
        }
        return (
            self.recall * weights["recall"]
            + self.precision * weights["precision"]
            + self.mrr_score * weights["mrr"]
            + self.faithfulness * weights["faithfulness"]
            + self.relevance * weights["relevance"]
            + self.correctness * weights["correctness"]
        )
