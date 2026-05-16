## 📑 Multimodal Document Ingestion & RAG Pipeline

An advanced, structure-aware Retrieval-Augmented Generation (RAG) pipeline built to ingest complex multi-format documents, preserve hierarchical layouts, and offer flexible retrieval mechanics.

### 🛠️ Tech Stack & Core Libraries
* **Document Parsing:** Docling (by IBM)
* **LLM Orchestration:** LangChain
* **Vision & OCR:** Local/API-based VLMs (Vision-Language Models) and custom OCR engines
* **Vector Storage:** LangChain-supported Vector Databases

---

### 🚀 Key Features

#### 1. Advanced Document Ingestion Engine
* **Structure-Aware Layout Detection:** Replaced native text extractors with **Docling**, utilizing its lightweight vision models to perform page-by-page layout detection. This ensures complex elements like multi-column layouts, images, and tables are preserved without losing structural integrity.
* **Multimodal Flexibility:** Highly customizable pipeline supporting local or API-driven **Vision-Language Models (VLMs)** and OCR integrations to handle scanned documents, text-heavy charts, and embedded graphics.
* **Semantic Chunking:** Transforms raw parses into Markdown/JSON formats before applying custom hybrid and hierarchical chunking strategies, retaining key contextual metadata for every chunk.
* **Vector Database Integration:** Automatically maps final document chunks into **LangChain Document objects** for streamlined embedding and downstream vector database ingestion.

#### 2. Dual-Mode Retrieval Architecture
Implemented and evaluated two distinct retrieval strategies to handle different user interaction paradigms:
* **Stateful (Conversational):** Tracks full dialogue and message history to resolve contextual dependencies over multi-turn Q&A sessions.
* **Stateless (Non-Conversational):** Optimized for direct, single-turn factual extraction and low-latency information lookup.

---

### 🔮 Future Roadmap & Enhancements

#### 📈 1. Transition to LLM-Driven Hierarchical Chunking
* **Current Limitation:** The token-based hybrid chunker strictly adheres to embedding model token limits but occasionally fractures the document’s natural hierarchy. This can split tables down the middle or create text fragments lacking distinct semantic meaning.
* **Proposed Solution:** Integrate **Llama-based models** to handle rule-and-semantic-based hierarchical chunking. This will maintain uniform chunk sizing and ensure tables or cohesive subsections remain unbroken.

#### 🔍 2. Chunk Contextualization & Hybrid Search
* **Current Limitation:** Traditional dense vector retrieval struggles with metadata-specific or structural queries (e.g., searching specifically for the "Abstract" or "Conclusion" section).
* **Proposed Solution:** Leverage Docling's native **chunk contextualization feature** to stamp rich, localized metadata onto each vector. This enables a hybrid search framework (Combining Semantic Dense Vectors + Keyword BM25 + Metadata Filtering) to handle precise document-level requests, such as: *"What is the abstract of report_xyz.pdf?"*
