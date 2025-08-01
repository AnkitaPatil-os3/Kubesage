# `/chat` API Deep-Dive Workflow Documentation

This document provides an in-depth explanation of the `/chat` API workflow in the Kubesage Demo backend. It covers the full lifecycle of a chat request, including authentication, session management, Kubernetes cluster integration, LangGraph agent orchestration, tool invocation, error handling, and streaming support. This is intended for KT sessions and onboarding new developers.

---

## 1. Overview

The `/chat` endpoint enables users to interact with a Kubernetes expert assistant. It leverages LangGraph (built on LangChain), integrates with Kubernetes clusters via dynamic credentials, and supports session-based conversation history. The assistant can invoke real Kubernetes operations using a set of Python tools.

---

## 2. Request Flow & Authentication

### Endpoint
- **POST** `/chat`
- **Request Model:** `ChatRequest`
  - `message`: User's chat message (string)
  - `session_id`: Optional session identifier (string)
  - `enable_tool_response`: Whether to include tool call details (bool)
  - `cluster_name`: Target Kubernetes cluster (string, optional)

### Authentication
- Requires a Bearer token in the `Authorization` header.
- Token is extracted using `get_user_token(request)` in `routes.py`.
- Token is used to fetch cluster credentials from the kubeconfig service.

---

## 3. Workflow Steps (Expanded)

### 1. **Rate Limiting**
- Implemented via `slowapi` (`Limiter`).
- Prevents excessive requests per user/IP.

### 2. **Service Initialization**
- `ChatService` and `MessageService` are instantiated with the DB session.
- These services handle session creation, message storage, and retrieval.

### 3. **User Token Extraction**
- `get_user_token(request)` parses the `Authorization` header.
- If missing or invalid, the request is rejected.

### 4. **Message Validation & Sanitization**
- `MessageService.validate_message_content(content)` checks for empty or overly long messages.
- `sanitize_message_content(content)` trims whitespace and enforces length limits.

### 5. **Session Handling**
- If `session_id` is provided, fetch the session for the user.
- If not, create a new session (`ChatService.create_session`).
- Sessions are tied to users via foreign key (`user_id`).

### 6. **Message Storage**
- User message is stored in the DB (`ChatService.add_message`).
- Each message is linked to its session and has a role (`user` or `assistant`).

### 7. **Conversation History Retrieval**
- Full session history is fetched (`ChatService.get_session_history`).
- History is formatted for LangGraph agent context.

### 8. **Cluster Context Setup**
- If `cluster_name` and token are provided:
  - `LangGraphService.get_cluster_info` calls the kubeconfig service to fetch cluster credentials.
  - Credentials are used to configure the Kubernetes Python client (`k8s_tools.configure_cluster_connection`).
  - This enables the agent to perform real operations on the specified cluster.

### 9. **LangGraph Agent Invocation**
- `LangGraphService.process_message` is called with:
  - User message
  - Conversation history
  - Cluster context (if configured)
  - Tool invocation flag
- The agent uses a custom prompt to enforce Kubernetes focus, safety, and Markdown formatting.

### 10. **Tool Usage & Safety**
- The agent may invoke functions from `k8s_tools.py` (e.g., list pods, create deployments).
- For destructive actions (deletion), the agent must prompt for explicit confirmation.
- Tool calls and their outputs are included in the response if `enable_tool_response` is true.

### 11. **Assistant Response Storage**
- The assistant's reply is stored in the session history as a new message (`role: assistant`).

### 12. **Response Formatting**
- `format_markdown_response` cleans up the response for UI display.
- Removes duplicate tool/result indicators and excessive newlines.

### 13. **API Response**
- Returns a `ChatResponse`:
  - `session_id`
  - `response` (assistant's reply)
  - `tools_info` (details of tools invoked)
  - `tool_response` (tool outputs)

---

## 4. Error Handling

- **Validation Errors:** Return HTTP 400 with details.
- **Session Not Found:** Return HTTP 404.
- **Cluster Credential Errors:** Return HTTP 401/403.
- **LangGraph/Tool Errors:** Return HTTP 500 with error details.
- All errors are logged for debugging.

---

## 5. Streaming Support

- **POST** `/chat/stream` streams the assistant's response token-by-token.
- Uses `StreamingResponse` for real-time UI updates.
- Stores the full assistant response after streaming completes.
- Streaming models are defined in `schemas.py`.

---

## 6. Session Management

- **GET** `/sessions`: List all user sessions (`ChatSessionList`).
- **GET** `/sessions/{session_id}`: Get session history (`ChatHistoryResponse`).
- **POST** `/sessions`: Create a new session (`ChatSessionCreate`).
- **DELETE** `/sessions/{session_id}`: Delete a session and its messages.

---

## 7. Kubernetes Tool Integration

- Tools in `k8s_tools.py` cover all major Kubernetes operations:
  - Pod, Deployment, Service, Namespace, ConfigMap, Secret, Ingress, HPA, PVC, NetworkPolicy management.
- Cluster context is configured per request using credentials from the kubeconfig service.
- Tool functions are invoked by the LangGraph agent as needed.

---

## 8. Health Check

- **GET** `/health`: Checks health of LLM, database, and Kubernetes tool connectivity.
- Returns status for each component.

---

## 9. Key Classes & Files (Deep Dive)

- **`routes.py`**: Main API endpoints, request parsing, workflow orchestration.
- **`langgraph_service.py`**: LangGraph agent setup, cluster info retrieval, message processing.
- **`k8s_tools.py`**: Kubernetes Python client functions for all supported operations.
- **`services.py`**: Session and message management, analytics, health checks.
- **`models.py` / `schemas.py`**: SQLModel DB models and Pydantic API schemas.

---

## 10. Sequence Diagram (Textual)

1. **User** → `/chat` → **API**
2. **API** → Validate & store message → **DB**
3. **API** → Get cluster credentials → **Kubeconfig Service**
4. **API** → Configure k8s client → **k8s_tools**
5. **API** → Invoke LangGraph agent → **LangGraph**
6. **LangGraph** → Call k8s tools as needed → **k8s_tools**
7. **LangGraph** → Return response → **API**
8. **API** → Store assistant response → **DB**
9. **API** → Return formatted response → **User**

---

## 11. Security & Safety

- All cluster operations require valid user authentication.
- Destructive actions (delete) require explicit confirmation.
- Only Kubernetes-related queries are processed; others are rejected.

---

## 12. Extensibility

- New Kubernetes tool functions can be added to `k8s_tools.py`.
- LangGraph agent prompt can be updated for new guardrails or capabilities.
- Session and message models support analytics and history tracking.

---

## 13. References & Further Reading

- See `routes.py`, `langgraph_service.py`, and `k8s_tools.py` for implementation details.
- API schemas: `schemas.py`
- Data models: `models.py`
- LangChain & LangGraph documentation for agent orchestration.

---

