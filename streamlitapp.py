import streamlit as st
import requests
import json
import time 
import hashlib 

# --- Page Configurations ---
st.set_page_config(page_title="Telehealth AI Assistant", layout="wide")

# --- Webhook URLs (Replace with your actual production URLs) ---
N8N_WEBHOOK_DOCTOR_CONFIG = "https://bytebeez.app.n8n.cloud/webhook-test/DOCinp1"
N8N_WEBHOOK_WORKFLOW_X_MANUAL = "https://bytebeez.app.n8n.cloud/webhook-test/WORKFLOW_X_MANUAL"
N8N_WEBHOOK_WORKFLOW_Y_AI = "https://your-n8n-instance.com/webhook/workflow-y"

N8N_WEBHOOK_GET_PATIENT_PARAMS = "https://adi440.app.n8n.cloud/webhook-test/PATIENTINPUT"
N8N_WEBHOOK_PROCESS_SUBMISSION = "https://your-n8n-instance.com/webhook/process-submission"
# Helper function to generate a unique Patient ID
def generate_patient_id(name):
    timestamp = str(time.time())
    unique_str = f"{name}-{timestamp}"
    return f"PAT-{hashlib.md5(unique_str.encode()).hexdigest()[:8].upper()}"

st.title("AI-Powered Patient Recovery Monitoring")

app_mode = st.sidebar.selectbox("Choose Interface", ["Doctor's Panel", "Patient's Portal"])

# ==========================================
# 1. Doctor's Interface 
# ==========================================
if app_mode == "Doctor's Panel":
    st.header("1. Doctor's Configuration Panel")
    
    # Initialize state to manage the two-step process
    if "doc_step" not in st.session_state:
        st.session_state.doc_step = "input"
    if "temp_doc_data" not in st.session_state:
        st.session_state.temp_doc_data = {}

    # --- STEP 1: Registration ---
    if st.session_state.doc_step == "input":
        with st.form("doctor_config_form"):
            col1, col2 = st.columns(2)
            with col1:
                doc_name = st.text_input("Doc Name")
                patient_name = st.text_input("Patient Name")
            with col2:
                patient_age = st.number_input("Patient Age", min_value=0, max_value=120)
                surgery_type = st.text_input("Surgery Type")

            submitted = st.form_submit_button("Register Patient & Proceed")

        if submitted:
            # The ID is generated here and kept in the payload variable
            new_patient_id = generate_patient_id(patient_name)
            
            payload = {
                "Patient ID": new_patient_id, # Sent to webhook, but hidden from UI later
                "Doc Name": doc_name,
                "Patient Name": patient_name,
                "Patient Age": patient_age,
                "Surgery Type": surgery_type
            }
            try:
                response = requests.get(N8N_WEBHOOK_DOCTOR_CONFIG, json=payload)
                if response.status_code == 200:
                    st.session_state.temp_data = payload
                    st.session_state.doc_step = "branch"
                    st.rerun()
                else:
                    st.error(f"Failed to register. Status: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")
# --- STEP 2: Success Message & Branching Choice ---
    elif st.session_state.doc_step == "branch":
        # DISPLAY: Success message with Name and ID
        p_name = st.session_state.temp_data.get('Patient Name')
        p_id = st.session_state.temp_data.get('Patient ID')
        
        st.success(f"✅ Patient Registered: **{p_name}** | ID: **{p_id}**")
        st.info("Please choose the monitoring setup below.")
        
        choice = st.radio("Choose Monitoring Method:", ["Manual Setup", "AI-Generated Setup"], horizontal=True)
        
        # --- MANUAL SETUP OPTION ---
        if choice == "Manual Setup":
            st.markdown("### 📝 Define Manual Parameters")
            with st.form("manual_param_form"):
                params = []
                for i in range(1, 4):
                    st.write(f"**Parameter {i}**")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        p_name = st.text_input(f"Name {i}", key=f"n{i}")
                    with c2:
                        p_thresh = st.text_input(f"Threshold {i}", key=f"t{i}")
                    with c3:
                        p_type = st.selectbox(f"Data Type {i}", ["text","audio", "image"], key=f"d{i}")
                    params.append({"name": p_name, "threshold": p_thresh, "data_type": p_type})

                if st.form_submit_button("Submit Manual Parameters"):
                    manual_payload = {
                        "patient_info": st.session_state.temp_data,
                        "parameters": params
                    }
                    try:
                        res = requests.get(N8N_WEBHOOK_WORKFLOW_X_MANUAL, json=manual_payload)
                        if res.status_code == 200:
                            st.success("Workflow X Triggered successfully!")
                            st.session_state.doc_step = "input" # Reset
                    except Exception as e:
                        st.error(f"Workflow X failed: {e}")

        # --- AI SETUP OPTION ---
        elif choice == "AI-Generated Setup":
            st.info("AI will automatically determine thresholds based on surgery type.")
            if st.button("Generate via AI (Workflow Y)"):
                try:
                    res = requests.post(N8N_WORKFLOW_Y_AI, json=st.session_state.temp_data)
                    if res.status_code == 200:
                        st.success("AI Workflow Y Triggered!")
                        st.balloons()
                except Exception as e:
                    st.error(f"Workflow Y failed: {e}")

        if st.button("← Cancel & Reset"):
            st.session_state.doc_step = "input"
            st.rerun()

# ==========================================
# 2. Patient's Interface
# ==========================================
elif app_mode == "Patient's Portal":
    st.header("2. Patient's Daily Portal")
    
    if "patient_params" not in st.session_state:
        st.info("Identify yourself to load your recovery parameters.")
        with st.form("patient_login_form"):
            id_patient_name = st.text_input("PATIENT NAME")
            id_doctor_name = st.text_input("DOCTOR NAME")
            id_surgery = st.text_input("SURGERY UNDERGONE")
            
            login_submitted = st.form_submit_button("Fetch My Daily Check-in Form")

        if login_submitted:
            if not all([id_patient_name, id_doctor_name, id_surgery]):
                st.warning("Please fill in all three identification fields.")
            else:
                with st.spinner("Connecting..."):
                    try:
                        lookup_payload = {
                            "Patient Name": id_patient_name,
                            "Doc Name": id_doctor_name,
                            "Surgery Type": id_surgery
                        }
                        response = requests.post(N8N_WEBHOOK_GET_PATIENT_PARAMS, json=lookup_payload)
                        response.raise_for_status()
                        patient_params = response.json()

                        if patient_params and isinstance(patient_params, list):
                            st.session_state["patient_params"] = patient_params
                            st.session_state["login_details"] = lookup_payload
                            st.rerun()
                        else:
                            st.error("Recovery plan not found. Please verify details.")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

    if "patient_params" in st.session_state:
        details = st.session_state["login_details"]
        st.subheader(f"Daily Entry for {details['Patient Name']}")
        st.caption(f"Physician: {details['Doc Name']} | Surgery: {details['Surgery Type']}")
        
        with st.form("daily_checkin_form"):
            input_data = {}
            files_to_send = {}

            for param in st.session_state["patient_params"]:
                p_name = param.get("name")
                p_type = param.get("data_type", "text").lower()
                
                if p_type == "text":
                    input_data[p_name] = st.text_input(p_name)
                elif p_type == "number":
                    input_data[p_name] = st.number_input(p_name)
                elif p_type == "audio":
                    audio = st.file_uploader(f"Upload Audio: {p_name}", type=["mp3", "wav"])
                    if audio: files_to_send["audio_file"] = (audio.name, audio, audio.type)
                elif p_type == "image":
                    img = st.file_uploader(f"Upload Image: {p_name}", type=["jpg", "png"])
                    if img: files_to_send["image_file"] = (img.name, img, img.type)

            submit_final = st.form_submit_button("Submit Daily Check-in & Analyze")

            if submit_final:
                with st.spinner("AI is analyzing..."):
                    payload = {
                        "identification": st.session_state["login_details"],
                        "readings": input_data
                    }
                    try:
                        res = requests.post(
                            N8N_WEBHOOK_PROCESS_SUBMISSION, 
                            data={"main_data": json.dumps(payload)}, 
                            files=files_to_send
                        )
                        res.raise_for_status()
                        analysis = res.json()
                        
                        st.divider()
                        st.success("Analysis Complete!")
                        st.metric("Recovery Rate", f"{analysis.get('recovery_rate', 0)}%")
                        st.write(f"**AI Evaluation:** {analysis.get('recovery_status')}")
                        
                        if analysis.get('risk_status') == "Risk":
                            st.error(f"🚨 ALERT: {analysis.get('alert_details')}")
                        else:
                            st.balloons()
                            
                    except Exception as e:
                        st.error(f"Submission failed: {e}")
