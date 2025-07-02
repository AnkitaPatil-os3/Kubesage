from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncIterator, List, Dict, Any
import subprocess
import json
import asyncio
import os
import uuid
import sqlite3
import datetime
from fastapi.middleware.cors import CORSMiddleware

from kubernetes import client, config

from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory

# Custom kubeconfig path
KUBECONFIG_PATH = "/home/aastha/rancher.yaml"

# Database setup
DB_PATH = "chat_sessions.db"

def init_db():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create messages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

# Initialize database on startup
init_db()

# Verify kubeconfig file exists
if not os.path.exists(KUBECONFIG_PATH):
    print(f"Warning: Kubeconfig file not found at {KUBECONFIG_PATH}")
else:
    print(f"Found kubeconfig file at {KUBECONFIG_PATH}")
    
    # Check if the file is readable
    if not os.access(KUBECONFIG_PATH, os.R_OK):
        print(f"Warning: Kubeconfig file at {KUBECONFIG_PATH} is not readable")

# Load K8s config with custom path
try:
    # First try to load in-cluster config (for when running inside a pod)
    config.load_incluster_config()
    print("Using in-cluster Kubernetes configuration")
except config.ConfigException:
    # If that fails, use the specified custom kubeconfig path
    print(f"Loading Kubernetes configuration from {KUBECONFIG_PATH}")
    try:
        config.load_kube_config(config_file=KUBECONFIG_PATH)
        print("Successfully loaded Kubernetes configuration")
    except Exception as e:
        print(f"Error loading Kubernetes configuration: {str(e)}")

# Test the connection
try:
    api_client = client.ApiClient()
    version_api = client.VersionApi(api_client)
    version_info = version_api.get_code()
    print(f"Successfully connected to Kubernetes cluster. Version: {version_info.git_version}")
except Exception as e:
    print(f"Failed to connect to Kubernetes cluster: {str(e)}")

v1 = client.CoreV1Api()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Session Management ===
def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def create_session():
    """Create a new chat session and return the session ID."""
    session_id = str(uuid.uuid4())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (session_id) VALUES (?)", (session_id,))
    conn.commit()
    conn.close()
    return session_id

def get_session(session_id: str):
    """Get a session by ID, or create a new one if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()
    
    if not session:
        conn.close()
        return None
    
    # Update last active timestamp
    cursor.execute("UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
    return dict(session)

def add_message(session_id: str, role: str, content: str):
    """Add a message to a session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )
    conn.commit()
    conn.close()

def get_messages(session_id: str):
    """Get all messages for a session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp",
        (session_id,)
    )
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def create_memory_from_messages(session_id: str):
    """Create a ConversationBufferMemory from stored messages."""
    messages = get_messages(session_id)
    memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
    
    # Add messages to memory
    for msg in messages:
        if msg['role'] == 'user':
            memory.chat_memory.add_user_message(msg['content'])
        elif msg['role'] == 'assistant':
            memory.chat_memory.add_ai_message(msg['content'])
    
    return memory

# === Tool Definitions ===

def fetch_k8s_events(namespace: Optional[str] = None, limit: int = 10) -> str:
    try:
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
        if args.startswith("["):
            parsed_args = json.loads(args)
        else:
            parsed_args = args.split()
        
        # Set environment variable for the subprocess
        env = os.environ.copy()
        env["KUBECONFIG"] = KUBECONFIG_PATH
        
        # Use the custom kubeconfig path for kubectl commands
        cmd = ["kubectl"] + parsed_args
        print(f"Executing kubectl command with KUBECONFIG={KUBECONFIG_PATH}: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True, 
            text=True,
            env=env
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
        description="Use this to run a kubectl command. Input is a JSON array string like ['get', 'pods'].",
        func=lambda input_str: run_kubectl(input_str)
    )
]

# === Custom Streaming Callback Handler ===
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

# === Codestral LLM ===
def get_streaming_llm(streaming_handler):
    return ChatOpenAI(
        model="codestral-latest",
        api_key="dq4yY78RkujcBjUMjgTwXRmAbE4zrt4h",
        base_url="https://codestral.mistral.ai/v1/",
        temperature=0.0,
        streaming=True,
        callbacks=[streaming_handler]
    )

# === FastAPI ===
class ChatRequest(BaseModel):
    message: str
    stream: bool = False
    session_id: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Welcome to the Kubernetes Chat API. Use /chat endpoint to interact."}

@app.post("/session")
async def create_new_session():
    """Create a new chat session."""
    session_id = create_session()
    return {"session_id": session_id}

@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = get_messages(session_id)
    return {
        "session": session,
        "messages": messages
    }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint that supports both streaming and non-streaming responses."""
    try:
        # Get or create session
        if not request.session_id:
            session_id = create_session()
        else:
            session = get_session(request.session_id)
            if not session:
                session_id = create_session()
            else:
                session_id = request.session_id
        
        # Store the user message
        add_message(session_id, "user", request.message)
        
        # Create memory from stored messages
        memory = create_memory_from_messages(session_id)
        
        # Create a system message to ensure context is maintained
        system_prompt = """You are KubeSage, an AI assistant specialized in Kubernetes. 
        When responding to follow-up questions, always consider the full conversation history.
        If a user refers to something mentioned earlier, make sure to connect it to the previous context.
        For example, if they ask about namespaces and then ask "How do I create one?", understand they want to create a namespace.
        Be specific and detailed in your responses about Kubernetes resources and operations."""
        
        if not request.stream:
            # Non-streaming response
            llm = ChatOpenAI(
                model="codestral-latest",
                api_key="dq4yY78RkujcBjUMjgTwXRmAbE4zrt4h",
                base_url="https://codestral.mistral.ai/v1/",
                temperature=0.0
            )
            
            # Initialize agent with memory and system prompt
            agent = initialize_agent(
                tools,
                llm,
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,  # Changed to conversational agent
                verbose=True,
                memory=memory,
                handle_parsing_errors=True,
                system_message=system_prompt
            )
            
            # Invoke the agent with the user's message
            result = agent.invoke({"input": request.message})
            
            # Store the assistant's response
            add_message(session_id, "assistant", result["output"])
            
            return {
                "response": result["output"],
                "session_id": session_id
            }
        else:
            # Streaming response
            return StreamingResponse(
                stream_chat_response(request.message, session_id, memory, system_prompt),
                media_type="text/event-stream"
            )
    except Exception as e:
        import traceback
        print(f"Error in chat endpoint: {str(e)}")
        print(traceback.format_exc())
        return {"error": str(e)}

async def stream_chat_response(message: str, session_id: str, memory, system_prompt: str) -> AsyncIterator[str]:
    """Generate a streaming response for the chat message."""
    # Create a streaming callback handler
    streaming_handler = StreamingCallbackHandler()
    
    # Create LLM with streaming
    llm = get_streaming_llm(streaming_handler)
    
    # Initialize agent with streaming and memory
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,  # Changed to conversational agent
        verbose=True,
        memory=memory,
        handle_parsing_errors=True,
        system_message=system_prompt
    )
    
    # Start the agent in a background task
    task = asyncio.create_task(agent.ainvoke({"input": message}))
    
    # Stream tokens as they come
    while True:
        try:
            # Get the next token from the queue
            token = await asyncio.wait_for(streaming_handler.tokens_queue.get(), timeout=30.0)
            
            # If token is None, we've reached the end of the stream
            if token is None:
                # Store the complete response in the database
                full_response = streaming_handler.get_full_response()
                add_message(session_id, "assistant", full_response)
                break
                
            # Send the token in SSE format
            yield f"data: {json.dumps({'token': token, 'session_id': session_id})}\n\n"
            
        except asyncio.TimeoutError:
            # If we don't get a token for 30 seconds, assume something went wrong
            yield f"data: {json.dumps({'token': '...', 'error': 'Timeout waiting for response', 'session_id': session_id})}\n\n"
            break
        except Exception as e:
            # Handle any other errors
            yield f"data: {json.dumps({'token': '...', 'error': str(e), 'session_id': session_id})}\n\n"
            break
    
    # Send a final message indicating the stream is complete
    yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
    
    # Make sure the task completes
    try:
        await task
    except Exception as e:
        import traceback
        print(f"Error in streaming task: {str(e)}")
        print(traceback.format_exc())
        # We've already handled errors in the streaming

# Add a health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        # Check Kubernetes connection
        version_api = client.VersionApi()
        version_info = version_api.get_code()
        
        return {
            "status": "healthy",
            "database": "connected",
            "kubernetes": f"connected (version {version_info.git_version})"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Add an endpoint to view conversation history
@app.get("/conversation/{session_id}")
async def view_conversation(session_id: str):
    """View the full conversation history for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = get_messages(session_id)
    
    # Format the conversation in a readable way
    formatted_conversation = []
    for msg in messages:
        formatted_conversation.append({
            "role": msg["role"],
            "content": msg["content"],
            "timestamp": msg.get("timestamp", "")
        })
    
    return {
        "session_id": session_id,
        "conversation": formatted_conversation
    }

# Add an endpoint to clear conversation history
@app.delete("/conversation/{session_id}")
async def clear_conversation(session_id: str):
    """Clear the conversation history for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
    
    return {"message": f"Conversation history cleared for session {session_id}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)