"""Component for the Equipment Upload & Registration wizard."""

import streamlit as st

def render_equipment_upload_wizard(st, edit_mode: bool) -> None:
    # 1. Stepper UI
    st.markdown("""
        <style>
        .wizard-stepper { display: flex; justify-content: space-between; margin-bottom: 2rem; position: relative; }
        .wizard-stepper::before {
            content: ''; position: absolute; top: 15px; left: 10%; right: 10%;
            height: 2px; background: #334155; z-index: 0;
        }
        .wizard-step { text-align: center; z-index: 1; flex: 1; font-size: 0.85rem; color: #94a3b8; font-weight: 500; }
        .wizard-icon { 
            width: 32px; height: 32px; border-radius: 50%; background: #1e293b; 
            color: #94a3b8; line-height: 32px; margin: 0 auto 8px; border: 2px solid #334155;
            font-size: 14px;
        }
        .wizard-step.completed .wizard-icon { background: #10b981; color: #fff; border-color: #10b981; }
        .wizard-step.active .wizard-icon { background: #0ea5e9; color: #fff; border-color: #0ea5e9; }
        .wizard-step.active { color: #f8fafc; }
        .wizard-step.completed { color: #f8fafc; }
        </style>
        <div class="wizard-stepper">
            <div class="wizard-step completed"><div class="wizard-icon">✔</div>Category</div>
            <div class="wizard-step active"><div class="wizard-icon">2</div>Specifications</div>
            <div class="wizard-step"><div class="wizard-icon">3</div>PDM Assignment</div>
            <div class="wizard-step"><div class="wizard-icon">4</div>Confirmation</div>
        </div>
    """, unsafe_allow_html=True)

    # Main layout: Left for upload, Right for form
    col_upload, col_form = st.columns([1, 1.4], gap="large")

    with col_upload:
        st.markdown("##### Upload Equipment Data")
        st.caption("Drag & drop files here or click to browse. Supported: CSV, Excel, PDF, Image (.jpg, .png)")
        uploaded_files = st.file_uploader("Pilih Dokumen", accept_multiple_files=True, label_visibility="collapsed")
        
        # Display mock uploaded files if empty just to mimic the design slightly, 
        # but in real usage we show actual uploaded files.
        if uploaded_files:
            for f in uploaded_files:
                st.info(f"📄 **{f.name}**")
        else:
            # Placeholder for visual parity with the mockup if no files uploaded yet
            st.markdown("""
                <div style="padding: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; margin-bottom: 8px; border-left: 3px solid #0ea5e9;">
                    📄 Motor_Spec_M205.xlsx
                </div>
                <div style="padding: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; margin-bottom: 8px; border-left: 3px solid #0ea5e9;">
                    📄 Transformer_Test_TR001.csv
                </div>
            """, unsafe_allow_html=True)

    with col_form:
        st.markdown("##### Equipment Specifications")
        with st.form("wizard_spec_form"):
            r1c1, r1c2, r1c3 = st.columns(3)
            asset_id = r1c1.text_input("ASSET ID", value="M-206")
            eq_name = r1c2.text_input("EQUIPMENT NAME", value="ID Fan Motor")
            category = r1c3.selectbox("CATEGORY", ["Transformer", "Motor", "Pump", "Fan", "Compressor"])

            r2c1, r2c2, r2c3 = st.columns(3)
            manufacturer = r2c1.text_input("MANUFACTURER", value="ABB")
            model = r2c2.text_input("MODEL / TYPE", value="M3BP 315 SMB")
            rated_power = r2c3.text_input("RATED POWER (KW)", value="750")

            r3c1, r3c2, r3c3 = st.columns(3)
            voltage = r3c1.text_input("VOLTAGE (V)", value="6600")
            rpm = r3c2.text_input("RPM", value="1485")
            location = r3c3.text_input("LOCATION / AREA", value="Unit 2 - ID Fan Area")

            install_date = st.date_input("INSTALL DATE")

            st.markdown("---")
            st.markdown("##### PDM TOOLS ASSIGNMENT (AUTO-DETECTED)")
            
            p1, p2, p3, p4, p5, p6 = st.columns(6)
            vibration = p1.checkbox("VIBRATION", value=True)
            mcsa = p2.checkbox("MCSA", value=True)
            thermal = p3.checkbox("THERMAL")
            tribology = p4.checkbox("TRIBOLOGY")
            dga = p5.checkbox("DGA")
            pd_online = p6.checkbox("PD ONLINE")

            st.markdown("<br>", unsafe_allow_html=True)
            b1, b2, _ = st.columns([1, 1, 3])
            submitted = b1.form_submit_button("Submit & Register", type="primary", disabled=not edit_mode)
            drafted = b2.form_submit_button("Save Draft", disabled=not edit_mode)

            if submitted:
                st.success("Equipment data submitted and registered successfully.")
            elif drafted:
                st.info("Draft saved.")

