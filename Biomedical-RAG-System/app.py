import streamlit as st
import tempfile
import os
from ingestor import ingest_pdf
from retriver import rag_answer

st.set_page_config(
    page_title="Biomedical RAG Assistant",
    layout="wide"
)
st.title("Biomedical Research Assistant")
st.caption("Upload PDFs • Ask questions • See sources")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.sidebar.header("Document Upload")
uploaded_file = st.sidebar.file_uploader(
    "Upload a biomedical PDF",
    type=["pdf"]
)
if uploaded_file:
    with st.sidebar:
        with st.spinner("Ingesting PDF..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                pdf_path = tmp.name
            ingest_pdf(
                pdf_path=pdf_path,
                namespace="biomedical"
            )
            os.remove(pdf_path)
        st.success("PDF ingested successfully!")
st.subheader("Ask a question")
question = st.chat_input("Ask something about the uploaded documents...")

if question:
    with st.spinner("Thinking..."):
        result = rag_answer(question)

    st.session_state.chat_history.append({
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"]
    })

for chat in reversed(st.session_state.chat_history):
    with st.chat_message("user"):
        st.write(chat["question"])

    with st.chat_message("assistant"):
        st.write(chat["answer"])

        if chat["sources"]:
            with st.expander("Sources"):
                for src in chat["sources"]:
                    st.markdown(f"- {src}")