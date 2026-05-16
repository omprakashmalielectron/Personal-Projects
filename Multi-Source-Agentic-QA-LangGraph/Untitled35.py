import asyncio
import streamlit as st
from __Untitled31 import run_agent  

st.set_page_config(
    page_title="LangGraph MCP Agent",
    page_icon="🧠",
    layout="centered",
)

st.title("🧠 LangGraph MCP Agent")
st.caption("SQL (Northwind) + RAG (PubMed) via MCP")

# Session state
if "chat" not in st.session_state:
    st.session_state.chat = []

# Render chat history
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Ask a question...")

if question:
    # User message
    st.session_state.chat.append(
        {"role": "user", "content": question}
    )
    with st.chat_message("user"):
        st.markdown(question)

    # Assistant message
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = asyncio.run(run_agent(question))

        answer = result.get("answer")
        route = result.get("route")
        sql_query = result.get("sql_query")
        metadata = result.get("metadata")

        # -------------------------
        # Main answer
        # -------------------------
        st.markdown(answer)

        # -------------------------
        # Routing info
        # -------------------------
        st.caption(f"🔀 Routed to: `{route}`")

        # -------------------------
        # Debug / inspection panel
        # -------------------------
        with st.expander("🛠️ Agent Debug Information", expanded=False):

            # ===== SQL PATH =====
            if route == "STRUCTURED_DATA":
                st.subheader("📊 SQL Agent")

                if sql_query:
                    st.markdown("**Generated SQL Query:**")
                    st.code(sql_query, language="sql")
                else:
                    st.warning("No SQL query was generated.")

                if metadata:
                    st.markdown("**Tables Used:**")
                    for t in metadata:
                        st.markdown(f"- `{t}`")
                else:
                    st.info("No table metadata available.")

            # ===== RAG PATH =====
            elif route == "UNSTRUCTURED_DATA":
                st.subheader("📚 RAG Agent")

                if metadata:
                    st.markdown("**Retrieved Sources:**")
                    for i, m in enumerate(metadata, 1):
                        st.markdown(
                            f"""
                            **{i}. Source**
                            - **Source:** {m.get('source', 'Unknown')}
                            - **Page:** {m.get('page', 'N/A')}
                            """
                        )
                else:
                    st.info("No document metadata available.")

            # ===== RAW METADATA =====
            st.divider()
            st.subheader("🧾 Raw Metadata (Full Object)")
            if metadata:
                st.json(metadata)
            else:
                st.write("None")

    st.session_state.chat.append(
        {"role": "assistant", "content": answer}
    )