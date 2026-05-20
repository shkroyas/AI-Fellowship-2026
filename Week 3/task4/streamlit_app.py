import streamlit as st
import pandas as pd
import json
from graph.workflow import TextToSQLWorkflow
from db import engine

# ---------------------------------------------------------
# Page Configurations & Design Palette
# ---------------------------------------------------------
st.set_page_config(
    page_title="Agentic Text-to-SQL Workspace",
    page_icon="🤖",
    layout="wide"
)

# Custom premium styling rules (Dark-mode, Glassmorphism, Micro-animations)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Premium Glassmorphic Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }
    
    .status-success {
        color: #00E676;
        font-weight: 600;
        background: rgba(0, 230, 118, 0.1);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        border: 1px solid rgba(0, 230, 118, 0.3);
    }
    
    .status-error {
        color: #FF5252;
        font-weight: 600;
        background: rgba(255, 82, 82, 0.1);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        border: 1px solid rgba(255, 82, 82, 0.3);
    }
    
    /* Code highlight enhancements */
    .stCodeBlock {
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        background: #0D0E15 !important;
    }
    </style>
""", unsafe_allow_value=True)

# Initialize Session Counters
if "total_runs" not in st.session_state:
    st.session_state.total_runs = 0
if "success_runs" not in st.session_state:
    st.session_state.success_runs = 0
if "retry_runs" not in st.session_state:
    st.session_state.retry_runs = 0

# ---------------------------------------------------------
# Sidebar Panel: Diagnostics & Quick-Links
# ---------------------------------------------------------
st.sidebar.title("⚙️ Engine Control Room")

# Database Connection Check
st.sidebar.subheader("🔌 Database Diagnostics")
try:
    with engine.connect() as conn:
        st.sidebar.markdown('<span class="status-success">PostgreSQL Connected (Port 5434)</span>', unsafe_allow_value=True)
except Exception as e:
    st.sidebar.markdown(f'<span class="status-error">Disconnected: {str(e)[:40]}...</span>', unsafe_allow_value=True)

st.sidebar.write("---")

# Click-to-Test preset questions panel
st.sidebar.subheader("💡 Click-to-Test Questions")
preset_questions = [
    "List all products",
    "How many customers are from the USA?",
    "Get product names and prices",
    "Average buy price per product line",
    "Get orders with customer names"
]

selected_query = None
for q in preset_questions:
    if st.sidebar.button(q, key=f"preset_{q}"):
        selected_query = q

st.sidebar.write("---")

# Live Session metrics tracker
st.sidebar.subheader("📊 Session metrics")
col1, col2 = st.sidebar.columns(2)
col1.metric("Executions", st.session_state.total_runs)
col2.metric("Success Rate", f"{st.session_state.success_runs}/{st.session_state.total_runs}")
st.sidebar.metric("Correction Retries", st.session_state.retry_runs)

if st.sidebar.button("Clear metrics logs"):
    st.session_state.total_runs = 0
    st.session_state.success_runs = 0
    st.session_state.retry_runs = 0
    st.rerun()

# ---------------------------------------------------------
# Main Workspace Dashboard
# ---------------------------------------------------------
st.title("🤖 Multi-Agent Text-to-SQL Workspace")
st.write("A production-grade Agentic SQL pipeline executing strict workflow routing: Planner ➔ Generator ➔ Validator ➔ Executor ➔ Summarizer.")

# Text-area input form
with st.container():
    st.markdown('<div class="glass-card">', unsafe_allow_value=True)
    input_text = st.text_input(
        "Ask a business intelligence question about the ClassicModels database:",
        value=selected_query if selected_query else "",
        placeholder="E.g., How many customers are from the USA?"
    )
    submit_button = st.button("🚀 Trigger Agent Workflow", use_container_width=True)
    st.markdown('</div>', unsafe_allow_value=True)

if submit_button and input_text.strip():
    st.session_state.total_runs += 1
    
    # Trigger State Machine Orchestrator
    with st.spinner("Pipelining request through active agent nodes..."):
        try:
            workflow = TextToSQLWorkflow()
            final_state = workflow.run(input_text.strip())
            
            # Update metric logs
            if final_state.execution_results:
                st.session_state.success_runs += 1
            if final_state.retry_count > 0:
                st.session_state.retry_runs += final_state.retry_count
                
            # Render workspace output tabs
            st.write("### 🏁 Pipeline Processing Results")
            tab1, tab2, tab3 = st.tabs(["📊 Final Response", "🔄 Agentic Pipeline Traces", "🛠️ Technical JSON Logs"])
            
            # Tab 1: Final natural summary answer and datasets
            with tab1:
                st.markdown("#### 💬 Synthesized BI Answer")
                st.info(final_state.final_answer)
                
                if final_state.execution_results:
                    st.markdown("#### 📂 Execution Result Dataframe")
                    df = pd.DataFrame(final_state.execution_results)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.warning("No records returned from the database execution.")
            
            # Tab 2: Individual Agent state transitions
            with tab2:
                # Node 1: Planner Agent Plan
                with st.expander("🔍 Step 1: Planner Agent Strategy Plan", expanded=True):
                    st.markdown(final_state.plan)
                    
                # Node 2: SQL Generator Query Output
                with st.expander("💻 Step 2: Generator Agent Raw SQL Query", expanded=True):
                    st.code(final_state.generated_sql, language="sql")
                    
                # Node 3: Validator Agent Checks
                with st.expander("🛡️ Step 3: Validator Agent Security Assessment", expanded=True):
                    if final_state.is_valid_sql:
                        st.markdown('<span class="status-success">Query Passed. No destructive DML or SQL injection command keywords captured.</span>', unsafe_allow_value=True)
                    else:
                        st.markdown(f'<span class="status-error">Validation Failed: {final_state.errors[0] if final_state.errors else "Invalid SELECT structure"}</span>', unsafe_allow_value=True)
                        
                # Node 4: Self-Correction Node
                with st.expander("🩹 Step 4: Self-Correction Repair Nodes (Feedback Loop)", expanded=True):
                    if final_state.retry_count > 0:
                        st.markdown(f"**Cures Attempted**: {final_state.retry_count}/1")
                        st.markdown("**Captured Compiler/Database Error:**")
                        st.code(final_state.errors[0] if final_state.errors else "DML exception")
                        st.markdown("**Corrected & Cured Output SQL:**")
                        st.code(final_state.generated_sql, language="sql")
                    else:
                        st.markdown("No SQL corrections required. Target query executed successfully on first compile.")
            
            # Tab 3: Detailed raw AgentState payload
            with tab3:
                st.markdown("#### Comprehensive Workflow State Payload")
                state_data = {
                    "question": final_state.user_query,
                    "plan": final_state.plan,
                    "generated_sql": final_state.generated_sql,
                    "is_valid_sql": final_state.is_valid_sql,
                    "retry_count": final_state.retry_count,
                    "errors": final_state.errors,
                    "columns": final_state.columns,
                    "records_count": len(final_state.execution_results) if final_state.execution_results else 0,
                    "execution_results": final_state.execution_results
                }
                st.json(state_data)
                
        except Exception as err:
            st.error(f"Workflow crashed due to an unhandled system failure: {str(err)}")
            st.exception(err)
