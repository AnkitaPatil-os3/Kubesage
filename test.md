KubeSage SaaS Agent Onboarding Workflow
1. User Interface (SaaS Dashboard)
⬇️

User copies the onboarding command from the dashboard.
2. Client-side (Kubernetes Cluster)
⬇️

User runs the copied command in their Kubernetes cluster.
This installs the Agent.
3. Agent Initialization
⬇️

Agent loads required environment variables / secrets:
api_key
agent_id
backend_url
4. Agent Connection Setup
⬇️

Agent initializes and opens a WebSocket connection to the SaaS Backend.
5. Onboarding API Call
⬇️
Agent sends the following request to the backend:

POST /onboard
Headers:
  agent_id: <AGENT_ID>
  api_key: <API_KEY>

Body:
{
  "cluster_name": "<cluster_name>",
  "metadata": { ... }
}

use this workflow for cluster onboarding for my saas backend and agent(goes inside k8s cluster) . Use and update my existing code #file:onboarding_service  and #file:agent and api key will generate from #file:user_service and validate internal service communication will be using rabbitmq like user and onboarding service backend connects with agent using websockect. Update my esiting to generate agent_id unique. Follow best practices and security measures.