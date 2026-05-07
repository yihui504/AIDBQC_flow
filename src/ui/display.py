from __future__ import annotations

import logging
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.events import EventBus, TestEvent, TestEventType

logger = logging.getLogger(__name__)
console = Console()

_FOCUS_COLORS = {
    "understanding": "cyan",
    "generation": "blue",
    "execution": "yellow",
    "verification": "magenta",
    "reporting": "green",
}

_SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "dim",
}


class AgentDisplay:
    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._current_round: int = 0
        self._current_focus: str = ""
        self._defects_count: int = 0
        self._issues_count: int = 0
        self._token_usage: int = 0
        self._max_rounds: int = 0
        self._session_id: str = ""
        self._tool_calls_in_round: int = 0
        self._round_start_time: float = 0.0
        self._recent_tools: list[str] = []
        self._paused: bool = False
        self._flash_fallback: bool = False

        self._bus.on(TestEventType.ROUND_STARTED, self._on_round_started)
        self._bus.on(TestEventType.TOOL_INVOKED, self._on_tool_invoked)
        self._bus.on(TestEventType.TOOL_COMPLETED, self._on_tool_completed)
        self._bus.on(TestEventType.DEFECT_DISCOVERED, self._on_defect_discovered)
        self._bus.on(TestEventType.DEFECT_VERIFIED, self._on_defect_verified)
        self._bus.on(TestEventType.ROUND_COMPLETED, self._on_round_completed)
        self._bus.on(TestEventType.RECOVERY_ATTEMPTED, self._on_recovery_attempted)

    def set_session_info(self, session_id: str, max_rounds: int) -> None:
        self._session_id = session_id
        self._max_rounds = max_rounds

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def _on_round_started(self, event: TestEvent) -> None:
        self._current_round = event.data.get("round", self._current_round)
        self._current_focus = event.data.get("focus", self._current_focus)
        self._tool_calls_in_round = 0
        self._recent_tools = []
        self._round_start_time = time.time()
        color = _FOCUS_COLORS.get(self._current_focus, "white")
        console.print(f"\n[bold {color}]{'=' * 60}[/bold {color}]")
        console.print(f"[bold {color}]  Round {self._current_round}/{self._max_rounds}  |  Focus: {self._current_focus.upper()}[/bold {color}]")
        console.print(f"[bold {color}]{'=' * 60}[/bold {color}]")

    def _on_tool_invoked(self, event: TestEvent) -> None:
        tool_name = event.data.get("tool", "unknown")
        self._tool_calls_in_round += 1
        self._recent_tools.append(tool_name)
        if len(self._recent_tools) > 8:
            self._recent_tools = self._recent_tools[-8:]
        args_summary = event.data.get("args_summary", "")
        if args_summary:
            args_summary = f"  {args_summary[:60]}"
        console.print(f"    [dim][*] {tool_name}{args_summary}[/dim]")

    def _on_tool_completed(self, event: TestEvent) -> None:
        success = event.data.get("success", True)
        duration_ms = event.data.get("duration_ms", 0)
        if not success:
            error = event.data.get("error", "unknown error")
            console.print(f"    [red][X] Tool failed ({duration_ms:.0f}ms): {error[:80]}[/red]")

    def _on_defect_discovered(self, event: TestEvent) -> None:
        self._defects_count += 1
        severity = event.data.get("severity", "medium")
        title = event.data.get("title", "Unknown defect")
        defect_id = event.data.get("defect_id", "")
        color = _SEVERITY_COLORS.get(severity, "yellow")
        console.print(f"\n    [{color}][BUG] [{severity.upper()}] {title}[/{color}]")
        console.print(f"    [dim]   ID: {defect_id}[/dim]")

    def _on_defect_verified(self, event: TestEvent) -> None:
        self._issues_count += 1
        defect_id = event.data.get("defect_id", "")
        passed = event.data.get("review_passed", False)
        if passed:
            console.print(f"    [green][+] Defect verified: {defect_id}[/green]")
        else:
            console.print(f"    [dim][-] Defect rejected: {defect_id} (false positive)[/dim]")

    def _on_round_completed(self, event: TestEvent) -> None:
        defects_found = event.data.get("defects", 0)
        flash = event.data.get("flash_fallback", False)
        self._flash_fallback = flash
        status = "[green][OK][/green]"
        extra = " [yellow](flash fallback)[/yellow]" if flash else ""
        console.print(f"\n  {status} Round {self._current_round} completed: {defects_found} defects{extra}")

    def _on_recovery_attempted(self, event: TestEvent) -> None:
        action = event.data.get("recovery_action", "unknown")
        error = event.data.get("error", "")
        console.print(f"  [yellow][RECOVER] {action}: {error[:60]}[/yellow]")

    def print_banner(self, target_db: str, target_version: str, model: str) -> None:
        banner = Text()
        banner.append("AIDBQC v6.0", style="bold blue")
        banner.append("  |  ", style="dim")
        banner.append(f"Target: {target_db} {target_version}", style="cyan")
        banner.append("  |  ", style="dim")
        banner.append(f"Model: {model}", style="green")
        console.print(Panel(banner, border_style="blue", padding=(0, 2)))

    def print_db_status(self, db_type: str, connected: bool, info: str = "") -> None:
        if connected:
            console.print(f"  [green][+] {db_type} connected[/green] {info}")
        else:
            console.print(f"  [red][-] {db_type} connection failed[/red] {info}")
            console.print("  [yellow]  Continuing in offline mode[/yellow]")

    def print_summary(self, session_id: str, rounds: int, defects: int,
                      issues: int, verified: int, tokens: int) -> None:
        table = Table(title="Run Summary", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Session ID", session_id)
        table.add_row("Rounds Completed", str(rounds))
        table.add_row("Defects Found", str(defects))
        table.add_row("Issues Generated", str(issues))
        table.add_row("Verified Issues", str(verified))
        table.add_row("Token Usage", f"{tokens:,}")
        console.print(table)

    def print_error(self, message: str) -> None:
        console.print(f"[bold red]ERROR:[/bold red] {message}")

    def print_info(self, message: str) -> None:
        console.print(f"[dim][i] {message}[/dim]")

    def print_paused(self) -> None:
        console.print("\n[bold yellow][PAUSED] - Type 'r' or 'resume' to continue[/bold yellow]")

    def print_resumed(self) -> None:
        console.print("[bold green][>] Resumed[/bold green]")

    def build_status_line(self) -> str:
        elapsed = time.time() - self._round_start_time if self._round_start_time else 0
        pause_indicator = " [PAUSED]" if self._paused else ""
        flash_indicator = " [FLASH]" if self._flash_fallback else ""
        return (
            f"R{self._current_round}/{self._max_rounds} | "
            f"{self._current_focus.upper()}{pause_indicator}{flash_indicator} | "
            f"tools:{self._tool_calls_in_round} | "
            f"defects:{self._defects_count} | "
            f"issues:{self._issues_count} | "
            f"{elapsed:.0f}s"
        )
