import streamlit as st
import requests
import json
import time
import hashlib
import base64
# --- Helper Function for File Handling ---
def encode_file_to_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()
            return base64.b64encode(file_bytes).decode('utf-8')
        except Exception as e:
            st.error(f"Encoding error: {e}")
    return None

# --- Page Configurations ---
st.set_page_config(page_title="Telehealth AI Assistant", layout="wide")

# --- Webhook URLs ---
N8N_WEBHOOK_DOCTOR_CONFIG = "https://bytebeez.app.n8n.cloud/webhook-test/DOCinp1"
N8N_WEBHOOK_WORKFLOW_X_MANUAL = "https://bytebeez.app.n8n.cloud/webhook-test/WORKFLOW_X_MANUAL"
N8N_WEBHOOK_WORKFLOW_Y_AI = "https://bytebeez.app.n8n.cloud/webhook-test/DOCinpY"
N8N_WEBHOOK_GET_PATIENT_PARAMS = "https://bytebeez.app.n8n.cloud/webhook-test/patientINP"
N8N_WEBHOOK_PROCESS_SUBMISSION = "https://your-n8n-instance.com/webhook/process-submission"
N8N_WEBHOOK_WORKFLOW_Z = "https://bytebeez.app.n8n.cloud/webhook-test/getParameters"

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
    
    if "doc_step" not in st.session_state:
        st.session_state.doc_step = "input"
    if "temp_data" not in st.session_state:
        st.session_state.temp_data = {}

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
            new_patient_id = generate_patient_id(patient_name)
            payload = {
                "Patient ID": new_patient_id,
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

    elif st.session_state.doc_step == "branch":
        p_name = st.session_state.temp_data.get('Patient Name')
        p_id = st.session_state.temp_data.get('Patient ID')
        
        st.success(f"✅ Patient Registered: **{p_name}** | ID: **{p_id}**")
        choice = st.radio("Choose Monitoring Method:", ["Manual Setup", "AI-Generated Setup"], horizontal=True)
        
        if choice == "Manual Setup":
            st.markdown("### 📝 Define Manual Parameters")
            with st.form("manual_param_form"):
                params = []
                for i in range(1, 4):
                    st.write(f"**Parameter {i}**")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        pn = st.text_input(f"Name {i}", key=f"n{i}")
                    with c2:
                        pt = st.text_input(f"Threshold {i}", key=f"t{i}")
                    with c3:
                        pty = st.selectbox(f"Data Type {i}", ["text","audio", "image"], key=f"d{i}")
                    params.append({"name": pn, "threshold": pt, "data_type": pty})

                if st.form_submit_button("Submit Manual Parameters"):
                    manual_payload = {"patient_info": st.session_state.temp_data, "parameters": params}
                    try:
                        res = requests.post(N8N_WEBHOOK_WORKFLOW_X_MANUAL, json=manual_payload)
                        if res.status_code == 200:
                            st.success("Workflow X Triggered!")
                            st.session_state.doc_step = "input"
                        else:
                            st.error(f"Error {res.status_code}")
                    except Exception as e:
                        st.error(f"Workflow X failed: {e}")

        elif choice == "AI-Generated Setup":
            if st.button("Generate via AI (Workflow Y)"):
                try:
                    res = requests.post(N8N_WEBHOOK_WORKFLOW_Y_AI, json=st.session_state.temp_data)
                    if res.status_code == 200:
                        st.success("AI Workflow Y Triggered!")
                        st.balloons()
                except Exception as e:
                    st.error(f"Workflow Y failed: {e}")

        if st.button("← Cancel & Reset"):
            st.session_state.doc_step = "input"
            st.rerun()

# ==========================================
# 2. Patient's Interface (Updated Section)
# ==========================================
if app_mode == "Patient's Portal":
    st.header("2. Patient's Daily Portal")
    
    # Initialize session states
    if "login_details" not in st.session_state:
        st.session_state.login_details = None
    if "dynamic_params" not in st.session_state:
        st.session_state.dynamic_params = None

    # --- Login Section (Existing Logic) ---
    if st.session_state.login_details is None:
        st.info("Identify yourself to load your recovery parameters.")
        with st.form("patient_login_form"):
            id_patient_name = st.text_input("PATIENT NAME")
            id_doctor_name = st.text_input("DOCTOR NAME")
            id_surgery = st.text_input("SURGERY UNDERGONE")
            login_submitted = st.form_submit_button("Fetch My Daily Check-in Form")

            if login_submitted:
                if not all([id_patient_name, id_doctor_name, id_surgery]):
                    st.warning("Please fill in all fields.")
                else:
                    st.session_state.login_details = {
                        "Patient Name": id_patient_name,
                        "Doc Name": id_doctor_name,
                        "Surgery Type": id_surgery
                    }
                    st.rerun()

  # --- Post-Login Section (The Dynamic Interface) ---
    else:
        details = st.session_state["login_details"]
        st.subheader(f"Welcome, {details['Patient Name']}")
        
        # 1. Trigger Workflow Z to get Parameters
        if st.button("🔄 Sync My Tasks (Workflow Z)"):
            with st.spinner("Fetching your doctor's requirements..."):
                try:
                    # Make sure this URL matches your N8N_WEBHOOK_WORKFLOW_Z variable
                    res = requests.post(N8N_WEBHOOK_WORKFLOW_Z, json=details)
                    if res.status_code == 200:
                        st.session_state.dynamic_params = res.json()
                        st.success("Tasks updated!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Connection error: {e}")

        # 2. Render Each Parameter with its own Upload/Submit
        if st.session_state.get("dynamic_params"):
            st.divider()
            st.markdown("### 📋 Recovery Action Items")

            for idx, item in enumerate(st.session_state.dynamic_params):
                # Normalize label and datatype
                label = item.get("parameter", "Unknown Task")
                dtype = str(item.get("datatype", "text")).lower().strip()
                
                # UNIQUE KEY: This prevents the 'DuplicateElementKey' error
                unique_key = f"{label.replace(' ', '_')}_{idx}"
                
                with st.expander(f"Task: {label}", expanded=True):
                    user_input = None
                    
                    if dtype == "number":
                        user_input = st.number_input(f"Value for {label}", key=unique_key)
                    
                    elif dtype == "text":
                        user_input = st.text_area(f"Notes for {label}", key=unique_key)
                    
                    # --- AUDIO UPLOADER ---
                    elif dtype == "audio":
                        st.write("🎵 **Audio Upload Required**")
                        user_input = st.file_uploader(f"Upload recording for {label}", 
                                                     type=['mp3', 'wav', 'm4a'], 
                                                     key=unique_key)
                    
                    # --- IMAGE UPLOADER ---
                    elif dtype == "image":
                        st.write("📷 **Image Upload Required**")
                        user_input = st.file_uploader(f"Upload photo for {label}", 
                                                     type=['png', 'jpg', 'jpeg'], 
                                                     key=unique_key)
                    
                    else:
                        user_input = st.text_input(f"Enter {label}", key=unique_key)

                    # 3. Individual Submit Button for this specific task
                    if st.button(f"Submit {label}", key=f"btn_{unique_key}"):
                        if user_input is not None:
                            # Prepare individual payload
                            val_to_send = user_input
                            
                            # Handle File Conversion to Base64
                            if dtype in ["audio", "image"]:
                                with st.spinner("Processing file..."):
                                    val_to_send = {
                                        "filename": user_input.name,
                                        "base64": encode_file_to_base64(user_input)
                                    }

                            payload = {
                                "patient_info": details,
                                "parameter": label,
                                "value": val_to_send
                            }

                            try:
                                # Send to your process-submission webhook
                                res = requests.post(N8N_WEBHOOK_PROCESS_SUBMISSION, json=payload)
                                if res.status_code == 200:
                                    st.success(f"✅ Submitted {label}!")
                                else:
                                    st.error("Failed to send to server.")
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Please provide input/file before submitting.")
