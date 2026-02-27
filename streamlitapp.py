import streamlit as st
import requests
import json

# --- Page Configurations ---
st.set_page_config(page_title="Telehealth AI Assistant", layout="wide")

# --- Custom N8N Webhook URLs ---
# Replace with your actual PRODUCTION URLs from n8n
N8N_WEBHOOK_DOCTOR_CONFIG = "https://your-n8n-instance.com/webhook/doctor-config"
N8N_WEBHOOK_GET_PATIENT_PARAMS = "https://your-n8n-instance.com/webhook/get-patient-params"
N8N_WEBHOOK_PROCESS_SUBMISSION = "https://your-n8n-instance.com/webhook/process-submission"

st.title("AI-Powered Patient Recovery Monitoring")

app_mode = st.sidebar.selectbox("Choose Interface", ["Doctor's Panel", "Patient's Portal"])

# ==========================================
# 1. Doctor's Interface 
# ==========================================
if app_mode == "Doctor's Panel":
    st.header("1. Doctor's Configuration Panel")
    
    with st.form("doctor_config_form"):
        col1, col2 = st.columns(2)
        with col1:
            # Updated labels based on your n8n mapping
            doc_name = st.text_input("Doc Name")
            patient_name = st.text_input("Patient Name")
            patient_age = st.number_input("Patient Age", min_value=0, max_value=120)
        with col2:
            surgery_type = st.text_input("Surgery Type")
            monitoring_setup = st.radio("Monitoring Setup", ("AI-generated", "Manual"))

        submitted = st.form_submit_button("Configure and Save")

    if submitted:
        payload = {
            "Doc Name": doc_name,
            "Patient Name": patient_name,
            "Patient Age": patient_age,
            "Surgery Type": surgery_type,
            "Monitoring Setup": monitoring_setup
        }
        try:
            # Allow_redirects handles the 302 'Sticky Window' trick
            response = requests.post(N8N_WEBHOOK_DOCTOR_CONFIG, json=payload, allow_redirects=True)
            if response.status_code == 200:
                st.success("Successfully configured!")
                # Force browser redirect if n8n returned a new Location
                if response.history:
                    target_url = response.url
                    st.components.v1.html(f"<script>window.parent.location.href = '{target_url}';</script>", height=0)
        except Exception as e:
            st.error(f"Error: {e}")

# ==========================================
# 2. Patient's Interface (MODIFIED FOR NEW FIELDS)
# ==========================================
elif app_mode == "Patient's Portal":
    st.header("2. Patient's Daily Portal")
    
    # Step 1: Identification using your specific Labels
    if "patient_params" not in st.session_state:
        st.info("Enter your details exactly as registered by your doctor.")
        with st.form("patient_login_form"):
            # Fields added to match your provided form element image
            id_patient_name = st.text_input("PATIENT NAME")
            id_doctor_name = st.text_input("DOCTOR NAME")
            id_surgery = st.text_input("SURGERY UNDERGONE")
