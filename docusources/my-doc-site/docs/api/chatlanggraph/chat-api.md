---
sidebar_position: 2
---

# Chat API

The Chat API allows users to ask questions about their Kubernetes cluster and receive AI-powered responses. It processes natural language queries, interacts with cluster data and knowledge graphs, and provides insightful answers to help users troubleshoot and manage their clusters effectively.

**Endpoint:** `POST /chat`

### Request

The request body must include a `question` field containing the user's query about the cluster.

Example request body:

```json
{
  "question": "Why are my pods crashing?"
}
```

### Response

The response contains an `answer` field with the AI-generated response to the user's question. The answer provides explanations, suggestions, or relevant information based on the cluster's state and data.

Example response body:

```json
{
  "answer": "Your pods are crashing due to OOM errors. Try increasing memory limits."
}
```
}
}
