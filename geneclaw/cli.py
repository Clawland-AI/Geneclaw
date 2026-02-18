"""CLI subcommand group for geneclaw (GEP v0).

Registered under ``nanobot geneclaw …`` via the main Typer app.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

geneclaw_app = typer.Typer(
    name="geneclaw",
    help="Geneclaw Evolution Protocol (GEP) commands",
)

console = Console()


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


@geneclaw_app.command("doctor")
def doctor() -> None:
    """Run health checks on geneclaw configuration (read-only)."""
    from nanobot.config.loader import load_config
    from geneclaw.doctor import run_checks, get_next_steps

    config = load_config()
    ws = config.workspace_path

    console.print("[bold]Geneclaw Doctor[/bold]\n")

    results = run_checks(ws, config)

    for r in results:
        if r.severity == "ok":
            icon = "[green]\u2713[/green]"
        elif r.severity == "warn":
            icon = "[yellow]\u26a0[/yellow]"
        else:
            icon = "[red]\u2717[/red]"
        console.print(f"  {icon} [bold]{r.name}[/bold]: {r.message}")

    # Summary
    errors = [r for r in results if r.severity == "error"]
    warns = [r for r in results if r.severity == "warn"]
    oks = [r for r in results if r.severity == "ok"]
    console.print(
        f"\n  Summary: [green]{len(oks)} ok[/green], "
        f"[yellow]{len(warns)} warnings[/yellow], "
        f"[red]{len(errors)} errors[/red]"
    )

    # Next steps
    steps = get_next_steps(config)
    console.print("\n[bold]Suggested next steps:[/bold]\n")
    for step in steps:
        if step.startswith("#"):
            console.print(f"  [dim]{step}[/dim]")
        else:
            console.print(f"  [cyan]{step}[/cyan]")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@geneclaw_app.command("status")
def status() -> None:
    """Show geneclaw status: enabled, runs count, last run time."""
    from nanobot.config.loader import load_config
    from geneclaw.recorder import RunRecorder

    config = load_config()
    gc = config.geneclaw
    ws = config.workspace_path

    console.print("[bold]Geneclaw Status[/bold]\n")
    console.print(f"  Enabled:           {'[green]yes[/green]' if gc.enabled else '[red]no[/red]'}")
    console.print(f"  Redact:            {gc.redact_enabled}")
    console.print(f"  Allow apply:       {gc.allow_apply_default}")
    console.print(f"  Max patch lines:   {gc.max_patch_lines}")

    sessions = RunRecorder.list_sessions(ws)
    console.print(f"  Sessions recorded: {len(sessions)}")

    runs_dir = ws / "geneclaw" / "runs"
    if runs_dir.exists():
        jsonl_files = sorted(runs_dir.rglob("*.jsonl"))
        if jsonl_files:
            last = jsonl_files[-1]
            mtime = datetime.fromtimestamp(last.stat().st_mtime, tz=timezone.utc)
            console.print(f"  Last run log:      {mtime.isoformat()}")
        else:
            console.print("  Last run log:      [dim]none[/dim]")
    else:
        console.print("  Last run log:      [dim]none[/dim]")


# ---------------------------------------------------------------------------
# evolve
# ---------------------------------------------------------------------------


@geneclaw_app.command("evolve")
def evolve(
    since: float = typer.Option(24.0, "--since", help="Look back N hours"),
    max_events: int = typer.Option(500, "--max-events", help="Max events to analyse"),
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Dry-run (default) or apply"),
    output: str = typer.Option(None, "--output", "-o", help="Write proposal JSON to file"),
) -> None:
    """Generate an evolution proposal from recent run events."""
    import asyncio
    from nanobot.config.loader import load_config

    config = load_config()
    gc = config.geneclaw

    if not gc.enabled:
        console.print("[yellow]Geneclaw is disabled in config. Set geneclaw.enabled=true.[/yellow]")
        raise typer.Exit(1)

    # Determine apply mode
    apply_mode = not dry_run
    if apply_mode and not gc.allow_apply_default:
        console.print("[yellow]Apply mode requested but allow_apply_default=false in config.[/yellow]")
        console.print("Pass --apply explicitly and set allow_apply_default=true, or use --dry-run.")
        raise typer.Exit(1)

    provider = None
    try:
        from nanobot.cli.commands import _make_provider
        provider = _make_provider(config)
    except (SystemExit, Exception) as _provider_err:
        if not dry_run:
            console.print("[red]No LLM provider available and apply mode requires one.[/red]")
            raise typer.Exit(1)
        console.print("[yellow]No LLM provider configured — running heuristic-only mode.[/yellow]")

    async def _run() -> None:
        from geneclaw.evolver import generate_proposal, diagnose_events as _diag
        from geneclaw.apply import apply_unified_diff
        from geneclaw.event_store import EventStore
        from geneclaw.models import EvoEvent, EvolutionProposal
        from geneclaw.recorder import RunRecorder
        import uuid

        store = EventStore(config.workspace_path, redact=gc.redact_enabled)

        console.print("[dim]Analysing recent events...[/dim]")

        if provider is not None:
            proposal = await generate_proposal(
                workspace=config.workspace_path,
                provider=provider,
                model=config.agents.defaults.model,
                since_hours=since,
                max_events=max_events,
            )
        else:
            all_events: list[dict] = []
            for sk in RunRecorder.list_sessions(config.workspace_path):
                rec = RunRecorder(workspace=config.workspace_path, session_key=sk, redact=True)
                all_events.extend(rec.iter_events(max_events=max_events))
            diagnosis = _diag(all_events)
            proposal = EvolutionProposal(
                id=str(uuid.uuid4()),
                title="heuristic-only",
                objective=f"Heuristic diagnosis (no LLM): {diagnosis['summary']}",
                evidence=[diagnosis["summary"]],
                risk_level="low",
            )

        # Display proposal
        console.print(f"\n[bold]Evolution Proposal: {proposal.title}[/bold]")
        console.print(f"  ID:         {proposal.id}")
        console.print(f"  Objective:  {proposal.objective}")
        console.print(f"  Risk:       {proposal.risk_level}")
        console.print(f"  Files:      {', '.join(proposal.files_touched) or '(none)'}")
        if proposal.evidence:
            console.print(f"  Evidence:   {'; '.join(proposal.evidence[:3])}")
        diff_line_count = len(proposal.unified_diff.splitlines()) if proposal.unified_diff else 0
        if diff_line_count:
            console.print(f"  Diff lines: {diff_line_count}")

        # Record evolve_generated event
        evolve_event = EvoEvent(
            event_type="evolve_generated",
            proposal_id=proposal.id,
            risk_level=proposal.risk_level,
            files_touched=proposal.files_touched,
            diff_lines=diff_line_count,
            tests_to_run=proposal.tests_to_run,
            result="ok",
        )
        store.record(evolve_event)

        # Write proposal to file
        proposal_json = proposal.model_dump_json(indent=2)
        if output:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(proposal_json, encoding="utf-8")
            console.print(f"\n[green]Proposal written to {out_path}[/green]")
        else:
            proposals_dir = config.workspace_path / "geneclaw" / "proposals"
            proposals_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            out_path = proposals_dir / f"proposal_{ts}.json"
            out_path.write_text(proposal_json, encoding="utf-8")
            console.print(f"\n[green]Proposal written to {out_path}[/green]")

        if apply_mode and proposal.unified_diff:
            console.print("\n[bold]Applying proposal...[/bold]")

            # Record apply_attempted
            attempt_event = EvoEvent(
                event_type="apply_attempted",
                proposal_id=proposal.id,
                risk_level=proposal.risk_level,
                files_touched=proposal.files_touched,
                diff_lines=diff_line_count,
                parent_event_id=evolve_event.event_id,
            )
            store.record(attempt_event)

            success, msg = apply_unified_diff(
                proposal,
                repo_root=config.workspace_path,
                allowlist_paths=gc.allowlist_paths,
                denylist_paths=gc.denylist_paths,
                max_patch_lines=gc.max_patch_lines,
                dry_run=False,
            )

            # Record result
            result_event = EvoEvent(
                event_type="apply_succeeded" if success else "apply_failed",
                proposal_id=proposal.id,
                risk_level=proposal.risk_level,
                files_touched=proposal.files_touched,
                diff_lines=diff_line_count,
                parent_event_id=attempt_event.event_id,
                result=f"{'ok' if success else 'fail'}: {msg[:200]}",
            )
            store.record(result_event)

            if success:
                console.print(f"[green]{msg}[/green]")
            else:
                console.print(f"[red]{msg}[/red]")
                raise typer.Exit(1)
        elif not apply_mode:
            console.print("\n[dim]Dry-run mode. Use --apply to apply the proposal.[/dim]")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# apply (from file)
# ---------------------------------------------------------------------------


@geneclaw_app.command("apply")
def apply_cmd(
    proposal_file: str = typer.Argument(..., help="Path to proposal JSON file"),
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Dry-run (default) or apply"),
) -> None:
    """Apply a previously generated proposal from a JSON file."""
    from nanobot.config.loader import load_config
    from geneclaw.models import EvolutionProposal, EvoEvent
    from geneclaw.apply import apply_unified_diff
    from geneclaw.event_store import EventStore

    config = load_config()
    gc = config.geneclaw

    path = Path(proposal_file)
    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)

    raw = json.loads(path.read_text(encoding="utf-8"))
    proposal = EvolutionProposal.model_validate(raw)

    console.print(f"[bold]Proposal: {proposal.title}[/bold] (risk: {proposal.risk_level})")

    apply_mode = not dry_run
    store = EventStore(config.workspace_path, redact=gc.redact_enabled)
    diff_line_count = len(proposal.unified_diff.splitlines()) if proposal.unified_diff else 0

    # Record apply_attempted
    attempt_event = EvoEvent(
        event_type="apply_attempted",
        proposal_id=proposal.id,
        risk_level=proposal.risk_level,
        files_touched=proposal.files_touched,
        diff_lines=diff_line_count,
    )
    store.record(attempt_event)

    success, msg = apply_unified_diff(
        proposal,
        repo_root=config.workspace_path,
        allowlist_paths=gc.allowlist_paths,
        denylist_paths=gc.denylist_paths,
        max_patch_lines=gc.max_patch_lines,
        dry_run=not apply_mode,
    )

    # Record result
    result_event = EvoEvent(
        event_type="apply_succeeded" if success else "apply_failed",
        proposal_id=proposal.id,
        risk_level=proposal.risk_level,
        files_touched=proposal.files_touched,
        diff_lines=diff_line_count,
        parent_event_id=attempt_event.event_id,
        result=f"{'ok' if success else 'fail'}: {msg[:200]}",
    )
    store.record(result_event)

    if success:
        console.print(f"[green]{msg}[/green]")
    else:
        console.print(f"[red]{msg}[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@geneclaw_app.command("report")
def report(
    since: float = typer.Option(24.0, "--since", help="Look back N hours"),
    fmt: str = typer.Option("table", "--format", help="Output format: table or json"),
) -> None:
    """Show evolution statistics for the last N hours (read-only)."""
    from nanobot.config.loader import load_config
    from geneclaw.event_store import EventStore
    from geneclaw.recorder import RunRecorder
    from geneclaw.report import generate_report

    config = load_config()
    ws = config.workspace_path

    store = EventStore(ws)
    evo_events = store.iter_events(since_hours=since)

    run_events: list[dict] = []
    for sk in RunRecorder.list_sessions(ws):
        rec = RunRecorder(workspace=ws, session_key=sk, redact=True)
        run_events.extend(rec.iter_events(max_events=1000))

    data = generate_report(evo_events, run_events)

    if fmt == "json":
        console.print(json.dumps(data.to_dict(), indent=2))
        return

    console.print(f"[bold]Geneclaw Report[/bold] (last {since}h)\n")

    table = Table(title="Evolution Pipeline")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Proposals generated", str(data.evolve_count))
    table.add_row("Apply attempted", str(data.apply_attempted))
    table.add_row("Apply succeeded", str(data.apply_succeeded))
    table.add_row("Apply failed", str(data.apply_failed))
    table.add_row("Success rate", f"{data.success_rate:.1f}%" if data.apply_attempted else "N/A")
    console.print(table)

    if data.risk_distribution:
        console.print("\n[bold]Risk Distribution[/bold]")
        for risk, count in sorted(data.risk_distribution.items()):
            bar = "\u2588" * count
            console.print(f"  {risk:>8}: {bar} ({count})")

    if data.top_files_touched:
        console.print("\n[bold]Top Files Touched[/bold]")
        for fp, count in data.top_files_touched:
            console.print(f"  {count:>3}x  {fp}")

    if data.top_tool_failures:
        console.print("\n[bold]Top Tool Failures (from run logs)[/bold]")
        for tool, count in data.top_tool_failures:
            console.print(f"  {count:>3}x  {tool}")

    if data.top_exceptions:
        console.print("\n[bold]Top Exceptions (from run logs)[/bold]")
        for msg, count in data.top_exceptions:
            console.print(f"  {count:>3}x  {msg}")

    if not evo_events and not run_events:
        console.print("\n[dim]No events found. Run 'nanobot geneclaw evolve --dry-run' first.[/dim]")

    console.print(f"\n[dim]Evolution event log: {store.path}[/dim]")


# ---------------------------------------------------------------------------
# autopilot
# ---------------------------------------------------------------------------


@geneclaw_app.command("autopilot")
def autopilot(
    max_cycles: int = typer.Option(3, "--max-cycles", help="Maximum evolution cycles"),
    cooldown: float = typer.Option(5.0, "--cooldown", help="Seconds between cycles"),
    auto_approve: str = typer.Option("low", "--auto-approve", help="Auto-approve risk level: none, low"),
    since: float = typer.Option(24.0, "--since", help="Look back N hours"),
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Dry-run (default) or apply"),
    stop_on_failure: bool = typer.Option(True, "--stop-on-failure/--continue", help="Stop on first failure"),
    fmt: str = typer.Option("table", "--format", help="Output format: table or json"),
) -> None:
    """Run the autopilot evolution loop (observe → evolve → gate → apply)."""
    import asyncio
    from nanobot.config.loader import load_config
    from geneclaw.autopilot import AutopilotConfig, run_autopilot

    config = load_config()
    gc = config.geneclaw

    if not gc.enabled:
        console.print("[yellow]Geneclaw is disabled. Set geneclaw.enabled=true.[/yellow]")
        raise typer.Exit(1)

    provider = None
    try:
        from nanobot.cli.commands import _make_provider
        provider = _make_provider(config)
    except (SystemExit, Exception):
        console.print("[yellow]No LLM provider — heuristic-only mode.[/yellow]")

    ap_config = AutopilotConfig(
        max_cycles=max_cycles,
        cooldown_seconds=cooldown,
        auto_approve_risk=auto_approve if auto_approve in ("none", "low") else "low",
        since_hours=since,
        dry_run=dry_run,
        stop_on_failure=stop_on_failure,
    )

    console.print(f"[bold]Geneclaw Autopilot[/bold] — {max_cycles} cycles, "
                  f"{'dry-run' if dry_run else 'APPLY'}, auto-approve={auto_approve}\n")

    async def _run():
        return await run_autopilot(
            workspace=config.workspace_path,
            provider=provider,
            model=config.agents.defaults.model,
            config=ap_config,
            allowlist_paths=gc.allowlist_paths,
            denylist_paths=gc.denylist_paths,
            max_patch_lines=gc.max_patch_lines,
            redact=gc.redact_enabled,
        )

    result = asyncio.run(_run())

    if fmt == "json":
        console.print(json.dumps(result.to_dict(), indent=2))
        return

    from rich.table import Table as RTable
    table = RTable(title="Autopilot Results")
    table.add_column("Cycle", style="cyan")
    table.add_column("Proposal", style="white")
    table.add_column("Risk", style="white")
    table.add_column("Gate", style="white")
    table.add_column("Applied", style="white")
    table.add_column("Result", style="white")
    table.add_column("Time (ms)", style="dim")

    for cr in result.cycle_results:
        if cr.skipped:
            table.add_row(
                str(cr.cycle), "[dim]skipped[/dim]", "-", "-", "-",
                cr.skip_reason[:60], f"{cr.duration_ms:.0f}",
            )
        else:
            gate_str = "[green]pass[/green]" if cr.gate_passed else "[red]fail[/red]"
            applied_str = "[green]yes[/green]" if cr.applied else "[dim]no[/dim]"
            table.add_row(
                str(cr.cycle),
                cr.proposal_title[:30],
                cr.risk_level,
                gate_str,
                applied_str,
                cr.apply_result[:60],
                f"{cr.duration_ms:.0f}",
            )

    console.print(table)
    console.print(
        f"\n  Generated: {result.proposals_generated}  "
        f"Gated: {result.proposals_gated}  "
        f"Applied: {result.proposals_applied}  "
        f"Failed: {result.proposals_failed}  "
        f"Total: {result.total_duration_ms:.0f}ms"
    )


# ---------------------------------------------------------------------------
# benchmark
# ---------------------------------------------------------------------------


@geneclaw_app.command("benchmark")
def benchmark(
    event_counts: str = typer.Option("100,500,1000", "--event-counts", help="Comma-separated event counts"),
    gate_iterations: int = typer.Option(100, "--gate-iterations", help="Gatekeeper validation iterations"),
    fmt: str = typer.Option("table", "--format", help="Output format: table or json"),
) -> None:
    """Run pipeline performance benchmarks with synthetic data."""
    from geneclaw.benchmarks import run_benchmarks

    counts = [int(x.strip()) for x in event_counts.split(",") if x.strip().isdigit()]
    if not counts:
        counts = [100, 500, 1000]

    console.print("[bold]Geneclaw Benchmark[/bold]\n")
    console.print("[dim]Running synthetic benchmarks...[/dim]")

    result = run_benchmarks(
        event_counts=counts,
        gate_iterations=gate_iterations,
    )

    if fmt == "json":
        console.print(json.dumps(result.to_dict(), indent=2))
        return

    from rich.table import Table as RTable
    table = RTable(title="Pipeline Benchmarks")
    table.add_column("Stage", style="cyan")
    table.add_column("Iterations", style="white")
    table.add_column("Total (ms)", style="white")
    table.add_column("Avg (ms)", style="green")

    for s in result.stages:
        table.add_row(
            s.stage,
            str(s.iterations),
            f"{s.duration_ms:.1f}",
            f"{s.avg_ms:.3f}",
        )

    console.print(table)
    console.print(f"\n  Total benchmark time: {result.total_duration_ms:.0f}ms")
