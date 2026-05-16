import os
import sys
import json
import sqlglot
from decimal import Decimal
from datetime import date, datetime
from sqlglot import exp
from sqlalchemy import create_engine, text, inspect
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from fastmcp import FastMCP
mcp = FastMCP("Unified-Agent")
DB_URL = "postgresql+psycopg2://postgres:omprakash@localhost:5432/northwind"
def get_engine():
    return create_engine(
        DB_URL,
        pool_pre_ping=True,
        pool_recycle=3600
    )
PERSIST_DIRECTORY = r"C:\Users\ompra\OneDrive\Documents\omprakash\New folder(3)\Unstructured RAG\python\chroma_store"
COLLECTION_NAME = "Biomedical_Research_Papers"
def get_vectordb():
    embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        encode_kwargs={"normalize_embeddings": True}
    )
    return Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIRECTORY,
        embedding_function=embedding
    )
def make_json_safe(obj):
    if isinstance(obj, memoryview):
        return obj.tobytes().hex()
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    return obj
class DatabaseJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, memoryview):
            return obj.tobytes().hex()
        if isinstance(obj, bytes):
            return obj.hex()
        return super().default(obj)

def safe_json_dumps(data, **kwargs):
    return json.dumps(data, cls=DatabaseJSONEncoder, **kwargs)

@mcp.tool()
def get_database_schema(
    table_names: list[str] | None = None,
    include_samples: bool = True,
    include_lov: bool = True
) -> dict:
    """
    Get schema information for database tables.
    
    Args:
        table_names: Specific tables to get schema for (None = all tables)
        include_samples: Whether to include sample data (first 3 rows)
        include_lov: Whether to include List of Values for categorical columns
    
    Returns:
        Dictionary containing:
        - schema: Table structures with columns, types, foreign keys, and optionally LOVs
        - sample_data: Sample rows from each table (if include_samples=True)
        - table_count: Number of tables returned
    """
    try:
        engine = get_engine()
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()
        if table_names:
            tables_to_fetch = [t for t in table_names if t in all_tables]
            if not tables_to_fetch:
                return {
                    "schema": {},
                    "sample_data": {},
                    "table_count": 0,
                    "error": f"None of the requested tables found. Available tables: {all_tables}"
                }
        else:
            tables_to_fetch = all_tables
        schema = {}
        sample_data = {}
        for table in tables_to_fetch:
            columns = inspector.get_columns(table)
            filtered_columns = [
                {
                    'name': col['name'],
                    'type': str(col['type']),
                    'nullable': col['nullable']
                }
                for col in columns
            ]
            foreign_keys = inspector.get_foreign_keys(table)
            filtered_foreign_keys = [
                {
                    'constrained_columns': fk['constrained_columns'],
                    'referred_table': fk['referred_table'],
                    'referred_columns': fk['referred_columns']
                }
                for fk in foreign_keys
            ]
            schema[table] = {
                "COLUMNS": filtered_columns,
                "FOREIGN_KEYS": filtered_foreign_keys
            }
        if include_lov:
            with engine.connect() as conn:
                for table_name in schema:
                    try:
                        count_query = text(f'SELECT COUNT(*) FROM "{table_name}"')
                        total_rows = conn.execute(count_query).scalar()
                        if total_rows == 0:
                            continue
                        for col in schema[table_name]["COLUMNS"]:
                            col_name = col["name"]
                            distinct_query = text(
                                f'SELECT COUNT(DISTINCT "{col_name}") FROM "{table_name}"'
                            )
                            dist_count = conn.execute(distinct_query).scalar()
                            is_categorical = (
                                (dist_count > 1) and
                                (dist_count / total_rows < 0.05) and
                                (dist_count <= 20)
                            )
                            if is_categorical:
                                lov_query = text(
                                    f'SELECT DISTINCT "{col_name}" FROM "{table_name}" '
                                    f'WHERE "{col_name}" IS NOT NULL LIMIT 20'
                                )
                                rows = conn.execute(lov_query).fetchall()
                                col["LOV"] = [r[0] for r in rows]
                    except Exception as e:
                        print(f"Error getting LOV for {table_name}: {e}", file=sys.stderr)
                        continue
        if include_samples:
            with engine.connect() as conn:
                for table in tables_to_fetch:
                    try:
                        query = text(f'SELECT * FROM "{table}" LIMIT 3')
                        result = conn.execute(query).mappings().fetchall()
                        sample_data[table] = [dict(row) for row in result]
                    except Exception as e:
                        print(f"Error getting samples for {table}: {e}", file=sys.stderr)
                        sample_data[table] = []
        engine.dispose()
        response = {
            "schema": schema,
            "sample_data": sample_data if include_samples else {},
            "table_count": len(tables_to_fetch),
            "tables_included": tables_to_fetch
        }
        return make_json_safe(response)
    except Exception as e:
        response = {
            "schema": {},
            "sample_data": {},
            "table_count": 0,
            "error": f"Schema retrieval failed: {str(e)}"
        }
        return make_json_safe(response)

@mcp.tool()
def execute_sql_query(query: str) -> dict:
    """
    Execute a READ-ONLY SQL SELECT query against the Northwind database.
    
    Args:
        query: A valid SQL SELECT statement (DML operations are not allowed)
    
    Returns:
        Dictionary containing:
        - success: Whether query executed successfully
        - data: List of result rows (if successful)
        - tables_involved: List of tables used in the query
        - metadata_table: Schema metadata for involved tables
        - row_count: Number of rows returned
        - query_executed: The actual query executed
        - error: Error message (if failed)
    """
    engine = None
    try:
        try:
            parsed = sqlglot.parse_one(query, dialect="postgres")
        except Exception as e:
            return {
                "success": False,
                "error": f"SQL syntax error: {str(e)}",
                "error_type": "validation"
            }
        if isinstance(parsed, (exp.Insert, exp.Update, exp.Delete)):
            return {
                "success": False,
                "error": "DML queries (INSERT, UPDATE, DELETE) are not authorized",
                "error_type": "validation"
            }
        if isinstance(parsed, (exp.Create, exp.Drop, exp.Alter, exp.Command)):
            return {
                "success": False,
                "error": "DDL queries (CREATE, DROP, ALTER) are not authorized",
                "error_type": "validation"
            }
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(query)).mappings().fetchall()
            
            tables = [
                table.name
                for table in parsed.find_all(exp.Table)
            ]
            
            data = [dict(row) for row in result]
            
            metadata = {}
            for table in tables:
                try:
                    meta_query = text("""
                        SELECT column_name, data_type, is_nullable 
                        FROM information_schema.columns 
                        WHERE table_name = :table
                    """)
                    meta_res = conn.execute(meta_query, {"table": table}).mappings().fetchall()
                    metadata[table] = [dict(r) for r in meta_res]
                except Exception:
                    metadata[table] = []
            
            return {
                "success": True,
                "data": data,
                "tables_involved": tables,
                "metadata_table": metadata,
                "row_count": len(data),
                "query_executed": query
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Query execution failed: {str(e)}",
            "error_type": "execution",
            "query_attempted": query
        }
    finally:
        if engine:
            engine.dispose()

@mcp.tool()
def retrieve_documents(query: str, k: int = 5) -> dict:
    """
    Retrieve relevant documents from the PubMed biomedical research database using RAG.
    
    Args:
        query: The search query or question to find relevant documents for
        k: Number of documents to retrieve (default: 5)
    
    Returns:
        Dictionary containing:
        - success: Whether retrieval was successful
        - content: List of relevant document chunks
        - metadata: List of metadata for each chunk (source, page)
        - num_results: Number of documents retrieved
        - query_executed: The query that was executed
        - error: Error message (if failed)
    """
    try:
        print(f"DEBUG: Searching for: {query}", file=sys.stderr)
        vectordb = get_vectordb()
        docs = vectordb.similarity_search(
            query=query,
            k=k,
            filter={"namespace": "biomedical"}
        )
        print(f"DEBUG: Found {len(docs)} documents", file=sys.stderr)
        if not docs:
            return {
                "success": True,
                "content": [],
                "metadata": [],
                "num_results": 0,
                "query_executed": query,
                "message": "No documents found matching the query"
            }
        content = []
        metadata = []
        for doc in docs:
            content.append(doc.page_content.strip())
            metadata.append({
                "source": os.path.basename(doc.metadata.get("source", "unknown")),
                "page": doc.metadata.get("page_numbers", "N/A")
            })
        
        return {
            "success": True,
            "content": content,
            "metadata": metadata,
            "num_results": len(content),
            "query_executed": query
        }
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return {
            "success": False,
            "content": [],
            "metadata": [],
            "num_results": 0,
            "error": f"Retrieval error: {str(e)}"
        }
if __name__ == "__main__":
    print("Starting Unified MCP Server (HTTP mode)...", file=sys.stderr)
    print(f"Available tools: get_database_schema, execute_sql_query, retrieve_documents", file=sys.stderr)
    print(f"Server will run on http://localhost:8000", file=sys.stderr)
    try:
        mcp.run(transport="sse", port=8000)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        raise