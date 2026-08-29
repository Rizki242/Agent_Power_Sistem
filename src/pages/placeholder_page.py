"""Lightweight placeholder for top-level nav destinations that don't have a
Streamlit UI yet (Reliability, Work Orders, Help & Support - see docs/desain.png).
"""

from src.components.theme import render_page_header


def render_placeholder_page(st, title: str, description: str):
    render_page_header(st, title, description)
    st.info("Halaman ini belum tersedia di Streamlit UI. Fitur ini direncanakan pada fase berikutnya.")
