## Plant
Flowchart struktur UI 

flowchart TD

    A[APPLICATION SHELL] --> B[LEFT SIDEBAR]
    A --> C[MAIN WORKSPACE]
    A --> D[TOP BAR]

    %% SIDEBAR
    B --> B1[Workspace / Project]
    B1 --> B2[PLTU / Site]
    B2 --> B3[UNIT 1]
    B2 --> B4[UNIT 2]
    B2 --> B5[UNIT 3]
    B2 --> B6[COMMON]

    %% UNIT 1
    B3 --> E1[Generator Transformer]
    B3 --> E2[Generator]
    B3 --> E3[Motor 6.6 kV]
    B3 --> E4[Boiler]
    B3 --> E5[Turbine]
    B3 --> E6[Auxiliary Equipment]

    %% EQUIPMENT TREE
    E1 --> F1[Overview]
    E1 --> F2[Documents]
    E1 --> F3[CBM Analysis]
    E1 --> F4[Database]
    E1 --> F5[Reports]
    E1 --> F6[AI Assistant]

    %% CBM
    F3 --> G1[DGA]
    F3 --> G2[Vibration]
    F3 --> G3[MCSA]
    F3 --> G4[Tribology]
    F3 --> G5[Partial Discharge]
    F3 --> G6[Thermal]

    %% CONTENT ACTION
    B3 --> H[+ ADD CONTENT]
    H --> H1[New Analysis]
    H --> H2[Page]
    H --> H3[Live Document]
    H --> H4[Database]
    H --> H5[Folder]
    H --> H6[Upload File]
    H --> H7[Report]
    H --> H8[Dashboard]

    %% MAIN AREA
    C --> C1[Breadcrumb]
    C --> C2[Page Header]
    C --> C3[Content Area]
    C --> C4[Right Context Panel]

    C3 --> I1[Dashboard]
    C3 --> I2[Editor]
    C3 --> I3[Analysis Workspace]
    C3 --> I4[Database Table]
    C3 --> I5[Report Viewer]
    C3 --> I6[AI Chat]

    %% TOP BAR
    D --> D1[Search]
    D --> D2[Command Palette]
    D --> D3[Notifications]
    D --> D4[Settings]
    D --> D5[User Profile]


┌──────────────────────────────────────────────────────────────────────┐
│ Logo     Search / Command                       🔔   ⚙️   Profile    │
├──────────────────────┬───────────────────────────────────────────────┤
│ LEFT SIDEBAR         │ MAIN WORKSPACE                                │
│                      │                                               │
│ ▼ PLTU Jeranjang     │ PLTU / UNIT 1 / Generator Transformer         │
│                      │                                               │
│   ▼ UNIT 1         + │ Generator Transformer                         │
│     ▼ GT-01          │ ───────────────────────────────────────────    │
│       • Overview     │                                               │
│       • Documents    │   [ Health ] [ Alert ] [ Last Analysis ]      │
│       ▼ CBM          │                                               │
│          • DGA       │   Main content                                │
│          • Vibration │                                               │
│          • Thermal   │   Chart / Table / Document / Analysis         │
│       • Database     │                                               │
│       • Reports      │                                               │
│                      │                                               │
│   ▶ UNIT 2           │                                               │
│   ▶ UNIT 3           │                                               │
│   ▶ COMMON           │                                               │
│                      │                                               │
│ + Create             │                                               │
│                      │                                               │
│ AI Assistant         │                                               │
│ Settings             │                                               │
└──────────────────────┴───────────────────────────────────────────────┘

Saat tombol + di samping UNIT 1, GT-01, atau folder ditekan, menu floating dibuat seperti Confluence:

                    ┌──────────────────────────┐
                    │ Start from Template      │
                    ├──────────────────────────┤
                    │ ✨ AI Analysis            │
                    │ 📄 Engineering Page       │
                    │ 📡 CBM Analysis           │
                    │ 📊 Dashboard              │
                    │ 🗃 Database               │
                    │ 🔗 Smart Link             │
                    ├──────────────────────────┤
                    │ 📁 Folder                 │
                    │ ⬆ Upload Data             │
                    │ 📑 Generate Report        │
                    └──────────────────────────┘

hierarchy datanya sebaiknya jangan hardcoded. Gunakan struktur dinamis

WORKSPACE
│
├── SITE / PLANT
│   │
│   ├── UNIT
│   │   │
│   │   ├── SYSTEM
│   │   │   │
│   │   │   └── EQUIPMENT
│   │   │       │
│   │   │       ├── Overview
│   │   │       ├── Specification
│   │   │       ├── Documents
│   │   │       ├── Data History
│   │   │       ├── CBM
│   │   │       │   ├── Vibration
│   │   │       │   ├── MCSA
│   │   │       │   ├── DGA
│   │   │       │   ├── Tribology
│   │   │       │   ├── PD
│   │   │       │   └── Thermal
│   │   │       │
│   │   │       ├── AI Diagnosis
│   │   │       ├── Recommendations
│   │   │       └── Reports
│   │
│   └── COMMON
│
└── KNOWLEDGE BASE
    ├── ISO
    ├── IEEE
    ├── IEC
    ├── OEM Manuals
    └── Internal Procedures


# gunakan konsep generic tree node. Jadi sidebar tidak membedakan secara kaku apakah sesuatu merupakan Unit, Equipment, Folder, Analysis, atau Report.

interface TreeNode {
  id: string;
  name: string;

  type:
    | "plant"
    | "unit"
    | "system"
    | "equipment"
    | "folder"
    | "analysis"
    | "database"
    | "document"
    | "dashboard"
    | "report";

  icon?: string;

  parentId?: string;

  children?: TreeNode[];

  metadata?: {
    equipmentId?: string;
    cbmType?: string;
    status?: string;
    severity?: number;
  };
}

UNIT 1
   +
   ├─ Tambah Equipment
   ├─ Tambah Folder
   ├─ Tambah Database
   ├─ Tambah CBM
   ├─ Tambah Dashboard
   └─ Tambah Report


#Arsitectur React 

src/
│
├── app/
│   ├── App.tsx
│   ├── router.tsx
│   └── providers.tsx
│
├── layouts/
│   └── WorkspaceLayout.tsx
│
├── components/
│   │
│   ├── sidebar/
│   │   ├── Sidebar.tsx
│   │   ├── TreeView.tsx
│   │   ├── TreeNode.tsx
│   │   ├── NodeActions.tsx
│   │   └── CreateMenu.tsx
│   │
│   ├── navigation/
│   │   ├── Breadcrumb.tsx
│   │   └── Topbar.tsx
│   │
│   ├── workspace/
│   │   ├── WorkspaceHeader.tsx
│   │   ├── WorkspaceContent.tsx
│   │   └── ContextPanel.tsx
│   │
│   ├── dashboard/
│   ├── database/
│   ├── report/
│   ├── document/
│   └── chat/
│
├── modules/
│   ├── vibration/
│   ├── mcsa/
│   ├── dga/
│   ├── tribology/
│   ├── partial-discharge/
│   └── thermal/
│
├── stores/
│   ├── workspaceStore.ts
│   ├── treeStore.ts
│   └── uiStore.ts
│
├── services/
│   ├── api.ts
│   ├── analysis.ts
│   └── aiAgent.ts
│
└── types/
    ├── workspace.ts
    ├── equipment.ts
    └── analysis.ts

#flow interaksi 

flowchart LR

A[User pilih Unit] --> B[Expand Tree]

B --> C[User pilih Equipment]

C --> D[Load Equipment Workspace]

D --> E{Pilih aktivitas}

E -->|Overview| F[Equipment Dashboard]

E -->|CBM| G[Pilih Metode]

G --> G1[Vibration]
G --> G2[MCSA]
G --> G3[DGA]
G --> G4[Tribology]
G --> G5[PD]
G --> G6[Thermal]

G1 --> H[Upload / Select Data]
G2 --> H
G3 --> H
G4 --> H
G5 --> H
G6 --> H

H --> I[Validation Engine]

I --> J[Analysis Engine]

J --> K[Diagnosis Engine]

K --> L[Severity / Health Index]

L --> M[AI Recommendation]

M --> N[Save to Database]

N --> O[Generate Report]