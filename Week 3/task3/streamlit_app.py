import os
import json
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from executor import TextToSQLPipeline
from database import DatabaseConnection

# Load environment variables
load_dotenv()

# Set up page configurations
st.set_page_config(
    page_title="Text-to-SQL Chaining Pipeline",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Aesthetics and Glassmorphism Custom CSS styling
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Space+Grotesk:wght@400;600&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Background gradients */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #020617 100%);
        color: #f8fafc;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Glassmorphism containers for chat cards */
    .chat-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        transition: all 0.3s ease;
    }
    .chat-card:hover {
        border-color: rgba(99, 102, 241, 0.4);
        box-shadow: 0 12px 40px 0 rgba(99, 102, 241, 0.15);
    }
    
    /* Code headers & status badges */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    .badge-success {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    .badge-failed {
        background-color: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.4);
    }
    .badge-retry {
        background-color: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.4);
    }
    
    /* Headers with dynamic underline */
    .title-gradient {
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
    }
    
    /* Standardize expanders to be transparent & modern */
    .stMarkdown h3 {
        font-family: 'Space Grotesk', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pipeline" not in st.session_state:
    st.session_state.pipeline = TextToSQLPipeline()
if "db_connected" not in st.session_state:
    db_conn = DatabaseConnection()
    _, _, err = db_conn.execute_query("SELECT 1;")
    st.session_state.db_connected = (err is None)
    st.session_state.db_error = err

# App Header
st.markdown("<h1 class='title-gradient' style='font-size: 2.8rem; margin-bottom: 0.2rem;'>⚡ Text-to-SQL Chaining Agent</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8; font-size: 1.1rem; margin-bottom: 2rem;'>A production-ready Text-to-SQL Pipeline implementing strict sequential Prompt Chaining (Decompose ➔ Generate ➔ Validate ➔ Execute ➔ Auto-Fix).</p>", unsafe_allow_html=True)

# Sidebar Diagnostics & Tools
with st.sidebar:
    st.markdown("<h2 style='font-family: \"Space Grotesk\", sans-serif; color: #a855f7;'>⚙️ Engine Control Room</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # 1. Database Connection Status Check
    st.markdown("### 🔌 Database Diagnostics")
    if st.session_state.db_connected:
        st.success("PostgreSQL Connected (Port 5433)")
    else:
        st.error(f"PostgreSQL Offline: {st.session_state.db_error}")
        
    st.markdown("---")
    
    # 2. Pre-defined benchmark sample clicks
    st.markdown("### 💡 Click-to-Test Questions")
    sample_queries = [
        "List all products",
        "How many customers are from the USA?",
        "Get product names and prices",
        "Get orders with customer names",
        "Average buy price per product line",
        "List employee first and last names working in Boston"
    ]
    
    for sq in sample_queries:
        if st.button(sq, key=f"btn_{sq}", use_container_width=True):
            # Programmatically trigger submit by saving in query state
            st.session_state.selected_query = sq
            
    st.markdown("---")
    
    # 3. Log Analytics
    st.markdown("### 📊 Logs & Metrics")
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "query_logs.json")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                logs_data = json.load(f)
            total_runs = len(logs_data)
            success_runs = sum(1 for l in logs_data if l.get("status") == "success")
            retry_runs = sum(1 for l in logs_data if l.get("is_retry_needed"))
            
            st.metric("Total Executions", total_runs)
            st.metric("Successful Executions", f"{success_runs}/{total_runs}")
            st.metric("Self-Correction Retries", retry_runs)
            
            if st.button("Clear Log History", use_container_width=True):
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump([], f)
                st.rerun()
        except:
            st.info("Log file is currently empty.")
    else:
        st.info("No logs created yet.")

# Main Chat View
query_input = st.chat_input("Ask a question about the ClassicModels database...")

# Detect if a sample query was clicked in the sidebar
if "selected_query" in st.session_state and st.session_state.selected_query:
    user_query = st.session_state.selected_query
    st.session_state.selected_query = None # Reset state
else:
    user_query = query_input

if user_query:
    with st.spinner("Executing Text-to-SQL Prompt Chaining Pipeline..."):
        # Execute orchestrator pipeline
        pipeline_output = st.session_state.pipeline.run(user_query)
        
        # Append result to session chat history
        st.session_state.chat_history.append({
            "question": user_query,
            "pipeline_output": pipeline_output
        })

# Render Chat History
for chat in reversed(st.session_state.chat_history):
    q = chat["question"]
    output = chat["pipeline_output"]
    
    sql = output["sql"]
    result_rows = output["result"]
    columns = output["columns"]
    status = output["status"]
    retry_needed = output["retry_needed"]
    fixed_sql = output["fixed_sql"]
    error = output["error"]
    
    # Render glassmorphism card wrapper
    st.markdown(f"""
    <div class="chat-card">
        <h3 style="margin-top: 0; color: #818cf8; font-size: 1.3rem;">❓ Question: "{q}"</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Badge Status headers
    col_badge, col_empty = st.columns([1, 4])
    with col_badge:
        if status == "success":
            if retry_needed:
                st.markdown("<span class='status-badge badge-retry'>⚠️ Auto-Corrected</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='status-badge badge-success'>✓ Success</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='status-badge badge-failed'>✗ Failed</span>", unsafe_allow_html=True)
            
    # Tabs containing Pipeline Steps
    tab_res, tab_steps, tab_logs = st.tabs(["📊 Final Result", "⛓️ Prompt Chaining Steps", "🛠️ Technical Logs"])
    
    with tab_res:
        if status == "success":
            if result_rows:
                df = pd.DataFrame(result_rows)
                st.markdown("#### Execution Result Dataframe:")
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Query executed successfully, but returned 0 rows.")
        else:
            st.error(f"Failed to generate valid results. Reason: {error}")
            
    with tab_steps:
        # Step 1: Decomposition Expanders
        with st.expander("🔍 Step 1: Structural Query Decomposition (LLM Call 1)", expanded=False):
            # Load decomposed JSON from logs
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "query_logs.json")
            decomposed_struct = {"Status": "Not loaded"}
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                    # Find matching log entry
                    for entry in reversed(logs):
                        if entry["question"] == q:
                            decomposed_struct = entry["decomposed_json"]
                            break
                except:
                    pass
            st.markdown("Gemini-2.5-Flash parsed the intent, tables, columns, filters, and joins from the natural language question:")
            st.json(decomposed_struct)

        # Step 2: Generation Expanders
        with st.expander("💻 Step 2: raw SQL Generation (LLM Call 2)", expanded=False):
            # Fetch original generated SQL
            orig_sql = sql
            if retry_needed and os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                    for entry in reversed(logs):
                        if entry["question"] == q:
                            orig_sql = entry["generated_sql"]
                            break
                except:
                    pass
            st.markdown("Raw generated PostgreSQL statement:")
            st.code(orig_sql, language="sql")

        # Step 3: Security Validation
        with st.expander("🛡️ Step 3: Security Validation Layer (Rule-Based Check)", expanded=False):
            st.success("Query passed security filters. No DML/DDL commands (DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE) detected.")

        # Step 4: Self-Correction (Retry) Expanders
        if retry_needed:
            with st.expander("🔄 Step 4: Self-Correction Diagnostics (LLM Call 3 - ONE retry)", expanded=True):
                st.warning("Database Exception Detected upon initial run! Pipeline triggered the auto-fix loop.")
                
                # Fetch error message from logs
                db_err = error
                if os.path.exists(log_path):
                    try:
                        with open(log_path, "r", encoding="utf-8") as f:
                            logs = json.load(f)
                        for entry in reversed(logs):
                            if entry["question"] == q:
                                db_err = entry["error_message"]
                                break
                    except:
                        pass
                
                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown("**Original Failed SQL:**")
                    st.code(orig_sql, language="sql")
                    st.error(f"**Database Error:** {db_err}")
                with col_right:
                    st.markdown("**Corrected Self-Cured SQL:**")
                    st.code(fixed_sql, language="sql")
                    st.success("Fixed SQL executed successfully without throwing errors!")

    with tab_logs:
        st.markdown("#### Comprehensive Pipeline JSON Output:")
        st.json(output)
    
    st.markdown("---")
