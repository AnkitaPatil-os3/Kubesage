#!/bin/bash

# Activate virtualenv
source /home/nisha/myenv/bin/activate

# Kill any previous session with the same name
tmux kill-session -t fastapi_services 2>/dev/null

# Define backend service paths
declare -a SERVICES=(
    "/home/nisha/kubesage-new-branch/backend/ai_service"
    "/home/nisha/kubesage-new-branch/backend/user_service"
    "/home/nisha/kubesage-new-branch/backend/kubeconfig_service"
    "/home/nisha/kubesage-new-branch/backend/k8sgpt_service"
    "/home/nisha/kubesage-new-branch/backend/chat_service"
    #"/home/nisha/kubesage-new-branch/backend/selfHealing"
)

# Start new tmux session with the first backend service
tmux new-session -s fastapi_services -d "cd ${SERVICES[0]} && uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload"

# Loop through remaining backend services
for ((i=1; i<${#SERVICES[@]}; i++)); do
    PORT=$((8000 + i))
    tmux split-window -h -t fastapi_services
    tmux select-layout tiled
    tmux send-keys -t fastapi_services "cd ${SERVICES[$i]} && uvicorn app.main:app --host 0.0.0.0 --port $PORT --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload" C-m
done

# Add frontend server
tmux split-window -h -t fastapi_services
tmux select-layout tiled
tmux send-keys -t fastapi_services "cd /home/nisha/kubesage-new-branch/frontend && npm run dev" C-m

# Rebalance the layout
tmux select-layout tiled

# Attach to the session
tmux attach -t fastapi_services
