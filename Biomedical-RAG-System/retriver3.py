import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv("C:/Users/ompra/OneDrive/Documents/omprakash/untitledx31/.env")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={
        "normalize_embeddings": True,
        "batch_size": 32
    }
)
vectordb = Chroma(
    collection_name="Biomedical_Research_Papers",
    persist_directory=r"C:\Users\ompra\OneDrive\Documents\omprakash\New folder (3)\python\chroma_store",
    embedding_function=embedding_model,
)
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    google_api_key=GOOGLE_API_KEY,
    temperature=0
)
history=[]
############################################################################
############### Setup for retriver pipeline is done #############
###########################################################################
def retrieve_docs(query: str, k: int = 5):
    return vectordb.similarity_search(
        query=query,
        k=k,
        filter={"namespace": "biomedical"}
    )
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "INSTRUCTION: "
        "You are a biomedical research assistant."
        "Answer ONLY using the provided CONTEXT."
        "Also use (PREVIOUS Q&A) as referal if CONTEXT is not enough to answer."
        "If the answer is not present,say that PROVIED DOCUMENT IS INSUFFICIENT TO ANSWER YOUR QUERY"
    ),
    (
        "human",
        "PREVIOUS Q&A:\n{history}\n\n"
        "CONTEXT:\n{context}\n\n"
        "QUESTION:\n{question}\n\n"
        "ANSWER:"
    )
])


def format_docs_for_llm(docs):
    return "\n\n".join(doc.page_content.strip() for doc in docs)

def format_sources_for_user(docs):
    sources = []
    for i, doc in enumerate(docs):
        source =os.path.basename(doc.metadata.get("source", "unknown"))
        pages =doc.metadata.get("page_numbers", "N/A")
        sources.append(f"[{i+1}] {source}, page(s): {pages}")
    return sources
def format_history(history):
    if not history:
        return "None"
    return "\n".join(
        f"Q: {item['question']}\nA: {item['answer']}"
        for item in history[-5:] 
    )

def rag_answer(question: str):
    docs =retrieve_docs(question)
    if not docs:
        answer_text ="No relevant biomedical sources found."
        sources = []
    else:
        context =format_docs_for_llm(docs)
        history_text =format_history(history)
        messages =prompt.format_messages(
            history=history_text,
            context=context,
            question=question
        )
        response =llm.invoke(messages)
        answer_text =response.content[0]["text"]
        sources =format_sources_for_user(docs)
    history.append({
        "question": question.strip(),
        "answer": answer_text.strip()
    })

    return {
        "answer": answer_text,
        "sources": sources
    }
if __name__ == "__main__":
    query = """
            Research Briefings
            Neonatology 2013;104:171-178 DOI: 10.1159/000351346
            Received: February 4, 2013
            Accepted after revision: April 12, Published online: August 1, 2013
            2013
            """
    result = rag_answer(query)
    print("\nANSWER:\n")
    print(result["answer"])
    print("\nSOURCES:\n")
    for src in result["sources"]:
        print(src)