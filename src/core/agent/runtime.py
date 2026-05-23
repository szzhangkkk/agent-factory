"""Agent runtime: the core loop with memory, tools, and reasoning strategies."""

from __future__ import annotations

import json

from src.core.llm.client import LLMClient, AgentResponse
from src.core.agent.tools import ToolRegistry

REACT_SYSTEM_SUFFIX = """

## 推理模式

你必须严格按照以下格式进行推理：

Thought: [分析当前情况，思考下一步应该做什么]
Action: [选择要使用的工具和参数]
Observation: [工具返回的结果]

重复以上步骤直到你有足够的信息来回答用户。

当你准备给出最终回答时，使用：
Thought: [总结你收集到的信息]
Final Answer: [完整的最终回答]
"""

PLAN_EXECUTE_SYSTEM_SUFFIX = """

## 任务执行模式

对于复杂问题，你需要分两步工作：

**第一步：制定计划**
分析用户问题，输出一个 JSON 格式的执行计划：
```json
{"plan": ["步骤1描述", "步骤2描述", ...]}
```

**第二步：逐步执行**
我会逐步告诉你执行每个步骤，你可以使用工具来完成每个步骤。
每步执行后，简要总结结果。

**第三步：综合回答**
所有步骤完成后，基于收集到的信息给出完整的最终回答。
"""


class AgentRuntime:
    """Core agent loop with memory, tools, and reasoning strategies."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        system_prompt: str,
        reasoning_strategy: str = "direct",
        max_iterations: int = 10,
    ):
        self.llm = llm_client
        self.tools = tool_registry
        self.system_prompt = system_prompt
        self.strategy = reasoning_strategy
        self.max_iterations = max_iterations
        self.history: list[dict] = []

    def run(self, user_message: str, context: str = "") -> AgentResponse:
        """Main entry point. Dispatches to strategy-specific handler."""
        if self.strategy == "react":
            return self._run_react(user_message, context)
        elif self.strategy == "plan_execute":
            return self._run_plan_execute(user_message, context)
        else:
            return self._run_direct(user_message, context)

    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history for multi-turn memory."""
        self.history.append({"role": role, "content": content})

    def _build_messages(self, user_message: str, context: str = "") -> list[dict]:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.history[-20:])
        if context:
            user_message = f"参考文档：\n{context}\n\n用户问题：{user_message}"
        messages.append({"role": "user", "content": user_message})
        return messages

    def _run_direct(self, user_message: str, context: str) -> AgentResponse:
        """Direct strategy: single-shot with optional tool calls."""
        messages = self._build_messages(user_message, context)
        openai_tools = self.tools.to_openai_tools()

        result = self.llm.chat_with_tools(
            messages=messages,
            tools=openai_tools,
            tool_registry=self.tools,
            max_iterations=self.max_iterations,
        )

        self.add_to_history("user", user_message)
        self.add_to_history("assistant", result.content)
        return result

    def _run_react(self, user_message: str, context: str) -> AgentResponse:
        """ReAct strategy: Thought -> Action -> Observation loop."""
        react_prompt = self.system_prompt + REACT_SYSTEM_SUFFIX
        messages = [{"role": "system", "content": react_prompt}]
        messages.extend(self.history[-20:])

        full_question = user_message
        if context:
            full_question = f"参考文档：\n{context}\n\n用户问题：{user_message}"
        messages.append({"role": "user", "content": full_question})

        openai_tools = self.tools.to_openai_tools()

        result = self.llm.chat_with_tools(
            messages=messages,
            tools=openai_tools,
            tool_registry=self.tools,
            max_iterations=self.max_iterations,
        )

        # Strip ReAct markers from final answer
        result.content = self._strip_react_markers(result.content)

        self.add_to_history("user", user_message)
        self.add_to_history("assistant", result.content)
        return result

    @staticmethod
    def _strip_react_markers(text: str) -> str:
        """Remove Thought:/Action:/Observation:/Final Answer: prefixes from output."""
        import re
        # If there's a "Final Answer:", only keep what comes after it
        fa_match = re.search(r'Final Answer:\s*(.*)', text, re.DOTALL)
        if fa_match:
            return fa_match.group(1).strip()
        # Otherwise strip leading "Thought: ..." lines
        text = re.sub(r'^(Thought:.*?\n\n)', '', text, flags=re.DOTALL)
        return text.strip()

    def _run_plan_execute(self, user_message: str, context: str) -> AgentResponse:
        """Plan-then-execute: create a plan, execute steps, synthesize answer."""
        from src.core.llm.client import ToolCallStep

        plan_prompt = self.system_prompt + PLAN_EXECUTE_SYSTEM_SUFFIX
        messages = [{"role": "system", "content": plan_prompt}]
        messages.extend(self.history[-20:])

        full_question = user_message
        if context:
            full_question = f"参考文档：\n{context}\n\n用户问题：{user_message}"

        # Phase 1: Generate plan
        messages.append({"role": "user", "content": full_question})
        plan_resp = self.llm.chat_text(messages=messages, max_tokens=1024)

        steps: list[ToolCallStep] = []
        total_calls = 0
        sources: set[str] = set()

        # Extract plan from response
        plan_steps = self._extract_plan(plan_resp)

        if not plan_steps:
            # If no plan extracted, fall back to direct with tools
            messages.append({"role": "assistant", "content": plan_resp})
            messages.append({"role": "user", "content": "请直接使用工具来回答我的问题。"})
            openai_tools = self.tools.to_openai_tools()
            result = self.llm.chat_with_tools(
                messages=messages,
                tools=openai_tools,
                tool_registry=self.tools,
                max_iterations=self.max_iterations,
            )
            self.add_to_history("user", user_message)
            self.add_to_history("assistant", result.content)
            return result

        # Phase 2: Execute each step
        step_results = []
        openai_tools = self.tools.to_openai_tools()

        for i, step_desc in enumerate(plan_steps):
            messages.append({
                "role": "assistant",
                "content": f"正在执行计划第 {i+1} 步: {step_desc}",
            })
            messages.append({
                "role": "user",
                "content": f"请执行第 {i+1} 步: {step_desc}。如果需要使用工具，请使用工具完成。",
            })

            step_result = self.llm.chat_with_tools(
                messages=messages,
                tools=openai_tools,
                tool_registry=self.tools,
                max_iterations=3,
            )
            steps.extend(step_result.steps)
            total_calls += step_result.total_tool_calls
            sources.update(step_result.sources)
            step_results.append(step_result.content)

        # Phase 3: Synthesize final answer
        synthesis_prompt = (
            f"基于以上执行结果，请对用户的问题给出完整的最终回答。\n\n"
            f"用户问题：{full_question}\n\n"
            f"执行结果：\n" + "\n".join(
                f"步骤{j+1}: {r}" for j, r in enumerate(step_results)
            )
        )
        messages.append({"role": "user", "content": synthesis_prompt})
        final_content = self.llm.chat_text(messages=messages)

        self.add_to_history("user", user_message)
        self.add_to_history("assistant", final_content)

        return AgentResponse(
            content=final_content,
            steps=steps,
            iterations=len(plan_steps) + 1,
            total_tool_calls=total_calls,
            sources=list(sources),
        )

    def _extract_plan(self, text: str) -> list[str]:
        """Extract a JSON plan from LLM response text."""
        # Try to find JSON plan in the response
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if "plan" in data and isinstance(data["plan"], list):
                    return [str(s) for s in data["plan"]]
            except json.JSONDecodeError:
                pass

        # Try to find JSON without code fences
        json_match = re.search(r'\{"plan"\s*:\s*\[.*?\]\}', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "plan" in data and isinstance(data["plan"], list):
                    return [str(s) for s in data["plan"]]
            except json.JSONDecodeError:
                pass

        # Fallback: look for numbered list
        lines = text.strip().split("\n")
        plan_steps = []
        for line in lines:
            line = line.strip()
            if line and line[0].isdigit() and (line[1] in ".、)" or line[:2] in ["1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."]):
                # Remove leading number and punctuation
                import re
                step = re.sub(r'^\d+[.、)\s]+', '', line)
                if step:
                    plan_steps.append(step)
        return plan_steps
