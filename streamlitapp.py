import streamlit as st
import requests

# Use the Production URL from your n8n Webhook node
N8N_WEBHOOK_DOCTOR_CONFIG = "https://your-n8n-instance.com/webhook/doctor-config"

st.title("Doctor's Configuration Panel")

with st.form("doctor_config_form"):
    # These labels match the keys n8n is expecting
    doc_name = st.text_input("Doc name")
    patient_name = st.text_input("Patient Name")
    patient_age = st.number_input("Patient Age", min_value=0, max_value=120, step=1)
    surgery_type = st.text_input("Surgery Type")
    monitoring_setup = st.selectbox("Monitoring Setup", ["Manual", "AI-Generated"])

    submitted = st.form_submit_button("Append to Sheet")

if submitted:
    # IMPORTANT: The keys in this dictionary MUST match your n8n expressions
    # e.g., 'Doc Name' matches {{ $json['Doc Name'] }}
    payload = {
        "Doc Name": doc_name,
        "Patient Name": patient_name,
        "Patient Age": patient_age,
        "Surgery Type": surgery_type,
        "Monitoring Setup": monitoring_setup
    }

    try:
        response = requests.post(N8N_WEBHOOK_DOCTOR_CONFIG, json=payload)
        if response.status_code == 200:
            st.success("Data successfully sent to n8n!")
        else:
            st.error(f"Error: Received status code {response.status_code}")
    except Exception as e:
        st.error(f"Connection failed: {e}")
