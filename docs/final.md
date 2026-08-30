# Engineering AGENT V2
## Dynamic Reliability Engineering Platform + CLI
### Step-by-Step Implementation Plan

---

# 1. TARGET AKHIR

PPLE V2 harus dapat menjalankan tiga interface dari satu Python Core:

```text
                         USER
                          │
            ┌─────────────┼──────────────┐
            │             │              │
            ▼             ▼              ▼
         React UI      Streamlit UI      CLI
            │             │              │
            └─────────────┼──────────────┘
                          │
                       PPLE CORE
                          │
           ┌──────────────┼──────────────┐
           │              │              │
           ▼              ▼              ▼
      Asset Engine   Engineering     Agent Engine
                     Module Engine
                          │
                          ▼
                 Reliability Fusion
                          │
                          ▼
                  Safety Guardrail
                          │
                          ▼
             Report / Recommendation
```

CLI harus menjadi **first-class interface**, bukan sekadar script tambahan.

Contoh penggunaan:

```bash
pple
```

Interactive shell:

```text
PPLE Reliability Engineering Agent
==================================

Site    : PLTU Jeranjang
User    : Engineer
Mode    : Local

pple >
```

Atau command langsung:

```bash
pple status
pple assets list
pple equipment show CWP-1A
pple analyze vibration CWP-1A spectrum.csv
pple analyze dga GT-U1 dga.xlsx
pple chat
pple report CWP-1A
```

---

# 2. PRINSIP ARSITEKTUR

Jangan lagi membuat:

```python
if module == "vibration":
    ...
elif module == "mcsa":
    ...
elif module == "dga":
    ...
```

Gunakan:

```python
module = registry.get(module_id)
result = module.analyze(input_data)
```

Artinya:

```text
Vibration
MCSA
DGA
Tribology
PD
Thermal
BDV
Insulation
Boiler Tube
Custom Module
```

semuanya mengikuti satu kontrak.

---

# 3. STRUKTUR PROJECT TARGET

```text
PPLE/
│
├── pple/
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── events.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── constants.py
│   │
│   ├── database/
│   │   ├── engine.py
│   │   ├── session.py
│   │   ├── migrations/
│   │   └── models/
│   │
│   ├── assets/
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── schemas.py
│   │   └── hierarchy.py
│   │
│   ├── engineering/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── loader.py
│   │   ├── schemas.py
│   │   └── modules/
│   │       ├── vibration/
│   │       ├── mcsa/
│   │       ├── dga/
│   │       ├── tribology/
│   │       ├── partial_discharge/
│   │       └── thermal/
│   │
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── specialist.py
│   │   ├── reliability.py
│   │   ├── reporting.py
│   │   └── safety.py
│   │
│   ├── reliability/
│   │   ├── fusion.py
│   │   ├── health.py
│   │   ├── risk.py
│   │   └── rul.py
│   │
│   ├── knowledge/
│   ├── reports/
│   ├── workorders/
│   │
│   ├── api/
│   │   ├── main.py
│   │   └── routers/
│   │
│   └── cli/
│       ├── main.py
│       ├── shell.py
│       └── commands/
│           ├── serve.py
│           ├── asset.py
│           ├── equipment.py
│           ├── module.py
│           ├── analyze.py
│           ├── chat.py
│           ├── report.py
│           └── doctor.py
│
├── frontend/
├── data/
├── knowledge/
├── plugins/
├── config/
├── tests/
│
├── pyproject.toml
├── .env
└── README.md
```

---

# PHASE 0 — BACKUP & BASELINE

Sebelum refactor:

```bash
git checkout -b feature/pple-v2
git add .
git commit -m "baseline before PPLE V2 refactor"
```

Jalankan:

```bash
python -m unittest discover -s . -p "test_*.py"
python verify_app.py
npm --prefix frontend run build
```

Pastikan kondisi awal hijau.

## PROMPT CODING AGENT — PHASE 0

```text
Anda bekerja pada project PPLE Agent existing.

Sebelum melakukan perubahan apa pun:

1. Pelajari:
   - app.py
   - api_server.py
   - src/
   - src/agents/
   - src/asset_graph.py jika tersedia
   - frontend/
   - tests/
   - CLAUDE.md
   - AGENTS.md

2. Jangan menghapus fitur existing.

3. Buat laporan baseline:
   - existing architecture
   - dependencies
   - API routes
   - data sources
   - test status
   - specialist agents
   - technical debt

4. Identifikasi code yang hard-coded terhadap:
   - Unit
   - Equipment
   - Vibration
   - MCSA
   - DGA
   - Tribology
   - Thermal
   - Partial Discharge

5. Jangan refactor pada tahap ini.

Output:
docs/pple_v2_baseline.md
```

---

# PHASE 1 — BUAT PACKAGE `pple`

Tujuan:

Memisahkan reusable core dari interface.

Buat:

```text
pple/
pple/core/
pple/assets/
pple/engineering/
pple/agents/
pple/reliability/
pple/api/
pple/cli/
```

Existing `src/` jangan langsung dihapus.

Gunakan compatibility layer:

```text
existing src
      ↓
PPLE V2 service
      ↓
migrasi bertahap
```

## PROMPT

```text
Implementasikan skeleton PPLE V2.

Constraints:

- Existing app harus tetap berjalan.
- Jangan pindahkan business logic sekaligus.
- Jangan menghapus src/.
- Buat package baru bernama pple.
- Pisahkan domain layer dari UI.
- Tidak boleh ada import React/Streamlit di pple/core.
- FastAPI, Streamlit dan CLI harus nantinya memakai service yang sama.

Tambahkan:

pple/core
pple/assets
pple/engineering
pple/agents
pple/reliability
pple/database
pple/api
pple/cli

Tambahkan __init__.py yang sesuai.

Tambahkan tests untuk memastikan package bisa diimport.
```

---

# PHASE 2 — DATABASE CONFIGURATION

Gunakan SQLite dahulu.

Production nanti dapat memakai PostgreSQL.

Tambahkan:

```text
plants
units
systems
equipment_types
equipment
equipment_spec_schemas
equipment_spec_values
components
measurement_points
sensors

engineering_modules
equipment_modules
module_parameters
module_standards
module_thresholds

measurements
analysis_runs
diagnostic_results

reports
work_orders
audit_logs
```

---

# PHASE 3 — DYNAMIC ASSET ENGINE

Asset hierarchy:

```text
Organization
    ↓
Site
    ↓
Plant
    ↓
Unit
    ↓
System
    ↓
Equipment
    ↓
Component
    ↓
Measurement Point
    ↓
Sensor
```

`Unit 1`, `Unit 2`, `Unit 3`, dan `COMMON` tidak boleh lagi dibuat sebagai konstanta.

Admin harus bisa:

```text
ADD
EDIT
DISABLE
ARCHIVE
```

untuk:

- Plant
- Unit
- System
- Equipment
- Component
- Measurement Point

Jangan hard delete asset yang sudah mempunyai historical measurement.

Gunakan:

```text
ACTIVE
INACTIVE
ARCHIVED
```

---

# PHASE 4 — EQUIPMENT TYPE & SPECIFICATION ENGINE

Buat model:

```text
EquipmentType
SpecificationSchema
SpecificationField
Equipment
EquipmentSpecification
```

Contoh:

```text
Motor
```

schema:

```text
manufacturer
model
rated_power
rated_voltage
rated_current
rated_speed
frequency
poles
bearing_de
bearing_nde
```

Transformer mempunyai schema berbeda.

Admin bisa menambahkan field sendiri.

Field mendukung:

```text
text
integer
float
boolean
date
enum
unit_value
json
```

## PROMPT

```text
Implementasikan Dynamic Equipment Specification Engine.

Requirement:

1. Equipment type tidak boleh memiliki kolom spesifikasi yang hard-coded.

2. Buat schema-driven specifications.

3. Admin harus dapat:
   - add field
   - edit field
   - deactivate field
   - change required status
   - define unit
   - define datatype
   - define validation

4. Existing equipment_mapping.json tetap dapat diimport.

5. Buat import migration untuk existing equipment.

6. Jangan kehilangan historical equipment identifier.

7. Tambahkan audit trail setiap perubahan specification.
```

---

# PHASE 5 — ENGINEERING MODULE INTERFACE

Buat abstract class:

```python
class EngineeringModule(ABC):

    id: str
    name: str
    version: str

    @abstractmethod
    def validate(self, data):
        ...

    @abstractmethod
    def analyze(self, data, context):
        ...

    @abstractmethod
    def diagnose(self, analysis):
        ...

    @abstractmethod
    def recommend(self, diagnostic):
        ...
```

Kemudian:

```text
VibrationModule
MCSAModule
DGAModule
TribologyModule
PDModule
ThermalModule
```

semuanya implement interface yang sama.

---

# PHASE 6 — MODULE MANIFEST

Setiap module memiliki:

```text
manifest.yaml
```

Contoh:

```yaml
id: vibration

name: Vibration Analysis

version: 1.0.0

category: condition_monitoring

enabled: true

applicable_equipment:
  - MOTOR
  - PUMP
  - FAN
  - TURBINE
  - GENERATOR
  - GEARBOX

capabilities:
  - waveform
  - fft
  - spectrum
  - envelope
  - trend
  - diagnosis

standards:
  - ISO_20816

agent:
  enabled: true

fusion:
  enabled: true
```

---

# PHASE 7 — MODULE REGISTRY

Buat:

```python
registry.register(module)
registry.unregister(module)
registry.get("vibration")
registry.list()
registry.get_for_equipment(equipment_id)
```

Saat aplikasi start:

```text
plugins/
    ↓
scan manifests
    ↓
validate
    ↓
load
    ↓
Module Registry
```

Module yang rusak **tidak boleh membuat seluruh aplikasi gagal start**.

Status:

```text
ACTIVE
DISABLED
ERROR
INCOMPATIBLE
```

---

# PHASE 8 — EQUIPMENT ↔ MODULE MAPPING

Database:

```text
equipment_modules
```

Contoh:

```text
CWP-1A

Vibration       enabled
MCSA            enabled
Thermal         enabled
Tribology       enabled
DGA             disabled
```

Admin bisa menentukan dari UI maupun CLI.

CLI:

```bash
pple equipment modules CWP-1A
```

Output:

```text
CWP-1A Engineering Modules

✓ Vibration
✓ MCSA
✓ Thermal
✓ Tribology
```

Assign:

```bash
pple equipment module-add CWP-1A vibration
```

Remove:

```bash
pple equipment module-remove CWP-1A vibration
```

---

# PHASE 9 — STANDARD DIAGNOSTIC RESULT

Semua domain harus menghasilkan schema yang sama:

```json
{
  "equipment_id": "CWP-1A",
  "module": "vibration",
  "timestamp": "...",

  "health_score": 70,
  "severity": "ALARM",
  "confidence": 0.88,

  "findings": [],

  "faults": [],

  "evidence": [],

  "recommendations": [],

  "standards": [],

  "metadata": {}
}
```

Gunakan Pydantic:

```python
class DiagnosticResult(BaseModel):
    equipment_id: str
    module_id: str
    timestamp: datetime

    health_score: float | None
    severity: Severity
    confidence: float | None

    findings: list[Finding]
    faults: list[FaultHypothesis]
    evidence: list[Evidence]
    recommendations: list[Recommendation]

    standards: list[StandardReference]
```

---

# PHASE 10 — MIGRASI SPECIALIST AGENT

Existing:

```text
Vibration Agent
MCSA Agent
DGA Agent
Tribology Agent
PD Agent
Thermal Agent
```

diubah menjadi:

```text
Specialist Agent Adapter
           │
           ▼
Engineering Module
```

Agent tidak lagi diregistrasi manual di coordinator.

Gunakan:

```python
modules = module_registry.get_for_equipment(equipment.id)

for module in modules:

    specialist = specialist_factory.create(module)

    result = specialist.run(...)
```

## PROMPT

```text
Refactor SubAgentCoordinator menjadi registry-driven.

Current specialist functionality tidak boleh hilang.

Requirements:

- jangan hard-code specialist agent names;
- gunakan EngineeringModuleRegistry;
- hanya module yang enabled untuk equipment yang dijalankan;
- preserve current safety guardrail;
- preserve current LLM persona injection;
- preserve fallback rule-based;
- maintain backwards compatibility API;
- add unit tests.
```

---

# PHASE 11 — RELIABILITY FUSION V2

Input:

```text
DiagnosticResult[]
```

Contoh:

```text
Vibration = 68
MCSA = 75
Thermal = 92
Tribology = 55
```

Fusion Engine:

```text
Normalize
    ↓
Evidence Weighting
    ↓
Confidence Weighting
    ↓
Cross-domain correlation
    ↓
Conflict Resolution
    ↓
Health Index
    ↓
Risk
    ↓
Failure Probability
    ↓
RUL
```

Jangan membuat formula RUL fiktif bila model/data belum tersedia.

Output harus membedakan:

```text
measured
calculated
rule_based
ML_prediction
LLM_interpretation
```

---

# PHASE 12 — CLI FOUNDATION

Gunakan Python:

```text
Typer
```

Dependencies:

```bash
pip install typer rich
```

Optional:

```bash
pip install prompt-toolkit
```

`pyproject.toml`:

```toml
[project.scripts]
pple = "pple.cli.main:app"
```

Setelah:

```bash
pip install -e .
```

user dapat mengetik:

```bash
pple
```

---

# PHASE 13 — CLI COMMAND TREE

Target:

```text
pple

├── status
├── version
├── doctor
│
├── serve
│   ├── api
│   ├── frontend
│   ├── streamlit
│   └── all
│
├── plant
│   ├── list
│   ├── show
│   ├── add
│   └── edit
│
├── unit
│   ├── list
│   ├── add
│   ├── edit
│   └── archive
│
├── equipment
│   ├── list
│   ├── show
│   ├── add
│   ├── edit
│   ├── specs
│   ├── modules
│   ├── module-add
│   └── module-remove
│
├── module
│   ├── list
│   ├── show
│   ├── enable
│   ├── disable
│   ├── install
│   └── validate
│
├── analyze
│   ├── vibration
│   ├── mcsa
│   ├── dga
│   ├── tribology
│   ├── pd
│   └── auto
│
├── reliability
│   ├── health
│   ├── fusion
│   ├── risk
│   └── fleet
│
├── chat
│
├── report
│
├── knowledge
│
└── config
```

---

# PHASE 14 — BASIC CLI

Contoh:

```bash
pple status
```

Output:

```text
PPLE Agent
────────────────────────────

Status          ONLINE
Database        SQLite
Engineering     6 modules
Assets          184
API             Offline
LLM             Local/Ollama
Safety Guard    ENABLED
```

---

# PHASE 15 — `pple doctor`

Ini sangat penting.

```bash
pple doctor
```

Periksa:

```text
✓ Python version
✓ Database
✓ Data directories
✓ Engineering manifests
✓ API configuration
✓ Knowledge index
✓ LLM connection
✓ Ollama
✓ API keys
✓ Frontend
✓ Required libraries
✓ Safety Guardrail
```

Contoh:

```text
PPLE SYSTEM DOCTOR

[OK] Python 3.11
[OK] Database
[OK] Asset Registry

[OK] vibration 1.0
[OK] mcsa 1.0
[OK] dga 1.0

[WARN] Gemini API key not configured
[OK] Ollama detected
[OK] Safety Guardrail enabled

System health: GOOD
```

---

# PHASE 16 — CLI ANALYSIS

Contoh Vibration:

```bash
pple analyze vibration \
  --equipment CWP-1A \
  --file vibration.csv
```

atau:

```bash
pple analyze vibration CWP-1A vibration.csv
```

Flow:

```text
File
 ↓
Equipment validation
 ↓
Module validation
 ↓
Data quality
 ↓
Analysis
 ↓
Diagnosis
 ↓
Severity
 ↓
Recommendation
 ↓
Save Result
```

Output:

```text
VIBRATION ANALYSIS

Equipment
CWP-1A

Data Quality
PASS

Overall RMS
9.23 mm/s

Severity
ALARM

Findings
• dominant 1X RPM
• harmonics detected

Possible fault
Misalignment

Recommendation
Inspect coupling alignment.
```

---

# PHASE 17 — AUTO ANALYSIS

Ini akan menjadi salah satu fitur terkuat.

Command:

```bash
pple analyze auto report.xlsx
```

Agent mencoba menentukan:

```text
data type
    ↓
equipment
    ↓
engineering module
    ↓
parser
    ↓
analysis
```

Tetapi jika confidence rendah:

```text
Could not confidently identify domain.

Possible:
1. MCSA
2. Vibration

Specify:

pple analyze vibration ...
```

Jangan membiarkan LLM menentukan domain tanpa validation.

---

# PHASE 18 — INTERACTIVE CLI AGENT

Command:

```bash
pple chat
```

Output:

```text
╭──────────────────────────────────╮
│ PPLE Reliability Engineering AI │
╰──────────────────────────────────╯

Plant : PLTU Jeranjang
Mode  : Engineering
Safety: Enabled

pple >
```

Contoh:

```text
pple > bagaimana kondisi CWP 1A?
```

Agent:

```text
Searching asset...
Loading CBM results...

Latest:
Vibration : Alarm
MCSA      : Normal
Thermal   : Normal
Tribology : Watch

Overall health: 71/100

Primary concern:
Possible alignment / mechanical condition.

Would you like:
1. Detailed analysis
2. Trend
3. Recommendation
4. Generate report
```

---

# PHASE 19 — CLI NATURAL LANGUAGE COMMAND

Tahap selanjutnya:

```text
pple > tambahkan Unit 4
```

Agent mengubahnya menjadi:

```text
Intent:
CREATE_UNIT

Name:
UNIT 4
```

Untuk operasi konfigurasi:

```text
PPLE:
Create UNIT 4?

[y/N]
```

Untuk destructive operation wajib confirm.

---

# PHASE 20 — SAFETY CLASSIFICATION

Command dibagi:

```text
READ
WRITE
HIGH-RISK
```

READ:

```bash
pple equipment list
pple status
pple analyze
```

WRITE:

```bash
pple equipment add
pple unit add
```

HIGH-RISK:

```text
trip
shutdown
start
stop equipment
breaker open
breaker close
```

CLI tidak boleh langsung mengeksekusi operasi HIGH-RISK.

Existing Safety Guardrail harus tetap menjadi layer wajib; source project saat ini juga sudah mendefinisikan bahwa Trip/Shutdown harus diblokir sampai ada Human-in-the-Loop.

---

# PHASE 21 — CLI LLM PROVIDER

Buat interface:

```python
LLMProvider
```

Implementasi:

```text
OllamaProvider
OpenAIProvider
GeminiProvider
AnthropicProvider
DisabledProvider
```

CLI:

```bash
pple config llm
```

atau:

```bash
pple config set llm.provider ollama
```

Model:

```bash
pple config set llm.model qwen3:8b
```

---

# PHASE 22 — OFFLINE MODE

PPLE harus tetap bekerja tanpa internet.

```bash
pple --offline chat
```

Offline stack:

```text
Python rules
      +
Local Database
      +
Local Knowledge
      +
FAISS/Chroma
      +
Ollama
```

LLM tidak boleh menjadi source of truth untuk threshold engineering.

---

# PHASE 23 — SERVE FROM CLI

Jangan lagi mengandalkan banyak `.bat`.

Gunakan:

```bash
pple serve api
```

FastAPI:

```text
http://localhost:8000
```

Frontend:

```bash
pple serve frontend
```

Semua:

```bash
pple serve all
```

Output:

```text
Starting PPLE...

API          http://localhost:8000
Swagger      http://localhost:8000/docs
Frontend     http://localhost:5173

Engineering modules : 6
Safety Guardrail     : ON

PPLE READY
```

Existing `.bat` tetap dapat dipertahankan sebagai compatibility wrapper karena project sekarang memang menggunakan `run_api.bat`, `run_frontend.bat`, dan `run_all.bat`.

---

# PHASE 24 — GENERIC REST API

Frontend dan CLI tidak boleh memiliki business logic sendiri.

Contoh API:

```text
/api/v2/plants
/api/v2/units
/api/v2/systems
/api/v2/equipment
/api/v2/equipment-types

/api/v2/modules
/api/v2/modules/{id}

/api/v2/equipment/{id}/modules

/api/v2/analysis
/api/v2/analysis/{id}

/api/v2/reliability/{equipment}

/api/v2/agent/chat
```

Existing API lama jangan langsung dihapus karena versi sekarang mempunyai banyak endpoint domain-specific.

Gunakan:

```text
/api/*
```

legacy.

Dan:

```text
/api/v2/*
```

new architecture.

---

# PHASE 25 — FRONTEND DYNAMIC

React jangan lagi:

```javascript
const modules = [
 "Vibration",
 "MCSA",
 "DGA"
]
```

Gunakan:

```javascript
GET /api/v2/modules
```

Frontend kemudian generate menu:

```text
Engineering
├── Vibration
├── MCSA
├── DGA
├── Tribology
└── Custom Module
```

Jika BDV ditambahkan dari Admin:

```text
Engineering
├── ...
└── BDV
```

tanpa edit `App.jsx`.

---

# PHASE 26 — ADMIN CONFIGURATION

Buat:

```text
Administration

Plant Configuration
Unit Configuration
System Configuration
Equipment Types
Equipment Specs
Engineering Modules
Module Mapping
Standards
Thresholds
Users & Roles
AI Settings
```

---

# PHASE 27 — KNOWLEDGE PER MODULE

Struktur:

```text
knowledge/

vibration/
mcsa/
dga/
tribology/
pd/
thermal/

standards/
manual/
sop/
training/
```

Manifest module dapat menentukan:

```yaml
knowledge_namespace:
  - vibration
  - standards
```

---

# PHASE 28 — EVENT BUS

Tambahkan internal events:

```text
equipment.created
equipment.updated

measurement.uploaded

analysis.started
analysis.completed
analysis.failed

diagnostic.created

severity.changed

recommendation.created

workorder.requested
```

Ini penting agar sistem agentic tidak saling tightly coupled.

---

# PHASE 29 — AUDIT LOG

Simpan:

```text
WHO
WHAT
WHEN
OLD VALUE
NEW VALUE
SOURCE
```

Contoh:

```text
2026-08-29
Engineer

Equipment CWP-1A
rated_speed

OLD
980 RPM

NEW
985 RPM

SOURCE
CLI
```

---

# PHASE 30 — TESTING

Minimum:

```text
tests/

test_asset_service.py
test_equipment_schema.py
test_module_registry.py
test_module_loader.py

test_vibration_module.py
test_mcsa_module.py
test_dga_module.py

test_diagnostic_schema.py
test_fusion_engine.py

test_safety.py

test_cli_asset.py
test_cli_module.py
test_cli_analyze.py

test_api_v2.py
```

Setiap module baru wajib lulus:

```text
manifest validation
input validation
output contract
safety test
diagnostic schema
registry load
```

---

# MASTER PROMPT IMPLEMENTASI

Gunakan prompt berikut untuk Claude Code / Codex / OpenCode:

```text
You are the lead software architect implementing PPLE Agent V2.

PPLE is an AI O&M Reliability Engineering platform.

IMPORTANT:
Do not rebuild the project from scratch.

Preserve all existing working functionality.

The current system contains:
- Python core
- FastAPI backend
- React/Vite frontend
- Streamlit dashboard
- specialist engineering agents
- reliability fusion
- safety guardrail
- engineering knowledge base
- reporting
- existing operational data

TARGET ARCHITECTURE:

Transform PPLE into a dynamic and configurable Reliability Engineering Platform.

The following entities MUST NOT be hard-coded:

- Plant
- Unit
- System
- Equipment
- Equipment Type
- Equipment Specification
- Engineering Module
- Engineering Specialist Agent

Asset hierarchy:

Organization
→ Site
→ Plant
→ Unit
→ System
→ Equipment
→ Component
→ Measurement Point
→ Sensor/Data Source

Engineering capabilities must use plugin/module architecture.

Examples:

Vibration
MCSA
DGA
Tribology
Partial Discharge
Thermal

Future modules must be installable without modifying the central orchestrator.

Examples:

BDV
Insulation Resistance
Boiler Tube Inspection
Ultrasound
Performance Monitoring
Electrical Testing
Custom Module

Create:

EngineeringModule interface
EngineeringModuleRegistry
ModuleManifest
ModuleLoader
ModuleValidator

Every engineering module must output the same DiagnosticResult schema.

DiagnosticResult must include:

equipment
module
timestamp
health score
severity
confidence
findings
fault hypotheses
evidence
recommendations
standard references
metadata

Reliability Fusion must consume DiagnosticResult[], not domain-specific objects.

Do not allow LLM output to override deterministic engineering calculations.

Rule-based and engineering standards remain the source of truth.

LLM is an assistance and interpretation layer only.

Safety Guardrail must remain mandatory.

HIGH-RISK commands such as:
- trip
- shutdown
- breaker operation
- start/stop equipment

must never be executed automatically.

HUMAN-IN-THE-LOOP is mandatory.

Also implement CLI as a first-class interface.

CLI command:

pple

Use:
Python Typer + Rich.

Required commands:

pple status
pple doctor

pple serve api
pple serve frontend
pple serve all

pple plant
pple unit
pple equipment

pple module list
pple module show
pple module enable
pple module disable

pple equipment modules
pple equipment module-add
pple equipment module-remove

pple analyze vibration
pple analyze mcsa
pple analyze dga
pple analyze tribology
pple analyze auto

pple reliability health
pple reliability fusion

pple chat

pple report

pple knowledge

pple config

Interactive CLI must support:

pple chat

and optionally:

pple shell

Both CLI, FastAPI, React and Streamlit MUST use the same Python business logic.

Never duplicate analysis logic in the CLI or frontend.

Implement changes incrementally.

After every phase:

1. Run Python tests.
2. Run existing verification.
3. Build React frontend.
4. Confirm legacy functionality still works.
5. Document changed files.
6. Commit a logical checkpoint.

Do NOT perform a big-bang rewrite.
```

---

# IMPLEMENTATION ORDER

Kerjakan dengan urutan:

```text
1  Baseline
↓
2  PPLE package
↓
3  Database
↓
4  Asset Engine
↓
5  Equipment Type
↓
6  Dynamic Specification
↓
7  Engineering Module Interface
↓
8  Module Registry
↓
9  Module Loader
↓
10 Migrate Vibration
↓
11 Migrate MCSA
↓
12 Migrate DGA
↓
13 Migrate Tribology
↓
14 Migrate PD
↓
15 Migrate Thermal
↓
16 Standard DiagnosticResult
↓
17 Reliability Fusion V2
↓
18 Agent Registry
↓
19 CLI
↓
20 API V2
↓
21 Dynamic React UI
↓
22 Admin Configuration
↓
23 Knowledge/RAG
↓
24 Reporting
↓
25 Audit
↓
26 Security
↓
27 Integration
↓
28 Tests
```

---

# RECOMMENDED FIRST MVP

Jangan langsung mengerjakan seluruh modul.

Implementasi pertama:

```text
PPLE CORE
   │
   ├── Asset Engine
   │
   ├── Equipment Engine
   │
   ├── Module Registry
   │
   └── CLI
           │
           ▼
       VIBRATION
```

Target MVP:

```bash
pple equipment add
```

↓

```bash
pple equipment module-add CWP-1A vibration
```

↓

```bash
pple analyze vibration CWP-1A vibration.csv
```

↓

```bash
pple reliability health CWP-1A
```

↓

```bash
pple report CWP-1A
```

Setelah flow ini stabil:

```text
Vibration
   ↓
MCSA
   ↓
DGA
   ↓
Tribology
   ↓
PD
   ↓
Thermal
```

Dengan strategi ini, PPLE berevolusi dari aplikasi multi-CBM yang relatif fixed menjadi **Reliability Engineering Operating Platform** yang dapat dikonfigurasi untuk plant, unit, equipment, metode inspeksi, engineering module, AI agent, dan interface baru tanpa melakukan rewrite pada core.