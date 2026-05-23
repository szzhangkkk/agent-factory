"""Tool system for AgentOS: base class, registry, and built-in tools."""

from __future__ import annotations

import ast
import json
import operator
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolCallRecord:
    """Record of a single tool invocation."""
    tool_name: str
    arguments: dict
    result: str
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
        }


class Tool(ABC):
    """Base class for all tools."""

    name: str = ""
    description: str = ""
    parameters: dict = {}  # JSON Schema for the tool's input

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool and return a string result."""

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_tool(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_all(self) -> list[Tool]:
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict]:
        return [t.to_openai_tool() for t in self._tools.values()]

    def to_anthropic_tools(self) -> list[dict]:
        return [t.to_anthropic_tool() for t in self._tools.values()]

    def execute(self, tool_name: str, arguments: dict) -> ToolCallRecord:
        """Execute a tool by name and return a record."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolCallRecord(
                tool_name=tool_name,
                arguments=arguments,
                result="",
                error=f"工具 '{tool_name}' 不存在",
            )
        try:
            result = tool.execute(**arguments)
            return ToolCallRecord(
                tool_name=tool_name,
                arguments=arguments,
                result=str(result),
            )
        except Exception as e:
            return ToolCallRecord(
                tool_name=tool_name,
                arguments=arguments,
                result="",
                error=f"工具执行失败: {e}",
            )


class DocumentRetrievalTool(Tool):
    """Retrieve relevant document chunks using the hybrid retriever."""

    name = "document_retrieval"
    description = "从知识库中检索与查询相关的文档片段。用于回答需要参考文档的问题。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "检索查询文本",
            },
            "strategy": {
                "type": "string",
                "description": "检索策略",
                "enum": ["vector", "bm25", "hybrid", "hybrid_rerank"],
                "default": "hybrid",
            },
        },
        "required": ["query"],
    }

    def __init__(self, retriever):
        self._retriever = retriever

    def execute(self, query: str, strategy: str = "hybrid", **kwargs) -> str:
        result = self._retriever.retrieve(query, strategy=strategy)
        if not result.chunks:
            return "未找到相关文档。"
        parts = []
        for i, chunk in enumerate(result.chunks, 1):
            parts.append(f"[{i}] (来源: {chunk.source})\n{chunk.content}")
        return "\n\n".join(parts)


class CalculatorTool(Tool):
    """Safe arithmetic calculator."""

    name = "calculator"
    description = "计算数学表达式。支持加减乘除、幂运算、括号。例如: '2 * (3 + 4)'"
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，如 '123 * 456 + 789'",
            },
        },
        "required": ["expression"],
    }

    _OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
    }

    def execute(self, expression: str, **kwargs) -> str:
        try:
            result = self._eval(ast.parse(expression, mode="eval").body)
            return str(result)
        except ZeroDivisionError:
            return "错误：除以零"
        except Exception:
            return f"错误：无法计算表达式 '{expression}'"

    def _eval(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in self._OPS:
            return self._OPS[type(node.op)](self._eval(node.left), self._eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._OPS:
            return self._OPS[type(node.op)](self._eval(node.operand))
        raise ValueError("不支持的表达式")


class TextAnalyzerTool(Tool):
    """Analyze text: extract keywords, count characters, summarize."""

    name = "text_analyzer"
    description = "分析文本：提取关键词、统计字数。"
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "要分析的文本",
            },
            "action": {
                "type": "string",
                "description": "分析类型",
                "enum": ["keywords", "count"],
            },
        },
        "required": ["text", "action"],
    }

    def execute(self, text: str, action: str = "count", **kwargs) -> str:
        if action == "count":
            chars = len(text)
            words = len(text.split())
            return f"字符数: {chars}, 词数: {words}"
        elif action == "keywords":
            import jieba.analyse
            keywords = jieba.analyse.extract_tags(text, topK=10, withWeight=True)
            if not keywords:
                return "未提取到关键词。"
            lines = [f"  {word}: {weight:.3f}" for word, weight in keywords]
            return "关键词:\n" + "\n".join(lines)
        else:
            return f"未知分析类型: {action}"


def create_default_registry(retriever=None) -> ToolRegistry:
    """Create a ToolRegistry with default built-in tools."""
    registry = ToolRegistry()
    if retriever is not None:
        registry.register(DocumentRetrievalTool(retriever))
    registry.register(CalculatorTool())
    registry.register(TextAnalyzerTool())
    return registry
