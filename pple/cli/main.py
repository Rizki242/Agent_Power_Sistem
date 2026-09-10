"""PPLE CLI (docs/final.md Phase 12-23) - MVP slice.

First-class commands that reuse the exact same pple.engineering module
layer api_server.py already routes through (docs/pple_v2_baseline.md's
"CLI and API share the same Python core" principle) - nothing here
duplicates analysis logic.

Invoke directly: `python -m pple.cli.main <command>`. `pyproject.toml`
registers this as the `pple` console script for `pip install -e .`.

Scope of this slice: status, doctor, module list/show, analyze, equipment
modules/module-add/module-remove (Phase 8 - per-equipment module overrides,
file-backed, see pple.engineering.equipment_modules), assets tree/list/show
(Phase 3 - read-only Plant/Unit/Equipment view, see pple.assets.registry),
and ask/shell (Phase 19-20 - rule-based natural-language command parsing,
see pple.cli.nl, gated by the READ/WRITE/HIGH-RISK classification in
pple.cli.safety which always defers to the existing, mandatory Safety
Guardrail for plant-actuation phrasing), and config llm/set/test (Phase 21 -
view/persist which LLM provider+model the assistant layer uses, see
src.ai_settings/src.llm_assistant - the same code the Streamlit Settings
page already uses, not a separate LLMProvider hierarchy), chat (Phase 22 -
rule-based src.chatbot.MCSAChatbot, optionally enriched by the configured
LLM, controlled by the root --offline flag which blocks any cloud provider
call and falls back to a pure rule-based answer), and serve api/frontend/all
(Phase 23 - a pple-native alternative to run_api.bat/run_frontend.bat/
run_all.bat; those .bat scripts are untouched and keep working - serve api
literally calls run_server.main()).
Asset/plant/unit CRUD (creating or editing equipment through the CLI, not
just viewing it) is still out of scope until the database layer (final.md
Phase 2-4) exists - there is nowhere durable to write new records to yet.
"""

import json
import os
import subprocess
import sys

import typer
from rich.console import Console
from rich.table import Table

from pple.core import audit
from pple.engineering.equipment_modules import EquipmentModuleStore
from pple.engineering.loader import ModuleStatus, load_modules_from_manifests

# This CLI prints Unicode symbols (checkmarks, the Safety Guardrail's warning
# emoji, box-drawing table borders) that don't exist in Windows' legacy
# console codepage (cp1252/cp437) - reconfigure stdout/stderr to UTF-8 so
# `pple <command>` doesn't crash with UnicodeEncodeError in a plain Windows
# terminal. Guarded because reconfigure() isn't available on every stream
# (e.g. when stdout is already replaced/captured by a test runner).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

app = typer.Typer(name="pple", help="PPLE Reliability Engineering Agent CLI", no_args_is_help=True)
module_app = typer.Typer(help="Inspect engineering modules loaded from manifests.")
app.add_typer(module_app, name="module")
equipment_app = typer.Typer(help="Manage per-equipment engineering module overrides (Phase 8).")
app.add_typer(equipment_app, name="equipment")
assets_app = typer.Typer(help="Browse the Plant/Unit/Equipment hierarchy (Phase 3).")
app.add_typer(assets_app, name="assets")
reliability_app = typer.Typer(help="Reliability Fusion V2 - health/risk/RUL across engineering modules (Phase 11).")
app.add_typer(reliability_app, name="reliability")
agents_app = typer.Typer(help="The specialist/fusion/safety agent roster and its live status (Phase 18).")
app.add_typer(agents_app, name="agents")
config_app = typer.Typer(help="View/persist which LLM provider+model the assistant layer uses (Phase 21).")
app.add_typer(config_app, name="config")
serve_app = typer.Typer(help="Start the API/frontend dev servers (Phase 23) - a pple-native alternative to the .bat scripts, which keep working unchanged.")
app.add_typer(serve_app, name="serve")
domain_app = typer.Typer(help="Upload/query/report over the 5 shared condition-monitoring domains (Vibrasi/DGA/Tribology/Thermal/PD) - the pple.api.domain_router/src.domain_ingest/src.domain_report layer the Streamlit workspace already uses.")
app.add_typer(domain_app, name="domain")
audit_app = typer.Typer(help="Read the configuration-change audit trail (Phase 29): WHO/WHAT/WHEN/OLD/NEW/SOURCE.")
app.add_typer(audit_app, name="audit")

# provider name -> ai_settings.json field holding that provider's model choice.
# Mirrors the exact set of providers src/pages/settings_page.py exposes -
# gemini_enterprise/vertex_ai exist in src/llm_assistant.py but are not wired
# to any UI, so they are deliberately left out here too.
_LLM_MODEL_FIELD = {
    "gemini": "gemini_model",
    "groq": "groq_model",
    "opencode": "opencode_model",
    "ollama": "ollama_model",
}
_LLM_PROVIDERS = tuple(_LLM_MODEL_FIELD)
_CLOUD_LLM_PROVIDERS = {"gemini", "groq", "opencode"}  # need internet; ollama is local-only

console = Console()

# Set by the --offline root option (Phase 22). Module-level rather than a
# Typer context object because every command already reaches its own
# collaborators via plain module-level imports, not a shared context.
_OFFLINE = False


@app.callback()
def _root(
    offline: bool = typer.Option(
        False, "--offline",
        help="Larang command apa pun memanggil provider LLM cloud (gemini/groq/opencode). "
             "Ollama (server lokal) dan seluruh logika rule-based tetap jalan seperti biasa.",
    ),
):
    """PPLE Reliability Engineering Agent CLI.

    Rule-based di src/ adalah sumber kebenaran untuk threshold dan status -
    LLM (bila dikonfigurasi) hanya memperkaya narasi jawaban `pple chat`,
    tidak pernah menggantikan angka/threshold engineering (docs/final.md
    Phase 22).
    """
    global _OFFLINE
    _OFFLINE = offline


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
    EquipmentModuleStore().add_module(equipment, module_id, source=audit.SOURCE_CLI)
    console.print(f"[green]Enabled[/green] {m.name} for {equipment}")


@equipment_app.command("module-remove")
def equipment_module_remove(
    equipment: str = typer.Argument(..., help="Equipment name/id, e.g. CWP-1A"),
    module_id: str = typer.Argument(..., help="Engineering module id, e.g. vibration"),
):
    """Disable an engineering module for this equipment."""
    registry, _ = load_modules_from_manifests()
    m = _get_active_module(registry, module_id)
    EquipmentModuleStore().remove_module(equipment, module_id, source=audit.SOURCE_CLI)
    console.print(f"[yellow]Disabled[/yellow] {m.name} for {equipment}")


@audit_app.command("list")
def audit_list(
    limit: int = typer.Option(20, "--limit", help="Jumlah event terbaru yang ditampilkan."),
    entity: str = typer.Option(None, "--entity", help="Filter satu equipment, mis. CWP-1A."),
    source: str = typer.Option(None, "--source", help="Filter asal perubahan: CLI, API, STREAMLIT."),
):
    """Tampilkan riwayat perubahan konfigurasi, terbaru lebih dulu."""
    events = audit.read_events(limit=limit, entity=entity, source=source)
    if not events:
        console.print("[yellow]Belum ada event audit yang tercatat.[/yellow]")
        return

    table = Table(title=f"Audit Log ({len(events)} event terbaru)")
    table.add_column("WHEN")
    table.add_column("WHO")
    table.add_column("ENTITY")
    table.add_column("FIELD")
    table.add_column("OLD")
    table.add_column("NEW")
    table.add_column("SOURCE")
    for event in events:
        table.add_row(
            str(event.get("when", "")),
            str(event.get("who", "")),
            str(event.get("entity", "")),
            str(event.get("field", "")),
            str(event.get("old_value", "")),
            str(event.get("new_value", "")),
            str(event.get("source", "")),
        )
    console.print(table)


@assets_app.command("tree")
def assets_tree(domain: str = typer.Option(None, "--domain", help="Restrict to one domain, e.g. dga, vibration")):
    """Show the full Plant -> Unit -> Equipment hierarchy."""
    from pple.assets import AssetRegistry

    plant = AssetRegistry().plant(domain=domain)
    console.print(f"[bold]{plant.name}[/bold] ({plant.id})")
    for unit in plant.units:
        console.print(f"\n[bold cyan]{unit.name}[/bold cyan] ({len(unit.equipment)} equipment)")
        for eq in unit.equipment:
            # Square brackets are Rich markup, not literal text - use parens for the
            # domain tag so e.g. "vibration" doesn't get silently swallowed as a style tag.
            console.print(f"  ({eq.domain}) {eq.id}  {eq.name}  ({eq.equipment_class or '-'})  status={eq.status or '-'}")


@assets_app.command("list")
def assets_list(
    unit: str = typer.Option(None, "--unit", help="Filter by unit, e.g. 'UNIT 1'"),
    domain: str = typer.Option(None, "--domain", help="Filter by domain, e.g. dga, vibration"),
):
    """List equipment, optionally filtered by unit and/or domain."""
    from pple.assets import AssetRegistry

    equipment = AssetRegistry().list_equipment(unit=unit, domain=domain)
    table = Table()
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Unit")
    table.add_column("Domain")
    table.add_column("Class")
    table.add_column("Status")
    for eq in equipment:
        table.add_row(eq.id, eq.name, eq.unit, eq.domain, eq.equipment_class or "-", eq.status or "-")
    console.print(table)


@assets_app.command("show")
def assets_show(equipment_id: str = typer.Argument(..., help="Equipment id, e.g. a DGA transformer id or vibration asset_id")):
    """Show detail for one piece of equipment."""
    from pple.assets import AssetRegistry

    eq = AssetRegistry().get_equipment(equipment_id)
    if eq is None:
        console.print(f"[red]Equipment '{equipment_id}' not found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]{eq.name}[/bold] ({eq.id})")
    console.print(f"Unit          {eq.unit}")
    console.print(f"Domain        {eq.domain}")
    console.print(f"Class         {eq.equipment_class or '-'}")
    console.print(f"Status        {eq.status or '-'}")
    if eq.metadata:
        console.print("Metadata:")
        for k, v in eq.metadata.items():
            console.print(f"  {k}: {v}")


@reliability_app.command("health")
def reliability_health(
    equipment_id: str = typer.Argument(..., help="Equipment id, e.g. a DGA transformer id or vibration asset_id"),
    criticality: str = typer.Option("B", "--criticality", help="Asset criticality for the risk calculation: A/B/C"),
):
    """Fuse every domain's latest real measurement for this equipment into
    one health/risk/RUL picture (docs/final.md Phase 11)."""
    from pple.reliability import ReliabilityFusionEngine

    try:
        result = ReliabilityFusionEngine().fuse_equipment(equipment_id, criticality=criticality)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    severity_color = {"NORMAL": "green", "WATCH": "yellow", "ALARM": "yellow", "CRITICAL": "red"}.get(result.severity.value, "white")
    console.print(f"\n[bold]RELIABILITY FUSION[/bold] - {equipment_id}\n")
    console.print(f"Health Index   {result.health_index} ({result.health_index_type.value})")
    console.print(f"Severity       [{severity_color}]{result.severity.value}[/{severity_color}]")
    console.print(f"Risk           {result.risk_level} (index {result.risk_index}, {result.risk_type.value})")
    console.print(f"Failure 30d    {result.failure_probability_30d}% ({result.failure_probability_type.value})")
    console.print(f"Est. RUL       {result.estimated_rul_days} ({result.rul_type.value})")
    console.print(f"Next window    {result.recommended_window}")

    console.print("\nDomain contributions:")
    for c in result.domain_contributions:
        console.print(f"  ({c.module_id}) health={c.health_score} severity={c.severity.value} confidence={c.confidence}")

    if result.notes:
        console.print("\nCatatan:")
        for note in result.notes:
            console.print(f"  - {note}")


@domain_app.command("list")
def domain_list():
    """List the 5 shared domains and the parameters each one recognizes."""
    from src import domain_ingest as ingest
    from src import domain_measurements as dm

    for domain in dm.DOMAINS:
        specs = ingest.parameter_specs(domain)
        console.print(f"\n[bold]{ingest.profile(domain)['label']}[/bold] ({domain}) - {len(specs)} parameter")
        console.print("  " + ", ".join(spec.key for spec in specs[:10]) + (" ..." if len(specs) > 10 else ""))


@domain_app.command("measurements")
def domain_measurements(
    domain: str = typer.Argument(..., help="Domain id, e.g. VIBRASI/DGA/TRIBOLOGY/THERMAL/PD"),
    equipment: str = typer.Option(None, "--equipment", help="Filter by equipment name"),
    start: str = typer.Option(None, "--start", help="YYYY-MM-DD"),
    end: str = typer.Option(None, "--end", help="YYYY-MM-DD"),
    limit: int = typer.Option(50, "--limit"),
):
    """Show stored readings for one domain, same store src.domain_measurements backs."""
    from datetime import datetime

    from src import domain_measurements as dm

    try:
        domain = dm.canon_domain(domain)
    except dm.UnknownDomainError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    frame = dm.filter_measurements(
        domain,
        equipment=equipment,
        date_start=datetime.strptime(start, "%Y-%m-%d").date() if start else None,
        date_end=datetime.strptime(end, "%Y-%m-%d").date() if end else None,
    )
    frame = frame.sort_values("test_date", ascending=False).head(max(1, limit))

    table = Table()
    for col in ("test_date", "equipment", "parameter", "raw_value", "uom"):
        table.add_column(col)
    for _, row in frame.iterrows():
        table.add_row(
            "" if row["test_date"] != row["test_date"] else f"{row['test_date']:%Y-%m-%d}",
            str(row["equipment"]), str(row["parameter"]), str(row["raw_value"]), str(row["uom"] or "-"),
        )
    console.print(table)
    console.print(f"{len(frame)} baris ditampilkan.")


@domain_app.command("upload")
def domain_upload(
    domain: str = typer.Argument(..., help="Domain id, e.g. VIBRASI/DGA/TRIBOLOGY/THERMAL/PD"),
    file_path: str = typer.Argument(..., help="Path to a CSV/XLSX export"),
    preview_only: bool = typer.Option(False, "--preview-only", help="Validate without writing anything."),
):
    """Ingest a CSV/XLSX export into the canonical store - the CLI equivalent
    of the Streamlit workspace's upload tab, same src.domain_ingest pipeline."""
    from src import domain_ingest as ingest
    from src import domain_measurements as dm

    try:
        domain = dm.canon_domain(domain)
    except dm.UnknownDomainError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if not os.path.exists(file_path):
        console.print(f"[red]File '{file_path}' tidak ditemukan.[/red]")
        raise typer.Exit(code=1)

    with open(file_path, "rb") as f:
        content = f.read()
    file_name = os.path.basename(file_path)

    try:
        preview = ingest.preview_upload(domain, file_name, content)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    console.print(f"Baris sumber: {preview['source_rows']}  |  Valid: {len(preview['valid'])}  |  Ditolak: {len(preview['rejected'])}")
    if preview["unmapped_columns"]:
        console.print(f"[yellow]Kolom tidak dikenali: {', '.join(preview['unmapped_columns'])}[/yellow]")
    if preview["duplicate_columns"]:
        console.print(f"[yellow]Kolom duplikat (diabaikan): {', '.join(preview['duplicate_columns'])}[/yellow]")

    if preview_only:
        console.print("[dim]--preview-only: tidak ada yang ditulis.[/dim]")
        return

    batch_path, _ = ingest.create_batch(domain, file_name, content, preview)
    result = ingest.commit_batch(domain, batch_path, preview)
    console.print(f"[bold green]Tersimpan {result['written']} pengukuran[/bold green] (batch {result['batch_id']})")


@domain_app.command("report")
def domain_report_cmd(
    domain: str = typer.Argument(..., help="Domain id, e.g. VIBRASI/DGA/TRIBOLOGY/THERMAL/PD"),
    out: str = typer.Argument(..., help="Output file path, e.g. laporan.docx"),
    start: str = typer.Option(None, "--start", help="YYYY-MM-DD, defaults to the earliest stored reading"),
    end: str = typer.Option(None, "--end", help="YYYY-MM-DD, defaults to today"),
    fmt: str = typer.Option(None, "--format", help="csv/docx/pptx, inferred from `out`'s extension if omitted"),
):
    """Build a period report for one domain - same src.domain_report builders
    the Streamlit workspace's Laporan tab downloads."""
    from datetime import date, datetime

    from src import domain_measurements as dm
    from src import domain_report as report

    try:
        domain = dm.canon_domain(domain)
    except dm.UnknownDomainError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    fmt = (fmt or os.path.splitext(out)[1].lstrip(".") or "docx").lower()
    if fmt not in ("csv", "docx", "pptx"):
        console.print(f"[red]Format '{fmt}' tidak didukung. Gunakan csv/docx/pptx.[/red]")
        raise typer.Exit(code=1)

    frame = dm.load_measurements(domain)
    start_date = (
        datetime.strptime(start, "%Y-%m-%d").date() if start
        else (frame["test_date"].min().date() if not frame.empty and frame["test_date"].notna().any() else date.today())
    )
    end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else date.today()

    bundle = report.build_report_bundle([domain], start_date, end_date, formats=[fmt])
    with open(out, "wb") as f:
        f.write(bundle[fmt])
    console.print(f"[bold green]Laporan disimpan ke {out}[/bold green] (periode {start_date} - {end_date})")


@domain_app.command("vibrasi-report")
def domain_vibrasi_report(
    equipment: str = typer.Argument(..., help="Nama equipment persis seperti di data Vibrasi"),
    out: str = typer.Argument(..., help="Output .docx path"),
):
    """DETAIL REPORT VIBRASI (FORM.JRG.F.05.001) for one equipment - same
    src.vibration_report.build_docx the Streamlit Vibrasi workspace uses."""
    from src import domain_measurements as dm
    from src import vibration_report

    frame = dm.filter_measurements("VIBRASI", equipment=equipment)
    if frame.empty:
        console.print(f"[red]Tidak ada pengukuran Vibrasi untuk equipment '{equipment}'.[/red]")
        raise typer.Exit(code=1)

    payload = vibration_report.build_docx(equipment)
    with open(out, "wb") as f:
        f.write(payload)
    console.print(f"[bold green]DETAIL REPORT VIBRASI disimpan ke {out}[/bold green]")


@agents_app.command("list")
def agents_list():
    """List the specialist/fusion/safety agent roster and each one's live status."""
    from pple.agents import AgentRegistry

    status_color = {"ACTIVE": "green", "ONLINE": "green", "DISABLED": "yellow", "ERROR": "red"}
    table = Table()
    table.add_column("Agent")
    table.add_column("Domain")
    table.add_column("Role")
    table.add_column("Status")
    for a in AgentRegistry().list_agents():
        color = status_color.get(a["status"], "white")
        table.add_row(a["name"], a["domain"], a["role"], f"[{color}]{a['status']}[/{color}]")
    console.print(table)


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


@config_app.command("llm")
def config_llm():
    """Show the persisted LLM provider/model and whether a key resolves for it.

    Reads the same data/MCSA/config/ai_settings.json the Streamlit Settings
    page writes (src/ai_settings.py) - CLI and UI share one preference store.
    Never prints the API key itself, only whether one resolved.
    """
    from src import ai_settings
    from src.llm_assistant import (
        DEFAULT_GEMINI_MODEL, DEFAULT_GROQ_MODEL, DEFAULT_OLLAMA_HOST, DEFAULT_OLLAMA_MODEL,
        DEFAULT_OPENCODE_MODEL, resolve_provider_key,
    )

    default_model_by_provider = {
        "gemini": DEFAULT_GEMINI_MODEL,
        "groq": DEFAULT_GROQ_MODEL,
        "opencode": DEFAULT_OPENCODE_MODEL,
        "ollama": DEFAULT_OLLAMA_MODEL,
    }

    prefs = ai_settings.load()
    provider = prefs.get("ai_provider", "gemini")
    model_field = _LLM_MODEL_FIELD.get(provider, "gemini_model")
    model = prefs.get(model_field) or default_model_by_provider.get(provider, "(default)")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("Provider", provider)
    table.add_row("Model", str(model))
    table.add_row("Enabled", str(prefs.get("ai_enabled", True)))
    if provider == "ollama":
        table.add_row("Host", prefs.get("ollama_host") or DEFAULT_OLLAMA_HOST)
        table.add_row("API Key", "n/a (server lokal)")
    else:
        has_key = bool(resolve_provider_key(provider))
        table.add_row("API Key", "[green]resolved[/green]" if has_key else "[yellow]belum diset[/yellow] (env/.env/secrets.toml)")
    console.print(table)
    console.print(
        "\n[dim]LLM adalah lapisan opsional - jika gagal atau tidak dikonfigurasi, "
        "aplikasi tetap memakai jawaban rule-based lokal (src/ tetap sumber kebenaran).[/dim]"
    )


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="llm.provider | llm.model | llm.host | llm.enabled"),
    value: str = typer.Argument(...),
):
    """Persist one LLM preference. Never accepts/stores an API key - those
    stay in environment variables / .env / secrets.toml (CLAUDE.md rule)."""
    from src import ai_settings

    if key == "llm.provider":
        if value not in _LLM_PROVIDERS:
            console.print(f"[red]Provider tidak dikenal: '{value}'. Pilihan: {', '.join(_LLM_PROVIDERS)}[/red]")
            raise typer.Exit(code=1)
        ai_settings.save({"ai_provider": value})
        console.print(f"[green]Provider LLM diset ke '{value}'.[/green]")
    elif key == "llm.model":
        provider = ai_settings.load().get("ai_provider", "gemini")
        field = _LLM_MODEL_FIELD.get(provider, "gemini_model")
        ai_settings.save({field: value})
        console.print(f"[green]Model {provider} diset ke '{value}'.[/green]")
    elif key == "llm.host":
        ai_settings.save({"ollama_host": value})
        console.print(f"[green]Ollama host diset ke '{value}'.[/green]")
    elif key == "llm.enabled":
        parsed = value.strip().lower() in {"1", "true", "yes", "on", "ya"}
        ai_settings.save({"ai_enabled": parsed})
        console.print(f"[green]LLM enabled diset ke {parsed}.[/green]")
    else:
        console.print(f"[red]Key tidak dikenal: '{key}'. Pilihan: llm.provider, llm.model, llm.host, llm.enabled[/red]")
        raise typer.Exit(code=1)


@config_app.command("test")
def config_test():
    """Test connectivity to the currently configured LLM provider, using the
    exact same test_*_connection helpers the Settings page's "Tes Koneksi"
    buttons call - no separate implementation to drift out of sync."""
    from src import ai_settings
    from src.llm_assistant import (
        DEFAULT_GEMINI_MODEL, DEFAULT_GROQ_MODEL, DEFAULT_OLLAMA_HOST, DEFAULT_OLLAMA_MODEL,
        DEFAULT_OPENCODE_BASE_URL, DEFAULT_OPENCODE_MODEL, resolve_provider_key,
        test_gemini_connection, test_groq_connection, test_ollama_connection, test_opencode_connection,
    )

    prefs = ai_settings.load()
    provider = prefs.get("ai_provider", "gemini")

    if _OFFLINE and provider in _CLOUD_LLM_PROVIDERS:
        console.print(
            f"[yellow]Mode --offline aktif: provider '{provider}' butuh internet, tes koneksi dilewati. "
            "Gunakan 'pple config set llm.provider ollama' untuk provider lokal.[/yellow]"
        )
        raise typer.Exit(code=1)

    if provider == "gemini":
        key = resolve_provider_key("gemini")
        if not key:
            console.print("[yellow]Gemini API key belum diset (env GEMINI_API_KEY / .env / secrets.toml).[/yellow]")
            raise typer.Exit(code=1)
        ok, msg = test_gemini_connection(key, prefs.get("gemini_model", DEFAULT_GEMINI_MODEL))
    elif provider == "groq":
        key = resolve_provider_key("groq")
        if not key:
            console.print("[yellow]Groq API key belum diset (env GROQ_API_KEY / .env / secrets.toml).[/yellow]")
            raise typer.Exit(code=1)
        ok, msg = test_groq_connection(key, prefs.get("groq_model", DEFAULT_GROQ_MODEL))
    elif provider == "opencode":
        key = resolve_provider_key("opencode")
        ok, msg = test_opencode_connection(
            prefs.get("opencode_base_url", DEFAULT_OPENCODE_BASE_URL), key, prefs.get("opencode_model", DEFAULT_OPENCODE_MODEL)
        )
    elif provider == "ollama":
        ok, msg, _models = test_ollama_connection(
            prefs.get("ollama_host", DEFAULT_OLLAMA_HOST), prefs.get("ollama_model", DEFAULT_OLLAMA_MODEL)
        )
    else:
        console.print(f"[red]Provider tidak dikenal: '{provider}'[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]{msg}[/green]" if ok else f"[red]{msg}[/red]")
    if not ok:
        raise typer.Exit(code=1)


@app.command()
def chat(question: str = typer.Argument(..., help="Pertanyaan bebas, mis. 'status CWP 1A' atau 'list alarm'")):
    """Chatbot MCSA rule-based (docs/final.md Phase 22 - tetap jalan tanpa internet).

    Jawaban dasar SELALU berasal dari src.chatbot.MCSAChatbot (rule-based,
    identik dengan halaman Chatbot Streamlit) dan tidak pernah kosong. Bila
    --offline tidak dipakai, provider LLM cloud terkonfigurasi, dan API
    key-nya resolve, jawaban itu boleh diperkaya lewat MCSALLMAssistant -
    tapi kalau langkah itu gagal atau dilewati (offline, tidak
    dikonfigurasi, tanpa key), jawaban rule-based apa adanya yang tampil.
    """
    from src import ai_settings
    from src.chatbot import MCSAChatbot
    from src.data_loader import get_data_path, get_latest_data, load_mcsa_data

    data_file = get_data_path("mcsa_updated.csv")
    if not os.path.exists(data_file):
        data_file = get_data_path("Report MCSA.xls")

    df_all = None
    if os.path.exists(data_file):
        try:
            df_all = load_mcsa_data(data_file)
        except Exception:
            df_all = None
    df_latest = get_latest_data(df_all) if df_all is not None else None

    bot = MCSAChatbot(df_latest, df_all=df_all)
    rule_answer = bot.process_query(question)

    prefs = ai_settings.load()
    provider = prefs.get("ai_provider", "gemini")

    if not prefs.get("ai_enabled", True) or (_OFFLINE and provider in _CLOUD_LLM_PROVIDERS):
        console.print(rule_answer)
        return

    from src.llm_assistant import MCSALLMAssistant, resolve_provider_key

    api_key = None if provider == "ollama" else resolve_provider_key(provider)
    if provider != "ollama" and not api_key:
        console.print(rule_answer)
        return

    llm = MCSALLMAssistant(
        enabled=True,
        provider=provider,
        api_key=api_key,
        model=prefs.get(_LLM_MODEL_FIELD.get(provider, "gemini_model")),
        base_url=prefs.get("opencode_base_url") if provider == "opencode" else None,
        ollama_host=prefs.get("ollama_host"),
    )
    response = llm.enhance_answer(question=question, rule_answer=rule_answer, df_context=df_latest, df_history=None)
    console.print(response)


def _dispatch_intent(intent) -> None:
    """Run one parsed Intent by calling the exact same function its formal
    `pple <command>` subcommand calls - no separate execution path."""
    params = intent.params
    if intent.command == "equipment module-add":
        equipment_module_add(params["equipment"], params["module_id"])
    elif intent.command == "equipment module-remove":
        equipment_module_remove(params["equipment"], params["module_id"])
    elif intent.command == "reliability health":
        reliability_health(params["equipment"])
    elif intent.command == "assets list":
        assets_list(unit=params.get("unit") or None, domain=None)
    elif intent.command == "status":
        status()
    else:
        console.print(f"[red]Intent '{intent.name}' dikenali tapi belum ada handler.[/red]")
        raise typer.Exit(code=1)


@app.command()
def ask(
    text: str = typer.Argument(..., help="Perintah bahasa natural, mis. 'cek CWP-1A' atau 'aktifkan modul vibration untuk CWP-1A'"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Lewati konfirmasi y/N untuk operasi WRITE (untuk scripting)."),
):
    """Parse satu perintah bahasa natural lalu jalankan (docs/final.md Phase 19-20).

    Urutan wajib: (1) teks mentah selalu dicek dulu ke Safety Guardrail -
    frasa HIGH-RISK (trip/shutdown/buka-tutup breaker/dst.) langsung
    diblokir sebelum sempat di-parse jadi intent apapun; (2) baru teks
    di-parse jadi intent; (3) intent bertipe WRITE minta konfirmasi y/N
    kecuali --yes; (4) intent yang tidak dikenali TIDAK pernah dieksekusi
    menebak-nebak - selalu ditolak dengan pesan yang jelas.
    """
    from pple.cli.nl import parse_intent
    from pple.cli.safety import RiskTier, check_high_risk

    guard = check_high_risk(text)
    if guard["violation_detected"]:
        console.print(f"[bold red][SAFETY GUARDRAIL BLOCKED][/bold red] {guard['message']}")
        raise typer.Exit(code=1)

    intent = parse_intent(text)
    if intent is None:
        console.print(
            "[yellow]Perintah tidak dikenali. Coba: 'cek <equipment>', "
            "'aktifkan modul <id> untuk <equipment>', 'daftar aset', 'status'.[/yellow]"
        )
        raise typer.Exit(code=1)

    if intent.risk == RiskTier.WRITE and not yes:
        confirmed = typer.confirm(f"PPLE: jalankan '{intent.name}' {intent.params}?")
        if not confirmed:
            console.print("[yellow]Dibatalkan.[/yellow]")
            raise typer.Exit(code=0)

    _dispatch_intent(intent)


@app.command()
def shell():
    """Shell interaktif bahasa natural (docs/final.md Phase 19). Ketik 'exit' untuk keluar."""
    console.print("[bold]PPLE interactive shell[/bold] - ketik perintah dalam bahasa natural, atau 'exit' untuk keluar.\n")
    while True:
        try:
            text = typer.prompt("pple >")
        except (EOFError, KeyboardInterrupt):
            break
        if text.strip().lower() in {"exit", "quit"}:
            break
        try:
            ask(text, yes=False)
        except typer.Exit:
            pass
        console.print()


def _print_serve_banner(*, api: bool, frontend: bool, host: str = "0.0.0.0", port: int = 8000) -> None:
    _, results = load_modules_from_manifests()
    active_count = sum(1 for r in results if r.status == ModuleStatus.ACTIVE)

    display_host = "localhost" if host in {"0.0.0.0", "127.0.0.1"} else host
    console.print("[bold]Starting PPLE...[/bold]\n")
    if api:
        console.print(f"API          http://{display_host}:{port}")
        console.print(f"Swagger      http://{display_host}:{port}/docs")
    if frontend:
        console.print("Frontend     http://localhost:5173")
    console.print(f"\nEngineering modules : {active_count}")
    console.print("Safety Guardrail     : ON")
    console.print("\n[bold green]PPLE READY[/bold green]\n")


@serve_app.command("api")
def serve_api(
    host: str = typer.Option(None, "--host", help="Default: env HOST or 0.0.0.0"),
    port: int = typer.Option(None, "--port", help="Default: env PORT or 8000"),
):
    """Start the FastAPI server - calls the exact same run_server.main()
    run_api.bat already uses (port-in-use cleanup, 0.0.0.0->127.0.0.1
    fallback), just reachable as `pple serve api` too. Blocks until Ctrl+C."""
    resolved_port = port if port is not None else int(os.environ.get("PORT", "8000"))
    resolved_host = host or os.environ.get("HOST", "0.0.0.0")
    _print_serve_banner(api=True, frontend=False, host=resolved_host, port=resolved_port)

    import run_server

    run_server.main(host=resolved_host, port=resolved_port)


@serve_app.command("frontend")
def serve_frontend():
    """Start the Vite/React dev server - same command run_frontend.bat
    runs (`npm --prefix frontend run dev`). Blocks until Ctrl+C."""
    _print_serve_banner(api=False, frontend=True)
    subprocess.run(["npm", "--prefix", "frontend", "run", "dev"])


@serve_app.command("all")
def serve_all(
    host: str = typer.Option(None, "--host", help="Default: env HOST or 0.0.0.0"),
    port: int = typer.Option(None, "--port", help="Default: env PORT or 8000"),
):
    """Start API and frontend together - same pair run_all.bat launches,
    as two separate OS processes (not two threads: uvicorn's --reload
    supervisor installs signal handlers that only work in a process's main
    thread, so the API runs as its own subprocess here exactly like the
    .bat's `start` does, just without opening a second console window).
    Ctrl+C (or closing the frontend dev server) stops both."""
    resolved_port = port if port is not None else int(os.environ.get("PORT", "8000"))
    resolved_host = host or os.environ.get("HOST", "0.0.0.0")
    _print_serve_banner(api=True, frontend=True, host=resolved_host, port=resolved_port)

    api_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "api_server:app",
        "--host", resolved_host, "--port", str(resolved_port), "--reload",
    ])
    try:
        subprocess.run(["npm", "--prefix", "frontend", "run", "dev"])
    finally:
        api_proc.terminate()
        try:
            api_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            api_proc.kill()


if __name__ == "__main__":
    app()
