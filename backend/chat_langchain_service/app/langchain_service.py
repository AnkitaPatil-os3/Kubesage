import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from app.config import settings
from app.logger import logger
import json
import subprocess
import ast
import re
from functools import lru_cache
import time

from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory

# Custom streaming callback handler
class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming LLM responses."""
    
    def __init__(self, max_queue_size: int = 1000):
        self.tokens_queue = asyncio.Queue(maxsize=max_queue_size)
        self.full_response = []
        self._is_streaming = True
        self._error_count = 0
        self._max_errors = 5
        
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Put the new token in the queue with error handling."""
        if not self._is_streaming or self._error_count >= self._max_errors:
            return
            
        try:
            self.full_response.append(token)
            await asyncio.wait_for(
                self.tokens_queue.put(token), 
                timeout=1.0
            )
        except asyncio.TimeoutError:
            self._error_count += 1
            logger.warning(f"Token queue timeout, error count: {self._error_count}")
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error adding token to queue: {str(e)}")
    
    async def on_llm_end(self, response, **kwargs) -> None:
        """Signal the end of the LLM response."""
        self._is_streaming = False
        try:
            await asyncio.wait_for(
                self.tokens_queue.put(None), 
                timeout=1.0
            )
        except Exception as e:
            logger.error(f"Error signaling end of stream: {str(e)}")
    
    async def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Handle LLM errors with graceful degradation."""
        self._is_streaming = False
        error_msg = f"LLM Error: {str(error)}"
        logger.error(error_msg)
        try:
            await asyncio.wait_for(
                self.tokens_queue.put(error_msg), 
                timeout=1.0
            )
            await asyncio.wait_for(
                self.tokens_queue.put(None), 
                timeout=1.0
            )
        except Exception as e:
            logger.error(f"Error handling LLM error: {str(e)}")
    
    def get_full_response(self) -> str:
        """Get the complete response as a string."""
        return "".join(self.full_response)

def safe_json_parse(input_str: str) -> Dict[str, Any]:
    """Parse JSON input with multiple fallback strategies."""
    if not input_str or not isinstance(input_str, str):
        return {}
    
    input_str = input_str.strip()
    
    # Strategy 1: Direct JSON parsing
    try:
        return json.loads(input_str)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Handle single quotes
    try:
        json_str = input_str.replace("'", '"')
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Python literal evaluation
    try:
        result = ast.literal_eval(input_str)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass
    
    # Strategy 4: Parse key-value pairs manually
    try:
        if '=' in input_str:
            pairs = {}
            for pair in input_str.split(','):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    key = key.strip().strip('"\'')
                    value = value.strip().strip('"\'')
                    try:
                        if value.isdigit():
                            value = int(value)
                        elif value.lower() in ('true', 'false'):
                            value = value.lower() == 'true'
                    except:
                        pass
                    pairs[key] = value
            return pairs
    except Exception:
        pass
    
    # Strategy 5: Extract parameters from natural language
    try:
        params = {}
        namespace_match = re.search(r'namespace[:\s=]+([a-zA-Z0-9-]+)', input_str, re.IGNORECASE)
        if namespace_match:
            params['namespace'] = namespace_match.group(1)
        
        limit_match = re.search(r'limit[:\s=]+(\d+)', input_str, re.IGNORECASE)
        if limit_match:
            params['limit'] = int(limit_match.group(1))
        
        return params
    except Exception:
        pass
    
    logger.warning(f"Could not parse input: {input_str}")
    return {}

def fetch_k8s_events(namespace: Optional[str] = None, limit: int = 10) -> str:
    """Fetch Kubernetes events using kubectl."""
    try:
        # Validate and sanitize inputs
        if limit is None or not isinstance(limit, int):
            limit = 10
        limit = max(1, min(limit, 100))  # Clamp between 1 and 100
        
        if namespace is not None and not isinstance(namespace, str):
            namespace = str(namespace) if namespace else None
        
        # Validate namespace name
        if namespace:
            if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', namespace):
                return f"Invalid namespace name: {namespace}"
        
        # Build kubectl command
        cmd = ["kubectl", "get", "events"]
        if namespace:
            cmd.extend(["-n", namespace])
        else:
            cmd.append("--all-namespaces")
        
        cmd.extend(["--sort-by=.metadata.creationTimestamp", f"--limit={limit}"])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                return f"kubectl error (exit code {result.returncode}): {error_msg}"
            
            output = result.stdout.strip()
            if not output:
                return f"No events found{f' in namespace {namespace}' if namespace else ''}"
            
            return output
            
        except subprocess.TimeoutExpired:
            return "Error: kubectl command timed out after 30 seconds"
        except FileNotFoundError:
            return "Error: kubectl command not found. Please ensure kubectl is installed and in PATH"
        except Exception as e:
            return f"Error executing kubectl: {str(e)}"
        
    except Exception as e:
        logger.error(f"Unexpected error in fetch_k8s_events: {str(e)}")
        return f"Unexpected error fetching events: {str(e)}"

def run_kubectl(args: str) -> str:
    """Run kubectl commands safely with security restrictions."""
    try:
        if not args or not isinstance(args, str):
            return "Error: No command arguments provided"
        
        args = args.strip()
        parsed_args = []
        
        # Enhanced parsing with multiple strategies
        if args.startswith("[") and args.endswith("]"):
            try:
                parsed_args = json.loads(args)
            except json.JSONDecodeError:
                try:
                    parsed_args = ast.literal_eval(args)
                except (ValueError, SyntaxError):
                    args = args.strip("[]")
                    parsed_args = [arg.strip().strip("'\"") for arg in args.split(",")]
        else:
            parsed_args = args.split()
        
        if not parsed_args:
            return "Error: No valid command arguments found"
        
        # Security: Whitelist allowed kubectl commands
        allowed_commands = {
            'get', 'describe', 'logs', 'top', 'version', 'cluster-info',
            'api-resources', 'api-versions', 'explain'
        }
        
        if parsed_args[0] not in allowed_commands:
            return f"Error: Command '{parsed_args[0]}' not allowed. Allowed commands: {', '.join(allowed_commands)}"
        
        # Security: Prevent dangerous flags
        dangerous_flags = {'--rm', '--force', '--grace-period=0', '--now'}
        if any(flag in ' '.join(parsed_args) for flag in dangerous_flags):
            return "Error: Dangerous flags detected and blocked"
        
        # Build and execute command
        cmd = ["kubectl"] + parsed_args
        logger.info(f"Executing kubectl command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                return f"kubectl error (exit code {result.returncode}): {error_msg}"
            
            output = result.stdout.strip()
            if not output:
                return "Command executed successfully (no output)"
            
            # Limit output size
            if len(output) > 10000:
                output = output[:10000] + "\n... (output truncated)"
            
            return output
            
        except subprocess.TimeoutExpired:
            return "Error: kubectl command timed out after 30 seconds"
        except FileNotFoundError:
            return "Error: kubectl command not found. Please ensure kubectl is installed and in PATH"
        except Exception as e:
            return f"Error executing kubectl: {str(e)}"
            
    except Exception as e:
        logger.error(f"Unexpected error in run_kubectl: {str(e)}")
        return f"Unexpected error: {str(e)}"

# LangChain tools
tools = [
    Tool(
        name="fetch_k8s_events",
        description=(
            "Fetch Kubernetes events. Input should be JSON with optional 'namespace' and 'limit' fields. "
            "Examples: '{\"namespace\": \"default\", \"limit\": 5}' or '{\"limit\": 10}' or '{}' for defaults."
        ),
        func=lambda input_str: fetch_k8s_events(**safe_json_parse(input_str))
    ),
    Tool(
        name="run_kubectl",
        description=(
            "Run kubectl commands safely. Input can be JSON array like [\"get\", \"pods\"] "
            "or space-separated string like 'get pods -n default'. "
            "Only read-only commands are allowed for security."
        ),
        func=lambda input_str: run_kubectl(input_str)
    )
]

@lru_cache(maxsize=10)
def get_streaming_llm():
    """Get a streaming LLM instance with caching."""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0.7,
        streaming=True,
        max_tokens=2000,
        request_timeout=60,
        max_retries=3
    )

@lru_cache(maxsize=10)
def get_non_streaming_llm():
    """Get a non-streaming LLM instance with caching."""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0.7,
        max_tokens=2000,
        request_timeout=60,
        max_retries=3
    )

async def process_with_langchain(
    user_message: str,
    memory: Optional[ConversationBufferMemory] = None,
    stream: bool = False
) -> Dict[str, Any]:
    """Process user message with LangChain agents and tools."""
    try:
        # Input validation
        if not user_message or not isinstance(user_message, str):
            raise ValueError("Invalid user message provided")
        
        user_message = user_message.strip()
        if len(user_message) > 10000:
            user_message = user_message[:10000] + "... (message truncated)"
        
        # Create or use provided memory
        if memory is None:
            memory = ConversationBufferMemory(
                return_messages=True, 
                memory_key="chat_history",
                max_token_limit=4000
            )
        
        # Enhanced system prompt for better tool usage
        system_prompt = """You are KubeSage, an expert Kubernetes assistant. You have access to tools to interact with Kubernetes clusters.

IMPORTANT TOOL USAGE GUIDELINES:
1. For fetch_k8s_events tool: Always use proper JSON format like {"namespace": "default", "limit": 5} or {} for defaults
2. For run_kubectl tool: Use JSON array format like ["get", "pods"] or ["describe", "pod", "pod-name"]
3. Always validate your tool inputs before using them
4. If a tool fails, explain the error and suggest alternatives

When using tools:
- Be precise with JSON formatting
- Handle errors gracefully
- Provide context for your actions
- Explain what you're doing and why

Respond in clear, structured markdown format with proper code blocks for commands and outputs."""
        
        logger.info(f"Processing message with LangChain (stream={stream})")
        
        if stream:
            # Streaming response
            streaming_handler = StreamingCallbackHandler(max_queue_size=1000)
            llm = get_streaming_llm()
            llm.callbacks = [streaming_handler]
            
            # Create agent
            agent = initialize_agent(
                tools,
                llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=False,
                handle_parsing_errors=True,
                max_iterations=5,
                max_execution_time=120,
                early_stopping_method="generate",
                memory=memory
            )
            
            # Start the agent in a background task
            task = asyncio.create_task(
                asyncio.wait_for(
                    agent.ainvoke({"input": user_message}),
                    timeout=120.0
                )
            )
            
            return {
                "type": "streaming",
                "task": task,
                "streaming_handler": streaming_handler,
                "memory": memory
            }
        else:
            # Non-streaming response
            llm = get_non_streaming_llm()
            
            # Create agent
            agent = initialize_agent(
                tools,
                llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=False,
                handle_parsing_errors=True,
                max_iterations=5,
                max_execution_time=120,
                early_stopping_method="generate",
                memory=memory
            )
            
            # Execute agent
            start_time = time.time()
            try:
                response = await asyncio.wait_for(
                    agent.ainvoke({"input": user_message}),
                    timeout=120.0
                )
                execution_time = time.time() - start_time
                
                return {
                    "type": "complete",
                    "response": response.get("output", ""),
                    "memory": memory,
                    "execution_time": execution_time,
                    "success": True
                }
                
            except asyncio.TimeoutError:
                logger.error("LangChain agent execution timed out")
                return {
                    "type": "error",
                    "error": "Request timed out. Please try a simpler query.",
                    "memory": memory,
                    "success": False
                }
            except Exception as e:
                logger.error(f"LangChain agent execution failed: {str(e)}")
                return {
                    "type": "error",
                    "error": f"I encountered an error: {str(e)}. Please try rephrasing your question.",
                    "memory": memory,
                    "success": False
                }
                
    except Exception as e:
        logger.error(f"Error in process_with_langchain: {str(e)}")
        return {
            "type": "error",
            "error": f"Failed to process your request: {str(e)}",
            "memory": None,
            "success": False
        }

async def stream_tokens(streaming_handler: StreamingCallbackHandler) -> AsyncIterator[str]:
    """Stream tokens from the streaming handler."""
    try:
        while True:
            try:
                token = await asyncio.wait_for(
                    streaming_handler.tokens_queue.get(),
                    timeout=30.0
                )
                
                if token is None:  # End of stream
                    break
                    
                yield token
                
            except asyncio.TimeoutError:
                logger.warning("Token streaming timeout")
                break
            except Exception as e:
                logger.error(f"Error streaming token: {str(e)}")
                break
                
    except Exception as e:
        logger.error(f"Error in stream_tokens: {str(e)}")
        yield f"Error: {str(e)}"

def create_memory_from_messages(messages: List[Dict[str, Any]]) -> ConversationBufferMemory:
    """Create ConversationBufferMemory from message history."""
    memory = ConversationBufferMemory(
        return_messages=True,
        memory_key="chat_history",
        max_token_limit=4000
    )
    
    try:
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            
            if not content:
                continue
                
            if role == "user":
                memory.chat_memory.add_user_message(content)
            elif role == "assistant":
                memory.chat_memory.add_ai_message(content)
                
    except Exception as e:
        logger.error(f"Error creating memory from messages: {str(e)}")
        
    return memory

def get_memory_summary(memory: ConversationBufferMemory) -> Dict[str, Any]:
    """Get a summary of the memory state for debugging."""
    try:
        messages = memory.chat_memory.messages
        return {
            "message_count": len(messages),
            "memory_buffer": memory.buffer if hasattr(memory, 'buffer') else "",
            "memory_messages": [
                {
                    "type": type(msg).__name__,
                    "content": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                }
                for msg in messages
            ]
        }
    except Exception as e:
        logger.error(f"Error getting memory summary: {str(e)}")
        return {"error": str(e)}