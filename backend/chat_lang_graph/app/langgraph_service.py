import json
from typing import Dict, List, Any, Optional
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from app.config import settings
from app.logger import logger
from app.k8s_tools import k8s_tools
import httpx



# LLM & Agent Initialization
def get_llm():
    """Get LLM instance."""
    return ChatOpenAI(
        base_url=settings.BASE_URL,
        model=settings.MODEL_NAME,
        api_key=settings.API_KEY,
        streaming=True
    )

def get_agent():
    """Get LangGraph agent instance."""
    llm = get_llm()
    
    return create_react_agent(
        model=llm,
        tools=k8s_tools,
        prompt=(
            "You are an **expert Kubernetes assistant**. Your primary function is to assist users with Kubernetes tasks by **utilizing the available tools** and providing **accurate, factual information** about **Kubernetes concepts and operations**. "
            "**Format your responses using Markdown** for clarity and readability in the UI."
            "**Key Directives and Guardrails:**\n"
            "- **Tool Usage:** Prioritize using your tools for specific Kubernetes tasks like listing resources, getting status, describing resources, etc.\n"
            "- **Tool Output Formatting:** When tools return properly formatted markdown content (like bullet lists), present the tool output directly without reformatting or duplicating it.\n"
            "- **Kubernetes Focus:** Only respond to queries directly related to Kubernetes. If a query is outside this scope, state that you cannot assist with that topic.\n"
            "- **Factual Information:** Provide accurate information about Kubernetes concepts and how they work, based on your training data and tool outputs. Avoid speculation or external information.\n"
            "- **Deletion Safety:** For **any deletion operation**, you **MUST ask for explicit confirmation** using the exact phrase: 'yes, delete [resource type] [resource name]'. **Absolutely do NOT proceed without this precise confirmation.**\n"
            "Be concise, clear, and prioritize safety and accuracy. Begin by confirming your role as a Kubernetes assistant."
        ),
    )

class LangGraphService:
    """Service for handling LangGraph agent interactions."""
    
    def __init__(self):
        self.agent = get_agent()
        self.llm = get_llm()
        self.kubeconfig_service_url = settings.KUBECONFIG_SERVICE_URL
    
    async def get_cluster_info(self, cluster_name: str, user_token: str) -> Optional[Dict]:
        """Get cluster information from kubeconfig service"""
        try:
            print(f"🔍 Fetching cluster info for: {cluster_name}")
            print(f"   Using token: {user_token[:20]}...{user_token[-10:] if len(user_token) > 30 else user_token}")
            
            # Call kubeconfig service to get cluster credentials
            async with httpx.AsyncClient(verify=False) as client:  # Disable SSL verification
                url = f"{self.kubeconfig_service_url}/kubeconfig/cluster/{cluster_name}/credentials"
                print(f"   Making request to: {url}")
                
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {user_token}"}
                )
                
                print(f"   Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Response data: {data}")
                    logger.info(f"Cluster info retrieved for {cluster_name}")
                    if data.get("success") and data.get("cluster"):
                        cluster_info = data["cluster"]
                        print(f"✅ Successfully retrieved cluster info:")
                        print(f"   Server URL: {cluster_info.get('server_url')}")
                        print(f"   Token: {cluster_info.get('token', '')[:20]}...")
                        return cluster_info
                    
                print(f"❌ Failed to get cluster info: {data}")
                logger.error(f"Failed to get cluster info: {data}")
                return None
                
        except Exception as e:
            print(f"❌ Exception getting cluster info: {e}")
            logger.error(f"Error getting cluster info: {e}")
            return None
    
    async def process_message(
        self, 
        message: str, 
        history: List[Dict[str, str]], 
        enable_tool_response: bool = False,
        cluster_name: Optional[str] = None,
        user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a message with the LangGraph agent."""
        try:
            print(f"🤖 Processing message: {message[:100]}...")
            print(f"   Cluster name: {cluster_name}")
            print(f"   User token provided: {'Yes' if user_token else 'No'}")
            
            logger.info(f"🤖 Processing message with LangGraph: {message[:100]}...")
            
            # Configure k8s tools with cluster connection if provided
            if cluster_name and user_token:
                print(f"🔧 Configuring cluster connection for: {cluster_name}")
                cluster_info = await self.get_cluster_info(cluster_name, user_token)
                if cluster_info:
                    print(f"✅ Got cluster info, configuring connection...")
                    from app.k8s_tools import configure_cluster_connection, configure_cluster_connection_alt
                    
                    try:
                        # Try primary configuration method
                        configure_cluster_connection(
                            cluster_info.get("server_url"),
                            cluster_info.get("token"),
                            cluster_name
                        )
                        print(f"✅ Primary cluster connection configured successfully")
                    except Exception as primary_error:
                        print(f"❌ Primary configuration failed: {primary_error}")
                        print(f"🔄 Trying alternative configuration...")
                        
                        try:
                            # Try alternative configuration method
                            configure_cluster_connection_alt(
                                cluster_info.get("server_url"),
                                cluster_info.get("token"),
                                cluster_name
                            )
                            print(f"✅ Alternative cluster connection configured successfully")
                        except Exception as alt_error:
                            print(f"❌ Alternative configuration also failed: {alt_error}")
                            logger.warning(f"Could not configure cluster connection for {cluster_name}: {alt_error}")
                else:
                    print(f"❌ Could not retrieve cluster info for {cluster_name}")
                    logger.warning(f"Could not retrieve cluster info for {cluster_name}")
            else:
                print(f"⚠️ No cluster configuration - using default kubeconfig")
            
            # Prepare messages for agent
            messages = history + [{"role": "user", "content": message}]
            print(f"📝 Prepared {len(messages)} messages for agent")
            
            # Invoke agent
            print(f"🚀 Invoking agent...")
            result = await self.agent.ainvoke({"messages": messages})
            print(f"✅ Agent invocation completed")
            
            # Process result
            final_response = ""
            tools_info, tool_responses = [], []
            tool_call_id_map = {}
            
            for msg in result.get("messages", []):
                if isinstance(msg, AIMessage):
                    if msg.content:
                        final_response = msg.content
                    
                    # Process tool calls
                    for call in msg.additional_kwargs.get("tool_calls", []):
                        func = call.get("function", {})
                        args_str = func.get("arguments", "{}")
                        try:
                            args = json.loads(args_str)
                        except Exception:
                            args = args_str
                        
                        if enable_tool_response:
                            tools_info.append({
                                "name": func.get("name", "unknown_tool"),
                                "args": json.dumps(args)
                            })
                        
                        tool_call_id_map[call.get("id")] = func.get("name", "unknown_tool")
                
                elif isinstance(msg, ToolMessage):
                    if enable_tool_response:
                        tool_name = tool_call_id_map.get(msg.tool_call_id, "unknown_tool")
                        tool_responses.append({
                            "name": tool_name,
                            "response": msg.content or ""
                        })
            
            print(f"✅ Processing completed, response length: {len(final_response)}")
            logger.info(f"✅ LangGraph processing completed, response length: {len(final_response)}")
            
            return {
                "success": True,
                "response": final_response,
                "tools_info": tools_info if enable_tool_response else [],
                "tool_responses": tool_responses if enable_tool_response else []
            }
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            print(f"   Error type: {type(e)}")
            logger.error(f"❌ Error processing message with LangGraph: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"❌ **Error:** I encountered an issue processing your request: {str(e)}\n\n💡 **Please try again** or contact support if the issue persists."
            }
    
    async def stream_message(
        self, 
        message: str, 
        history: List[Dict[str, str]],
        cluster_name: Optional[str] = None,
        user_token: Optional[str] = None
    ):
        """Stream a message response from the LangGraph agent."""
        try:
            print(f"🌊 Streaming message: {message[:100]}...")
            print(f"   Cluster name: {cluster_name}")
            
            logger.info(f"🌊 Streaming message with LangGraph: {message[:100]}...")
            
            # Configure k8s tools with cluster connection if provided
            if cluster_name and user_token:
                print(f"🔧 Configuring cluster connection for streaming...")
                cluster_info = await self.get_cluster_info(cluster_name, user_token)
                if cluster_info:
                    from app.k8s_tools import configure_cluster_connection
                    configure_cluster_connection(
                        cluster_info.get("server_url"),
                        cluster_info.get("token"),
                        cluster_name
                    )
                    print(f"✅ Cluster connection configured for streaming")
            
            # Prepare messages for agent
            messages = history + [{"role": "user", "content": message}]
            
            # Stream response
            async for token, _ in self.agent.astream({"messages": messages}, stream_mode="messages"):
                if hasattr(token, 'content') and token.content:
                    yield token.content
                    
        except Exception as e:
            print(f"❌ Error streaming message: {e}")
            print(f"   Error type: {type(e)}")
            logger.error(f"❌ Error streaming message with LangGraph: {e}")
            yield f"❌ **Error:** {str(e)}"
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of LangGraph service."""
        try:
            # Test LLM connection
            test_response = await self.llm.ainvoke("Health check", config={"max_tokens": 1})
            
            # Get tool names
            tool_names = [tool.__name__ for tool in k8s_tools]
            
            return {
                "status": "healthy",
                "llm_connection": {"status": "ok"},
                "tools_available": len(tool_names),
                "tools": tool_names
            }
            
        except Exception as e:
            logger.error(f"❌ LangGraph health check failed: {e}")
            return {
                "status": "unhealthy",
                "llm_connection": {"status": "error", "details": str(e)},
                "tools_available": 0,
                "tools": []
            }