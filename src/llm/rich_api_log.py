"""Rich-formatted logging for LLM API calls."""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@lru_cache(maxsize=1)
def _console() -> Console:
    return Console(stderr=True, highlight=False)


@contextmanager
def llm_api_request_spinner(provider: str, model: str, prompt_char_count: int) -> Iterator[None]:
    """Shows a Rich spinner while the LLM API request is in flight."""
    console = _console()
    label = Text.assemble(
        ("● ", "bold cyan"),
        (provider, "bold cyan"),
        (" · ", "dim"),
        (model, "bold white"),
        (" · ", "dim"),
        (f"{prompt_char_count:,} chars", "dim"),
    )
    with console.status(label, spinner="dots12", spinner_style="cyan"):
        yield


def _fmt_count(value: Optional[int]) -> str:
    if value is None:
        return "[dim]n/a[/dim]"
    return f"[cyan]{value:,}[/cyan]"


def log_llm_api_success(
    provider: str,
    model: str,
    duration_s: float,
    *,
    input_char_count: int,
    output_char_count: int,
    input_token_count: Optional[int] = None,
    output_token_count: Optional[int] = None,
) -> None:
    console = _console()
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", justify="right")
    grid.add_column()
    grid.add_row("Provider", provider)
    grid.add_row("Model", model)
    grid.add_row("Duration", f"[bold green]{duration_s:.2f}s[/bold green]")
    grid.add_row("Input chars", f"[blue]{input_char_count:,}[/blue]")
    grid.add_row("Output chars", f"[blue]{output_char_count:,}[/blue]")
    grid.add_row("Input tokens", _fmt_count(input_token_count))
    grid.add_row("Output tokens", _fmt_count(output_token_count))
    console.print(
        Panel(
            grid,
            title="[bold green]Response received[/bold green]",
            border_style="green",
            padding=(0, 1),
        )
    )


def log_llm_orchestration_attempt(attempt: int, max_attempts: int) -> None:
    """Logs which retry attempt the runner is about to make, before calling the handler."""
    if max_attempts <= 1:
        return
    _console().print(
        f"  [dim]Orchestration · attempt[/dim] [bold]{attempt}[/bold][dim]/{max_attempts}[/dim]"
    )


def log_llm_api_failure(
    provider: str,
    model: str,
    exc: BaseException,
    detail: Optional[str] = None,
) -> None:
    console = _console()
    body = f"[red bold]{type(exc).__name__}[/red bold]: {exc}"
    if detail:
        body += f"\n\n[dim]{detail}[/dim]"
    console.print(
        Panel(
            body,
            title="[bold red]LLM API failure[/bold red]",
            subtitle=f"{provider} · {model}",
            border_style="red",
            padding=(0, 1),
        )
    )
