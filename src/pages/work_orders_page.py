"""Work Orders Management Page for Streamlit UI.

Provides interactive maintenance workflow management:
- View CBM and engineer-created Work Orders
- Filter by status, priority, and equipment
- Approve, start progress, complete, or reject work orders
- Create new Work Orders directly from CBM recommendations or manual inspection
"""

from datetime import datetime
import streamlit as st

from src.components.theme import render_page_header
from src.work_orders import (
    create_work_order,
    load_work_orders,
    update_work_order_status,
)

PRIORITY_COLORS = {
    "P1 - Critical": "#EF4444",
    "P2 - High": "#F97316",
    "P3 - Medium": "#F59E0B",
    "P4 - Low": "#10B981",
}

STATUS_COLORS = {
    "Draft": "#64748B",
    "Approved": "#3B82F6",
    "In Progress": "#8B5CF6",
    "Completed": "#10B981",
    "Rejected": "#EF4444",
}


def _get_status_color(status_str: str) -> str:
    for key, color in STATUS_COLORS.items():
        if key.lower() in status_str.lower():
            return color
    return "#64748B"


def render_work_orders_page(st_context=st):
    render_page_header(
        st_context,
        "Work Orders & Tindak Lanjut Pemeliharaan",
        "Pusat pengelolaan perintah kerja dan eksekusi rekomendasi pemeliharaan multi-disiplin CBM",
    )

    work_orders = load_work_orders()

    # KPI Summary Cards
    total_wo = len(work_orders)
    draft_count = sum(1 for w in work_orders if "draft" in w.get("status", "").lower())
    in_progress_count = sum(1 for w in work_orders if "progress" in w.get("status", "").lower())
    completed_count = sum(1 for w in work_orders if "complete" in w.get("status", "").lower())

    c1, c2, c3, c4 = st_context.columns(4)
    with c1:
        st_context.metric("Total Work Orders", total_wo)
    with c2:
        st_context.metric("Menunggu Approval", draft_count, delta=f"{draft_count} pending" if draft_count > 0 else None, delta_color="inverse")
    with c3:
        st_context.metric("Sedang Dikerjakan", in_progress_count)
    with c4:
        st_context.metric("Selesai & Ditutup", completed_count)

    tab_list, tab_create = st_context.tabs([":material/list_alt: Daftar Work Order", ":material/add_task: Buat Work Order Baru"])

    with tab_list:
        # Filter section
        with st_context.container(border=True):
            f_col1, f_col2, f_col3 = st_context.columns([1, 1, 2])
            with f_col1:
                status_filter = st_context.selectbox(
                    "Filter Status",
                    ["Semua Status", "Draft / Menunggu Approval", "Approved / Ready", "In Progress", "Completed", "Rejected"],
                )
            with f_col2:
                priority_filter = st_context.selectbox(
                    "Filter Prioritas",
                    ["Semua Prioritas", "P1 - Critical", "P2 - High", "P3 - Medium", "P4 - Low"],
                )
            with f_col3:
                search_query = st_context.text_input("Cari Equipment / Nomor WO", placeholder="Ketik nama aset atau WO...")

        # Apply filtering
        filtered_orders = []
        for wo in work_orders:
            wo_status = wo.get("status", "")
            wo_priority = wo.get("priority", "")
            wo_eq = wo.get("equipment", "")
            wo_num = wo.get("wo_number", "")
            wo_title = wo.get("title", "")

            # Status match
            if status_filter == "Draft / Menunggu Approval" and "draft" not in wo_status.lower():
                continue
            if status_filter == "Approved / Ready" and "ready" not in wo_status.lower() and "approved" not in wo_status.lower():
                continue
            if status_filter == "In Progress" and "progress" not in wo_status.lower():
                continue
            if status_filter == "Completed" and "complete" not in wo_status.lower():
                continue
            if status_filter == "Rejected" and "reject" not in wo_status.lower():
                continue

            # Priority match
            if priority_filter != "Semua Prioritas" and priority_filter != wo_priority:
                continue

            # Search match
            if search_query:
                q = search_query.lower()
                if q not in wo_eq.lower() and q not in wo_num.lower() and q not in wo_title.lower():
                    continue

            filtered_orders.append(wo)

        if not filtered_orders:
            st_context.info("Tidak ada Work Order yang sesuai dengan kriteria filter.")
        else:
            for idx, wo in enumerate(filtered_orders):
                wo_num = wo.get("wo_number", f"WO-{idx}")
                status_color = _get_status_color(wo.get("status", ""))
                prio_color = PRIORITY_COLORS.get(wo.get("priority", ""), "#F59E0B")

                with st_context.container(border=True):
                    head_col1, head_col2 = st_context.columns([3, 1])
                    with head_col1:
                        st_context.markdown(
                            f"#### **{wo.get('title', 'Perawatan')}**"
                        )
                        st_context.caption(
                            f"**{wo_num}** · Equipment: **{wo.get('equipment', '-')}** · "
                            f"Target: **{wo.get('target_completion_date', '-')}** · "
                            f"Dibuat oleh: *{wo.get('created_by', 'Sistem')}* ({wo.get('created_at', '-')})"
                        )
                    with head_col2:
                        st_context.markdown(
                            f"<div style='text-align: right;'>"
                            f"<span style='display:inline-block;padding:3px 10px;border-radius:12px;background:{prio_color}22;color:{prio_color};font-weight:bold;font-size:0.85rem;border:1px solid {prio_color}55;margin-right:6px;'>{wo.get('priority', '-')}</span>"
                            f"<span style='display:inline-block;padding:3px 10px;border-radius:12px;background:{status_color}22;color:{status_color};font-weight:bold;font-size:0.85rem;border:1px solid {status_color}55;'>{wo.get('status', '-')}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    st_context.markdown(f"**Justifikasi Diagnosa / Alasan:** {wo.get('reason', '-')}")

                    detail_col1, detail_col2, detail_col3 = st_context.columns(3)
                    with detail_col1:
                        tools = wo.get("required_tools", [])
                        st_context.markdown(f"🛠️ **Tools:** {', '.join(tools) if tools else '-'}")
                    with detail_col2:
                        parts = wo.get("required_parts", [])
                        st_context.markdown(f"⚙️ **Spare Parts:** {', '.join(parts) if parts else '-'}")
                    with detail_col3:
                        st_context.markdown(f"👷 **Tenaga Kerja:** {wo.get('required_manpower', '-')}")

                    # Actions row
                    st_context.divider()
                    btn_col1, btn_col2, btn_col3, btn_col4, _ = st_context.columns([1.2, 1.2, 1.4, 1.2, 2])
                    with btn_col1:
                        if st_context.button("✅ Setujui", key=f"app_{wo_num}"):
                            update_work_order_status(wo_num, "Approve", actor="Supervisor O&M")
                            st_context.success(f"{wo_num} berhasil disetujui!")
                            st_context.rerun()
                    with btn_col2:
                        if st_context.button("🚀 Kerjakan", key=f"prog_{wo_num}"):
                            update_work_order_status(wo_num, "Progress", actor="Teknisi Pemeliharaan")
                            st_context.info(f"{wo_num} status diubah ke In Progress.")
                            st_context.rerun()
                    with btn_col3:
                        if st_context.button("🎉 Tandai Selesai", key=f"comp_{wo_num}"):
                            update_work_order_status(wo_num, "Complete", actor="Supervisor O&M")
                            st_context.success(f"{wo_num} telah selesai dan ditutup.")
                            st_context.rerun()
                    with btn_col4:
                        if st_context.button("❌ Tolak", key=f"rej_{wo_num}"):
                            update_work_order_status(wo_num, "Reject", actor="Supervisor O&M")
                            st_context.warning(f"{wo_num} ditolak.")
                            st_context.rerun()

    with tab_create:
        st_context.markdown("### Formulir Perintah Kerja (Work Order Baru)")
        with st_context.form("create_wo_form", clear_on_submit=True):
            form_col1, form_col2 = st_context.columns(2)
            with form_col1:
                f_equipment = st_context.text_input("Nama Equipment *", placeholder="misal: CWP 1A, BC 10.1, BFP 2B")
                f_title = st_context.text_input("Judul Pekerjaan *", placeholder="misal: Penggantian Bearing & Balancing Rotor")
                f_priority = st_context.selectbox("Tingkat Prioritas", ["P1 - Critical", "P2 - High", "P3 - Medium", "P4 - Low"], index=2)
                f_target_date = st_context.date_input("Target Penyelesaian", value=datetime.now())
            with form_col2:
                f_reason = st_context.text_area("Justifikasi / Hasil Temuan CBM", placeholder="Jelaskan alasan tindakan pemeliharaan...")
                f_tools = st_context.text_input("Peralatan Khusus (Pisahkan dengan koma)", placeholder="Vibration Analyzer, Laser Alignment, Torque Wrench")
                f_parts = st_context.text_input("Material / Spare Part (Pisahkan dengan koma)", placeholder="Bearing 6314 C3, Seal Kit, Grease")
                f_manpower = st_context.text_input("Kebutuhan Tenaga Kerja", value="2 Teknisi Mekanik")

            submitted = st_context.form_submit_button("Simpan & Rilis Work Order", type="primary")
            if submitted:
                if not f_equipment.strip() or not f_title.strip():
                    st_context.error("Nama Equipment dan Judul Pekerjaan wajib diisi!")
                else:
                    tools_list = [t.strip() for t in f_tools.split(",") if t.strip()]
                    parts_list = [p.strip() for p in f_parts.split(",") if p.strip()]
                    new_order = create_work_order(
                        equipment=f_equipment,
                        title=f_title,
                        priority=f_priority,
                        reason=f_reason,
                        required_tools=tools_list,
                        required_parts=parts_list,
                        required_manpower=f_manpower,
                        target_completion_date=str(f_target_date),
                        created_by="Engineer (Manual Input)",
                    )
                    st_context.success(f"Work Order {new_order['wo_number']} berhasil dibuat!")
                    st_context.rerun()
