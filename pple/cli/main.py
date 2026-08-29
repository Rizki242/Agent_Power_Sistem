"""PPLE CLI (docs/final.md Phase 12-19) - MVP slice.

First-class commands that reuse the exact same pple.engineering module
layer api_server.py already routes through (docs/pple_v2_baseline.md's
"CLI and API share the same Python core" principle) - nothing here
duplicates analysis logic.

Invoke directly: `python -m pple.cli.main <command>`. `pyproject.toml`
registers this as the `pple` console script for `pip install -e .`.

Scope of this slice: status, doctor, module list/show, analyze, equipment
modules/module-add/module-remove (Phase 8 - per-equipment module overrides,
file-backed, see pple.engineering.equipment_modules). Full asset/plant/unit
CRUD commands are still out of scope until the database layer (final.md
Phase 2-4) exists - there is nowhere durable to write them to yet.
"""

import json
import os
import sys

import typer
from rich.console import Console
from rich.table import Table

from pple.engineering.equipment_modules import EquipmentModuleStore
from pple.engineering.loader import ModuleStatus, load_modules_from_manifests

app = typer.Typer(name="pple", help="PPLE Reliability Engineering Agent CLI", no_args_is_help=True)
module_app = typer.Typer(help="Inspect engineering modules loaded from manifests.")
app.add_typer(module_app, name="module")
equipment_app = typer.Typer(help="Manage per-equipment engineering module overrides (Phase 8).")
app.add_typer(equipment_app, name="equipment")

console = Console()


def _equipment_count() -> str:
    try:
        from src.data_loader import get_data_path, load_mcsa_data, get_latest_data

        data_file = get_data_path("mcsa_updated.csv")
        if not os.path.exists(data_file):
            data_file = get_data_path("Report MCSA.xls")
        if not os.path.exists(data_file):
            return "N/A (no data file found)"
        df = load_mcsa_data(data_file)
        latest = get_latest_data(df)
        return str(latest["Equipment"].nunique()) if "Equipment" in latest.columns else str(len(latest))
    except Exception as exc:
        return f"N/A ({exc})"


@app.command()
def status():
    """Show a snapshot of PPLE's current state."""
    registry, results = load_modules_from_manifests()
    active_count = sum(1 for r in results if r.status == ModuleStatus.ACTIVE)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("Status", "[bold green]ONLINE[/bold green]")
    table.add_row("Data Source", "File-based (CSV/Excel, data/MCSA/)")
    table.add_row("Engineering", f"{active_count}/{len(results)} modules ACTIVE")
    table.add_row("Equipment", _equipment_count())
    table.add_row("Safety Guard", "[bold green]ENABLED[/bold green]")
    console.print(table)


@app.command()
def doctor():
    """Run startup health checks (docs/final.md Phase 15)."""
    console.print("[bold]PPLE SYSTEM DOCTOR[/bold]\n")
    healthy = True

    console.print(f"[green][OK][/green] Python {sys.version.split()[0]}")

    from src.data_loader import get_data_path

    data_root = os.environ.get("MCSA_DATA_DIR") or "data/"
    if os.path.isdir(data_root):
        console.print(f"[green][OK][/green] Data directory ({data_root})")
    else:
        console.print(f"[red][ERROR][/red] Data directory not found ({data_root})")
        healthy = False

    data_file = get_data_path("mcsa_updated.csv")
    if os.path.exists(data_file):
        console.print(f"[green][OK][/green] Active dataset (mcsa_updated.csv)")
    else:
        console.print("[yellow][WARN][/yellow] mcsa_updated.csv not found - falling back to Report MCSA.xls if present")

    _, results = load_modules_from_manifests()
    for r in results:
        if r.status == ModuleStatus.ACTIVE:
            console.print(f"[green][OK][/green] {r.module_id} 1.0")
        elif r.status == ModuleStatus.DISABLED:
            console.print(f"[yellow][WARN][/yellow] {r.module_id} disabled in manifest")
        else:
            console.print(f"[red][ERROR][/red] {r.module_id}: {r.detail}")
            healthy = False

    if os.environ.get("GEMINI_API_KEY"):
        console.print("[green][OK][/green] Gemini API key configured")
    else:
        console.print("[yellow][WARN][/yellow] Gemini API key not configured (LLM assistance disabled, rule-based fallback active)")

    try:
        from src.agents.safety_guard import SafetyGuardrailAgent

        SafetyGuardrailAgent()
        console.print("[green][OK][/green] Safety Guardrail enabled")
    except Exception as exc:
        console.print(f"[red][ERROR][/red] Safety Guardrail failed to load: {exc}")
        healthy = False

    console.print(f"\nSystem health: {'[bold green]GOOD[/bold green]' if healthy else '[bold red]DEGRADED[/bold red]'}")
    if not healthy:
        raise typer.Exit(code=1)


@module_app.command("list")
def module_list():
    """List engineering modules and their manifest load status."""
    registry, results = load_modules_from_manifests()
    status_by_id = {r.module_id: r.status.value for r in results}

    table = Table()
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Applicable Equipment")
    for m in registry.list():
        table.add_row(m.id, m.name, m.version, status_by_id.get(m.id, "?"), ", ".join(m.applicable_equipment))
    console.print(table)


def _get_active_module(registry, module_id: str):
    """Look up a module and exit(1) with a consistent message if it's missing/inactive."""
    try:
        return registry.get(module_id)
    except Exception:
        console.print(f"[red]Engineering module '{module_id}' not found or not ACTIVE.[/red]")
        raise typer.Exit(code=1)


@module_app.command("show")
def module_show(module_id: str):
    """Show detail for one engineering module."""
    registry, results = load_modules_from_manifests()
    m = _get_active_module(registry, module_id)

    report = next((r for r in results if r.module_id == module_id), None)
    console.print(f"[bold]{m.name}[/bold] ({m.id}) v{m.version}")
    console.print(f"Status: {report.status.value if report else '?'}")
    console.print(f"Applicable equipment: {', '.join(m.applicable_equipment) or 'any'}")


@equipment_app.command("modules")
def equipment_modules(equipment: str = typer.Argument(..., help="Equipment name/id, e.g. CWP-1A")):
    """List which engineering modules are enabled for this equipment."""
    registry, _ = load_modules_from_manifests()
    store = EquipmentModuleStore()
    console.print(f"\n[bold]{equipment}[/bold] Engineering Modules\n")
    for module_id, enabled in store.list_for_equipment(equipment, registry):
        m = registry.get(module_id)
        mark = "[green]✓[/green]" if enabled else "[red]✗[/red]"
        console.print(f"{mark} {m.name}")


@equipment_app.command("module-add")
def equipment_module_add(
    equipment: str = typer.Argument(..., help="Equipment name/id, e.g. CWP-1A"),
    module_id: str = typer.Argument(..., help="Engineering module id, e.g. vibration"),
):
    """Enable an engineering module for this equipment (clears any prior disable)."""
    registry, _ = load_modules_from_manifests()
    m = _get_active_module(registry, module_id)
    EquipmentModuleStore().add_module(equipment, module_id)
    console.print(f"[green]Enabled[/green] {m.name} for {equipment}")


@equipment_app.command("module-remove")
def equipment_module_remove(
    equipment: str = typer.Argument(..., help="Equipment name/id, e.g. CWP-1A"),
    module_id: str = typer.Argument(..., help="Engineering module id, e.g. vibration"),
):
    """Disable an engineering module for this equipment."""
    registry, _ = load_modules_from_manifests()
    m = _get_active_module(registry, module_id)
    EquipmentModuleStore().remove_module(equipment, module_id)
    console.print(f"[yellow]Disabled[/yellow] {m.name} for {equipment}")


@app.command()
def analyze(
    module_id: str = typer.Argument(..., help="Engineering module id, e.g. vibration, mcsa, dga"),
    equipment: str = typer.Argument(..., help="Equipment name/id"),
    data: str = typer.Option(None, "--data", help="Measurement data as a JSON object string"),
    file: str = typer.Option(None, "--file", help="Path to a JSON file with measurement data"),
):
    """Run one engineering module's diagnosis on measurement data."""
    if data and file:
        console.print("[red]Pass either --data or --file, not both.[/red]")
        raise typer.Exit(code=1)

    if file:
        with open(file, "r", encoding="utf-8") as f:
            payload = json.load(f)
    elif data:
        payload = json.loads(data)
    else:
        payload = {}

    registry, _ = load_modules_from_manifests()
    m = _get_active_module(registry, module_id)

    result = m.run(equipment, payload)

    severity_color = {"NORMAL": "green", "WATCH": "yellow", "ALARM": "yellow", "CRITICAL": "red"}.get(result.severity.value, "white")
    console.print(f"\n[bold]{module_id.upper()} ANALYSIS[/bold] - {equipment}\n")
    console.print(f"Severity      [{severity_color}]{result.severity.value}[/{severity_color}]")
    console.print(f"Health Score  {result.health_score}")
    console.print(f"Confidence    {result.confidence}")
    if result.findings:
        console.print("\nFindings:")
        for f in result.findings:
            if f.text:
                console.print(f"  - {f.text}")
    if result.evidence:
        console.print("\nEvidence:")
        for e in result.evidence:
            console.print(f"  - {e.text}")
    if result.recommendations:
        console.print("\nRecommendations:")
        for r in result.recommendations:
            console.print(f"  - {r.text}")


if __name__ == "__main__":
    app()
