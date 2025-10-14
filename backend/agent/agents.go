package main

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

// onboardAgent handles the onboarding of a Kubernetes cluster.
func onboardAgent(event map[string]interface{}) (string, error) {
	clusterName, ok := event["cluster_name"].(string)
	if !ok {
		return "Invalid cluster_name", nil
	}
	serverURL, ok := event["server_url"].(string)
	if !ok {
		return "Invalid server_url", nil
	}
	token, ok := event["token"].(string)
	if !ok {
		return "Invalid token", nil
	}
	contextName, ok := event["context_name"].(string)
	if !ok {
		return "Invalid context_name", nil
	}
	useSecureTLS, ok := event["use_secure_tls"].(bool)
	if !ok {
		return "Invalid use_secure_tls", nil
	}

	// Create kubeconfig content
	kubeconfig := `apiVersion: v1
clusters:
- cluster:
    server: ` + serverURL
	if useSecureTLS {
		caData, ok := event["ca_data"].(string)
		if !ok {
			return "Invalid ca_data", nil
		}
		kubeconfig += `
    certificate-authority-data: ` + caData
	} else {
		kubeconfig += `
    insecure-skip-tls-verify: true`
	}
	kubeconfig += `
  name: ` + clusterName + `
contexts:
- context:
    cluster: ` + clusterName + `
    user: ` + clusterName + `-user
  name: ` + contextName + `
current-context: ` + contextName + `
kind: Config
preferences: {}
users:
- name: ` + clusterName + `-user
  user:
    token: ` + token + `
`

	// Write kubeconfig to file
	filename := "/tmp/" + clusterName + ".kubeconfig"
	err := os.WriteFile(filename, []byte(kubeconfig), 0644)
	if err != nil {
		return "Failed to create kubeconfig file: " + err.Error(), err
	}

	return "Cluster onboarded successfully, kubeconfig created at " + filename, nil
}

// deleteClusterAgent handles the deletion of a Kubernetes cluster by removing its kubeconfig file.
func deleteClusterAgent(event map[string]interface{}) (string, error) {
	clusterName, ok := event["cluster_name"].(string)
	if !ok {
		return "Invalid cluster_name", nil
	}

	// Remove kubeconfig file
	filename := "/tmp/" + clusterName + ".kubeconfig"
	err := os.Remove(filename)
	if err != nil {
		if os.IsNotExist(err) {
			return "Kubeconfig file not found, assuming already deleted", nil
		}
		return "Failed to remove kubeconfig file: " + err.Error(), err
	}
	return "Cluster deleted successfully, kubeconfig removed at " + filename, nil
}

// NamespaceInfo represents detailed information about a Kubernetes namespace
type NamespaceInfo struct {
	Name        string            `json:"name"`
	Status      string            `json:"status"`
	CreatedAt   string            `json:"createdAt,omitempty"`
	Labels      map[string]string `json:"labels,omitempty"`
	Annotations map[string]string `json:"annotations,omitempty"`
}

// getNamespacesAgent retrieves the list of namespaces from a Kubernetes cluster using either in-cluster configuration or external server URL and token.
func getNamespacesAgent(event map[string]interface{}) (string, error) {
	// Check if detailed information is requested
	includeDetails, _ := event["include_details"].(bool)

	// First, try to get server URL and token from event (external cluster)
	serverURL, hasServerURL := event["server_url"].(string)
	token, hasToken := event["token"].(string)

	var config *rest.Config
	var err error
	var configType string

	if hasServerURL && hasToken {
		// Use external cluster configuration
		configType = "external"
		useSecureTLS, ok := event["use_secure_tls"].(bool)
		if !ok {
			useSecureTLS = false
		}

		config = &rest.Config{
			Host:        serverURL,
			BearerToken: token,
		}

		if useSecureTLS {
			caData, ok := event["ca_data"].(string)
			if ok && caData != "" {
				config.CAData = []byte(caData)
			}
			tlsCert, ok := event["tls_cert"].(string)
			tlsKey, ok2 := event["tls_key"].(string)
			if ok && ok2 && tlsCert != "" && tlsKey != "" {
				config.CertData = []byte(tlsCert)
				config.KeyData = []byte(tlsKey)
			}
		} else {
			config.Insecure = true
		}
	} else {
		// Try in-cluster configuration
		configType = "in-cluster"
		config, err = rest.InClusterConfig()
		if err != nil {
			return createErrorResponse("Agent is not running in-cluster and no external cluster configuration provided"), nil
		}
	}

	// Create Kubernetes clientset
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return createErrorResponse("Failed to create Kubernetes client: " + err.Error()), err
	}

	// Get namespaces with details
	namespacesInfo, err := getNamespacesWithDetails(clientset, includeDetails)
	if err != nil {
		return createErrorResponse(err.Error()), err
	}

	// Create response with metadata
	result := map[string]interface{}{
		"namespaces":  namespacesInfo,
		"total_count": len(namespacesInfo),
		"cluster_info": map[string]interface{}{
			"config_type":     configType,
			"agent_id":        os.Getenv("AGENT_ID"),
			"cluster_name":    os.Getenv("CLUSTER_NAME"),
			"include_details": includeDetails,
		},
		"timestamp": fmt.Sprintf("%d", time.Now().Unix()),
	}

	resultBytes, err := json.Marshal(result)
	if err != nil {
		return createErrorResponse("Failed to marshal namespace result: " + err.Error()), err
	}

	return string(resultBytes), nil
}

// isSystemAnnotation checks if an annotation is a system-managed annotation
func isSystemAnnotation(key string) bool {
	systemPrefixes := []string{
		"kubectl.kubernetes.io/",
		"kubernetes.io/",
		"k8s.io/",
		"control-plane.alpha.kubernetes.io/",
		"node.alpha.kubernetes.io/",
	}

	for _, prefix := range systemPrefixes {
		if strings.HasPrefix(key, prefix) {
			return true
		}
	}
	return false
}

// getConfigType returns the configuration type used for the cluster connection
func getConfigType(isExternal bool) string {
	if isExternal {
		return "external"
	}
	return "in-cluster"
}

// createErrorResponse creates a standardized error response
func createErrorResponse(message string) string {
	errorResult := map[string]interface{}{
		"error":       true,
		"message":     message,
		"namespaces":  []interface{}{},
		"total_count": 0,
	}
	resultBytes, _ := json.Marshal(errorResult)
	return string(resultBytes)
}

// getNamespaceDetails fetches additional details for a namespace including resource usage
func getNamespaceDetails(clientset *kubernetes.Clientset, namespace string) map[string]interface{} {
	details := make(map[string]interface{})

	// Get resource quotas
	quotas, err := clientset.CoreV1().ResourceQuotas(namespace).List(context.TODO(), metav1.ListOptions{})
	if err == nil && len(quotas.Items) > 0 {
		quotaInfo := make([]map[string]interface{}, 0)
		for _, quota := range quotas.Items {
			quotaInfo = append(quotaInfo, map[string]interface{}{
				"name": quota.Name,
				"hard": quota.Status.Hard,
				"used": quota.Status.Used,
			})
		}
		details["resource_quotas"] = quotaInfo
	}

	// Get pod count
	pods, err := clientset.CoreV1().Pods(namespace).List(context.TODO(), metav1.ListOptions{})
	if err == nil {
		details["pod_count"] = len(pods.Items)

		// Count pods by phase
		phaseCount := make(map[string]int)
		for _, pod := range pods.Items {
			phase := string(pod.Status.Phase)
			phaseCount[phase]++
		}
		details["pod_phases"] = phaseCount
	}

	// Get service count
	services, err := clientset.CoreV1().Services(namespace).List(context.TODO(), metav1.ListOptions{})
	if err == nil {
		details["service_count"] = len(services.Items)
	}

	return details
}

// getNamespacesWithDetails retrieves namespaces with additional resource information
func getNamespacesWithDetails(clientset *kubernetes.Clientset, includeDetails bool) ([]NamespaceInfo, error) {
	namespaceList, err := clientset.CoreV1().Namespaces().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list namespaces: %v", err)
	}

	var namespacesInfo []NamespaceInfo
	for _, ns := range namespaceList.Items {
		nsInfo := NamespaceInfo{
			Name:   ns.Name,
			Status: string(ns.Status.Phase),
		}

		// Add creation timestamp if available
		if !ns.CreationTimestamp.IsZero() {
			nsInfo.CreatedAt = ns.CreationTimestamp.Format("2006-01-02T15:04:05Z")
		}

		// Add labels if present
		if len(ns.Labels) > 0 {
			nsInfo.Labels = ns.Labels
		}

		// Add annotations if present (filter out system annotations for cleaner output)
		if len(ns.Annotations) > 0 {
			nsInfo.Annotations = make(map[string]string)
			for k, v := range ns.Annotations {
				// Include only user-defined annotations, skip system ones
				if !isSystemAnnotation(k) {
					nsInfo.Annotations[k] = v
				}
			}
			// If no user annotations, set to nil for cleaner JSON
			if len(nsInfo.Annotations) == 0 {
				nsInfo.Annotations = nil
			}
		}

		namespacesInfo = append(namespacesInfo, nsInfo)
	}

	return namespacesInfo, nil
}

// getClusterInfoFromInCluster retrieves cluster information using in-cluster configuration
func getClusterInfoFromInCluster() (map[string]interface{}, error) {
	// Create in-cluster config
	config, err := rest.InClusterConfig()
	if err != nil {
		// Fallback for development - try to get basic info
		return map[string]interface{}{
			"node_count":         1,
			"kubernetes_version": "unknown",
			"namespace_count":    1,
			"cluster_type":       "development",
		}, nil
	}

	// Create clientset
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create clientset: %v", err)
	}

	// Get cluster info
	clusterInfo := make(map[string]interface{})

	// Get node count
	nodes, err := clientset.CoreV1().Nodes().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		clusterInfo["node_count"] = 0
	} else {
		clusterInfo["node_count"] = len(nodes.Items)
	}

	// Get Kubernetes version
	version, err := clientset.Discovery().ServerVersion()
	if err != nil {
		clusterInfo["kubernetes_version"] = "unknown"
	} else {
		clusterInfo["kubernetes_version"] = version.GitVersion
	}

	// Get namespace count
	namespaces, err := clientset.CoreV1().Namespaces().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		clusterInfo["namespace_count"] = 0
	} else {
		clusterInfo["namespace_count"] = len(namespaces.Items)
	}

	// Add cluster type
	clusterInfo["cluster_type"] = "kubernetes"
	clusterInfo["agent_mode"] = "in-cluster"

	return clusterInfo, nil
}

// callOnboardingAPI calls the onboarding API with the provided event data
func callOnboardingAPI(event map[string]interface{}) error {
	// Get cluster name from environment or event
	clusterName := os.Getenv("CLUSTER_NAME")
	if clusterName == "" {
		if cn, ok := event["cluster_name"].(string); ok {
			clusterName = cn
		} else {
			clusterName = "default-cluster"
		}
	}

	// Get required environment variables
	agentID := os.Getenv("AGENT_ID")
	if agentID == "" {
		return fmt.Errorf("AGENT_ID environment variable not set")
	}
	apiKey := os.Getenv("API_KEY")
	if apiKey == "" {
		return fmt.Errorf("API_KEY environment variable not set")
	}
	backendURL := os.Getenv("BACKEND_URL")
	if backendURL == "" {
		return fmt.Errorf("BACKEND_URL environment variable not set")
	} // Get cluster information using in-cluster config
	clusterInfo, err := getClusterInfoFromInCluster()
	if err != nil {
		return fmt.Errorf("failed to get cluster info: %v", err)
	}

	// Prepare the request body with cluster metadata (no server_url or token needed)
	requestBody := map[string]interface{}{
		"cluster_name":   clusterName,
		"context_name":   clusterName + "-context",
		"provider_name":  "kubernetes",
		"use_secure_tls": true,
		"metadata": map[string]interface{}{
			"agent_id":           agentID,
			"agent_version":      "1.0.0",
			"node_count":         clusterInfo["node_count"],
			"kubernetes_version": clusterInfo["kubernetes_version"],
			"provider":           "kubernetes",
			"namespace_count":    clusterInfo["namespace_count"],
			"cluster_info":       clusterInfo,
		},
	}

	// Override with event data if provided (only for optional fields)
	if contextName, ok := event["context_name"].(string); ok {
		requestBody["context_name"] = contextName
	}
	if providerName, ok := event["provider_name"].(string); ok {
		requestBody["provider_name"] = providerName
	}
	if tags, ok := event["tags"].([]interface{}); ok {
		requestBody["tags"] = tags
	}

	// Convert to JSON
	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return fmt.Errorf("failed to marshal request body: %v", err)
	}

	// Make HTTP POST request to onboarding API
	url := backendURL
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create HTTP request: %v", err)
	}

	// Set headers
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("agent_id", agentID)
	req.Header.Set("X-API-Key", apiKey)

	// Create HTTP client with appropriate TLS config
	skipTLSVerify := os.Getenv("SKIP_TLS_VERIFY") == "true"
	client := &http.Client{
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: skipTLSVerify,
				MinVersion:         tls.VersionTLS12,
			},
		},
	}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send HTTP request: %v", err)
	}
	defer resp.Body.Close()

	// Check response status
	if resp.StatusCode != http.StatusCreated {
		return fmt.Errorf("onboarding API returned status %d", resp.StatusCode)
	}

	fmt.Printf("Onboarding API called successfully for cluster %s\n", clusterName)
	return nil
}
