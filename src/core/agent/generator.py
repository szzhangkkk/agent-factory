"""Agent auto-generation: from documents and requirements to a runnable agent."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from src.core.llm.client import LLMClient


@dataclass
class AgentSpec:
    name: str
    description: str
    system_prompt: str
    tools: list[dict]
    retrieval_config: dict
    reasoning_strategy: str  # direct, react, plan_execute
    output_format: str = "text"
    metadata: dict = field(default_factory=dict)


@dataclass
class GeneratedAgent:
    spec: AgentSpec
    code: str
    config: dict
    test_cases: list[dict] = field(default_factory=list)


ANALYSIS_PROMPT = """你是一个 AI Agent 架构师。根据以下文档内容和用户需求，设计一个 Agent 的完整规格。

文档内容摘要：
---
{doc_summary}
---

用户需求：
---
{user_requirement}
---

可用工具列表：
- document_retrieval: 从知识库中检索相关文档
- calculator: 数学计算（加减乘除、幂运算）
- text_analyzer: 文本分析（提取关键词、统计字数）

请输出以下 JSON 格式的设计方案：
{{
    "system_prompt": "完整的 system prompt，包含角色定义、能力范围、回答规范、限制条件",
    "reasoning_strategy": "direct|react|plan_execute",
    "tools_needed": ["document_retrieval", "calculator", "text_analyzer"],
    "output_format": "text|json|markdown",
    "key_constraints": ["约束条件1", "约束条件2"],
    "suggested_name": "Agent 建议名称",
    "suggested_description": "Agent 建议描述"
}}

推理策略说明：
- direct: 适合简单问答，单轮工具调用即可解决
- react: 适合需要多步推理的复杂问题，LLM 会逐步思考、行动、观察
- plan_execute: 适合需要拆解为多个子任务的问题，先制定计划再逐步执行

要求：
1. system_prompt 要详细且专业，包含明确的角色定义和行为规范
2. 根据任务复杂度选择最合适的推理策略
3. tools_needed 只包含真正需要的工具
"""


class AgentGenerator:
    """Generates a complete agent specification from documents and requirements."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate(
        self,
        doc_summary: str,
        user_requirement: str,
        agent_name: str = "",
        agent_description: str = "",
        retrieval_config: dict | None = None,
    ) -> GeneratedAgent:
        spec = self._analyze_and_design(doc_summary, user_requirement)

        if agent_name:
            spec.name = agent_name
        if agent_description:
            spec.description = agent_description

        code = self._generate_code(spec)
        config = self._generate_config(spec, retrieval_config or {})
        test_cases = self._generate_test_cases(spec)

        return GeneratedAgent(
            spec=spec,
            code=code,
            config=config,
            test_cases=test_cases,
        )

    def _analyze_and_design(self, doc_summary: str, user_requirement: str) -> AgentSpec:
        prompt = ANALYSIS_PROMPT.format(
            doc_summary=doc_summary[:4000],
            user_requirement=user_requirement,
        )
        response = self.llm.chat_text(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4096,
        )

        design = self._parse_json(response)

        # Build tools list from LLM's chosen tools
        tool_descriptions = {
            "document_retrieval": "从知识库中检索相关文档",
            "calculator": "数学计算",
            "text_analyzer": "文本分析",
        }
        tools = []
        for t in design.get("tools_needed", ["document_retrieval"]):
            tools.append({
                "type": t,
                "description": tool_descriptions.get(t, f"{t} tool"),
            })

        return AgentSpec(
            name=design.get("suggested_name", "Generated Agent"),
            description=design.get("suggested_description", ""),
            system_prompt=design.get("system_prompt", ""),
            tools=tools,
            retrieval_config={},
            reasoning_strategy=design.get("reasoning_strategy", "direct"),
            output_format=design.get("output_format", "text"),
            metadata={"key_constraints": design.get("key_constraints", [])},
        )

    def _generate_code(self, spec: AgentSpec) -> str:
        sep = "\n\n---\n\n"
        return f'''"""Auto-generated Agent: {spec.name}"""

from src.core.llm.client import LLMClient
from src.core.retrieval.hybrid_search import HybridRetriever
from src.core.agent.tools import create_default_registry
from src.core.agent.runtime import AgentRuntime


SYSTEM_PROMPT = """{spec.system_prompt}"""


class {self._to_class_name(spec.name)}:
    """{spec.description}"""

    def __init__(self, llm_client: LLMClient, retriever: HybridRetriever):
        self.retriever = retriever
        self.retrieval_strategy = "{spec.retrieval_config.get('strategy', 'hybrid')}"

        # Create tool registry with built-in tools
        self.tool_registry = create_default_registry(retriever=retriever)

        # Create agent runtime with configured reasoning strategy
        self.runtime = AgentRuntime(
            llm_client=llm_client,
            tool_registry=self.tool_registry,
            system_prompt=SYSTEM_PROMPT,
            reasoning_strategy="{spec.reasoning_strategy}",
            max_iterations=10,
        )

    def chat(self, user_message: str) -> str:
        # Retrieve relevant context
        retrieval_result = self.retriever.retrieve(
            user_message, strategy=self.retrieval_strategy
        )
        contexts = [c.content for c in retrieval_result.chunks]
        context_block = {repr(sep)}.join(contexts) if contexts else ""

        # Run agent with tool access
        result = self.runtime.run(user_message, context=context_block)
        return result.content

    def chat_with_details(self, user_message: str) -> dict:
        """Chat with full details: answer, reasoning steps, tool calls."""
        retrieval_result = self.retriever.retrieve(
            user_message, strategy=self.retrieval_strategy
        )
        contexts = [c.content for c in retrieval_result.chunks]
        context_block = {repr(sep)}.join(contexts) if contexts else ""
        sources = list({{c.source for c in retrieval_result.chunks}})

        result = self.runtime.run(user_message, context=context_block)
        return {{
            "answer": result.content,
            "sources": result.sources or sources,
            "reasoning_steps": [s.to_dict() for s in result.steps],
            "iterations": result.iterations,
            "tool_calls_made": result.total_tool_calls,
            "retrieval_strategy": self.retrieval_strategy,
            "retrieval_latency": retrieval_result.latency,
        }}
'''

    def _generate_config(self, spec: AgentSpec, retrieval_config: dict) -> dict:
        return {
            "agent": {
                "name": spec.name,
                "description": spec.description,
                "reasoning_strategy": spec.reasoning_strategy,
                "output_format": spec.output_format,
            },
            "tools": [{"type": t["type"], "description": t["description"]} for t in spec.tools],
            "retrieval": retrieval_config or {
                "strategy": "hybrid",
                "top_k": 5,
                "vector_weight": 0.7,
                "bm25_weight": 0.3,
                "rerank": True,
            },
            "system_prompt": spec.system_prompt,
        }

    def _generate_test_cases(self, spec: AgentSpec) -> list[dict]:
        prompt = f"""根据以下 Agent 设计，生成 5 个测试用例。

Agent 名称：{spec.name}
Agent 描述：{spec.description}
推理策略：{spec.reasoning_strategy}
可用工具：{", ".join(t["type"] for t in spec.tools)}
System Prompt：{spec.system_prompt[:1000]}

请输出 JSON 数组：
[
  {{
    "input": "测试输入",
    "expected_behavior": "期望的行为描述",
    "test_type": "happy_path|edge_case|adversarial",
    "expected_tools": ["预期会使用的工具"]
  }}
]"""

        try:
            response = self.llm.chat_text(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048,
            )
            return self._parse_json(response)
        except Exception:
            return []

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > 0:
            return json.loads(text[start:end])
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > 0:
            return json.loads(text[start:end])
        return {}

    @staticmethod
    def _to_class_name(name: str) -> str:
        return "".join(word.capitalize() for word in name.replace("-", " ").replace("_", " ").split()) + "Agent"
