import streamlit as st
import requests
import json
import time 
import hashlib 

# --- Page Configurations ---
st.set_page_config(page_title="Telehealth AI Assistant", layout="wide")

# --- Webhook URLs ---
N8N_WEBHOOK_DOCTOR_CONFIG = "https://bytebeez.app.n8n.cloud/webhook/DOCinp1"
N8N_WEBHOOK_WORKFLOW_X_MANUAL = "https://bytebeez.app.n8n.cloud/webhook/WORKFLOW_X_MANUAL"
N8N_WEBHOOK_WORKFLOW_Y_AI = "https://bytebeez.app.n8n.cloud/webhook/DOCinpY"
N8N_WEBHOOK_GET_PATIENT_PARAMS = "https://bytebeez.app.n8n.cloud/webhook-test/patientINP"
N8N_WEBHOOK_PROCESS_SUBMISSION = "https://your-n8n-instance.com/webhook/process-submission"
# --- NEW WEBHOOK FOR WORKFLOW Z ---
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
                        res = requests.get(N8N_WEBHOOK_WORKFLOW_X_MANUAL, json=manual_payload)
                        if res.status_code == 200:
                            st.success("Workflow X Triggered successfully!")
                            st.session_state.doc_step = "input"
                    except Exception as e:
                        st.error(f"Workflow X failed: {e}")

        elif choice == "AI-Generated Setup":
            if st.button("Generate via AI (Workflow Y)"):
                try:
                    res = requests.get(N8N_WEBHOOK_WORKFLOW_Y_AI, json=st.session_state.temp_data)
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
    
    # Initialize session state for storing analysis results
    if "last_analysis" not in st.session_state:
        st.session_state.last_analysis = None
    if "login_details" not in st.session_state:
        st.session_state.login_details = None
    if "patient_params" not in st.session_state:
        st.session_state.patient_params = None

    # --- Login Section ---
    if st.session_state.login_details is None:
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
                        response = requests.get(N8N_WEBHOOK_GET_PATIENT_PARAMS, json=lookup_payload)
                        response.raise_for_status()
                        
                        # Save to session state upon success
                        st.session_state.patient_params = response.json()
                        st.session_state.login_details = lookup_payload
                        st.rerun() # Refresh to show the next section
                        
                    except Exception as e:
                        st.error(f"Error fetching patient parameters: {e}")

    # --- Post-Login Section (Workflow Z) ---
else:
    details = st.session_state["login_details"]
    st.subheader(f"Welcome, {details['Patient Name']}")
    st.write("Your profile is loaded. Before entering your daily data, please initialize the session.")
    
    if st.button("Fetch Data Input Details (Trigger Workflow Z)"):
        with st.spinner("Running Workflow Z..."):
   [ in my code after workflow z is trigered, it will give a json output using respond to webhook. the format of this is [
  {
    "parameter": "Pain Level",
    "datatype": "number"
  },
  {
    "parameter": "Wound Status",
    "datatype": "text"
  },
  {
    "parameter": "Wound Status",
    "datatype": "text"
  }
]. the next feature i want to add to code is, the code should be able to get all the parameters and datatypes. These need to be output to user, with the each parameter as question header. important thing is, based on the datatype for each parameter, the input field should be according to the data type, for example if datatype is audio they should have inputfield to enter sudio. please help with this
