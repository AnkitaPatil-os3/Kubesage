
# KubeSage

KubeSage is a comprehensive platform for Kubernetes cluster analysis, troubleshooting, and management. It combines AI-powered analysis with intuitive interfaces to help users identify and resolve issues in their Kubernetes environments.

## Features

- **K8sGPT Integration**: Analyze Kubernetes clusters for potential issues and get AI-powered explanations
- **Multiple AI Backend Support**: Connect to various AI providers including OpenAI, and more
- **Kubeconfig Management**: Securely store and manage multiple Kubernetes configurations
- **Command Generation**: AI-assisted generation of kubectl commands based on natural language queries
- **Analysis History**: Save and review past cluster analyses
- **Multi-user Support**: Role-based access with regular and admin user capabilities
- **Chat Service**: Interactive chat interface for Kubernetes assistance

## Architecture

KubeSage is built with a microservices architecture:

- **Frontend**: Vue-based web interface
- **Backend Services**:
  - **User Service**: Authentication and user management
  - **K8sGPT Service**: Kubernetes cluster analysis
  - **Kubeconfig Service**: Management of Kubernetes configurations
  - **AI Agent Service**: LLM integration for command generation and analysis
  - **Chat Service**: Real-time chat functionality for Kubernetes assistance

## Prerequisites

### Core Requirements

- **Node.js and npm**: [https://nodejs.org/](https://nodejs.org/) (v16 or later recommended)
- **Python**: [https://www.python.org/downloads/](https://www.python.org/downloads/) (v3.9 or later)
- **Docker and Docker Compose**: [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/)
- **Kubernetes Cluster**: Any Kubernetes distribution (for testing, [minikube](https://minikube.sigs.k8s.io/docs/start/) is recommended)

### Infrastructure Components

- **PostgreSQL**: [https://www.postgresql.org/download/](https://www.postgresql.org/download/) (v13 or later)
- **RabbitMQ**: [https://www.rabbitmq.com/download.html](https://www.rabbitmq.com/download.html)
- **Redis**: [https://redis.io/download/](https://redis.io/download/)

### Kubernetes Tools

- **kubectl**: [https://kubernetes.io/docs/tasks/tools/](https://kubernetes.io/docs/tasks/tools/)
- **Helm**: [https://helm.sh/docs/intro/install/](https://helm.sh/docs/intro/install/)
- **K8sGPT**: [https://k8sgpt.ai/](https://k8sgpt.ai/) - Install with:
  ```bash
  helm repo add k8sgpt https://charts.k8sgpt.ai/
  helm repo update
  helm install k8sgpt k8sgpt/k8sgpt-operator -n k8sgpt --create-namespace
  ```

## Development Setup

### Getting Started

1. Clone the repository
   ```bash
   git clone https://10.0.32.141/kubesage/kubesage-development.git
   cd kubesage-development
   ```

2. Set up environment variables
   ```bash
   # Copy example env files for each service
   cp backend/user_service/.env.example backend/user_service/.env
   cp backend/k8sgpt_service/.env.example backend/k8sgpt_service/.env
   cp backend/kubeconfig_service/.env.example backend/kubeconfig_service/.env
   cp backend/ai_service/.env.example backend/ai_service/.env
   cp frontend/.env.example frontend/.env
   
   # Edit the .env files with your configuration
   ```


3. Start the backend services
    ### AI Agent Service
    ```bash
    ### Ai Agent Service
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload 

    ### User Service
    uvicorn app.main:app --host 0.0.0.0 --port 8001 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload

    ### Kubeconfig Service
    uvicorn app.main:app --host 0.0.0.0 --port 8002 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload 

    ### K8sgpt Service
    uvicorn app.main:app --host 0.0.0.0 --port 8003 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload --app-dir backend/kubeconfig_service

    ### Chat Service
    uvicorn app.main:app --host 0.0.0.0 --port 8004 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload --app-dir backend/ai_service 
    ```

    


5. Start the frontend
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

6. Access the web interface at https://your-server-ip:9980



## API Documentation

API documentation is available at:
- AI Service: https://your-server-ip:8000/docs
- user Service: https://your-server-ip:8001/docs
- K8sgpt Service: https://your-server-ip:8002/docs
- Kubeconfig Service: https://your-server-ip:8003/docs
- AI Agent Service: https://your-server-ip:8004/docs


## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

=======
# KubeSage-Development



## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/ee/gitlab-basics/add-file.html#add-a-file-using-the-command-line) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://10.0.32.141/kubesage/kubesage-development.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://10.0.32.141/kubesage/kubesage-development/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/ee/user/project/merge_requests/merge_when_pipeline_succeeds.html)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/index.html)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
>>>>>>> README.md
