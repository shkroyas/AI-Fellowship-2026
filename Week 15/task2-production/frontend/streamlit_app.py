"""
Task 2: Production AI Assistant - Streamlit Web UI.

A beautiful, production-ready web interface for the AI assistant
with chat history, document upload, and configuration options.
"""

import json
import time
import streamlit as st
import httpx
import asyncio
from datetime import datetime


# ── Page Configuration ──
st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for Premium UI ──
st.markdown("""
<style>
    /* Dark theme with glassmorphism */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }

    /* Chat container styling */
    .chat-message {
        padding: 1rem 1.5rem;
        border-radius: 16px;
        margin: 0.5rem 0;
        animation: fadeIn 0.3s ease-in;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
        border-bottom-right-radius: 4px;
    }

    .assistant-message {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #e0e0e0;
        margin-right: 20%;
        border-bottom-left-radius: 4px;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.95);
        backdrop-filter: blur(20px);
    }

    /* Header */
    .main-header {
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 1rem;
    }

    .main-header h1 {
        background: linear-gradient(135deg, #667eea, #764ba2, #f093fb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
    }

    .stats-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }

    /* Tool call indicator */
    .tool-call {
        background: rgba(102, 126, 234, 0.15);
        border-left: 3px solid #667eea;
        padding: 0.5rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.3rem 0;
        font-size: 0.85rem;
    }

    /* Source badge */
    .source-badge {
        display: inline-block;
        background: rgba(240, 147, 251, 0.2);
        color: #f093fb;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        margin: 2px;
    }

    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ── Configuration ──
BACKEND_URL = st.sidebar.text_input(
    "🔗 Backend URL",
    value="http://localhost:8000",
    help="URL of the AI Assistant FastAPI backend",
)

# ── Session State Initialization ──
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0


def call_backend(endpoint: str, method: str = "GET", data: dict = None, files=None, timeout: float = 60.0) -> dict:
    """Make a request to the backend API with error handling."""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        with httpx.Client(timeout=timeout) as client:
            if method == "GET":
                response = client.get(url)
            elif method == "POST":
                if files:
                    response = client.post(url, files=files)
                else:
                    response = client.post(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        st.error(f"❌ Cannot connect to backend at {BACKEND_URL}. Is the server running?")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"❌ Backend error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None


# ── Header ──
st.markdown("""
<div class="main-header">
    <h1>🤖 AI Assistant</h1>
    <p style="color: #a0a0a0; font-size: 1.1rem;">
        Powered by RAG • Multi-Provider LLM • Tool Calling
    </p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    # Provider selection
    provider = st.selectbox(
        "LLM Provider",
        options=["gemini", "openai", "local_vllm"],
        index=0,
        help="Select the LLM provider to use",
    )

    # Prompt style
    prompt_style = st.selectbox(
        "Prompt Style",
        options=["balanced", "creative", "precise", "deterministic"],
        index=0,
        help="Controls temperature and creativity",
    )

    # RAG toggle
    use_rag = st.checkbox("📚 Use RAG", value=True, help="Enable knowledge base retrieval")
    use_tools = st.checkbox("🔧 Use Tools", value=True, help="Enable tool calling")

    st.markdown("---")

    # Document upload
    st.markdown("## 📄 Knowledge Base")
    uploaded_file = st.file_uploader(
        "Upload Document",
        type=["txt", "md", "pdf", "json", "csv"],
        help="Upload a document to the RAG knowledge base",
    )

    if uploaded_file:
        if st.button("📥 Ingest Document"):
            with st.spinner("Ingesting document..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                result = call_backend("/documents/upload", method="POST", files=files)
                if result:
                    st.success(f"✅ {result.get('message', 'Document ingested!')}")

    # Direct text ingestion
    with st.expander("📝 Ingest Text"):
        ingest_text = st.text_area("Enter text to add to knowledge base")
        ingest_source = st.text_input("Source name", value="manual_input")
        if st.button("Add to Knowledge Base"):
            if ingest_text:
                result = call_backend(
                    "/documents/ingest",
                    method="POST",
                    data={"text": ingest_text, "source": ingest_source},
                )
                if result:
                    st.success(f"✅ Added {result.get('chunks_added', 0)} chunks")

    st.markdown("---")

    # Stats
    st.markdown("## 📊 Statistics")
    if st.button("Refresh Stats"):
        stats = call_backend("/documents/stats")
        if stats:
            st.json(stats)

    # Session info
    st.markdown("---")
    st.markdown("## 💬 Session")
    st.write(f"Messages: {len(st.session_state.messages)}")
    st.write(f"Total tokens: {st.session_state.total_tokens}")

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.session_state.total_tokens = 0
        st.rerun()


# ── Chat Display ──
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]

    if role == "user":
        st.markdown(f'<div class="chat-message user-message">👤 {content}</div>', unsafe_allow_html=True)
    else:
        # Build assistant message with extras
        extras = ""
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                extras += f'<div class="tool-call">🔧 Used <strong>{tc["tool"]}</strong>: {tc.get("result", "")[:100]}</div>'
        if msg.get("sources"):
            sources_html = "".join(f'<span class="source-badge">📄 {s}</span>' for s in msg["sources"])
            extras += f'<div style="margin-top: 0.5rem">{sources_html}</div>'

        st.markdown(
            f'<div class="chat-message assistant-message">🤖 {content}{extras}</div>',
            unsafe_allow_html=True,
        )


# ── Chat Input ──
if prompt := st.chat_input("Ask me anything..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(f'<div class="chat-message user-message">👤 {prompt}</div>', unsafe_allow_html=True)

    # Build history for API
    history = []
    for msg in st.session_state.messages[:-1]:
        history.append({"role": msg["role"], "content": msg["content"]})

    # Call backend
    with st.spinner("🤔 Thinking..."):
        start_time = time.time()
        result = call_backend(
            "/chat",
            method="POST",
            data={
                "message": prompt,
                "conversation_id": st.session_state.conversation_id,
                "history": history,
                "use_rag": use_rag,
                "use_tools": use_tools,
                "prompt_style": prompt_style,
                "provider": provider,
            },
        )
        elapsed = time.time() - start_time

    if result:
        response_text = result.get("response", "No response received")
        st.session_state.conversation_id = result.get("conversation_id")

        # Track tokens
        usage = result.get("usage", {})
        st.session_state.total_tokens += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

        # Store assistant message with extras
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "tool_calls": result.get("tool_calls_made", []),
            "sources": result.get("sources", []),
        })

        # Display response
        extras = ""
        tool_calls = result.get("tool_calls_made", [])
        if tool_calls:
            for tc in tool_calls:
                extras += f'<div class="tool-call">🔧 Used <strong>{tc["tool"]}</strong>: {tc.get("result", "")[:100]}</div>'

        sources = result.get("sources", [])
        if sources:
            sources_html = "".join(f'<span class="source-badge">📄 {s}</span>' for s in sources)
            extras += f'<div style="margin-top: 0.5rem">{sources_html}</div>'

        st.markdown(
            f'<div class="chat-message assistant-message">🤖 {response_text}{extras}</div>',
            unsafe_allow_html=True,
        )

        # Show performance info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"⏱️ {elapsed:.2f}s")
        with col2:
            st.caption(f"📊 Model: {result.get('model', 'N/A')}")
        with col3:
            rag_icon = "✅" if result.get("rag_context_used") else "❌"
            st.caption(f"📚 RAG: {rag_icon}")
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "⚠️ Failed to get response. Please check the backend connection.",
        })
        st.rerun()

# ── Structured Output Section ──
with st.expander("📋 Structured Output"):
    st.markdown("Get structured JSON responses from the AI")
    struct_input = st.text_area("Query for structured output", key="struct_input")
    struct_type = st.selectbox("Output Schema", ["analysis", "qa"])

    if st.button("Generate Structured Output"):
        if struct_input:
            with st.spinner("Generating..."):
                result = call_backend(
                    "/chat/structured",
                    method="POST",
                    data={
                        "message": struct_input,
                        "output_type": struct_type,
                        "provider": provider,
                    },
                )
                if result:
                    st.json(result.get("output", {}))
