package main

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"net/http"
	"os"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	v1 "k8s.io/api/core/v1"
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

// getPodsAgent retrieves pods from a namespace with detailed information
func getPodsAgent(event map[string]interface{}) (string, error) {
	namespace, ok := event["namespace"].(string)
	if !ok {
		namespace = "default"
	}

	// Try in-cluster config
	config, err := rest.InClusterConfig()
	if err != nil {
		return "Not running in-cluster", nil
	}
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return "Failed to create k8s client: " + err.Error(), err
	}

	pods, err := clientset.CoreV1().Pods(namespace).List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return "Failed to list pods: " + err.Error(), err
	}

	var podList []map[string]interface{}
	for _, pod := range pods.Items {
		podInfo := map[string]interface{}{
			"name":      pod.Name,
			"namespace": pod.Namespace,
			"status":    string(pod.Status.Phase),
			"node":      pod.Spec.NodeName,
			"restarts":  int32(0),
			"age":       pod.CreationTimestamp.Time,
			"containers": []map[string]interface{}{},
		}

		// Get container information
		for _, container := range pod.Spec.Containers {
			containerInfo := map[string]interface{}{
				"name":  container.Name,
				"image": container.Image,
				"ready": false,
			}
			podInfo["containers"] = append(podInfo["containers"].([]map[string]interface{}), containerInfo)
		}

		// Get container statuses
		if pod.Status.ContainerStatuses != nil {
			for i, containerStatus := range pod.Status.ContainerStatuses {
				if i < len(podInfo["containers"].([]map[string]interface{})) {
					containers := podInfo["containers"].([]map[string]interface{})
					containers[i]["ready"] = containerStatus.Ready
					containers[i]["restart_count"] = containerStatus.RestartCount
					podInfo["restarts"] = podInfo["restarts"].(int32) + containerStatus.RestartCount
				}
			}
		}

		podList = append(podList, podInfo)
	}

	result := map[string]interface{}{
		"namespace": namespace,
		"pods":      podList,
		"count":     len(podList),
	}
	resultBytes, _ := json.Marshal(result)
	return string(resultBytes), nil
}

// getDeploymentsAgent retrieves deployments from a namespace
func getDeploymentsAgent(event map[string]interface{}) (string, error) {
	namespace, ok := event["namespace"].(string)
	if !ok {
		namespace = "default"
	}

	config, err := rest.InClusterConfig()
	if err != nil {
		return "Not running in-cluster", nil
	}
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return "Failed to create k8s client: " + err.Error(), err
	}

	deployments, err := clientset.AppsV1().Deployments(namespace).List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return "Failed to list deployments: " + err.Error(), err
	}

	var deploymentList []map[string]interface{}
	for _, deployment := range deployments.Items {
		deploymentInfo := map[string]interface{}{
			"name":       deployment.Name,
			"namespace":  deployment.Namespace,
			"replicas":   deployment.Spec.Replicas,
			"ready":      deployment.Status.ReadyReplicas,
			"available":  deployment.Status.AvailableReplicas,
			"updated":    deployment.Status.UpdatedReplicas,
			"age":        deployment.CreationTimestamp.Time,
			"containers": []string{},
		}

		// Get container images
		for _, container := range deployment.Spec.Template.Spec.Containers {
			deploymentInfo["containers"] = append(deploymentInfo["containers"].([]string), container.Image)
		}

		deploymentList = append(deploymentList, deploymentInfo)
	}

	result := map[string]interface{}{
		"namespace":   namespace,
		"deployments": deploymentList,
		"count":       len(deploymentList),
	}
	resultBytes, _ := json.Marshal(result)
	return string(resultBytes), nil
}

// getServicesAgent retrieves services from a namespace
func getServicesAgent(event map[string]interface{}) (string, error) {
	namespace, ok := event["namespace"].(string)
	if !ok {
		namespace = "default"
	}

	config, err := rest.InClusterConfig()
	if err != nil {
		return "Not running in-cluster", nil
	}
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return "Failed to create k8s client: " + err.Error(), err
	}

	services, err := clientset.CoreV1().Services(namespace).List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return "Failed to list services: " + err.Error(), err
	}

	var serviceList []map[string]interface{}
	for _, service := range services.Items {
		serviceInfo := map[string]interface{}{
			"name":         service.Name,
			"namespace":    service.Namespace,
			"type":         string(service.Spec.Type),
			"cluster_ip":   service.Spec.ClusterIP,
			"external_ip":  service.Status.LoadBalancer.Ingress,
			"ports":        []map[string]interface{}{},
			"age":          service.CreationTimestamp.Time,
			"selector":     service.Spec.Selector,
		}

		// Get port information
		for _, port := range service.Spec.Ports {
			portInfo := map[string]interface{}{
				"name":        port.Name,
				"port":        port.Port,
				"target_port": port.TargetPort.String(),
				"protocol":    string(port.Protocol),
			}
			serviceInfo["ports"] = append(serviceInfo["ports"].([]map[string]interface{}), portInfo)
		}

		serviceList = append(serviceList, serviceInfo)
	}

	result := map[string]interface{}{
		"namespace": namespace,
		"services":  serviceList,
		"count":     len(serviceList),
	}
	resultBytes, _ := json.Marshal(result)
	return string(resultBytes), nil
}

// getNodesAgent retrieves node information
func getNodesAgent(event map[string]interface{}) (string, error) {
	config, err := rest.InClusterConfig()
	if err != nil {
		return "Not running in-cluster", nil
	}
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return "Failed to create k8s client: " + err.Error(), err
	}

	nodes, err := clientset.CoreV1().Nodes().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return "Failed to list nodes: " + err.Error(), err
	}

	var nodeList []map[string]interface{}
	for _, node := range nodes.Items {
		nodeInfo := map[string]interface{}{
			"name":                node.Name,
			"status":              "Unknown",
			"roles":               []string{},
			"age":                 node.CreationTimestamp.Time,
			"version":             node.Status.NodeInfo.KubeletVersion,
			"internal_ip":         "",
			"external_ip":         "",
			"os":                  node.Status.NodeInfo.OSImage,
			"kernel":              node.Status.NodeInfo.KernelVersion,
			"container_runtime":   node.Status.NodeInfo.ContainerRuntimeVersion,
		}

		// Get node status
		for _, condition := range node.Status.Conditions {
			if condition.Type == "Ready" {
				if condition.Status == "True" {
					nodeInfo["status"] = "Ready"
				} else {
					nodeInfo["status"] = "NotReady"
				}
				break
			}
		}

		// Get node roles from labels
		if node.Labels != nil {
			for label := range node.Labels {
				if label == "node-role.kubernetes.io/master" || label == "node-role.kubernetes.io/control-plane" {
					nodeInfo["roles"] = append(nodeInfo["roles"].([]string), "control-plane")
				} else if label == "node-role.kubernetes.io/worker" {
					nodeInfo["roles"] = append(nodeInfo["roles"].([]string), "worker")
				}
			}
		}

		// Get IP addresses
		for _, address := range node.Status.Addresses {
			if address.Type == "InternalIP" {
				nodeInfo["internal_ip"] = address.Address
			} else if address.Type == "ExternalIP" {
				nodeInfo["external_ip"] = address.Address
			}
		}

		nodeList = append(nodeList, nodeInfo)
	}

	result := map[string]interface{}{
		"nodes": nodeList,
		"count": len(nodeList),
	}
	resultBytes, _ := json.Marshal(result)
	return string(resultBytes), nil
}

// getClusterResourcesAgent retrieves overall cluster resource information
func getClusterResourcesAgent(event map[string]interface{}) (string, error) {
	config, err := rest.InClusterConfig()
	if err != nil {
		return "Not running in-cluster", nil
	}
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return "Failed to create k8s client: " + err.Error(), err
	}

	// Get nodes for resource calculation
	nodes, err := clientset.CoreV1().Nodes().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return "Failed to list nodes: " + err.Error(), err
	}

	// Get namespaces
	namespaces, err := clientset.CoreV1().Namespaces().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return "Failed to list namespaces: " + err.Error(), err
	}

	// Get all pods for counting
	pods, err := clientset.CoreV1().Pods("").List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return "Failed to list pods: " + err.Error(), err
	}

	// Get deployments
	deployments, err := clientset.AppsV1().Deployments("").List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return "Failed to list deployments: " + err.Error(), err
	}

	// Get services
	services, err := clientset.CoreV1().Services("").List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return "Failed to list services: " + err.Error(), err
	}

	result := map[string]interface{}{
		"cluster_summary": map[string]interface{}{
			"nodes":       len(nodes.Items),
			"namespaces":  len(namespaces.Items),
			"pods":        len(pods.Items),
			"deployments": len(deployments.Items),
			"services":    len(services.Items),
		},
		"nodes_status": map[string]int{
			"ready":     0,
			"not_ready": 0,
		},
		"pods_status": map[string]int{
			"running":   0,
			"pending":   0,
			"failed":    0,
			"succeeded": 0,
		},
	}

	// Count node statuses
	for _, node := range nodes.Items {
		for _, condition := range node.Status.Conditions {
			if condition.Type == "Ready" {
				if condition.Status == "True" {
					result["nodes_status"].(map[string]int)["ready"]++
				} else {
					result["nodes_status"].(map[string]int)["not_ready"]++
				}
				break
			}
		}
	}

	// Count pod statuses
	for _, pod := range pods.Items {
		switch pod.Status.Phase {
		case "Running":
			result["pods_status"].(map[string]int)["running"]++
		case "Pending":
			result["pods_status"].(map[string]int)["pending"]++
		case "Failed":
			result["pods_status"].(map[string]int)["failed"]++
		case "Succeeded":
			result["pods_status"].(map[string]int)["succeeded"]++
		}
	}

	resultBytes, _ := json.Marshal(result)
	return string(resultBytes), nil
}

// getPodLogsAgent retrieves logs from a specific pod
func getPodLogsAgent(event map[string]interface{}) (string, error) {
	namespace, ok := event["namespace"].(string)
	if !ok {
		namespace = "default"
	}
	
	podName, ok := event["pod_name"].(string)
	if !ok {
		return "pod_name is required", nil
	}

	containerName, _ := event["container_name"].(string)
	tailLines := int64(100)
	if lines, ok := event["tail_lines"].(float64); ok {
		tailLines = int64(lines)
	}

	config, err := rest.InClusterConfig()
	if err != nil {
		return "Not running in-cluster", nil
	}
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return "Failed to create k8s client: " + err.Error(), err
	}

	// Get pod logs
	podLogOptions := &v1.PodLogOptions{
		TailLines: &tailLines,
	}
	if containerName != "" {
		podLogOptions.Container = containerName
	}

	req := clientset.CoreV1().Pods(namespace).GetLogs(podName, podLogOptions)
	logs, err := req.Stream(context.TODO())
	if err != nil {
		return "Failed to get pod logs: " + err.Error(), err
	}
	defer logs.Close()

	// Read logs
	buf := new(bytes.Buffer)
	_, err = buf.ReadFrom(logs)
	if err != nil {
		return "Failed to read logs: " + err.Error(), err
	}

	result := map[string]interface{}{
		"namespace":      namespace,
		"pod_name":       podName,
		"container_name": containerName,
		"logs":           buf.String(),
		"tail_lines":     tailLines,
	}
	resultBytes, _ := json.Marshal(result)
	return string(resultBytes), nil
}
	serverURL, ok := event["server_url"].(string)
	if !ok {
		// Try in-cluster config
		config, err := rest.InClusterConfig()
		if err != nil {
			return "Invalid server_url and not running in-cluster", nil
		}
		clientset, err := kubernetes.NewForConfig(config)
		if err != nil {
			return "Failed to create in-cluster k8s client: " + err.Error(), err
		}
		namespaces, err := clientset.CoreV1().Namespaces().List(context.TODO(), metav1.ListOptions{})
		if err != nil {
			return "Failed to list namespaces in-cluster: " + err.Error(), err
		}
		var nsList []string
		for _, ns := range namespaces.Items {
			nsList = append(nsList, ns.Name)
		}
		result := map[string]interface{}{
			"namespaces": nsList,
		}
		resultBytes, _ := json.Marshal(result)
		return string(resultBytes), nil
	}

	token, ok := event["token"].(string)
	if !ok {
		return "Invalid token", nil
	}
	useSecureTLS, ok := event["use_secure_tls"].(bool)
	if !ok {
		useSecureTLS = false
	}

	// Create config
	config := &rest.Config{
		Host:        serverURL,
		BearerToken: token,
	}
	if useSecureTLS {
		caData, ok := event["ca_data"].(string)
		if ok {
			config.CAData = []byte(caData)
		}
		tlsCert, ok := event["tls_cert"].(string)
		tlsKey, ok2 := event["tls_key"].(string)
		if ok && ok2 {
			config.CertData = []byte(tlsCert)
			config.KeyData = []byte(tlsKey)
		}
	} else {
		config.Insecure = true
	}

	// Create client
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return "Failed to create k8s client: " + err.Error(), err
	}

	// List namespaces
	namespaces, err := clientset.CoreV1().Namespaces().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return "Failed to list namespaces: " + err.Error(), err
	}

	var nsList []string
	for _, ns := range namespaces.Items {
		nsList = append(nsList, ns.Name)
	}

	result := map[string]interface{}{
		"namespaces": nsList,
	}
	resultBytes, err := json.Marshal(result)
	if err != nil {
		return "Failed to marshal result", err
	}
	return string(resultBytes), nil
}

// getClusterInfoFromInCluster retrieves cluster information using in-cluster configuration
func getClusterInfoFromInCluster() (map[string]interface{}, error) {
	// Create in-cluster config
	config, err := rest.InClusterConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to get in-cluster config - agent must run inside Kubernetes cluster: %v", err)
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
		backendURL = "https://10.0.32.122:8006/onboard"
	}
	
	// Get cluster information using in-cluster config
	clusterInfo, err := getClusterInfoFromInCluster()
	if err != nil {
		return fmt.Errorf("failed to get cluster info: %v", err)
	}

	// Prepare the request body with cluster metadata (no server_url or token needed)
	requestBody := map[string]interface{}{
		"cluster_name":  clusterName,
		"context_name":  clusterName + "-context",
		"provider_name": "kubernetes",
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
