---
title: ""
sidebar_label: " Getting Started"
---

import HeaderWithImage from '@site/src/components/HeaderWithImage';

<HeaderWithImage />


KubeSage is an AI-powered cloud-native super app for Kubernetes

import PrequisitesWithImage from '@site/src/components/PrerequisitesWithImage';

<PrequisitesWithImage />


- Kubernetes cluster (EKS, GKE, AKS, or local Minikube)
- Helm installed
- Access token & server URL
- Docker and kubectl installed

<!-- ## 🛠️ Installation Steps -->
import InstallationWithImage from '@site/src/components/InstallationWithImage';

<InstallationWithImage />

### 1. Clone the Repo

```bash
git clone https://github.com/your-org/kubesage.git
cd kubesage
```

### 2. Configure Your Cluster

Edit the values.yaml with your cluster's server URL and token.

### 3. Deploy with Helm

```bash
helm install kubesage ./helm/kubesage
```

### 4. Access Dashboard

```bash
kubectl port-forward svc/kubesage-ui 8080:80
```

Visit: http://localhost:8080

---
import InsideWithImage from '@site/src/components/InsideWithImage';

<InsideWithImage />
<!-- 
## 🧠 What's Inside? -->

| Feature           | Description                                         |
|-------------------|-----------------------------------------------------|
| AI Troubleshooting | Use LLMs to suggest fixes based on cluster events |
| Observability     | View CPU, memory, workloads, and errors per cluster |
| RBAC Support      | Role-based views for SRE, Devs, Platform Engineers  |
| Security Audits    | View policy violations and compliance reports       |

---
import NextstepWithImage from '@site/src/components/NextstepWithImage';

<NextstepWithImage />


<!-- ## 🧪 Next Step -->

- Add Clusters
- Explore Workloads
- Use "Edit YAML" to update resources live
- Review AI recommendations in Insights panel
- Want to enable multi-cluster event monitoring? Head over to the Cluster Monitoring Guide
