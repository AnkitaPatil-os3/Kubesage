import React, { useState, useEffect } from 'react';
import { motion } from "framer-motion";
import { Icon } from "@iconify/react";
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Textarea,
  Chip,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Spinner,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  useDisclosure,
  Divider,
  Input,
  Select,
  SelectItem,
  Code,
  ScrollShadow
} from "@heroui/react";

import { addToast } from "../components/toast-manager";

interface ClusterConfig {
  id: number;
  cluster_name: string;
  server_url: string;
  provider_name?: string;
  tags?: string[];
  use_secure_tls: boolean;
  ca_data?: string;
  tls_key?: string;
  tls_cert?: string;
  user_id: number;
  is_operator_installed: boolean;
  created_at: string;
  updated_at: string;
}

interface OnboardClusterRequest {
  cluster_name: string;
  server_url: string;
  token: string;
  provider_name?: string;
  tags?: string[];
  use_secure_tls: boolean;
  ca_data?: string;
  tls_key?: string;
  tls_cert?: string;
}

const UploadKubeconfig: React.FC = () => {
  // State
  const [clusters, setClusters] = useState<ClusterConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [onboarding, setOnboarding] = useState(false);
  const [removing, setRemoving] = useState<number | null>(null);
  
  // Modal states
  const { isOpen: isOnboardOpen, onOpen: onOnboardOpen, onClose: onOnboardClose } = useDisclosure();
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const [clusterToDelete, setClusterToDelete] = useState<ClusterConfig | null>(null);

  const [formData, setFormData] = useState<OnboardClusterRequest>({
    cluster_name: '',
    server_url: '',
    token: '',
    provider_name: 'AWS EKS',
    tags: [],
    use_secure_tls: false,
    ca_data: '',
    tls_key: '',
    tls_cert: ''
  });

  // Add these functions after the existing helper functions
const generateDynamicScript = () => {
  const clusterName = formData.cluster_name || "your-cluster";
  return `curl -O http://10.0.34.169/onboard.sh && bash onboard.sh "${clusterName}" --webhook-endpoint "https://10.0.32.106:8004/remediation/webhook/incidents""`;
};

const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    addToast({
      title: "Copied!",
      description: "Script copied to clipboard",
      color: "success"
    });
  }).catch(() => {
    addToast({
      title: "Copy Failed",
      description: "Failed to copy to clipboard",
      color: "danger"
    });
  });
};


  // Provider options
  const providers = [
    { value: 'AWS EKS', label: 'Amazon EKS' },
    { value: 'Google GKE', label: 'Google GKE' },
    { value: 'Azure AKS', label: 'Azure AKS' },
    { value: 'DigitalOcean', label: 'DigitalOcean' },
    { value: 'Minikube', label: 'Minikube' },
    { value: 'Kind', label: 'Kind' },
    { value: 'K3s', label: 'K3s' },
    { value: 'Other', label: 'Other' }
  ];

  // Helper function to get auth token
  const getAuthToken = () => {
    return localStorage.getItem("access_token") || "";
  };

  // Helper function to get auth headers
  const getAuthHeaders = () => ({
    'Authorization': `Bearer ${getAuthToken()}`,
    'Content-Type': 'application/json'
  });

  // Fetch clusters
  const fetchClusters = async () => {
    try {
      setLoading(true);
      const response = await fetch('/kubeconfig/clusters', {
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch clusters: ${response.statusText}`);
      }

      const data = await response.json();
      setClusters(data.clusters || []);
    } catch (error) {
      console.error('Error fetching clusters:', error);
      addToast({
        title: "Error",
        description: "Failed to fetch clusters",
        color: "danger"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleOnboardCluster = async () => {
    // Validation
    if (!formData.cluster_name.trim()) {
      addToast({
        title: "Validation Error",
        description: "Cluster name is required",
        color: "warning"
      });
      return;
    }

    if (!formData.server_url.trim()) {
      addToast({
        title: "Validation Error",
        description: "Server URL is required",
        color: "warning"
      });
      return;
    }

    if (!formData.token.trim()) {
      addToast({
        title: "Validation Error",
        description: "Authentication token is required",
        color: "warning"
      });
      return;
    }

    // Validate server URL format
    try {
      new URL(formData.server_url);
    } catch {
      addToast({
        title: "Validation Error",
        description: "Please enter a valid server URL",
        color: "warning"
      });
      return;
    }

    try {
      setOnboarding(true);
      const response = await fetch('/kubeconfig/onboard-cluster', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          cluster_name: formData.cluster_name.trim(),
          server_url: formData.server_url.trim(),
          token: formData.token.trim(),
          context_name: formData.cluster_name.trim(),
          provider_name: formData.provider_name,
          tags: formData.tags?.filter(tag => tag.trim().length > 0).join(',') || '',
          use_secure_tls: formData.use_secure_tls,
          ca_data: formData.use_secure_tls && formData.ca_data ? formData.ca_data : null,
          tls_key: formData.use_secure_tls && formData.tls_key ? formData.tls_key : null,
          tls_cert: formData.use_secure_tls && formData.tls_cert ? formData.tls_cert : null
        })
      });

      const data = await response.json();

      if (response.ok) {
        addToast({
          title: "Success",
          description: "Cluster onboarded successfully! You can now manage your Kubernetes cluster.",
          color: "success"
        });
        
        // Reset form
        setFormData({
          cluster_name: '',
          server_url: '',
          token: '',
          provider_name: 'AWS EKS',
          tags: [],
          use_secure_tls: false,
          ca_data: '',
          tls_key: '',
          tls_cert: ''
        });
        
        onOnboardClose();
        fetchClusters(); // Refresh the list
      } else {
        // Handle API error response
        console.error('API Error Response:', data);
        let errorMessage = 'Failed to onboard cluster';
        
        if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (Array.isArray(data.detail)) {
            errorMessage = data.detail.map(err => {
              if (typeof err === 'object' && err.msg) {
                return `${err.loc ? err.loc.join('.') + ': ' : ''}${err.msg}`;
              }
              return err.message || JSON.stringify(err);
            }).join(', ');
          } else {
            errorMessage = JSON.stringify(data.detail);
          }
        } else if (data.message) {
          errorMessage = data.message;
        }
        
        addToast({
          title: "Error",
          description: errorMessage,
          color: "danger"
        });
      }
    } catch (error) {
      console.error('Error onboarding cluster:', error);
      addToast({
        title: "Error",
        description: error instanceof Error ? error.message : "Network error occurred",
        color: "danger"
      });
    } finally {
      setOnboarding(false);
    }
  };

  // Remove cluster
  const handleRemoveCluster = async (cluster: ClusterConfig) => {
    try {
      setRemoving(cluster.id);
      const response = await fetch(`/kubeconfig/remove-cluster/${cluster.id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      const data = await response.json();

      if (response.ok) {
        addToast({
          title: "Success",
          description: data.message || "Cluster removed successfully",
          color: "success"
        });
        fetchClusters(); // Refresh the list
      } else {
        throw new Error(data.detail || 'Failed to remove cluster');
      }
    } catch (error) {
      console.error('Error removing cluster:', error);
      addToast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to remove cluster",
        color: "danger"
      });
    } finally {
      setRemoving(null);
      onDeleteClose();
      setClusterToDelete(null);
    }
  };

  // Handle delete confirmation
  const confirmDelete = (cluster: ClusterConfig) => {
    setClusterToDelete(cluster);
    onDeleteOpen();
  };

  // Handle form input changes
  const handleInputChange = (field: keyof OnboardClusterRequest, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Handle tags input
  const handleTagsChange = (value: string) => {
    const tags = value.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
    handleInputChange('tags', tags);
  };

  // Handle modal close with form reset
  const handleModalClose = () => {
    setFormData({
      cluster_name: '',
      server_url: '',
      token: '',
      provider_name: 'AWS EKS',
      tags: [],
      use_secure_tls: false,
      ca_data: '',
      tls_key: '',
      tls_cert: ''
    });
    onOnboardClose();
  };

  // Load clusters on component mount
  useEffect(() => {
    fetchClusters();
  }, []);

  // Get provider icon
  const getProviderIcon = (provider?: string) => {
    if (!provider) return "lucide:server";
    
    const providerLower = provider.toLowerCase();
    if (providerLower.includes('aws') || providerLower.includes('eks')) return "logos:aws";
    if (providerLower.includes('google') || providerLower.includes('gke')) return "logos:google-cloud";
    if (providerLower.includes('azure') || providerLower.includes('aks')) return "logos:microsoft-azure";
    if (providerLower.includes('digitalocean')) return "logos:digitalocean";
    if (providerLower.includes('minikube')) return "logos:kubernetes";
    if (providerLower.includes('kind')) return "logos:kubernetes";
    if (providerLower.includes('k3s')) return "logos:rancher";
    return "lucide:server";
  };

  // Format date
  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid Date';
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="p-6 max-w-7xl mx-auto space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Cluster Management</h1>
          <p className="text-foreground-600 mt-1">
            Manage your Kubernetes clusters and their configurations
          </p>
        </div>
        <Button
          color="primary"
          startContent={<Icon icon="lucide:plus" />}
          onPress={onOnboardOpen}
          size="lg"
          className="w-full sm:w-auto"
        >
          Onboard Cluster
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardBody className="flex flex-row items-center gap-4">
              <div className="p-3 bg-primary/10 rounded-lg">
                <Icon icon="lucide:server" className="text-2xl text-primary" />
              </div>
              <div>
                <p className="text-small text-foreground-600">Total Clusters</p>
                <p className="text-2xl font-bold">{clusters.length}</p>
              </div>
            </CardBody>
          </Card>
        </motion.div>
        
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <CardBody className="flex flex-row items-center gap-4">
              <div className="p-3 bg-success/10 rounded-lg">
                <Icon icon="lucide:check-circle" className="text-2xl text-success" />
              </div>
              <div>
                <p className="text-small text-foreground-600">Managed Clusters</p>
                <p className="text-2xl font-bold">{clusters.length}</p>
              </div>
            </CardBody>
          </Card>
        </motion.div>
      </div>

      {/* Clusters Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <Card>
          <CardHeader className="flex items-center gap-3">
            <Icon icon="lucide:server" className="text-2xl text-primary" />
            <div>
              <h2 className="text-xl font-semibold">Onboarded Clusters</h2>
              <p className="text-small text-foreground-600">
                {clusters.length} cluster{clusters.length !== 1 ? 's' : ''} configured
              </p>
            </div>
          </CardHeader>
          <CardBody>
            {loading ? (
                            <div className="flex justify-center items-center py-12">
                            <div className="text-center">
                              <Spinner size="lg" />
                              <p className="text-foreground-600 mt-4">Loading clusters...</p>
                            </div>
                          </div>
                        ) : clusters.length === 0 ? (
                          <div className="text-center py-12">
                            <Icon icon="lucide:server-off" className="text-6xl text-foreground-300 mx-auto mb-4" />
                            <h3 className="text-lg font-semibold text-foreground-600 mb-2">No Clusters Found</h3>
                            <p className="text-foreground-500 mb-6 max-w-md mx-auto">
                              Get started by onboarding your first Kubernetes cluster to begin managing your infrastructure
                            </p>
                            <Button
                              color="primary"
                              startContent={<Icon icon="lucide:plus" />}
                              onPress={onOnboardOpen}
                              size="lg"
                            >
                              Onboard Your First Cluster
                            </Button>
                          </div>
                        ) : (
                          <div className="overflow-x-auto">
                            <Table aria-label="Clusters table" className="min-w-full">
                              <TableHeader>
                                <TableColumn>CLUSTER</TableColumn>
                                <TableColumn>PROVIDER</TableColumn>
                                {/* <TableColumn>TAGS</TableColumn> */}
                                <TableColumn>CREATED</TableColumn>
                                <TableColumn>ACTIONS</TableColumn>
                              </TableHeader>
                              <TableBody>
                                {clusters.map((cluster) => (
                                  <TableRow key={cluster.id}>
                                    <TableCell>
                                      <div className="flex items-center gap-3">
                                        <Icon 
                                          icon={getProviderIcon(cluster.provider_name)} 
                                          className="text-2xl flex-shrink-0" 
                                        />
                                        <div className="min-w-0">
                                          <p className="font-semibold truncate">{cluster.cluster_name}</p>
                                        </div>
                                      </div>
                                    </TableCell>
                                    <TableCell>
                                      <Chip
                                        variant="flat"
                                        color="default"
                                        size="sm"
                                      >
                                        {cluster.provider_name || 'Unknown'}
                                      </Chip>
                                    </TableCell>
                                    
                                    <TableCell>
                                      <p className="text-small">
                                        {formatDate(cluster.created_at)}
                                      </p>
                                    </TableCell>
                                    <TableCell>
                                      <div className="flex items-center gap-1">
                                        <Button
                                          isIconOnly
                                          size="sm"
                                          variant="light"
                                          color="danger"
                                          onPress={() => confirmDelete(cluster)}
                                          isLoading={removing === cluster.id}
                                          isDisabled={removing !== null}
                                          aria-label="Remove Cluster"
                                        >
                                          <Icon icon="lucide:trash-2" />
                                        </Button>
                                      </div>
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        )}
                      </CardBody>
                    </Card>
                  </motion.div>
            
                  {/* Onboard Cluster Modal */}
                  <Modal 
                    isOpen={isOnboardOpen} 
                    onClose={handleModalClose}
                    size="3xl"
                    scrollBehavior="inside"
                    isDismissable={!onboarding}
                    hideCloseButton={onboarding}
                  >
                    <ModalContent>
                      <ModalHeader className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <Icon icon="lucide:server-cog" className="text-primary" />
                          <span>Onboard New Cluster</span>
                        </div>
                        <p className="text-small text-foreground-500 font-normal">
                          Connect your Kubernetes cluster to KubeSage platform
                        </p>
                      </ModalHeader>
                      <ModalBody>
                        <div className="space-y-6">
                          {/* Basic Information */}
                          <div className="space-y-4">
                            <h3 className="text-lg font-semibold flex items-center gap-2">
                              <Icon icon="lucide:info" className="text-primary" />
                              Basic Information
                            </h3>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              <Input
                                label="Cluster Name"
                                placeholder="e.g., production-cluster"
                                value={formData.cluster_name}
                                onValueChange={(value) => handleInputChange('cluster_name', value)}
                                startContent={<Icon icon="lucide:tag" className="text-foreground-400" />}
                                isRequired
                                variant="bordered"
                                isDisabled={onboarding}
                              />
                              
                              <Select
                                label="Provider"
                                placeholder="Select provider"
                                selectedKeys={formData.provider_name ? [formData.provider_name] : []}
                                onSelectionChange={(keys) => {
                                  const selected = Array.from(keys)[0] as string;
                                  handleInputChange('provider_name', selected);
                                }}
                                variant="bordered"
                                isDisabled={onboarding}
                              >
                                {providers.map((provider) => (
                                  <SelectItem key={provider.value} value={provider.value}>
                                    {provider.label}
                                  </SelectItem>
                                ))}
                              </Select>
                            </div>
            
                            <Input
                              label="Tags"
                              placeholder="e.g., production, web, backend (optional)"
                              value={formData.tags?.join(', ') || ''}
                              onValueChange={handleTagsChange}
                              startContent={<Icon icon="lucide:tags" className="text-foreground-400" />}
                              description="Separate multiple tags with commas"
                              variant="bordered"
                              isDisabled={onboarding}
                            />
                          </div>
            
                          <Divider />
            
                          {/* Connection Details */}
                          <div className="space-y-4">
                            <h3 className="text-lg font-semibold flex items-center gap-2">
                              <Icon icon="lucide:link" className="text-primary" />
                              Connection Details
                            </h3>
            
                            {/* Dynamic Script Generation Section */}
                            <Card className="bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-950/30 dark:to-blue-950/30 border-l-4 border-indigo-500 dark:border-indigo-400">
                              <CardHeader className="pb-2">
                                <h4 className="font-semibold text-indigo-800 dark:text-indigo-200 flex items-center gap-2">
                                  <Icon icon="mdi:terminal" className="text-indigo-600 dark:text-indigo-400" />
                                  Auto-Generated Onboarding Script
                                </h4>
                              </CardHeader>
                              <CardBody className="pt-0">
                                <p className="text-indigo-700 dark:text-indigo-300 text-sm mb-3">
                                  Run this command on your Kubernetes cluster to automatically generate the required credentials:
                                </p>
                                <div className="bg-gray-900 dark:bg-gray-950 p-4 rounded-lg relative border dark:border-gray-800">
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="text-green-400 dark:text-green-300 text-sm font-mono">Terminal Command</span>
                                    <Button
                                      size="sm"
                                      variant="flat"
                                      color="success"
                                      onPress={() => copyToClipboard(generateDynamicScript())}
                                      startContent={<Icon icon="mdi:content-copy" />}
                                      className="text-xs bg-green-500/10 dark:bg-green-400/10 hover:bg-green-500/20 dark:hover:bg-green-400/20"
                                    >
                                      Copy
                                    </Button>
                                  </div>
                                  <ScrollShadow className="max-h-32">
                                    <Code 
                                      className="block text-green-400 dark:text-green-300 bg-transparent p-0 text-sm whitespace-pre-wrap break-all font-mono"
                                      style={{ wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}
                                    >
                                      {generateDynamicScript()}
                                    </Code>
                                  </ScrollShadow>
                                </div>
                                <div className="mt-3 p-3 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg border dark:border-indigo-800/50">
                                  <div className="flex items-start gap-2">
                                    <Icon icon="mdi:information" className="text-indigo-600 dark:text-indigo-400 mt-0.5 flex-shrink-0" />
                                    <div className="text-sm text-indigo-700 dark:text-indigo-300">
                                      <p className="font-medium mb-1">What this script does:</p>
                                      <ul className="space-y-1 text-xs">
                                        <li>• Downloads the onboarding script from the server</li>
                                        <li>• Creates a service account for cluster: <strong className="text-indigo-800 dark:text-indigo-200">{formData.cluster_name || "your-cluster"}</strong></li>
                                        <li>• Generates the required bearer token and server URL</li>
                                        <li>• Sends the credentials to the webhook endpoint</li>
                                      </ul>
                                    </div>
                                  </div>
                                </div>
                              </CardBody>
                            </Card>
            
                            <Divider className="my-4" />
            
                            <div className="text-center">
                              <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">Or manually enter your cluster credentials below:</p>
                            </div>
            
                            <Input
                              label="Server URL"
                              placeholder="https://your-cluster-api-server.com:6443"
                              value={formData.server_url}
                              onValueChange={(value) => handleInputChange('server_url', value)}
                              startContent={<Icon icon="lucide:server" className="text-foreground-400" />}
                              isRequired
                              variant="bordered"
                              isDisabled={onboarding}
                            />
            
                            <Textarea
                              label="Authentication Token"
                              placeholder="Enter your cluster authentication token"
                              value={formData.token}
                              onValueChange={(value) => handleInputChange('token', value)}
                              minRows={3}
                              maxRows={6}
                              isRequired
                              variant="bordered"
                              isDisabled={onboarding}
                              description="Service account token or other authentication token"
                            />
                          </div>
            
                          <Divider />
            
                          {/* TLS Configuration */}
                          <div className="space-y-4">
                            <div className="flex items-center justify-between">
                              <h3 className="text-lg font-semibold flex items-center gap-2">
                                <Icon icon="lucide:shield" className="text-primary" />
                                TLS Configuration
                              </h3>
                              <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={formData.use_secure_tls}
                                  onChange={(e) => handleInputChange('use_secure_tls', e.target.checked)}
                                  disabled={onboarding}
                                  className="w-4 h-4 text-primary bg-gray-100 border-gray-300 rounded focus:ring-primary focus:ring-2"
                                />
                                <span className="text-sm">Enable Secure TLS</span>
                              </label>
                            </div>
            
                            {formData.use_secure_tls && (
                              <div className="space-y-4 p-4 bg-default-50 rounded-lg border">
                                <div className="flex items-center gap-2 mb-2">
                                  <Icon icon="lucide:info" className="text-primary text-sm" />
                                  <p className="text-small text-foreground-600">
                                    Configure TLS certificates for secure cluster communication
                                  </p>
                                </div>
                                
                                <Textarea
                                  label="CA Certificate Data"
                                  placeholder="-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----"
                                  value={formData.ca_data}
                                  onValueChange={(value) => handleInputChange('ca_data', value)}
                                  minRows={4}
                                  maxRows={8}
                                  description="Base64 encoded CA certificate (optional)"
                                  variant="bordered"
                                  isDisabled={onboarding}
                                />
            
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                  <Textarea
                                    label="TLS Certificate"
                                    placeholder="-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----"
                                    value={formData.tls_cert}
                                    onValueChange={(value) => handleInputChange('tls_cert', value)}
                                    minRows={4}
                                    maxRows={8}
                                    description="Client certificate for mutual TLS (optional)"
                                    variant="bordered"
                                    isDisabled={onboarding}
                                  />
            
                                  <Textarea
                                    label="TLS Private Key"
                                    placeholder="-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----"
                                    value={formData.tls_key}
                                    onValueChange={(value) => handleInputChange('tls_key', value)}
                                    minRows={4}
                                    maxRows={8}
                                    description="Private key for client certificate (optional)"
                                    variant="bordered"
                                    isDisabled={onboarding}
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </ModalBody>
                      <ModalFooter>
                        <Button 
                          color="danger" 
                          variant="light" 
                          onPress={handleModalClose}
                          isDisabled={onboarding}
                        >
                          Cancel
                        </Button>
                        <Button 
                          color="primary" 
                          onPress={handleOnboardCluster}
                          isLoading={onboarding}
                          startContent={!onboarding ? <Icon icon="lucide:plus" /> : null}
                        >
                          {onboarding ? "Onboarding Cluster..." : "Onboard Cluster"}
                        </Button>
                      </ModalFooter>
                    </ModalContent>
                  </Modal>
            
                  {/* Delete Confirmation Modal */}
                  <Modal 
                    isOpen={isDeleteOpen} 
                    onClose={onDeleteClose}
                    isDismissable={removing === null}
                    hideCloseButton={removing !== null}
                  >
                    <ModalContent>
                      <ModalHeader className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <Icon icon="lucide:alert-triangle" className="text-danger" />
                          <span>Confirm Deletion</span>
                        </div>
                      </ModalHeader>
                      <ModalBody>
                        <div className="space-y-3">
                          <p>
                            Are you sure you want to remove the cluster{' '}
                            <strong className="text-danger">{clusterToDelete?.cluster_name}</strong>?
                          </p>
                          <div className="p-3 bg-danger-50 border border-danger-200 rounded-lg">
                            <div className="flex items-start gap-2">
                              <Icon icon="lucide:alert-triangle" className="text-danger mt-0.5 flex-shrink-0" />
                              <div>
                                <p className="text-small font-medium text-danger">Warning</p>
                                <p className="text-small text-danger-600">
                                  This action cannot be undone. The cluster configuration will be permanently deleted from KubeSage.
                                </p>
                              </div>
                            </div>
                          </div>
                          {clusterToDelete && (
                            <div className="text-small text-foreground-600">
                              <p><strong>Provider:</strong> {clusterToDelete.provider_name}</p>
                              <p><strong>Created:</strong> {formatDate(clusterToDelete.created_at)}</p>
                            </div>
                          )}
                        </div>
                      </ModalBody>
                      <ModalFooter>
                        <Button 
                          color="default" 
                          variant="light" 
                          onPress={onDeleteClose}
                          isDisabled={removing !== null}
                        >
                          Cancel
                        </Button>
                        <Button 
                          color="danger" 
                          onPress={() => clusterToDelete && handleRemoveCluster(clusterToDelete)}
                          isLoading={removing !== null}
                          startContent={removing === null ? <Icon icon="lucide:trash-2" /> : null}
                        >
                          {removing !== null ? "Removing..." : "Remove Cluster"}
                        </Button>
                      </ModalFooter>
                    </ModalContent>
                  </Modal>
                </motion.div>
              );
            };
            
            export default UploadKubeconfig;
            