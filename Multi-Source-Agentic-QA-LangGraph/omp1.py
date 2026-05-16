import asyncio
import json
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from prompt import SQL_AGENT_PROMPT
from langchain_mcp_adapters.client import MultiServerMCPClient
from prompt import RAG_AGENT_PROMPT
from dotenv import load_dotenv
load_dotenv()

class RAGAgent:    
    def __init__(self):
        self.agent = None
        self._initialized = False
    async def initialize(self):
        if self._initialized:
            return
        print("\n############### Initializing RAG Agent...")
        self.client = MultiServerMCPClient(
            {
                "unified-agent": {
                    "url": "http://localhost:8000/sse",
                    "transport": "sse",
                }
            }
        )
        tools = await self.client.get_tools()
        rag_tools = [
            t for t in tools
            if t.name in ["retrieve_documents"]
        ]
        system_message = RAG_AGENT_PROMPT
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("placeholder", "{messages}"),
        ])
        self.agent = create_react_agent(
             ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=os.environ.get("GROQ_KEY3"),
            temperature=0
        ),
            tools=rag_tools,
            prompt=prompt
        )
        self._initialized = True
        print("################ RAG Agent initialized and ready\n")
    async def query(self, nl_query: str) -> dict:
        if not self._initialized:
            await self.initialize()
        try:
            result = await self.agent.ainvoke(
                {"messages": [HumanMessage(content=nl_query)]},
                config=RunnableConfig(recursion_limit=10)
            )
            messages = result.get("messages", [])
            
            if not messages:
                print(" No messages returned from agent!")
            else:
                print(f"\n Debug - Message structure ({len(messages)} messages):")
                for i, msg in enumerate(messages):
                    msg_type = msg.type
                    has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
                    content_preview = str(msg.content)[:100] if msg.content else "No content"
                    print(f"  {i+1}. Type: {msg_type}, Has tools: {bool(has_tool_calls)}, Content: {content_preview}...")
            
            final_result = None
            for msg in reversed(messages):
                if msg.type == "tool" and msg.content:
                    try:
                        if isinstance(msg.content, list):
                            for block in msg.content:
                                if isinstance(block, dict) and "text" in block:
                                    parsed = json.loads(block["text"])
                                    if isinstance(parsed, dict) and parsed.get("success"):
                                        final_result = parsed
                                        break
                        elif isinstance(msg.content, str):
                            parsed = json.loads(msg.content)
                            if isinstance(parsed, dict) and parsed.get("success"):
                                final_result = parsed
                                break
                    except Exception:
                        continue
            
            final_answer = None
            for msg in reversed(messages):
                if msg.type == "ai":
                    has_tool_calls = (hasattr(msg, 'tool_calls') and 
                                    msg.tool_calls is not None and 
                                    len(msg.tool_calls) > 0)
                    
                    if not has_tool_calls and msg.content:
                        final_answer = msg.content
                        break
            
            if not final_answer and messages:
                last_msg = messages[-1]
                if last_msg.type == "ai" and last_msg.content:
                    final_answer = last_msg.content
            
            return {
                "nl_query": nl_query,
                "success": final_result is not None,
                "content": final_result.get("content") if final_result else None,
                "metadata": final_result.get("metadata") if final_result else None,
                "num_results": final_result.get("num_results") if final_result else 0,
                "summary": final_answer,  
                "num_steps": len([m for m in messages if m.type == "ai"])
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "nl_query": nl_query,
                "success": False,
                "error": str(e)
            }
if __name__ == "__main__":
    async def run():
        agent = RAGAgent()
        result = await agent.query(
            "Can you describe conclusion section of Effect of tuberculosis and retention intervention"
        )
        print(result)
    asyncio.run(run())