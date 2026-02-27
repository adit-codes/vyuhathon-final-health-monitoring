import streamlit as st
import requests
import json

# --- Page Configurations ---
st.set_page_config(page_title="Telehealth AI Assistant", layout="wide")

# --- Custom N8N Webhook URLs (REPLACE THESE) ---
# For Workflow A (Doctor - Setup)
N8N_WEBHOOK_DOCTOR_CONFIG = "https://your-n8n-instance.com/webhook/doctor-config"

# For Workflow B (Patient - Part 1: Get Parameters)
N8N_WEBHOOK_GET_PATIENT_PARAMS = "https://your-n8n-instance.com/webhook/get-patient-params"

# For Workflow B (Patient - Part 2: Submit and Analyze)
N8N_WEBHOOK_PROCESS_SUBMISSION = "https://your-n8n-instance.com/webhook/process-submission"


# --- Application Title ---
st.title("AI-Powered Patient Recovery Monitoring")


# --- Sidebar for Navigation ---
app_mode = st.sidebar.selectbox("Choose Interface", ["Doctor's Panel", "Patient's Portal"])


# ==========================================
# 1. Doctor's Interface
# ==========================================
if app_mode == "Doctor's Panel":
    st.header("1. Doctor's Configuration Panel")
    st.subheader("Define monitoring parameters for a new patient.")

    # Input form
    with st.form("doctor_config_form"):
        col1, col2 = st.columns(2)
        with col1:
            doctor_name = st.text_input("Your Name (Doctor)")
            patient_name = st.text_input("Patient's Full Name")
        with col2:
            disease = st.text_input("Diagnosed Disease/Condition")
            parameter_method = st.radio("How would you like to set parameters?", ("AI-generated (Recommended)", "Manually set"))

        submitted = st.form_submit_button("Configure and Save")

    if submitted:
        if not all([doctor_name, patient_name, disease]):
            st.error("Please fill in all the patient's basic information.")
        else:
            # Prepare data to send to n8n
            data_to_send = {
                "doctor_name": doctor_name,
                "patient_name": patient_name,
                "disease": disease,
                "config_method": "ai" if "AI-generated" in parameter_method else "manual"
            }

            # If manual, the doctor must provide the parameters (not implemented in this simplified code for brevity)
            if "Manually set" in parameter_method:
                st.info("In a full system, a form would appear here to manually list parameters. For this demo, we'll proceed as if it's AI-generated.")
                data_to_send["config_method"] = "ai" # Defaulting back for the demo

            with st.spinner("Talking to n8n backend..."):
                try:
                    # 1. Trigger the n8n "Doctor's Configuration" Workflow
                    response = requests.post(N8N_WEBHOOK_DOCTOR_CONFIG, json=data_to_send)
                    response.raise_for_status() # Raise error for bad status codes

                    st.success(f"Configuration for {patient_name} successfully sent to the backend database!")
                    # In a real app, n8n might send back the AI-generated parameters for review.
                    # We can display that here if needed.

                except requests.exceptions.RequestException as e:
                    st.error(f"Error connecting to n8n: {e}")


# ==========================================
# 2. Patient's Interface
# ==========================================
elif app_mode == "Patient's Portal":
    st.header("2. Patient's Daily Portal")
    st.subheader("Submit your daily check-in data.")

    # Part 1: Patient Identifies Themselves and Fetches Their Form
    if "patient_params" not in st.session_state:
        st.write("---")
        with st.form("patient_login_form"):
            login_patient_name = st.text_input("Your Full Name to begin")
            login_submitted = st.form_submit_button("Fetch My Check-in Form")

        if login_submitted and login_patient_name:
            with st.spinner(f"Fetching your personalized form for {login_patient_name}..."):
                try:
                    # 1. Trigger n8n Workflow #2a to get parameters
                    response = requests.post(N8N_WEBHOOK_GET_PATIENT_PARAMS, json={"patient_name": login_patient_name})
                    response.raise_for_status()
                    patient_params = response.json() # Expecting a JSON list of parameters

                    if patient_params and isinstance(patient_params, list) and len(patient_params) > 0:
                        st.session_state["patient_params"] = patient_params
                        st.session_state["login_patient_name"] = login_patient_name
                        st.success("Form loaded! See below.")
                        st.experimental_rerun() # Refresh page to show the form
                    else:
                        st.warning("No monitoring plan found for that name. Please check with your doctor.")

                except requests.exceptions.RequestException as e:
                    st.error(f"Error fetching parameters: {e}")

    # Part 2: Display the Form and Process the Submission
    if "patient_params" in st.session_state:
        st.write("---")
        st.write(f"### Daily Check-in form for: **{st.session_state['login_patient_name']}**")
        st.info("Please fill out the following information as accurately as possible.")

        # Create a dictionary to store the user's input values
        input_data = {}
        files_to_send = {} # For audio/images

        # Loop through each parameter defined by the doctor and create an input widget
        for param in st.session_state["patient_params"]:
            p_name = param.get("name")
            p_desc = param.get("description", "")
            p_type = param.get("data_type", "text").lower()
            label = f"{p_name} ({p_desc})"

            if p_type == "text":
                input_data[p_name] = st.text_input(label)
            elif p_type == "number":
                input_data[p_name] = st.number_input(label, value=0.0)
            elif p_type == "boolean":
                input_data[p_name] = st.checkbox(label)
            elif p_type == "audio":
                audio_file = st.file_uploader(label, type=["mp3", "wav", "m4a"])
                if audio_file:
                    files_to_send["audio_file"] = (audio_file.name, audio_file, audio_file.type)
            elif p_type == "image":
                image_file = st.file_uploader(label, type=["jpg", "jpeg", "png"])
                if image_file:
                    files_to_send["image_file"] = (image_file.name, image_file, image_file.type)

        # Final submission button
        submit_daily_checkin = st.button("Submit My Daily Check-in")

        if submit_daily_checkin:
            with st.spinner("Analyzing your data and image with AI..."):
                # Prepare the main JSON payload
                payload = {
                    "patient_name": st.session_state["login_patient_name"],
                    "form_data": input_data # Text, numbers, etc.
                }

                # We must use 'data' for the JSON and 'files' for multipart/form-data
                try:
                    # 1. Trigger n8n Workflow #2b for final analysis
                    # Note: We send payload as a string and n8n Code node must parse it.
                    response = requests.post(
                        N8N_WEBHOOK_PROCESS_SUBMISSION,
                        data={"main_data": json.dumps(payload)},
                        files=files_to_send
                    )
                    response.raise_for_status()
                    analysis_result = response.json() # Expecting a JSON object

                    # 2. Display the AI's detailed analysis
                    st.write("---")
                    st.success("Analysis Complete!")

                    st.markdown(f"### **Recovery Status:** {analysis_result.get('recovery_status')}")

                    # Recovery Rate Visual
                    rate = analysis_result.get("recovery_rate", 0)
                    st.progress(rate / 100.0)
                    st.write(f"Recovery Rate: **{rate}%**")

                    st.write("### **Personalized Guidelines:**")
                    guidelines = analysis_result.get("recovery_guidelines", [])
                    if isinstance(guidelines, list):
                        for item in guidelines:
                            st.write(f"- {item}")
                    else:
                        st.write(guidelines) # Fallback

                    # Show a warning for 'Risk' status
                    if analysis_result.get("risk_status") == "Risk":
                        st.error("### 🚨 **Attention Required** 🚨")
                        st.write(analysis_result.get("alert_details"))
                        st.warning("Your doctor and a clinic assistant have been automatically notified. A professional will contact you shortly.")

                except requests.exceptions.RequestException as e:
                    st.error(f"Error during submission and analysis: {e}")

        # Button to 'log out' and reset the form
        st.write("---")
        if st.button("Clear Form / Start Over"):
            del st.session_state["patient_params"]
            del st.session_state["login_patient_name"]
            st.experimental_rerun()
