"""Auto-generate test sets from documents using LLM."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from src.core.llm.client import LLMClient


@dataclass
class TestCase:
    question: str
    answer: str
    ground_truth_context: str
    question_type: str  # fact, reasoning, cross_section, summary
    difficulty: str  # easy, medium, hard


@dataclass
class TestSet:
    cases: list[TestCase]
    source_doc: str
    metadata: dict = field(default_factory=dict)


GENERATION_PROMPT = """你是一个专业的测试集生成专家。根据以下文档内容，生成 {n} 个高质量的问答对。

要求：
1. 问题类型要多样化：事实查询、推理分析、跨段落综合、概括总结
2. 难度分布：easy 40%, medium 40%, hard 20%
3. 答案必须能从文档中直接找到依据
4. 标注答案对应的原文段落

文档内容：
---
{document}
---

请严格按以下 JSON 格式输出（直接输出 JSON 数组，不要包含其他文字）：
[
  {{
    "question": "用户可能会问的问题",
    "answer": "基于文档的标准答案",
    "ground_truth_context": "文档中支撑答案的原文段落",
    "question_type": "fact|reasoning|cross_section|summary",
    "difficulty": "easy|medium|hard"
  }}
]
"""


class TestSetGenerator:
    """Generates QA test cases from document chunks using LLM."""

    def __init__(self, llm_client: LLMClient, questions_per_doc: int = 5):
        self.llm_client = llm_client
        self.questions_per_doc = questions_per_doc

    def generate_from_chunks(self, chunks: list[dict], max_chunks: int = 20) -> TestSet:
        """Generate test cases from a list of document chunks.

        Args:
            chunks: List of dicts with 'content' and 'source' keys.
            max_chunks: Max chunks to use (avoids overwhelming the LLM).
        """
        selected = chunks[:max_chunks]
        all_cases: list[TestCase] = []
        errors: list[str] = []

        for chunk in selected:
            try:
                cases = self._generate_for_chunk(chunk["content"])
                all_cases.extend(cases)
            except Exception as e:
                errors.append(str(e))

        return TestSet(
            cases=all_cases,
            source_doc=selected[0].get("source", "unknown") if selected else "unknown",
            metadata={"total_chunks_used": len(selected), "errors": errors},
        )

    def generate_from_text(self, text: str) -> TestSet:
        cases = self._generate_for_chunk(text)
        return TestSet(cases=cases, source_doc="direct_input")

    def _generate_for_chunk(self, content: str) -> list[TestCase]:
        prompt = GENERATION_PROMPT.format(
            n=self.questions_per_doc,
            document=content[:6000],
        )
        response = self.llm_client.chat_text(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=4096,
        )
        return self._parse_response(response)

    def _parse_response(self, response: str) -> list[TestCase]:
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        start = text.find("[")
        end = text.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError(f"Failed to parse LLM response as JSON: {text[:200]}")

        data = json.loads(text[start:end])
        cases = []
        for item in data:
            cases.append(TestCase(
                question=item["question"],
                answer=item["answer"],
                ground_truth_context=item.get("ground_truth_context", ""),
                question_type=item.get("question_type", "fact"),
                difficulty=item.get("difficulty", "medium"),
            ))
        return cases
