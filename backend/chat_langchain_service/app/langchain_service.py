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
    """Process a message using LangChain."""
    try:
        # Replace the existing system prompt with this new one
        system_prompt = """You are KubeSage, an AI assistant specialized in Kubernetes.
        When responding to follow-up questions, always consider the full conversation history.
        If a user refers to something mentioned earlier, make sure to connect it to the previous context.
        For example, if they ask about namespaces and then ask "How do I create one?", understand they want to create a namespace.

        You are integrated into a system where responses are rendered as Markdown in the frontend. Follow these rules strictly:
        - Do NOT return final thoughts or answers inside a JSON block.
        - Instead, directly return only the action_input content as a Markdown-formatted response that can be rendered by the frontend.
        - Do NOT include metadata like action, Final Answer, or any wrapper like json code blocks.
        - The output must only contain pure Markdown content.
        - Make all responses detailed and descriptive.
        - Always assume the user wants a thorough explanation unless explicitly asked for a brief answer.
        - Expand on technical terms, root causes, and provide clear next steps or resolutions.

        Use appropriate Markdown formatting, including:
        - Headings (##, ###)
        - Bold or italic emphasis
        - Bullet or numbered lists
        - Code blocks (only for command or config snippets)

        IMPORTANT GUIDELINES:
        1. Don't solve the problem unless the user explicitly asks to solve it.
        2. If the user is only describing or asking about a problem, just explain or acknowledge it — do not execute or take action.
        3. Only execute commands or take actions when the user gives an explicit instruction like "run this command", "execute", "create", or similar clear directives.
        4. Follow the user's instructions exactly, and do not execute anything on your own without permission.
        5. If you are unable to complete a requested task, inform the user immediately.
        6. For kubectl commands, only execute them when explicitly instructed to do so.
        7. When explaining concepts, provide information without taking action unless specifically requested.
        """

        
        # Create or use provided memory
        if memory is None:
            memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
        
        if stream:
            # Streaming response
            streaming_handler = StreamingCallbackHandler()
            llm = get_streaming_llm(streaming_handler)
            
            # Initialize agent with streaming
            agent = initialize_agent(
                tools,
                llm,
                agent=AgentType.OPENAI_FUNCTIONS,  # OpenAI-style tool use
                verbose=True,
                memory=memory,
                handle_parsing_errors=True,
                system_message=system_prompt
            )
            
            # Start the agent in a background task
            task = asyncio.create_task(agent.ainvoke({"input": user_message}))
            
            return {
                "type": "streaming",
                "task": task,
                "streaming_handler": streaming_handler,
                "memory": memory
            }
        else:
            # Non-streaming response
            llm = get_non_streaming_llm()
            
            # Initialize agent
            agent = initialize_agent(
                tools,
                llm,
                agent=AgentType.OPENAI_FUNCTIONS,  # Changed from CHAT_CONVERSATIONAL_REACT_DESCRIPTION
                verbose=True,
                memory=memory,
                handle_parsing_errors=True,
                system_message=system_prompt
            )
            
            # Invoke the agent
            result = await agent.ainvoke({"input": user_message})
            
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
    memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
    
    # Add messages to memory
    for msg in messages:
        if msg.role == 'user':
            memory.chat_memory.add_user_message(msg.content)
        elif msg.role == 'assistant':
            memory.chat_memory.add_ai_message(msg.content)
    
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
