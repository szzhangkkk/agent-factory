"""CLI entry point for agent-factory."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """AgentOS - Auto-generate RAG agents from documents."""
    pass


@main.command()
@click.option("--docs", required=True, help="Path to documents (file or directory)")
@click.option("--name", default="", help="Agent name")
@click.option("--description", default="", help="Agent description")
@click.option("--requirement", default="", help="Specific requirements for the agent")
@click.option("--output", default="./output", help="Output directory")
@click.option("--config", "config_path", default="", help="Config file path")
@click.option("--skip-benchmark", is_flag=True, help="Skip benchmark evaluation")
def create(docs, name, description, requirement, output, config_path, skip_benchmark):
    """Create a new agent from documents."""
    from src.core.orchestrator import Orchestrator

    console.print(Panel("[bold blue]AgentOS[/bold blue] - Creating Agent", expand=False))

    if not Path(docs).exists():
        console.print(f"[red]Error: Path not found: {docs}[/red]")
        sys.exit(1)

    orchestrator = Orchestrator(config_path=config_path)

    result = orchestrator.create_agent(
        docs_path=docs,
        agent_name=name,
        agent_description=description,
        user_requirement=requirement,
        output_dir=output,
        skip_benchmark=skip_benchmark,
    )

    console.print()
    table = Table(title="Agent Created Successfully")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Name", result.agent.spec.name)
    table.add_row("Output", result.output_dir)
    table.add_row("Best Strategy", result.best_config)
    if result.benchmark_scores:
        table.add_row("Overall Score", str(result.benchmark_scores.get("overall_score", "N/A")))
        table.add_row("Recall", str(result.benchmark_scores.get("recall", "N/A")))
        table.add_row("Faithfulness", str(result.benchmark_scores.get("faithfulness", "N/A")))
    console.print(table)

    console.print(f"\n[bold green]✓ Agent ready![/bold green] Test it with:")
    console.print(f"  agent-factory chat --agent {output} --question 'your question'")


@main.command()
@click.option("--agent", required=True, help="Path to agent output directory")
@click.option("--question", "-q", required=True, help="Question to ask")
@click.option("--config", "config_path", default="", help="Config file path")
@click.option("--show-sources", is_flag=True, help="Show source documents")
def chat(agent, question, config_path, show_sources):
    """Chat with a generated agent."""
    from src.core.orchestrator import Orchestrator

    orchestrator = Orchestrator(config_path=config_path)
    result = orchestrator.chat(agent, question)

    console.print(Panel(result["answer"], title="Answer", border_style="green"))

    if show_sources:
        console.print(f"\n[dim]Sources: {', '.join(result['sources'])}[/dim]")
        console.print(f"[dim]Strategy: {result['retrieval_strategy']} | "
                       f"Latency: {result['retrieval_latency']:.2f}s | "
                       f"Chunks: {result['chunks_used']}[/dim]")


@main.command()
@click.option("--config", "config_path", default="", help="Config file path")
def providers(config_path):
    """List available LLM providers."""
    from src.core.llm.providers import list_providers

    table = Table(title="Available LLM Providers")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Default Models")
    table.add_column("API URL")

    for p in list_providers():
        table.add_row(
            p["id"],
            p["name"],
            ", ".join(p.get("models", [])[:2]),
            p.get("base_url", ""),
        )
    console.print(table)


@main.command()
@click.option("--config", "config_path", default="", help="Config file path")
def test_connection(config_path):
    """Test LLM and embedding connections."""
    from src.core.orchestrator import Orchestrator

    orchestrator = Orchestrator(config_path=config_path)

    console.print("Testing LLM connection...")
    try:
        response = orchestrator.llm_client.chat_text(
            messages=[{"role": "user", "content": "Say 'OK' in one word."}],
            max_tokens=10,
        )
        console.print(f"  [green]✓ LLM OK[/green] - Response: {response.strip()}")
    except Exception as e:
        console.print(f"  [red]✗ LLM failed[/red] - {e}")

    console.print("Testing Embedding connection...")
    try:
        emb = orchestrator.embedding_client.embed("test")
        console.print(f"  [green]✓ Embedding OK[/green] - Dimension: {len(emb)}")
    except Exception as e:
        console.print(f"  [red]✗ Embedding failed[/red] - {e}")


if __name__ == "__main__":
    main()
