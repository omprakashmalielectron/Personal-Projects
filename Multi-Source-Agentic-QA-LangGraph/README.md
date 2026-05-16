# omprakash.malli
Capstone projects for omprakash.malli@neuleap.ai
Multi-Agent Query Router with LangGraph
A sophisticated multi-agent system that intelligently routes queries to specialized agents (SQL and RAG) using LangGraph orchestration, with conversation memory and guardrails.

# Intelligent Query Routing & Agent System

An intelligent system that automatically routes user queries to either a SQL Agent (for business data) or a RAG Agent (for medical research) based on content. It features content guardrails, conversation memory, and robust error handling.

## Key Features
* **Intelligent Query Routing:** Automatically routes queries to SQL or RAG agents.
* **Guardrails:** Validates queries are within system scope (business data or medical research).
* **Conversation Memory:** Maintains context across multiple turns using LangGraph checkpointing.
* **SQL Agent:** Natural language to PostgreSQL queries for Northwind database.
* **RAG Agent:** Document retrieval from PubMed medical literature.
* **MCP Integration:** Uses Model Context Protocol servers for data access.
* **Error Handling:** Automatic SQL query reformulation and RAG fallback strategies.
* **Source Citations:** All responses include metadata and source information.

---

## Architecture

### System Components
```text
┌─────────────────────────────────────────────────────────────────┐
│                              START                              │
│                      (User submits query)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │    Guardrail   │
                    │      Node      │
                    │                │
                    │   Validates:   │
                    │  - Business?   │
                    │  - Medical?    │
                    │  - Other?      │
                    └────────┬───────┘
                             │
           ┌────────┴────────┐
           ▼                 ▼
      ┌─────────┐       ┌─────────┐
      │  VALID  │       │ INVALID │
      └────┬────┘       └────┬────┘
           │                 │
           ▼                 ▼
    ┌────────────┐    ┌──────────────┐
    │   Router   │    │   Generate   │
    │    Node    │    │   Rejection  │
    └──────┬─────┘    │    Message   │
           │          └──────┬───────┘
  ┌─────────┴─────────┐      │
  ▼                   ▼      │
┌─────────────┐ ┌─────────────┐
│ STRUCTURED  │ │UNSTRUCTURED │
│    DATA     │ │    DATA     │
└──────┬──────┘ └──────┬──────┘
       │               │
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│  SQL Agent  │ │  RAG Agent  │
│    Node     │ │    Node     │
│             │ │             │
│ • Generate  │ │ • Retrieve  │
│    SQL      │ │  Documents  │
│ • Execute   │ │ • Synthesize│
│ • Summarize │ │ • Cite      │
└──────┬──────┘ └──────┬──────┘
       │               │
       │               │
       └────────┬─────────┘
                │
                ▼
         ┌─────────────┐
         │    Answer   │◄──────────┘
         │     Node    │
         │             │
         │ • Aggregate │
         │ • Format    │
         └──────┬──────┘
                │
                ▼
         ┌─────────────┐
         │     END     │
         └─────────────┘
NLtoSQLAgent
├── Schema Caching
│   ├── Load all table definitions
│   ├── Extract foreign keys
│   └── Detect LOV (List of Values) for categorical columns
├── Sample Data Loading
│   └── First 3 rows from each table
├── MCP Tool: execute_sql_query, get_schema(this tool provides flexibility to agent how much
                                             information it wants from the database in order to generate query)
├── Query Validation (sqlglot parser)
│   ├── Block DML (INSERT, UPDATE, DELETE)
│   ├── Block DDL (CREATE, DROP, ALTER)
│   └── Block TCL (COMMIT, ROLLBACK)
├── Execution via MCP server
└── Result serialization (handle dates, decimals, binary)
    └── ReAct Agent Loop
        ├── Understand user question
        ├── Generate SQL using schema + samples
        ├── Execute query
        ├── If error: analyze and retry (max 5 times)
        └── Summarize results in natural language
RAGAgent
├── MCP Tool: retrieve_documents
│   ├── Vector similarity search
│   ├── Return top-k documents
│   └── Include metadata (source, page, etc.)
└── ReAct Agent Loop
    ├── Understand user question
    ├── Retrieve relevant documents
    ├── Analyze all retrieved content
    ├── Synthesize information across sources
    ├── Cite specific sources
    └── Generate comprehensive answer

