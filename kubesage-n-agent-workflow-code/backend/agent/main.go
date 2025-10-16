package main

import (
    "crypto/tls"
    "encoding/json"
    "log"
    "net/http"
    "os"
    "time"
    "net/url"
    // "os/exec"
    "github.com/gorilla/websocket"
    "github.com/joho/godotenv"
)

type OnboardingRequest struct {
    ClusterName string                 `json:"cluster_name"`
    Metadata    map[string]interface{} `json:"metadata"`
}

type RequestMessage struct {
    RequestID string                 `json:"request_id"`
    User      map[string]interface{} `json:"user"`
    Request   map[string]interface{} `json:"request"`
}

type ResponseMessage struct {
    RequestID string `json:"request_id"`
    Result    string `json:"result"`
    Error     string `json:"error,omitempty"`
}

var upgrader = websocket.Upgrader{
    CheckOrigin: func(r *http.Request) bool {
        return true
    },
}

// connectToBackendAndOnboard connects to backend WebSocket and sends onboarding request
func connectToBackendAndOnboard() {
    agentID := os.Getenv("AGENT_ID")
    apiKey := os.Getenv("API_KEY")
    backendWSURL := os.Getenv("BACKEND_WS_URL")
    
    if backendWSURL == "" {
        backendWSURL = "wss://localhost:8007/ws"  // Default WebSocket URL
    }
    
    // Parse the WebSocket URL
    u, err := url.Parse(backendWSURL)
    if err != nil {
        log.Printf("Error parsing WebSocket URL: %v", err)
        return
    }
    
    log.Printf("Connecting to backend WebSocket: %s", backendWSURL)
    
    // Set headers for authentication
    headers := http.Header{}
    headers.Set("agent_id", agentID)
    headers.Set("X-API-Key", apiKey)
    
    // Create a dialer with TLS config
    dialer := *websocket.DefaultDialer
    
    // Configure TLS based on environment
    skipTLSVerify := os.Getenv("SKIP_TLS_VERIFY") == "true"
    if skipTLSVerify {
        log.Printf("WARNING: TLS verification disabled - only use in development")
        dialer.TLSClientConfig = &tls.Config{InsecureSkipVerify: true}
    } else {
        // Use secure TLS configuration for production
        dialer.TLSClientConfig = &tls.Config{
            MinVersion: tls.VersionTLS12,
            // Add ServerName if needed for certificate verification
            // ServerName: "your-domain.com",
        }
    }
    
    // Connect to backend WebSocket
    conn, _, err := dialer.Dial(u.String(), headers)
    if err != nil {
        log.Printf("Warning: Could not connect to backend WebSocket: %v (continuing with HTTP only)", err)
        return
    }
    defer conn.Close()
    
    log.Println("Connected to backend WebSocket successfully")
    
    // Prepare onboarding request with cluster metadata
    clusterName := os.Getenv("CLUSTER_NAME")
    if clusterName == "" {
        clusterName = "default-cluster"
    }
    
    // Get cluster information using in-cluster config
    clusterInfo, err := getClusterInfoFromInCluster()
    if err != nil {
        log.Printf("Warning: Could not get cluster info: %v", err)
        return
    }
    
    metadata := map[string]interface{}{
        "agent_id":           os.Getenv("AGENT_ID"),
        "agent_version":      "1.0.0",
        "node_count":         clusterInfo["node_count"],
        "kubernetes_version": clusterInfo["kubernetes_version"],
        "namespace_count":    clusterInfo["namespace_count"],
        "cluster_info":       clusterInfo,
        "provider":           "kubernetes",
    }
    
    onboardingReq := OnboardingRequest{
        ClusterName: clusterName,
        Metadata:    metadata,
    }
    
    // Send onboarding request
    reqBytes, err := json.Marshal(onboardingReq)
    if err != nil {
        log.Printf("Error marshaling onboarding request: %v", err)
        return
    }
    
    err = conn.WriteMessage(websocket.TextMessage, reqBytes)
    if err != nil {
        log.Printf("Error sending onboarding request: %v", err)
        return
    }
    
    log.Printf("Sent onboarding request for cluster: %s", clusterName)
    
    // Wait for response
    _, response, err := conn.ReadMessage()
    if err != nil {
        log.Printf("Error reading response: %v", err)
        return
    }
    
    log.Printf("Received response from backend: %s", string(response))
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("OK"))
}

func handleWebSocket(w http.ResponseWriter, r *http.Request) {
    conn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
        log.Println("Upgrade error:", err)
        return
    }
    defer conn.Close()

    for {
        _, message, err := conn.ReadMessage()
        if err != nil {
            log.Println("Read error:", err)
            break
        }
        log.Printf("Received WebSocket message: %s", message)

        var req RequestMessage
        if err := json.Unmarshal(message, &req); err != nil {
            log.Println("JSON unmarshal error:", err)
            continue
        }
        log.Printf("Processing request ID %s", req.RequestID)

        var result string
        var execErr error

        // Call onboarding API after WebSocket connection establish
        if reqText, ok := req.Request["message"].(string); ok && reqText == "onboard" {
            err := callOnboardingAPI(req.Request)
            if err != nil {
                result = "Failed to call onboarding API: " + err.Error()
                execErr = err
            }
        }

        // Parse the request
        requestText, ok := req.Request["message"].(string)
        if !ok {
            result = "Invalid request format: missing 'message' field"
            execErr = nil
        } else {
            // Handle dynamic functions
            log.Printf("Processing request text: %s", requestText)
            switch requestText {
            case "onboard":
                if execErr == nil {
                    result, execErr = onboardAgent(req.Request)
                    log.Printf("Responding with onboard: %s", result)
                }
            case "delete-cluster":
                result, execErr = deleteClusterAgent(req.Request)
                log.Printf("Responding with delete: %s", result)
            case "get-namespaces":
                result, execErr = getNamespacesAgent(req.Request)
                log.Printf("Responding with get-namespaces: %s", result)
            case "get-pods":
                result, execErr = getPodsAgent(req.Request)
                log.Printf("Responding with get-pods: %s", result)
            case "get-deployments":
                result, execErr = getDeploymentsAgent(req.Request)
                log.Printf("Responding with get-deployments: %s", result)
            case "get-services":
                result, execErr = getServicesAgent(req.Request)
                log.Printf("Responding with get-services: %s", result)
            case "get-nodes":
                result, execErr = getNodesAgent(req.Request)
                log.Printf("Responding with get-nodes: %s", result)
            case "get-cluster-resources":
                result, execErr = getClusterResourcesAgent(req.Request)
                log.Printf("Responding with get-cluster-resources: %s", result)
            case "get-pod-logs":
                result, execErr = getPodLogsAgent(req.Request)
                log.Printf("Responding with get-pod-logs: %s", result)
            default:
                result = "Unknown command."
                execErr = nil
                log.Printf("Responding with unknown command: %s", result)
            }
        }

        resp := ResponseMessage{
            RequestID: req.RequestID,
            Result:    result,
        }
        if execErr != nil {
            resp.Error = execErr.Error()
        }

        respBytes, err := json.Marshal(resp)
        if err != nil {
            log.Println("JSON marshal error:", err)
            continue
        }

        err = conn.WriteMessage(websocket.TextMessage, respBytes)
        if err != nil {
            log.Println("Write error:", err)
            break
        }
        // Send close frame
        conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
        break
    }
}

func main() {
    // Load environment variables from .env file
    if err := godotenv.Load(); err != nil {
        log.Println("Warning: Could not load .env file:", err)
    }
    
    // Validate required environment variables
    agentID := os.Getenv("AGENT_ID")
    if agentID == "" {
        log.Fatal("AGENT_ID environment variable is required")
    }
    
    apiKey := os.Getenv("API_KEY")
    if apiKey == "" {
        log.Fatal("API_KEY environment variable is required")
    }
    
    backendURL := os.Getenv("BACKEND_URL")
    if backendURL == "" {
        log.Fatal("BACKEND_URL environment variable is required")
    }
    
    log.Printf("Agent initialized with ID: %s", agentID)
    log.Printf("Backend URL: %s", backendURL)
    
    // Start the WebSocket server for incoming connections
    go func() {
        http.HandleFunc("/ws", handleWebSocket)
        http.HandleFunc("/health", handleHealth)
        port := os.Getenv("PORT")
        if port == "" {
            port = "9000"
        }
        log.Println("---------------------------> WebSocket server with Agent started successfully on port", port, "<-------------------------------")
        err := http.ListenAndServe(":"+port, nil)
        if err != nil {
            log.Fatal("ListenAndServe:", err)
        }
    }()
    
    // Wait a moment for server to start
    time.Sleep(2 * time.Second)
    
    // Automatically connect to backend and send onboarding request
    log.Println("Initiating automatic onboarding...")
    go func() {
        time.Sleep(1 * time.Second) // Give server time to start
        connectToBackendAndOnboard()
    }()
    
    // Send onboarding request via HTTP API as well
    log.Println("Sending onboarding request via HTTP API...")
    go func() {
        time.Sleep(3 * time.Second) // Wait a bit for WebSocket attempt
        err := callOnboardingAPI(map[string]interface{}{
            "cluster_name": os.Getenv("CLUSTER_NAME"),
            "message": "onboard",
        })
        if err != nil {
            log.Printf("Error calling onboarding API: %v", err)
        } else {
            log.Println("Onboarding API call successful")
        }
    }()
    
    // Keep the agent running
    select {}
}
