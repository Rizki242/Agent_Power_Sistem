"""MCSA Control Design System & Modern Theme.

Provides modern CSS variables, typography, sleek card elevations,
status pills, and UI micro-interactions for Streamlit.
"""


def get_modern_theme_css() -> str:
    return """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap');

      :root {
        --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        --font-mono: 'JetBrains Mono', monospace;

        --mcsa-bg: #f8fafc;
        --mcsa-card: #ffffff;
        --mcsa-border: #e2e8f0;
        --mcsa-border-focus: #94a3b8;
        
        --mcsa-slate-900: #0f172a;
        --mcsa-slate-800: #1e293b;
        --mcsa-slate-700: #334155;
        --mcsa-slate-600: #475569;
        --mcsa-slate-500: #64748b;
        --mcsa-slate-400: #94a3b8;
        --mcsa-slate-200: #e2e8f0;
        --mcsa-slate-100: #f1f5f9;
        --mcsa-slate-50:  #f8fafc;

        /* Primary Accent (Cobalt & Cyan Teal) */
        --mcsa-primary: #0284c7;
        --mcsa-primary-hover: #0369a1;
        --mcsa-primary-light: #e0f2fe;
        --mcsa-primary-text: #0369a1;

        /* Status Colors */
        --mcsa-ok-bg: #ecfdf5;
        --mcsa-ok-border: #a7f3d0;
        --mcsa-ok-text: #065f46;
        --mcsa-ok-dot: #10b981;

        --mcsa-warn-bg: #fffbeb;
        --mcsa-warn-border: #fde68a;
        --mcsa-warn-text: #92400e;
        --mcsa-warn-dot: #f59e0b;

        --mcsa-err-bg: #fef2f2;
        --mcsa-err-border: #fecaca;
        --mcsa-err-text: #991b1b;
        --mcsa-err-dot: #ef4444;

        --shadow-xs: 0 1px 2px 0 rgba(0, 0, 0, 0.04);
        --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.07), 0 1px 2px -1px rgba(0, 0, 0, 0.07);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.06);
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
      }

      /* Global App Reset & Typography */
      html, body, [class*="css"] {
        font-family: var(--font-sans) !important;
        color: var(--mcsa-slate-800);
        letter-spacing: -0.01em;
      }

      .stApp {
        background-color: var(--mcsa-bg) !important;
      }

      /* Main container padding */
      .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 3rem !important;
        max-width: 1380px !important;
      }

      /* Sidebar Refinement */
      [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid var(--mcsa-border) !important;
        box-shadow: var(--shadow-xs);
      }
      [data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem !important;
      }

      /* Clean Headers */
      h1 {
        font-weight: 800 !important;
        font-size: 1.75rem !important;
        color: var(--mcsa-slate-900) !important;
        letter-spacing: -0.025em !important;
        margin-bottom: 0.75rem !important;
      }
      h2 {
        font-weight: 700 !important;
        font-size: 1.35rem !important;
        color: var(--mcsa-slate-900) !important;
        letter-spacing: -0.02em !important;
        margin-top: 1rem !important;
        margin-bottom: 0.5rem !important;
      }
      h3 {
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        color: var(--mcsa-slate-800) !important;
      }

      /* Metric KPI Cards with Sleek Shadows */
      [data-testid="stMetric"] {
        background-color: var(--mcsa-card) !important;
        border: 1px solid var(--mcsa-border) !important;
        border-radius: var(--radius-md) !important;
        padding: 16px 20px !important;
        box-shadow: var(--shadow-sm) !important;
        transition: transform 0.18s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.18s cubic-bezier(0.4, 0, 0.2, 1);
      }
      [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md) !important;
        border-color: #cbd5e1 !important;
      }
      [data-testid="stMetricLabel"] p {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        color: var(--mcsa-slate-500) !important;
        letter-spacing: 0.04em !important;
      }
      [data-testid="stMetricValue"] {
        font-weight: 800 !important;
        color: var(--mcsa-slate-900) !important;
        font-family: var(--font-sans) !important;
      }

      /* Dataframe and Chart Wrapper */
      [data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {
        background-color: var(--mcsa-card) !important;
        border: 1px solid var(--mcsa-border) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-xs) !important;
        overflow: hidden;
      }

      /* Tabs Modernization */
      .stTabs [data-baseweb="tab-list"] {
        background-color: var(--mcsa-slate-100) !important;
        border-radius: var(--radius-md) !important;
        padding: 4px !important;
        gap: 4px !important;
        border: 1px solid var(--mcsa-border) !important;
      }
      .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        padding: 8px 16px !important;
        color: var(--mcsa-slate-600) !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.15s ease-in-out !important;
      }
      .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: var(--mcsa-primary) !important;
        box-shadow: var(--shadow-xs) !important;
      }

      /* Expanders */
      [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid var(--mcsa-border) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-xs) !important;
        margin-bottom: 12px !important;
      }
      [data-testid="stExpander"] summary {
        font-weight: 600 !important;
        color: var(--mcsa-slate-800) !important;
      }

      /* Buttons & CTAs */
      .stButton button {
        font-weight: 600 !important;
        border-radius: var(--radius-sm) !important;
        letter-spacing: -0.01em !important;
        transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
      }
      .stButton button[kind="primary"] {
        background-color: var(--mcsa-primary) !important;
        border: none !important;
        box-shadow: 0 2px 4px rgba(2, 132, 199, 0.25) !important;
      }
      .stButton button[kind="primary"]:hover {
        background-color: var(--mcsa-primary-hover) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(2, 132, 199, 0.35) !important;
      }
      .stButton button[kind="secondary"] {
        border: 1px solid var(--mcsa-border) !important;
        background-color: #ffffff !important;
        color: var(--mcsa-slate-700) !important;
      }
      .stButton button[kind="secondary"]:hover {
        background-color: var(--mcsa-slate-50) !important;
        border-color: var(--mcsa-slate-400) !important;
        color: var(--mcsa-slate-900) !important;
      }

      /* Brand Header & Navigation Pills in Sidebar */
      .mcsa-header-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #ffffff;
        padding: 16px 18px;
        border-radius: var(--radius-md);
        margin-bottom: 20px;
        box-shadow: var(--shadow-sm);
      }
      .mcsa-header-title {
        font-size: 1.05rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .mcsa-header-sub {
        font-size: 0.76rem;
        color: #94a3b8;
        margin-top: 2px;
      }
      .mcsa-pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        display: inline-block;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        animation: mcsaPulse 2s infinite;
      }
      @keyframes mcsaPulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
      }

      /* Sidebar filter section (below native st.navigation nav) */
      .mcsa-group {
        font-size: 0.68rem;
        font-weight: 800;
        text-transform: uppercase;
        color: var(--mcsa-slate-400);
        letter-spacing: 0.08em;
        margin: 16px 0 6px 4px;
      }

      .mcsa-period {
        background-color: var(--mcsa-slate-100);
        color: var(--mcsa-slate-700);
        font-size: 0.78rem;
        padding: 8px 12px;
        border-radius: var(--radius-sm);
        margin-top: 6px;
      }

      /* Custom scrollbars */
      ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
      }
      ::-webkit-scrollbar-track {
        background: transparent;
      }
      ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 4px;
      }
      ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
      }
    </style>
    """


def render_page_header(st, title: str, subtitle: str = "", badge: str = ""):
    """Render a page header using native Streamlit elements.

    Deliberately not raw HTML: Streamlit's markdown renderer auto-promotes a
    bare <h1>..<h6> into its own anchor-linked heading widget, which breaks
    when nested inside a custom flex <div> (observed: the heading collapses
    to a near-zero-width column and wraps one character per line).
    """
    if badge:
        col_title, col_badge = st.columns([5, 1], vertical_alignment="center")
        with col_title:
            st.title(title, anchor=False)
        with col_badge:
            st.badge(badge)
    else:
        st.title(title, anchor=False)
    if subtitle:
        st.caption(subtitle)
    st.divider()


def render_data_disclaimer_banner(st, message: str = "Data Contoh - Belum Terverifikasi dari Sumber Asli") -> None:
    """Persistent warning banner for pages whose underlying data is not yet sourced from real measurements."""
    st.warning(message, icon=":material/report:")
