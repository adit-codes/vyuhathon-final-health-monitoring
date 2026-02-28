import streamlit as st
import requests
import json
import time 
import hashlib 

# --- Page Configurations ---
st.set_page_config(page_title="Telehealth AI Assistant", layout="wide")

# --- Webhook URLs ---
# Note: Ensure these are set to POST in n8n and the workflows are ACTIVE.
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
                # Changed to POST as we are sending a JSON payload
                response = requests.get(N8N_WEBHOOK_DOCTOR_CONFIG, json=payload)
                if response.status_code == 200:
                    st.session_state.temp_data = payload
                    st.session_state.doc_step = "branch"
                    st.rerun()
                else:
                    st.error(f"Failed to register. Status: {response.status_code}. Check if n8n workflow is active.")
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
                            st.success("Workflow X Triggered successfully!")
                            st.session_state.doc_step = "input"
                        else:
                            st.error(f"Error {res.status_code}: Could not trigger workflow.")
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
# 2. Patient's Interface
# ==========================================
elif app_mode == "Patient's Portal":
    st.header("2. Patient's Daily Portal")
    
    # Initialize session state keys
    if "login_details" not in st.session_state:
        st.session_state.login_details = None
    if "patient_params" not in st.session_state:
        st.session_state.patient_params = None
    if "dynamic_form_fields" not in st.session_state:
        st.session_state.dynamic_form_fields = None

    # --- Step 1: Login Section ---
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
                with st.spinner("Connecting to Server..."):
                    try:
                        lookup_payload = {
                            "Patient Name": id_patient_name,
                            "Doc Name": id_doctor_name,
                            "Surgery Type": id_surgery
                        }
                        # Use POST to ensure JSON body is received by n8n
                        response = requests.post(N8N_WEBHOOK_GET_PATIENT_PARAMS, json=lookup_payload)
                        response.raise_for_status()
                        
                        st.session_state.patient_params = response.json()
                        st.session_state.login_details = lookup_payload
                        st.rerun() 
                        
                    except Exception as e:
                        st.error(f"Error fetching patient parameters: {e}. Check if Webhook URL is correct and Active.")

    # --- Step 2: Post-Login Section (Parameters & Dynamic Form) ---
    else:
        details = st.session_state["login_details"]
        st.subheader(f"Welcome, {details['Patient Name']}")
        
        # If we haven't fetched the dynamic fields yet
        if st.session_state.dynamic_form_fields is None:
            st.info("Your profile is loaded. Please initialize your daily check-in.")
            if st.button("Fetch My Daily Parameters"):
                with st.spinner("Loading requirements..."):
                    try:
                        z_payload = {
                            "patient_info": details, 
                            "params": st.session_state["patient_params"]
                        }
                        z_res = requests.post(N8N_WEBHOOK_WORKFLOW_Z, json=z_payload)
                        
                        if z_res.status_code == 200:
                            data_from_n8n = z_res.json()
                            fields = data_from_n8n if isinstance(data_from_n8n, list) else data_from_n8n.get("fields", [])
                            st.session_state.dynamic_form_fields = fields
                            st.rerun()
                        else:
                            st.error(f"Server returned error: {z_res.status_code}")
                    except Exception as e:
                        st.error(f"Error fetching dynamic fields: {e}")

  

        
        # If fields are loaded, render the form
        else:
            st.write("### Today's Recovery Check-in")
            st.caption("Please provide the data requested by your doctor:")
            # --- START OF THE IMPROVED DYNAMIC FORM RENDERING ---
    else:
        st.write("### Today's Recovery Check-in")
        st.caption("Please provide the data requested by your doctor:")

        for idx, field in enumerate(st.session_state.dynamic_form_fields):
            # Standardizing keys: handles 'name' or 'Parameter Name'
            f_name = field.get("name") or field.get("Parameter Name") or f"Parameter {idx+1}"
            
            # Get the type and clean it (handles 'image ', 'Image', 'IMAGE')
            raw_type = field.get("data_type") or field.get("type") or "text"
            f_type = str(raw_type).strip().lower()
            
            with st.container(border=True):
                st.markdown(f"### {f_name}")
                
                user_input = None
                
                if f_type == "text":
                    user_input = st.text_area(f"Provide details for {f_name}", key=f"input_{idx}")
                    
                elif f_type == "image":
                    user_input = st.file_uploader(f"Upload photo for {f_name}", type=['png', 'jpg', 'jpeg'], key=f"input_{idx}")
                    if user_input: 
                        st.image(user_input, width=300, caption="Preview")
                        
                elif f_type == "audio":
                    user_input = st.file_uploader(f"Upload audio recording for {f_name}", type=['mp3', 'wav', 'm4a'], key=f"input_{idx}")
                    if user_input: 
                        st.audio(user_input)
                
                else:
                    # Fallback for unexpected types
                    user_input = st.text_input(f"Enter {f_name}", key=f"input_{idx}")

                if st.button(f"Submit {f_name}", key=f"btn_{idx}"):
                    if user_input:
                        # Logic to send data back to n8n would go here
                        st.success(f"✅ {f_name} submitted!")
                    else:
                        st.warning("Please provide data.")

        if st.button("Logout / Reset Portal"):
            for key in ["login_details", "patient_params", "dynamic_form_fields"]:
                if key in st.session_state:
                    st.session_state[key] = None
            st.rerun()  
