import streamlit as st
import requests
import pandas as pd

from typing import List

# --- Configuration ---
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="ArcheoEA",
    page_icon="🏗️",
    layout="wide"
)

st.title("🏗️ ArcheoEA")
st.markdown("Enterprise Architecture Urbanization & Model Management Portal : Use a semantic power strip for the archaeology of your enterprise architecture.")

# --- Helper Functions ---
def api_request(method, endpoint, **kwargs):
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None

# --- Sidebar Navigation ---
st.sidebar.header("Navigation")
menu = st.sidebar.selectbox(
    "Select Operation", 
    ["🏠 Dashboard", "📥 Import Model", "🔍 Model Explorer", "🔄 Migration", "⚖️ Model Comparison"]
)

# Session State to track loaded models
if "model_ids" not in st.session_state:
    st.session_state.model_ids = []

# --- Module: Dashboard ---
if menu == "🏠 Dashboard":
    st.subheader("Architecture Overview")
    st.info("Welcome, Enterprise Architect. Use the sidebar to import and manage your ArchiMate models.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Models in Memory", len(st.session_state.model_ids))
    with col2:
        st.metric("Formalism Support", "v3.2, v4.0")

# --- Module: Import Model ---
elif menu == "📥 Import Model":
    st.subheader("Import XML (ArchiMate Model Exchange File Format required)")
    
    with st.form("import_form"):
        model_name = st.text_input("Model Name", placeholder="e.g., Target State 2025")
        model_version = st.selectbox("ArchiMate Version", ["3.2", "4.0"])
        uploaded_file = st.file_uploader("Choose ArchiMate XML File", type=["xml"])
        submit = st.form_submit_button("Upload & Parse")
        
        if submit:
            if uploaded_file and model_name:
                # The API expects multipart/form-data
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/xml")}
                data = {"name": model_name, "version": model_version}
                
                result = api_request("POST", "/models/import", files=files, data=data)
                if result:
                    st.success(f"Model imported successfully! ID: {result['model_id']}")
                    st.session_state.model_ids.append(result['model_id'])
            else:
                st.warning("Please provide a name and upload a file.")

# --- Module: Model Explorer ---
elif menu == "🔍 Model Explorer":
    st.subheader("Navigate Model Elements")
    
    if not st.session_state.model_ids:
        st.warning("No models loaded. Please import a model first.")
    else:
        selected_id = st.selectbox("Select Model", st.session_state.model_ids)
        search_query = st.text_input("Search elements by name...", "")
        
        if selected_id:
            result = api_request("GET", f"/models/{selected_id}/search?q={search_query}")
            if result:
                df = pd.DataFrame(result)
                if not df.empty:
                    # Cleaning the dataframe for display
                    st.dataframe(df[['id', 'name']], use_container_width=True)
                    st.write(f"Found {len(df)} elements matching your criteria.")
                else:
                    st.info("No elements found.")

# --- Module: Migration ---
elif menu == "🔄 Migration":
    st.subheader("Formalism Version Migration")
    
    if not st.session_state.model_ids:
        st.warning("No models loaded.")
    else:
        selected_id = st.selectbox("Model to Migrate", st.session_state.model_ids)
        target_version = st.selectbox("Target Version", ["3.2", "4.0"])
        
        if st.button("Perform Migration"):
            result = api_request("POST", f"/models/migrate/{selected_id}", params={"target_version": target_version})
            if result:
                st.success(f"Model {selected_id} has been migrated to version {target_version}.")
                st.json(result)

# --- Module: Model Comparison ---
elif menu == "⚖️ Model Comparison":
    st.subheader("Compare Two Architectural States")
    
    if len(st.session_state.model_ids) < 2:
        st.warning("You need at least two imported models to perform a comparison.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            model_a = st.selectbox("Model A (Baseline)", st.session_state.model_ids, index=0)
        with col2:
            model_b = st.selectbox("Model B (Target)", st.session_state.model_ids, index=1)
            
        if st.button("Compare Models"):
            result = api_request("GET", f"/models/compare", params={"a": model_a, "b": model_b})
            if result:
                st.write("### Difference Report")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Only in Model A", len(result['only_in_a']))
                c2.metric("Only in Model B", len(result['only_in_b']))
                c3.metric("Common Elements", len(result['common']))
                
                st.write("---")
                tab1, tab2 = st.tabs(["Elements in A (Gaps)", "Elements in B (New)"])
                with tab1:
                    st.write(result['only_in_a'])
                with tab2:
                    st.write(result['only_in_b'])
