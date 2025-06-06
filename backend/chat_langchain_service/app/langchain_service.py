import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from app.config import settings
from app.logger import logger
import json
import os
from kubernetes import client, config
 
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
 
# Custom streaming callback handler
class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming LLM responses."""
    
    def __init__(self):
        self.tokens_queue = asyncio.Queue()
        self.full_response = []
        
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Put the new token in the queue."""
        self.full_response.append(token)
        await self.tokens_queue.put(token)
    
    async def on_llm_end(self, response, **kwargs) -> None:
        """Signal the end of the LLM response."""
        await self.tokens_queue.put(None)  # Signal end of stream
    
    async def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Handle LLM errors."""
        await self.tokens_queue.put(f"Error: {str(error)}")
        await self.tokens_queue.put(None)  # Signal end of stream
    
    def get_full_response(self):
        """Get the complete response as a string."""
        return "".join(self.full_response)
 
# Try to load K8s config
try:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    logger.info("Kubernetes configuration loaded successfully")
except Exception as e:
    logger.warning(f"Could not load Kubernetes configuration: {str(e)}")
    v1 = None
 
# Define Kubernetes tools
def fetch_k8s_events(namespace: Optional[str] = None, limit: int = 10) -> str:
    try:
        if not v1:
            return "Kubernetes client not initialized"
            
        events = (
            v1.list_namespaced_event(namespace) if namespace else v1.list_event_for_all_namespaces()
        )
        items = events.items[:limit]
        return "\n".join(
            f"{e.last_timestamp} {e.type}/{e.reason} - {e.message}" for e in items
        ) or "No events found"
    except Exception as e:
        return f"Error: {str(e)}"
 
def run_kubectl(args: str) -> str:
    try:
        # Improved parsing logic to handle different input formats
        if args.startswith("[") and args.endswith("]"):
            try:
                # Try to parse as JSON first
                parsed_args = json.loads(args)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to evaluate as a Python literal
                # This handles cases like "['create', 'namespace', 'test']"
                import ast
                parsed_args = ast.literal_eval(args)
        else:
            # Handle space-separated string format
            parsed_args = args.split()
        
        # Use the kubectl command
        import subprocess
        cmd = ["kubectl"] + parsed_args
        logger.info(f"Executing kubectl command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        return result.stdout or result.stderr
    except Exception as e:
        return f"Error running kubectl: {str(e)}"
 
tools = [
    Tool(
        name="fetch_k8s_events",
        description="Use this to fetch Kubernetes events. Input is JSON string with optional 'namespace' and 'limit'.",
        func=lambda input_str: fetch_k8s_events(**json.loads(input_str))
    ),
    Tool(
        name="run_kubectl",
        description="Use this to run a kubectl command. Input can be a JSON array like [\"get\", \"pods\"] or a Python list representation like ['get', 'pods'].",
        func=lambda input_str: run_kubectl(input_str)
    )
]
 
def get_streaming_llm(streaming_handler):
    """Get a streaming LLM instance."""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0.5,
        streaming=True,
        callbacks=[streaming_handler],
        max_tokens=5000
    )
 
def get_non_streaming_llm():
    """Get a non-streaming LLM instance."""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0.5,
        max_tokens=5000
        
    )
async def process_with_langchain(
    user_message: str,
    memory: Optional[ConversationBufferMemory] = None,
    stream: bool = False
) -> Dict[str, Any]:
    """Process a message using LangChain with direct context injection."""
    try:
        # Create or use provided memory
        if memory is None:
            memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
        
        # Get conversation history as string
        conversation_context = ""
        if hasattr(memory.chat_memory, 'messages') and memory.chat_memory.messages:
            conversation_context = "\n\nPrevious conversation:\n"
            for msg in memory.chat_memory.messages:
                if hasattr(msg, 'content'):
                    role = "Human" if "Human" in str(type(msg)) else "Assistant"
                    conversation_context += f"{role}: {msg.content}\n"
        
        # Inject context directly into the user message
        enhanced_message = f"{conversation_context}\n\nCurrent question: {user_message}\n\nPlease respond considering the full conversation history above."
        
        logger.info(f"Enhanced message with context: {enhanced_message[:200]}...")
        
        if stream:
            # Streaming response
            streaming_handler = StreamingCallbackHandler()
            llm = get_streaming_llm(streaming_handler)
            
            # Use simple agent without complex memory handling
            agent = initialize_agent(
                tools,
                llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True
            )
            
            # Start the agent in a background task with enhanced message
            task = asyncio.create_task(agent.ainvoke({"input": enhanced_message}))
            
            return {
                "type": "streaming",
                "task": task,
                "streaming_handler": streaming_handler,
                "memory": memory
            }
        else:
            # Non-streaming response
            llm = get_non_streaming_llm()
            
            # Use simple agent without complex memory handling
            agent = initialize_agent(
                tools,
                llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True
            )
            
            # Invoke the agent with enhanced message
            result = await agent.ainvoke({"input": enhanced_message})
            
            return {
                "type": "non_streaming",
                "result": result["output"],
                "memory": memory
            }
    except Exception as e:
        logger.error(f"Error in LangChain processing: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        if stream:
            return {
                "type": "streaming",
                "error": str(e),
                "memory": memory
            }
        else:
            return {
                "type": "non_streaming",
                "result": f"I'm sorry, I encountered an error: {str(e)}",
                "memory": memory
            }
 
 
 
async def create_memory_from_messages(messages):
    """Create a ConversationBufferMemory from stored messages."""
    memory = ConversationBufferMemory(
        return_messages=True,
        memory_key="chat_history",
        human_prefix="Human",
        ai_prefix="Assistant"
    )
    
    # Add messages to memory in chronological order
    for msg in messages:
        logger.info(f"Adding message to memory: {msg.role} - {msg.content[:50]}...")
        if msg.role == 'user':
            memory.chat_memory.add_user_message(msg.content)
        elif msg.role == 'assistant':
            memory.chat_memory.add_ai_message(msg.content)
    
    # Verify memory contents
    logger.info(f"Created memory with {len(messages)} messages")
    if hasattr(memory.chat_memory, 'messages'):
        logger.info(f"Memory contains {len(memory.chat_memory.messages)} messages")
        for i, msg in enumerate(memory.chat_memory.messages):
            logger.info(f"Memory message {i}: {type(msg).__name__} - {msg.content[:100]}...")
    
    # Test memory buffer
    try:
        buffer = memory.buffer
        logger.info(f"Memory buffer: {buffer[:200]}...")
    except Exception as e:
        logger.error(f"Error accessing memory buffer: {e}")
    
    return memory
 
async def stream_langchain_response(streaming_handler) -> AsyncIterator[str]:
    """Stream tokens from the LangChain response."""
    while True:
        try:
            # Get the next token from the queue
            token = await asyncio.wait_for(streaming_handler.tokens_queue.get(), timeout=30.0)
            
            # If token is None, we've reached the end of the stream
            if token is None:
                break
                
            # Yield the token
            yield token
                        
        except asyncio.TimeoutError:
            # If we don't get a token for 30 seconds, assume something went wrong
            yield "..."
            yield "\n\n[Timeout waiting for response]"
            break
        except Exception as e:
            # Handle any other errors
            yield f"\n\n[Error: {str(e)}]"
            break
 
 