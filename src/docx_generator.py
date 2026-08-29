from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
import pandas as pd
import io
import re
from src.analytics import build_risk_summary
from src.standards import generate_esa_mcsa_quick_recommendations
from src.ppt_theme import canon_status, STATUS_TINT_HEX

def create_docx(df_latest, context=None):
    """
    Generates a DOCX file from the latest MCSA data.
    Returns a BytesIO object containing the DOCX file.
    """
    context = context or {}
    doc = Document()
    
    # --- Style Definitions ---
    # (We can use default styles or customize)
    
    # --- Title Page ---
    title = doc.add_heading('LAPORAN BULANAN MCSA & KONDISI EQUIPMENT', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph() # Spacer
    
    period_start = context.get('period_start')
    period_end = context.get('period_end')
    unit_label = context.get('unit_label', 'PLTU Jeranjang')
    volt_label = context.get('volt_label', 'Semua Voltage')
    compliance = context.get('compliance') # {expected, updated, missing, pct}
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"Unit: {unit_label}\n")
    run.font.size = Pt(14)
    run = p.add_run(f"Voltage: {volt_label}\n")
    run.font.size = Pt(14)
    if period_start and period_end:
        run = p.add_run(f"Periode: {period_start} s/d {period_end}\n")
        run.font.size = Pt(14)
    
    if compliance:
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"Compliance Sampling: {compliance.get('pct', 0):.1f}%\n")
        run.font.size = Pt(12)
        run = p.add_run(f"(Updated: {compliance.get('updated', 0)} / Total: {compliance.get('expected', 0)})")
        run.italic = True

    doc.add_page_break()
    
    # --- 1. RINGKASAN STATUS EQUIPMENT ---
    doc.add_heading('1. RINGKASAN STATUS EQUIPMENT', level=1)
    
    df_cond = pd.DataFrame()
    if isinstance(df_latest, pd.DataFrame) and not df_latest.empty and 'Parameter' in df_latest.columns:
        df_cond = df_latest[df_latest['Parameter'].astype(str) == 'Kondisi'].copy()

    def _canon_status(s) -> str:
        return canon_status(s)

    def _get_status_color(status_name):
        """Warna shading sel, memakai palet tema yang sama dengan laporan PPT.

        Dipakai varian tint (bukan warna penuh) karena isi sel berupa teks
        gelap; fill jenuh membuat teks tidak terbaca.
        """
        s = canon_status(status_name)
        return f"{STATUS_TINT_HEX.get(s, 0xFFFFFF):06X}"

    if not df_cond.empty:
        df_cond['_status_clean'] = df_cond['Raw_Value'].astype(str).map(_canon_status)
        
        # summary table
        status_order = ['Normal', 'Alarm', 'High', 'Standby', 'Unknown']
        status_counts = df_cond['_status_clean'].value_counts().to_dict()
        
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Status Kondisi'
        hdr_cells[1].text = 'Jumlah Equipment'
        
        for st_name in status_order:
            row_cells = table.add_row().cells
            row_cells[0].text = st_name
            row_cells[1].text = str(int(status_counts.get(st_name, 0)))
            
            # Shading
            color = _get_status_color(st_name)
            shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>')
            row_cells[0]._tc.get_or_add_tcPr().append(shading_elm)

        doc.add_paragraph()
        
        # List of Equipment Status (Summary Table for ALL)
        doc.add_heading('Status Per Equipment', level=2)
        
        # Sort by Unit and Voltage if available
        sort_cols = []
        if 'Unit_Name' in df_cond.columns: sort_cols.append('Unit_Name')
        if 'Voltage_Level' in df_cond.columns: sort_cols.append('Voltage_Level')
        sort_cols.append('Equipment')
        df_cond_sorted = df_cond.sort_values(by=sort_cols)
        
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Equipment'
        hdr_cells[1].text = 'Unit'
        hdr_cells[2].text = 'Voltage'
        hdr_cells[3].text = 'Status'
        
        for _, row in df_cond_sorted.iterrows():
            row_cells = table.add_row().cells
            row_cells[0].text = str(row.get('Full_Name', row.get('Equipment', '')))
            row_cells[1].text = str(row.get('Unit_Name', ''))
            row_cells[2].text = str(row.get('Voltage_Level', ''))
            
            st_val = row.get('_status_clean', 'Unknown')
            row_cells[3].text = st_val
            
            # Color coding status cell
            color = _get_status_color(st_val)
            shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>')
            row_cells[3]._tc.get_or_add_tcPr().append(shading_elm)

        risk_rows = build_risk_summary(df_latest, top_n=10)
        if risk_rows:
            doc.add_paragraph()
            doc.add_heading('Top 10 Equipment Risiko Tertinggi', level=2)
            risk_table = doc.add_table(rows=1, cols=4)
            risk_table.style = 'Table Grid'
            hdr_cells = risk_table.rows[0].cells
            hdr_cells[0].text = 'Equipment'
            hdr_cells[1].text = 'Unit'
            hdr_cells[2].text = 'Health Score'
            hdr_cells[3].text = 'Driver'
            for row in risk_rows:
                row_cells = risk_table.add_row().cells
                row_cells[0].text = str(row.get('Full_Name') or row.get('Equipment') or '-')
                row_cells[1].text = str(row.get('Unit_Name') or '-')
                row_cells[2].text = str(row.get('Health Score') or '-')
                row_cells[3].text = str(row.get('Drivers') or '-')

    doc.add_page_break()
    
    # --- 2. DETAIL MEASUREMENT ---
    doc.add_heading('2. DETAIL PENGUKURAN', level=1)
    
    def _unit_limit(param_name: str):
        p = (param_name or '').strip().lower()
        if p in {'dev voltage', 'dev voltage %'}: return '%', 'Alarm >1%, High >2%'
        if p in {'dev current', 'dev current %'}: return '%', 'Alarm >5%, High >10%'
        if p in {'thd voltage %'}: return '%', 'Alarm >5%, High >8%'
        if p in {'thd current %'}: return '%', 'Alarm >5%, High >8%'
        if p == 'load': return '%', 'Valid \u226540%, Monitoring \u226520%'
        if p.startswith('current'): return 'A', ''
        if p.startswith('voltage'): return 'V', ''
        if p in {'real power', 'power'}: return 'kW', ''
        if p in {'upper sideband', 'lower sideband'}: return 'dB', ''
        if p in {'rotorbar level %'}: return '%', ''
        return '', ''

    def _format_value(param_name: str, raw_value, num_value):
        v = num_value if (isinstance(num_value, (int, float)) and not pd.isna(num_value)) else raw_value
        if isinstance(v, (int, float)) and not pd.isna(v):
            p = (param_name or '').strip().lower()
            if p in {'dev voltage', 'dev voltage %', 'dev current', 'dev current %', 'thd voltage %', 'thd current %', 'load', 'rotorbar level %', 'upper sideband', 'lower sideband'}:
                return f"{float(v):.1f}"
            if p.startswith('current') or p.startswith('voltage'):
                return f"{float(v):.2f}"
            if p in {'real power', 'power'}:
                return f"{float(v):.3f}"
            return f"{v}"
        if isinstance(v, str):
            s = v.replace('\r', ' ').replace('\n', ' ')
            return ' '.join(s.split()) or "-"
        return str(v) if v is not None else "-"

    equipments = df_latest['Equipment'].unique()
    
    for eq in equipments:
        doc.add_heading(f"Equipment: {eq}", level=2)
        
        eq_data = df_latest[df_latest['Equipment'] == eq].copy()
        if 'Parameter' not in eq_data.columns:
            continue
            
        eq_data = eq_data.dropna(subset=['Parameter'])
        
        # Sort parameters
        preferred_order = [
            'Kondisi', 'Bearing', 'Load', 'power factor', 'Real Power',
            'Voltage 1', 'Voltage 2', 'Voltage 3',
            'Current 1', 'Current 2', 'Current 3',
            'Dev Voltage', 'Dev Current', 'THD Voltage %', 'THD Current %',
            'Rotorbar', 'Rotorbar Health', 'Rotorbar Level %', 'Rotorbar Severity',
            'Upper Sideband', 'Lower Sideband',
        ]
        order_map = {p: i for i, p in enumerate(preferred_order)}
        eq_data['_sort_key'] = eq_data['Parameter'].astype(str).map(lambda p: order_map.get(p, 10_000))
        eq_data = eq_data.sort_values('_sort_key').drop(columns=['_sort_key'])
        
        # Check condition for highlighting
        cond_row = eq_data[eq_data['Parameter'].astype(str) == 'Kondisi']
        cond_val = cond_row['Raw_Value'].iloc[0] if not cond_row.empty else "Unknown"
        
        p = doc.add_paragraph()
        run = p.add_run(f"Status Terakhir: {cond_val}")
        run.bold = True
        
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Parameter'
        hdr_cells[1].text = 'Nilai'
        hdr_cells[2].text = 'Satuan'
        hdr_cells[3].text = 'Limit'
        
        for _, row in eq_data.iterrows():
            p_name = str(row.get('Parameter', ''))
            num_val = row.get('Value')
            raw_val = row.get('Raw_Value')
            
            row_cells = table.add_row().cells
            row_cells[0].text = p_name
            row_cells[1].text = _format_value(p_name, raw_val, num_val)
            
            unit_txt = str(row.get('Unit', '')) if pd.notna(row.get('Unit')) else ''
            limit_txt = str(row.get('Limit', '')) if pd.notna(row.get('Limit')) else ''
            
            if not unit_txt or unit_txt.lower() in {'nan', 'none'}:
                u_def, l_def = _unit_limit(p_name)
                unit_txt = u_def
                limit_txt = limit_txt or l_def
            
            row_cells[2].text = unit_txt or "-"
            row_cells[3].text = limit_txt or "-"

        # --- ANALYSIS & RECOMMENDATIONS SECTION ---
        doc.add_paragraph()
        
        # Only analyze if not Standby
        if cond_val.lower() != 'standby':
            try:
                # Generate Analysis
                analysis_data = generate_esa_mcsa_quick_recommendations(eq_data)
                detailed_report = analysis_data.get('detailed_report', '')
                
                if detailed_report:
                    # Parse the detailed report string
                    lines = detailed_report.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        if line.startswith('#'):
                            # Header style
                            h = doc.add_paragraph()
                            run = h.add_run(line.replace('#', '').strip())
                            run.bold = True
                            run.font.size = Pt(12)
                            run.underline = True
                        elif line.startswith('-'):
                            # Subheader/Bullet style
                            p = doc.add_paragraph(style='List Bullet')
                            run = p.add_run(line.replace('-', '', 1).strip())
                            run.bold = True
                        else:
                            # Contextual bolding for numeric values if found (simple regex)
                            p = doc.add_paragraph()
                            p.paragraph_format.left_indent = Inches(0.2)
                            p.add_run(line)
                else:
                    doc.add_paragraph("Analisa tidak tersedia untuk equipment ini.")
            except Exception as e:
                doc.add_paragraph(f"Gagal melakukan analisa: {str(e)}")
        else:
            doc.add_paragraph("Analisa tidak tersedia karena status equipment adalah Standby.")

        doc.add_paragraph() # Spacer between equipment

    # Save to buffer
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output
