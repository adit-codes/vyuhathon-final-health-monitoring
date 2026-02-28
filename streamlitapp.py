import streamlit as st
import requests
import json
import time 
import hashlib 
import base64

# --- Page Configurations ---
st.set_page_config(page_title="Telehealth AI Assistant", layout="wide")

# --- Webhook URLs ---
N8N_WEBHOOK_DOCTOR_CONFIG = "https://bytebeez.app.n8n.cloud/webhook-test/DOCinp1"
N8N_WEBHOOK_WORKFLOW_X_MANUAL = "https://bytebeez.app.n8n.cloud/webhook-test/WORKFLOW_X_MANUAL"
N8N_WEBHOOK_WORKFLOW_Y_AI = "https://bytebeez.app.n8n.cloud/webhook-test/DOCinpY"
N8N_WEBHOOK_GET_PATIENT_PARAMS = "https://bytebeez.app.n8n.cloud/webhook-test/patientINP"
N8N_WEBHOOK_WORKFLOW_Z = "https://bytebeez.app.n8n.cloud/webhook-test/getParameters"
N8N_WEBHOOK_SUBMIT_DATA = "https://bytebeez.app.n8n.cloud/webhook-test/submitPatientData"

# --- Helper Functions ---
def generate_patient_id(name):
    timestamp = str(time.time())
    unique_str = f"{name}-{timestamp}"
    return f"PAT-{hashlib.md5(unique_str.encode()).hexdigest()[:8].upper()}"

def file_to_base64(uploaded_file):
    """Converts a Streamlit uploaded file to a base64 string for n8n."""
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        return base64.b64encode(file_bytes).decode()
    return None

# --- UI Header ---
st.title("🩺 AI-Powered Patient Recovery Monitoring")
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
                response = requests.post(N8N_WEBHOOK_DOCTOR_CONFIG, json=payload)
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
        st.success(f"✅ Patient Registered: **{p_name}**")
        choice = st.radio("Choose Monitoring Method:", ["Manual Setup", "AI-Generated Setup"], horizontal=True)
        
        if choice == "Manual Setup":
            st.markdown("### 📝 Define Manual Parameters")
            with st.form("manual_param_form"):
                params = []
                for i in range(1, 4):
                    st.write(f"**Parameter {i}**")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        pn = st.text_input(f"Name {i}", key=f"n{i}", placeholder="e.g. Wound Photo")
                    with c2:
                        pt = st.text_input(f"Threshold/Instruction {i}", key=f"t{i}")
                    with c3:
                        pty = st.selectbox(f"Data Type {i}", ["text", "audio", "image"], key=f"d{i}")
                    params.append({"name": pn, "threshold": pt, "data_type": pty})

                if st.form_submit_button("Submit Manual Parameters"):
                    manual_payload = {"patient_info": st.session_state.temp_data, "parameters": params}
                    res = requests.post(N8N_WEBHOOK_WORKFLOW_X_MANUAL, json=manual_payload)
                    if res.status_code == 200:
                        st.success("Workflow X Triggered!")
                        st.session_state.doc_step = "input"

        elif choice == "AI-Generated Setup":
            if st.button("Generate via AI (Workflow Y)"):
                res = requests.post(N8N_WEBHOOK_WORKFLOW_Y_AI, json=st.session_state.temp_data)
                if res.status_code == 200:
                    st.success("AI Workflow Y Triggered!")
                    st.balloons()

        if st.button("← Cancel & Reset"):
            st.session_state.doc_step = "input"
            st.rerun()

# ==========================================
# 2. Patient's Interface
# ==========================================
elif app_mode == "Patient's Portal":
    st.header("2. Patient's Daily Portal")
    
    if "login_details" not in st.session_state:
        st.session_state.login_details = None
    if "dynamic_form_fields" not in st.session_state:
        st.session_state.dynamic_form_fields = None

    # --- Step 1: Login ---
    if st.session_state.login_details is None:
        with st.form("patient_login_form"):
            id_patient_name = st.text_input("PATIENT NAME")
            id_doctor_name = st.text_input("DOCTOR NAME")
            id_surgery = st.text_input("SURGERY UNDERGONE")
            login_submitted = st.form_submit_button("Fetch My Daily Check-in Form")

        if login_submitted:
            if not all([id_patient_name, id_doctor_name, id_surgery]):
                st.warning("Please fill in all fields.")
            else:
                try:
                    lookup_payload = {"Patient Name": id_patient_name, "Doc Name": id_doctor_name, "Surgery Type": id_surgery}
                    # Getting the patient parameters first
                    response = requests.post(N8N_WEBHOOK_GET_PATIENT_PARAMS, json=lookup_payload)
                    response.raise_for_status()
                    
                    # Store details and trigger next step
                    st.session_state.login_details = lookup_payload
                    st.rerun()
                except Exception as e:
                    st.error(f"Login Error: {e}")

    # --- Step 2: Dynamic Form Generation ---
    else:
        details = st.session_state["login_details"]
        st.subheader(f"Welcome, {details['Patient Name']}")
        
        if st.session_state.dynamic_form_fields is None:
            if st.button("Load Today's Requirements"):
                with st.spinner("Fetching parameters..."):
                    z_res = requests.post(N8N_WEBHOOK_WORKFLOW_Z, json=details)
                    if z_res.status_code == 200:
                        data = z_res.json()
                        # Handling both list format and nested 'fields' key
                        fields = data if isinstance(data, list) else data.get("fields", [])
                        st.session_state.dynamic_form_fields = fields
                        st.rerun()

        else:
            st.write("### Today's Recovery Check-in")
            
            # This loop renders the UI based on data_type from Webhook
            for idx, field in enumerate(st.session_state.dynamic_form_fields):
                # We handle multiple possible key names from n8n for flexibility
                f_name = field.get("name") or field.get("Parameter Name") or f"Input {idx+1}"
                f_type = str(field.get("data_type") or field.get("type") or "text").strip().lower()
                
                with st.container(border=True):
                    st.markdown(f"**{f_name}**")
                    user_input = None
                    
                    # DYNAMIC UI LOGIC
                    if f_type == "image":
                        user_input = st.file_uploader(f"Upload photo", type=['png', 'jpg', 'jpeg'], key=f"f_{idx}")
                        if user_input: st.image(user_input, width=250)
                    
                    elif f_type == "audio":
                        user_input = st.file_uploader(f"Upload voice note", type=['mp3', 'wav'], key=f"f_{idx}")
                        if user_input: st.audio(user_input)
                    
                    else: # Defaults to text if type is 'text' or unknown
                        user_input = st.text_area("Enter update", key=f"f_{idx}")

                    if st.button(f"Submit {f_name}", key=f"b_{idx}"):
                        if user_input:
                            # Process data for sending (Base64 for files)
                            final_val = file_to_base64(user_input) if f_type in ["image", "audio"] else user_input
                            
                            submit_payload = {
                                "patient": details["Patient Name"],
                                "parameter": f_name,
                                "type": f_type,
                                "data": final_val
                            }
                            # Send to n8n
                            res = requests.post(N8N_WEBHOOK_SUBMIT_DATA, json=submit_payload)
                            if res.status_code == 200:
                                st.success(f"Sent {f_name}!")
                        else:
                            st.warning("Empty field.")

        if st.button("Logout"):
            st.session_state.login_details = None
            st.session_state.dynamic_form_fields = None
            st.rerun()
