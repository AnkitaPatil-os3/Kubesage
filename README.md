# Auto-REM AI Agent System

A Python-based agent system with Kubernetes deployment capabilities.

## Project Structure

```
auto-rem-ai/
├── app/                   # Main application code
│   ├── main.py            # Entry point
│   ├── models.py          # Data models
│   └── agents/            # Agent implementations
│       ├── analyzer.py    # Analysis agent
│       ├── executor.py    # Execution agent
│       ├── enforcer.py    # Enforcement agent
│       └── reasoner.py    # Reasoning agent
├── k8s/                   # Kubernetes deployment files
│   ├── deployment.yaml
│   ├── rbac.yaml
│   ├── service.yaml
│   └── watcher-deployment.yaml
├── tests/                 # Test files
│   └── agents/
│       └── test_analyzer.py
├── .dockerignore
├── .gitignore
├── Dockerfile             # Docker configuration
├── env-sample             # Environment variables template
├── plan.md                # Project plan
├── requirements.txt       # Python dependencies
├── sample_request.sh      # Example request script
├── structure.txt          # Project structure
├── test.py                # Test script
└── watcher.py             # Monitoring component
```

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
# or
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the env-sample file to .env:
```bash
cp env-sample .env
```

2. Edit the .env file with your configuration values.

## Usage

Run the main application:
```bash
python app/main.py
```

## Testing

Run tests:
```bash
python -m pytest tests/
```

## Docker Deployment

Build the Docker image:
```bash
docker build -t auto-rem-ai .
```

Run the container:
```bash
docker run -p 5000:5000 auto-rem-ai
```

## Kubernetes Deployment

Apply Kubernetes configurations:
```bash
kubectl apply -f k8s/
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request