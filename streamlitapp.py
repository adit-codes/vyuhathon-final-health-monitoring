import streamlit as st
import requests
import json

# --- Page Configurations ---
st.set_page_config(page_title="Telehealth AI Assistant", layout="wide")

# --- Custom N8N Webhook URLs (REPLACE WITH YOUR PRODUCTION URLS) ---
N8N_WEBHOOK_DOCTOR_CONFIG = "https://am-space.app.n8n.cloud/webhook-test/DOCTORDATA"
N8N_WEBHOOK_GET_PATIENT_PARAMS = "https://adi440.app.n8n.cloud/webhook-test/PATIENTINPUT"
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
            response = requests.post(N8N_WEBHOOK_DOCTOR_CONFIG, json=payload, allow_redirects=True)
            if response.status_code == 200:
                st.success("Successfully configured!")
                if response.history: # If n8n triggers a 302 redirect
                    st.components.v1.html(f"<script>window.parent.location.href = '{response.url}';</script>", height=0)
        except Exception as e:
            st.error(f"Error: {e}")

# ==========================================
# 2. Patient's Interface
# ==========================================
elif app_mode == "Patient's Portal":
    st.header("2. Patient's Daily Portal")
    
    # --- Step 1: Identification (Fetch Form) ---
    if "patient_params" not in st.session_state:
        st.info("Identify yourself to load your recovery parameters.")
        with st.form("patient_login_form"):
            # These fields match your UI requirement exactly
            id_patient_name = st.text_input("PATIENT NAME")
            id_doctor_name = st.text_input("DOCTOR NAME")
            id_surgery = st.text_input("SURGERY UNDERGONE")
            
            login_submitted = st.form_submit_button("Fetch My Daily Check-in Form")

        if login_submitted:
            if not all([id_patient_name, id_doctor_name, id_surgery]):
                st.warning("Please fill in all three identification fields.")
            else:
                with st.spinner("Connecting to n8n..."):
                    try:
                        lookup_payload = {
                            "Patient Name": id_patient_name,
                            "Doc Name": id_doctor_name,
                            "Surgery Type": id_surgery
                        }
                        # n8n will use this to find the row in Google Sheets
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

    # --- Step 2: Input Parameters & Final Submit ---
    if "patient_params" in st.session_state:
        details = st.session_state["login_details"]
        st.subheader(f"Daily Entry for {details['Patient Name']}")
        st.caption(f"Physician: {details['Doc Name']} | Surgery: {details['Surgery Type']}")
        
        # Create a container for the input form
        with st.form("daily_checkin_form"):
            input_data = {}
            files_to_send = {}

            # Generate UI based on parameters stored in Google Sheets
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

            # --- THE MISSING SUBMIT BUTTON ---
            submit_final = st.form_submit_button("Submit Daily Check-in & Analyze")

            if submit_final:
                with st.spinner("AI is analyzing your recovery status..."):
                    payload = {
                        "identification": st.session_state["login_details"],
                        "readings": input_data
                    }
                    try:
                        # Send JSON data and Binary files to n8n
                        res = requests.post(
                            N8N_WEBHOOK_PROCESS_SUBMISSION, 
                            data={"main_data": json.dumps(payload)}, 
                            files=files_to_send
                        )
                        res.raise_for_status()
                        analysis = res.json()
                        
                        # Display AI Results
                        st.divider()
                        st.success("Analysis Complete!")
                        st.metric("Recovery Rate", f"{analysis.get('recovery_rate', 0)}%")
                        st.write(f"**AI Evaluation:** {analysis.get('recovery_status')}")
                        
                        # Handle Risk Alerts
                        if analysis.get('risk_status') == "Risk":
                            st.error(f"🚨 ALERT: {analysis.get('alert_details')}")
                            st.warning("The doctor has been notified via email.")
                        else:
                            st.balloons()
                            
                    except Exception as e:
                        st.error(f"Submission failed: {e}")

        if st.button("Logout / Switch Account"):
            st.session_state.clear()
            st.rerun()
