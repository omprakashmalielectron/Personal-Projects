import os
import asyncio
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import TypedDict, Optional, List, Annotated
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from __Untitled3 import NLtoSQLAgent
from __Untitled33 import RAGAgent

load_dotenv()

sql_agent = NLtoSQLAgent()
rag_agent = RAGAgent()
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.environ.get("GROQ_KEY"),
    temperature=0
)
checkpointer = InMemorySaver()

class QueryState(TypedDict):
    original_question: str      
    current_question: str        
    query_type: Optional[str]   
    sql_summary: Optional[str]   
    sql_data: Optional[list]     
    sql_query: Optional[str]     
    rag_summary: Optional[str]   
    rag_data: Optional[list]     
    metadata: Optional[list]     
    final_answer: Optional[str]
    is_valid_query: Optional[bool] 
    messages: Annotated[List[BaseMessage], add_messages] 
####################################################################################################
###################### SETUP FOR AGENTS STATE ENDS HERE #########################################
####################################################################################################
def guardrail_node(state: QueryState):
    print("\n" + "="*80)
    print("### GUARDRAIL - VALIDATING QUERY SCOPE ###")
    print("="*80)
    validation_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are a query validator for a specialized multi-agent system.

            THIS SYSTEM CAN ANSWER:
            1. BUSINESS/SALES DATA questions:
               - Customer analytics, revenue, orders, products
               - Sales metrics, inventory, transactions
               - Database: Northwind (retail/sales)
               
            2. MEDICAL/BIOMEDICAL questions:
               - Disease information, treatments, symptoms
               - Drug interactions, clinical research
               - Medical literature and studies
               - Database: PubMed (medical research)

            THIS SYSTEM CANNOT ANSWER:
            - General knowledge questions (history, geography, science)
            - Personal advice (legal, financial, relationship)
            - Current events, news, weather
            - Entertainment (movies, games, sports)
            - Coding/programming help
            - Mathematical calculations
            - Creative writing requests
            - Questions unrelated to business data or medical research

            TASK:
            Analyze the user's question considering conversation history.
            Respond with EXACTLY one word:
            - "VALID" if the question relates to business data OR medical research
            - "INVALID" if the question is outside these domains
            
            IMPORTANT:
            - Consider follow-up questions in context of conversation history
            - If previous questions were valid, follow-ups are likely valid too
            - Be lenient with ambiguous questions that could relate to the domains
            
            Output ONLY: VALID or INVALID"""
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])
    validation_chain = validation_prompt | llm | StrOutputParser()
    decision = validation_chain.invoke({
        "messages": state["messages"],
    }).strip().upper()
    is_valid = decision == "VALID"
    print(f" Question: {state['current_question']}")
    print(f" Validation: {decision}")
    print(f" Is Valid: {is_valid}")
    
    if not is_valid:
        print(" Query is out of scope - generating rejection message")
        
        rejection_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a helpful assistant that politely declines out-of-scope questions.

                The system you represent can ONLY answer:
                1. Business/sales data questions (customers, orders, products, revenue)
                2. Medical/biomedical questions (diseases, treatments, research)

                TASK:
                Generate a friendly, concise response that:
                1. Politely explains the question is outside your scope
                2. Briefly mentions what you CAN help with
                3. Encourages the user to ask relevant questions
                
                Keep it warm, professional, and under 3 sentences."""
            ),
            ("human", "User asked: {question}\n\nProvide a polite rejection message.")
        ])
        
        rejection_chain = rejection_prompt | llm | StrOutputParser()
        rejection_message = rejection_chain.invoke({
            "question": state["current_question"]
        })
        
        print(f"Rejection message generated")
        print("="*80 + "\n")
        
        return {
            "is_valid_query": False,
            "final_answer": rejection_message,
            "messages": [AIMessage(content=rejection_message)]
        }
    else:
        print("Query is valid - proceeding to router")
        print("="*80 + "\n")
        
        return {"is_valid_query": True}

def router_node(state: QueryState):
    print("\n" + "="*80)
    print("### ROUTING QUERY ###")
    print("="*80)
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert query router with access to conversation history.

                AVAILABLE ROUTES:
                1. STRUCTURED_DATA: For business, sales, orders, customers, products, transactions, analytics
                - Examples: "Top 5 customers", "Revenue by region", "Product inventory"
                - Database: Northwind (retail/sales database)

                2. UNSTRUCTURED_DATA: For medical, biomedical, research, clinical, scientific literature
                - Examples: "Tuberculosis treatment", "Drug interactions", "Disease symptoms"
                - Database: PubMed (medical research documents)

                IMPORTANT:
                - Consider conversation history - follow-up questions should use the same route
                - The latest question may reference previous results
                - Output EXACTLY one word: STRUCTURED_DATA or UNSTRUCTURED_DATA
                - No explanation, no punctuation, just the route name"""
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm | StrOutputParser()
    decision = chain.invoke({
        "messages": state["messages"],
    }).strip()
    if decision not in ("STRUCTURED_DATA", "UNSTRUCTURED_DATA"):
        print(f"Invalid routing decision '{decision}', defaulting to UNSTRUCTURED_DATA")
        decision = "UNSTRUCTURED_DATA"
    print(f" Route: {decision}")
    print(f" Question: {state['current_question']}")
    print("="*80 + "\n")
    return {"query_type": decision}
### SQL subagent node with historical context pf past two conversation of multiagent system
### to provide it with context necessary to answer NL question
async def sql_agent_node(state: QueryState):
    print("\n" + "="*80)
    print("### EXECUTING SQL AGENT WITH CONVERSATION CONTEXT ###")
    print("="*80)
    try:
        if not sql_agent._initialized:
            await sql_agent.initialize()
        messages = state.get("messages", [])
        current_question = state["current_question"]
        conversation_history = messages[:-1] if len(messages) > 1 else []
        print(f" Current question: {current_question}")
        print(f" Previous messages in history: {len(conversation_history)}")
        if conversation_history:
            context_parts = ["Previous conversation:"]
            for msg in conversation_history[-4:]:  
                if msg.type == "human":
                    context_parts.append(f"User: {msg.content}")
                elif msg.type == "ai":
                    content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
                    context_parts.append(f"Assistant: {content}")
            context_parts.append(f"\nCurrent question: {current_question}")
            enhanced_question = "\n".join(context_parts)
            print(f"Enhanced question with context:")
            print(f"   {enhanced_question[:200]}...")
        else:
            enhanced_question = current_question
        result = await sql_agent.query(enhanced_question)
        if result.get("success"):
            print(f" SQL Agent Success!")
            print(f" SQL Query: {result.get('sql_query')}")
            print(f" Rows Retrieved: {result.get('row_count')}")
            print(f" Tables Used: {result.get('tables')}")
            print("="*80 + "\n")
            return {
                "sql_summary": result.get("summary"),
                "sql_data": result.get("data"),
                "sql_query": result.get("sql_query"),
                "metadata": result.get("tables")
            }
        else:
            print(f"SQL Agent Failed: {result.get('error')}")
            print("="*80 + "\n")
            return {
                "sql_summary": f"Error: {result.get('error')}",
                "sql_data": None,
                "sql_query": None,
                "metadata": None
            }
    except Exception as e:
        print(f"SQL Agent Exception: {e}")
        print("="*80 + "\n")
        import traceback
        traceback.print_exc()
        return {
            "sql_summary": f"Error: {str(e)}",
            "sql_data": None,
            "sql_query": None,
            "metadata": None
        }
### RAG agent node with same functiona;ity as SQL subagent
async def rag_agent_node(state: QueryState):
    print("\n" + "="*80)
    print("### EXECUTING RAG AGENT WITH CONVERSATION CONTEXT ###")
    print("="*80)
    try:
        if not rag_agent._initialized:
            await rag_agent.initialize()
        messages = state.get("messages", [])
        current_question = state["current_question"]
        conversation_history = messages[:-1] if len(messages) > 1 else []
        print(f"Current question: {current_question}")
        print(f"Previous messages in history: {len(conversation_history)}")
        if conversation_history:
            context_parts = ["Previous conversation:"]
            for msg in conversation_history[-4:]:
                if msg.type == "human":
                    context_parts.append(f"User: {msg.content}")
                elif msg.type == "ai":
                    content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
                    context_parts.append(f"Assistant: {content}")
            context_parts.append(f"\nCurrent question: {current_question}")
            enhanced_question = "\n".join(context_parts)
            print(f"Enhanced question with context:")
            print(f" {enhanced_question[:200]}...")
        else:
            enhanced_question = current_question
        result = await rag_agent.query(enhanced_question)
        
        if result.get("success"):
            print(f"RAG Agent Success!")
            print(f"Documents Retrieved: {result.get('num_results')}")
            print(f"Sources: {len(result.get('metadata', []))} sources")
            print("="*80 + "\n")
            return {
                "rag_summary": result.get("summary"),
                "rag_data": result.get("content"),
                "metadata": result.get("metadata")
            }
        else:
            print(f"RAG Agent Failed: {result.get('error')}")
            print("="*80 + "\n")
            return {
                "rag_summary": f"Error: {result.get('error')}",
                "rag_data": None,
                "metadata": None
            }
    except Exception as e:
        print(f"RAG Agent Exception: {e}")
        print("="*80 + "\n")
        import traceback
        traceback.print_exc()
        return {
            "rag_summary": f"Error: {str(e)}",
            "rag_data": None,
            "metadata": None
        }

def final_answer_node(state: QueryState):
    print("\n" + "="*80)
    print("### GENERATING FINAL ANSWER ###")
    print("="*80)
    if state.get("sql_summary"):
        final_answer = state["sql_summary"]
        print("Using SQL Agent's summary")
    elif state.get("rag_summary"):
        final_answer = state["rag_summary"]
        print("Using RAG Agent's summary")
    else:
        final_answer = "I apologize, but I wasn't able to retrieve any information to answer your question. Please try rephrasing or ask a different question."
        print("No agent data available, using fallback")
    print("="*80 + "\n")
    return {
        "final_answer": final_answer,
        "messages": [AIMessage(content=final_answer)]
    }
###########################################################################################################
########### IMPLEMENTATION OF NODES OF WORKFLOW END'S HERE ############
##########################################################################################################
def route_after_guardrail(state: QueryState):
    if state.get("is_valid_query", False):
        return "valid"
    else:
        return "invalid"
def route_after_router(state: QueryState):
    return state["query_type"]
graph = StateGraph(QueryState)
graph.add_node("guardrail", guardrail_node)
graph.add_node("router", router_node)
graph.add_node("STRUCTURED_DATA", sql_agent_node)
graph.add_node("UNSTRUCTURED_DATA", rag_agent_node)
graph.add_node("Answer", final_answer_node)
graph.set_entry_point("guardrail")
graph.add_conditional_edges(
    "guardrail",
    route_after_guardrail,
    {
        "valid": "router",      
        "invalid": END,         
    },
)
graph.add_conditional_edges(
    "router",
    route_after_router,
    {
        "STRUCTURED_DATA": "STRUCTURED_DATA",
        "UNSTRUCTURED_DATA": "UNSTRUCTURED_DATA",
    },
)
graph.add_edge("STRUCTURED_DATA", "Answer")
graph.add_edge("UNSTRUCTURED_DATA", "Answer")
graph.add_edge("Answer", END)
app = graph.compile(checkpointer=checkpointer)
config = {
    "configurable": {
        "thread_id": "1",
    }
}
async def run_agent(question: str, thread_id: str = "1"):
    current_config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    new_message = HumanMessage(content=question)
    state_snapshot = app.get_state(current_config)
    if state_snapshot and state_snapshot.values:
        previous_state = state_snapshot.values
        original_question = previous_state.get("original_question", question)
        previous_messages = previous_state.get("messages", [])
        print(f"\n Continuing conversation (Thread: {thread_id})")
        print(f"Previous messages: {len(previous_messages)}")
    else:
        original_question = question
        previous_messages = []
        print(f"\n Starting new conversation (Thread: {thread_id})")
    initial_state = {
        "original_question": original_question,
        "current_question": question,
        "messages": previous_messages + [new_message],
        "query_type": None,
        "sql_summary": None,
        "sql_data": None,
        "sql_query": None,
        "rag_summary": None,
        "rag_data": None,
        "metadata": None,
        "final_answer": None,
    }
    result = await app.ainvoke(initial_state, current_config)
    return {
        "answer": result["final_answer"],
        "route": result["query_type"],
        "sql_query": result.get("sql_query"),
        "metadata": result.get("metadata"),
        "conversation_length": len(result.get("messages", [])),
    }
##############################################################################################################
######################### IMPLEMENTATION OF AGENT WITH SESSION MEMORY END'S HERE ############
##############################################################################################################
async def demo():    
    print("\n" + "=" * 40)
    print("MULTI-AGENT ROUTER WITH CONVERSATION HISTORY")
    print("Agents receive full conversation context and handle follow-ups naturally")
    print("=" * 40 + "\n")
    test_conversations = [
        {
            "thread_id": "sql_conv_1",
            "questions": [
                "What are the top 5 customers by revenue?",
                "What about their total orders?",  
                "Which one is from Germany?",     
            ]
        },
        {
            "thread_id": "rag_conv_1",
            "questions": [
                "What are the effects of tuberculosis treatment?",
                "What are the side effects?",      # Follow-up - agent gets full history
                "How effective is it?",            # Follow-up - agent gets full history
            ]
        },
        {
            "thread_id": "sql_conv_2",
            "questions": [
                "Show me products in the Beverages category",
                "Which one has the highest price?",  # Follow-up - agent gets full history
            ]
        },
    ]
    
    for conv in test_conversations:
        thread_id = conv["thread_id"]
        questions = conv["questions"]
        
        print("\n" + "=" * 40)
        print(f"NEW CONVERSATION - Thread ID: {thread_id}")
        print("=" * 40)
        
        for i, question in enumerate(questions, 1):
            print(f"\n{'─' * 80}")
            print(f"Question {i}/{len(questions)}: {question}")
            print('─' * 80)
            
            result = await run_agent(question, thread_id=thread_id)
            
            print(f"\n Route: {result['route']}")
            if result.get('sql_query'):
                print(f" SQL Query: {result['sql_query']}")
            if result.get('metadata'):
                print(f"Metadata: {result['metadata']}")
            print(f" Conversation length: {result['conversation_length']} messages")
            print(f"\n{'='*80}")
            print("FINAL ANSWER:")
            print('='*80)
            print(result['answer'])
            print('='*80)
            await asyncio.sleep(0.5)
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(demo())