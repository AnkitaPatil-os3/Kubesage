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

  const username = localStorage.getItem("username");

  // Optimized functions
  const generateDynamicScript = () => {
    const clusterName = formData.cluster_name;
    return `curl -O http://10.0.34.169/onboarding.sh && bash onboarding.sh "${clusterName}" "${username}" "https://10.0.32.106:8004/remediation/webhook/incidents"`;
  };

  const [copied, setCopied] = useState(false);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000); // Reset after 2 seconds
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
      const response = await fetch('https://10.0.32.106:8002/kubeconfig/clusters', {
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
      const response = await fetch('https://10.0.32.106:8002/kubeconfig/onboard-cluster', {
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
          provider_name: 'AWS EKS', // Reset to default
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
      const response = await fetch(`https://10.0.32.106:8002/kubeconfig/remove-cluster/${cluster.id}`, {
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
      provider_name: 'AWS EKS', // Reset to default
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
    if (!provider) return "logos:kubernetes";

    const providerLower = provider.toLowerCase();
    if (providerLower.includes('aws') || providerLower.includes('eks')) return "logos:aws";
    if (providerLower.includes('google') || providerLower.includes('gke')) return "logos:google-cloud";
    if (providerLower.includes('azure') || providerLower.includes('aks')) return "logos:microsoft-azure";
    if (providerLower.includes('digitalocean')) return "logos:digitalocean";
    if (providerLower.includes('minikube')) return "logos:kubernetes";
    if (providerLower.includes('kind')) return "logos:kubernetes";
    if (providerLower.includes('k3s')) return "logos:rancher";
    return "logos:kubernetes";
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
    <div className="min-h-screen ">
      {/* Simple Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-green-400/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-emerald-400/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 container mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl shadow-lg">
                <Icon icon="mdi:kubernetes" className="text-3xl text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-green-600 via-emerald-600 to-teal-600 bg-clip-text text-transparent">
                  Cluster Management Hub
                </h1>
                <p className="text-slate-600 dark:text-slate-300 text-lg font-medium flex items-center gap-2">
                  <Icon icon="mdi:cog" className="text-green-500" />
                  Orchestrate your Kubernetes infrastructure with precision
                </p>
              </div>
            </div>
          </div>

          <Button
            color="success"
            size="lg"
            radius="lg"
            startContent={<Icon icon="mdi:plus-circle" className="text-xl" />}
            onPress={onOnboardOpen}
            className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 shadow-lg hover:shadow-xl transition-all duration-200 font-semibold px-8 py-3"
          >
            Onboard New Cluster
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border border-green-200 dark:border-green-700 hover:shadow-lg transition-all duration-200">
            <CardBody className="flex flex-row items-center gap-4 p-6">
              <div className="p-4 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl shadow-lg">
                <Icon icon="mdi:server-network" className="text-3xl text-white" />
              </div>
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400 font-medium">Total Clusters</p>
                <p className="text-3xl font-bold text-green-600">{clusters.length}</p>
              </div>
            </CardBody>
          </Card>

          <Card className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border border-emerald-200 dark:border-emerald-700 hover:shadow-lg transition-all duration-200">
            <CardBody className="flex flex-row items-center gap-4 p-6">
              <div className="p-4 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl shadow-lg">
                <Icon icon="mdi:shield-check" className="text-3xl text-white" />
              </div>
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400 font-medium">Active Clusters</p>
                <p className="text-3xl font-bold text-emerald-600">{clusters.length}</p>
              </div>
            </CardBody>
          </Card>

          <Card className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border border-teal-200 dark:border-teal-700 hover:shadow-lg transition-all duration-200">
            <CardBody className="flex flex-row items-center gap-4 p-6">
              <div className="p-4 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-xl shadow-lg">
                <Icon icon="mdi:cloud-check" className="text-3xl text-white" />
              </div>
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400 font-medium">Providers</p>
                <p className="text-3xl font-bold text-teal-600">
                  {new Set(clusters.map(c => c.provider_name)).size}
                </p>
              </div>
            </CardBody>
          </Card>
        </div>

        {/* Clusters Table */}
        <Card className="bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm border border-green-200 dark:border-green-700 shadow-xl">
          <CardHeader className="flex items-center gap-4 p-6 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border-b border-green-200 dark:border-green-700">
            <div className="p-3 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl shadow-lg">
              <Icon icon="mdi:database" className="text-2xl text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                Connected Clusters
              </h2>
              <p className="text-slate-600 dark:text-slate-300 font-medium flex items-center gap-2">
                <Icon icon="mdi:information" className="text-green-500" />
                {clusters.length} cluster{clusters.length !== 1 ? 's' : ''} ready for management
              </p>
            </div>
          </CardHeader>
          <CardBody className="p-0">
            {loading ? (
              <div className="flex justify-center items-center py-20">
                <div className="text-center space-y-4">
                  <Spinner size="lg" color="success" />
                  <p className="text-slate-600 dark:text-slate-300 text-lg font-medium flex items-center gap-2 justify-center">
                    <Icon icon="mdi:cloud-download" className="text-green-500" />
                    Loading clusters...
                  </p>
                </div>
              </div>
            ) : clusters.length === 0 ? (
              <div className="text-center py-20 px-8">
                <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-green-100 to-emerald-200 dark:from-green-800 dark:to-emerald-700 rounded-3xl flex items-center justify-center">
                  <Icon icon="mdi:server-off" className="text-5xl text-green-600 dark:text-green-400" />
                </div>
                <h3 className="text-2xl font-bold text-slate-700 dark:text-slate-200 mb-3">
                  No Clusters Found
                </h3>
                <p className="text-slate-500 dark:text-slate-400 mb-8 max-w-md mx-auto text-lg">
                  <Icon icon="mdi:rocket-launch" className="inline mr-2 text-green-500" />
                  Start your Kubernetes journey by connecting your first cluster
                </p>
                <Button
                  color="success"
                  size="lg"
                  radius="lg"
                  startContent={<Icon icon="mdi:plus-circle" className="text-xl" />}
                  onPress={onOnboardOpen}
                  className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 shadow-lg font-semibold px-8"
                >
                  Connect Your First Cluster
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table aria-label="Clusters table" className="min-w-full">
                  <TableHeader>
                    <TableColumn className="bg-green-50 dark:bg-green-900/30 font-bold text-slate-700 dark:text-slate-200">
                      <Icon icon="mdi:server" className="inline mr-2 text-green-600" />
                      CLUSTER
                    </TableColumn>
                    <TableColumn className="bg-green-50 dark:bg-green-900/30 font-bold text-slate-700 dark:text-slate-200">
                      <Icon icon="mdi:cloud" className="inline mr-2 text-emerald-600" />
                      PROVIDER
                    </TableColumn>
                    <TableColumn className="bg-green-50 dark:bg-green-900/30 font-bold text-slate-700 dark:text-slate-200">
                      <Icon icon="mdi:calendar" className="inline mr-2 text-teal-600" />
                      CREATED
                    </TableColumn>
                    <TableColumn className="bg-green-50 dark:bg-green-900/30 font-bold text-slate-700 dark:text-slate-200">
                      <Icon icon="mdi:cog" className="inline mr-2 text-orange-600" />
                      ACTIONS
                    </TableColumn>
                  </TableHeader>
                  <TableBody>
                    {clusters.map((cluster) => (
                      <TableRow key={cluster.id} className="hover:bg-green-50/50 dark:hover:bg-green-900/20 transition-colors duration-200">
                        <TableCell>
                          <div className="flex items-center gap-4">
                            <div className="relative">
                              <div className="w-12 h-12 bg-gradient-to-br from-green-600 to-emerald-600 rounded-xl flex items-center justify-center shadow-lg">
                                <Icon
                                  icon={getProviderIcon(cluster.provider_name)}
                                  className="text-2xl text-white"
                                />
                              </div>
                              <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <h4 className="font-bold text-lg text-slate-800 dark:text-slate-100 truncate">
                                {cluster.cluster_name}
                              </h4>
                              <p className="text-sm text-slate-500 dark:text-slate-400 flex items-center gap-1">
                                <Icon icon="mdi:link" className="text-green-500" />
                                Connected
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Chip
                            variant="flat"
                            size="lg"
                            className="bg-gradient-to-r from-green-100 to-emerald-100 dark:from-green-900/30 dark:to-emerald-900/30 text-green-700 dark:text-green-300 font-semibold border border-green-200 dark:border-green-700"
                            startContent={<Icon icon="mdi:check-circle" className="text-green-500" />}
                          >
                            {cluster.provider_name || 'Unknown'}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Icon icon="mdi:clock" className="text-slate-400" />
                            <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                              {formatDate(cluster.created_at)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-start">
                            <Button
                              isIconOnly
                              size="sm"
                              variant="flat"
                              color="danger"
                              onPress={() => confirmDelete(cluster)}
                              isLoading={removing === cluster.id}
                              isDisabled={removing !== null}
                              aria-label="Remove Cluster"
                              className="bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/40 text-red-600 border border-red-200 dark:border-red-800"
                            >
                              <Icon icon="mdi:delete" />
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

        {/* Onboard Cluster Modal */}
        <Modal
          isOpen={isOnboardOpen}
          onClose={handleModalClose}
          size="4xl"
          scrollBehavior="inside"
          isDismissable={!onboarding}
          hideCloseButton={onboarding}
          className="bg-white/95 dark:bg-slate-800/95"
          backdrop="blur"
        >
          <ModalContent>
            <ModalHeader className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border-b border-green-200 dark:border-green-700">
              <div className="flex items-center gap-4 w-full">
                <div className="p-3 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl shadow-lg">
                  <Icon icon="mdi:server-plus" className="text-white text-2xl" />
                </div>
                <div className="flex-1">
                  <h2 className="text-2xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                    Connect New Cluster
                  </h2>
                  <p className="text-slate-600 dark:text-slate-300 font-medium flex items-center gap-2">
                    <Icon icon="mdi:link" className="text-green-500" />
                    Integrate your Kubernetes cluster with KubeSage
                  </p>
                </div>
              </div>
            </ModalHeader>
            <ModalBody className="p-8">
              <div className="space-y-8">
                {/* Basic Information */}
                <div className="space-y-6">
                  <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl border border-green-200 dark:border-green-700">
                    <div className="p-3 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl shadow-lg">
                      <Icon icon="mdi:information" className="text-white text-xl" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                        Basic Information
                      </h3>
                      <p className="text-slate-600 dark:text-slate-300 text-sm">
                        Configure your cluster's basic details
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Input
                      label="Cluster Name"
                      placeholder="e.g., production-cluster"
                      value={formData.cluster_name}
                      onValueChange={(value) => handleInputChange('cluster_name', value)}
                      startContent={<Icon icon="mdi:tag" className="text-green-500" />}
                      isRequired
                      variant="bordered"
                      isDisabled={onboarding}
                      classNames={{
                        inputWrapper: "border-green-200 hover:border-green-400 focus-within:border-green-500"
                      }}
                    />

                    <Select
                      label="Provider"
                      placeholder="Select provider"
                      selectedKeys={formData.provider_name ? [formData.provider_name] : ['AWS EKS']}
                      onSelectionChange={(keys) => {
                        const selected = Array.from(keys)[0] as string;
                        handleInputChange('provider_name', selected);
                      }}
                      variant="bordered"
                      isDisabled={onboarding}
                      startContent={<Icon icon="mdi:cloud" className="text-emerald-500" />}
                      classNames={{
                        trigger: "border-green-200 hover:border-green-400 focus:border-green-500",
                        value: "text-slate-700 dark:text-slate-200 font-medium"
                      }}
                      defaultSelectedKeys={["AWS EKS"]}
                    >
                      {providers.map((provider) => (
                        <SelectItem
                          key={provider.value}
                          value={provider.value}
                          textValue={provider.label}
                        >
                          <div className="flex items-center gap-3">
                            <Icon icon={getProviderIcon(provider.value)} className="text-lg flex-shrink-0" />
                            <span className="font-medium text-slate-700 dark:text-slate-200">
                              {provider.label}
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </Select>
                  </div>

                  <Input
                    label="Tags"
                    placeholder="e.g., production, web, backend (optional)"
                    value={formData.tags?.join(', ') || ''}
                    onValueChange={handleTagsChange}
                    startContent={<Icon icon="mdi:tag-multiple" className="text-teal-500" />}
                    description="Separate multiple tags with commas"
                    variant="bordered"
                    isDisabled={onboarding}
                    classNames={{
                      inputWrapper: "border-green-200 hover:border-green-400 focus-within:border-green-500"
                    }}
                  />
                </div>

                <Divider className="bg-gradient-to-r from-transparent via-green-300 to-transparent" />

                {/* Connection Details */}
                <div className="space-y-6">
                  <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 rounded-xl border border-emerald-200 dark:border-emerald-700">
                    <div className="p-3 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl shadow-lg">
                      <Icon icon="mdi:connection" className="text-white text-xl" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
                        Connection Details
                      </h3>
                      <p className="text-slate-600 dark:text-slate-300 text-sm">
                        Configure secure connection to your cluster
                      </p>
                    </div>
                  </div>

                  {/* Auto-Generated Script */}
                  <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-2 border-blue-200 dark:border-blue-700">
                    <CardHeader className="pb-4">
                      <div className="flex items-center gap-4 w-full">
                        <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl shadow-lg">
                          <Icon icon="mdi:console" className="text-white text-xl" />
                        </div>
                        <div className="flex-1">
                          <h4 className="font-bold text-blue-800 dark:text-blue-200 text-lg">
                            Automated Setup Script
                          </h4>
                          <p className="text-blue-600 dark:text-blue-300 text-sm">
                            One-click cluster integration
                          </p>
                        </div>
                      </div>
                    </CardHeader>
                    <CardBody className="pt-0 space-y-4">
                      <div className="p-4 bg-gradient-to-r from-blue-100 to-indigo-100 dark:from-blue-900/40 dark:to-indigo-900/40 rounded-xl border border-blue-200 dark:border-blue-700">
                        <div className="flex items-start gap-3">
                          <Icon icon="mdi:rocket-launch" className="text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0 text-xl" />
                          <div className="text-sm text-blue-700 dark:text-blue-300">
                            <p className="font-bold mb-2">Execute this command on your cluster:</p>
                            <div className="space-y-1 text-xs">
                              <div className="flex items-center gap-2">
                                <Icon icon="mdi:download" className="text-blue-600 dark:text-blue-400" />
                                <span>Downloads secure onboarding script</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Icon icon="mdi:account-plus" className="text-blue-600 dark:text-blue-400" />
                                <span>Creates service account: <strong>{formData.cluster_name || "your-cluster"}</strong></span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Icon icon="mdi:key" className="text-blue-600 dark:text-blue-400" />
                                <span>Generates authentication tokens</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Icon icon="mdi:send" className="text-blue-600 dark:text-blue-400" />
                                <span>Transmits credentials securely</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="relative bg-slate-900 p-4 rounded-xl border border-slate-700">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <div className="flex gap-1">
                              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                              <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                            </div>
                            <span className="text-green-400 text-sm font-mono">Terminal</span>
                          </div>
                          <Button
                            size="sm"
                            variant="flat"
                            color="success"
                            onPress={() => copyToClipboard(generateDynamicScript())}
                            startContent={
                              copied ?
                                <Icon icon="mdi:check" className="text-green-400" /> :
                                <Icon icon="mdi:content-copy" />
                            }
                            className={`transition-all duration-200 border ${copied
                              ? 'bg-green-500/30 border-green-400 text-green-300'
                              : 'bg-green-500/20 hover:bg-green-500/30 text-green-400 border-green-500/30'
                              }`}
                          >
                            {copied ? 'Copied!' : 'Copy'}
                          </Button>
                        </div>
                        <div className="h-12 overflow-y-auto scrollbar-thin scrollbar-thumb-green-500 scrollbar-track-slate-700">
                          <Code className="block text-green-400 bg-transparent p-0 text-sm font-mono whitespace-pre-wrap break-all leading-6">
                            {generateDynamicScript()}
                          </Code>
                        </div>
                      </div>

                    </CardBody>
                  </Card>

                  <div className="text-center py-4">
                    <div className="flex items-center justify-center gap-4">
                      <div className="h-px bg-slate-300 dark:bg-slate-600 flex-1"></div>
                      <p className="text-slate-600 dark:text-slate-400 font-medium flex items-center gap-2 px-4">
                        <Icon icon="mdi:arrow-down" className="text-green-500" />
                        Or configure manually
                        <Icon icon="mdi:arrow-down" className="text-green-500" />
                      </p>
                      <div className="h-px bg-slate-300 dark:bg-slate-600 flex-1"></div>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <Input
                      label="Server URL"
                      placeholder="https://your-cluster-api-server.com:6443"
                      value={formData.server_url}
                      onValueChange={(value) => handleInputChange('server_url', value)}
                      startContent={<Icon icon="mdi:server" className="text-blue-500" />}
                      isRequired
                      variant="bordered"
                      isDisabled={onboarding}
                      classNames={{
                        inputWrapper: "border-green-200 hover:border-green-400 focus-within:border-green-500"
                      }}
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
                      description="Service account token or authentication credentials"
                      startContent={<Icon icon="mdi:key" className="text-purple-500 mt-2" />}
                      classNames={{
                        inputWrapper: "border-green-200 hover:border-green-400 focus-within:border-green-500"
                      }}
                    />
                  </div>
                </div>

                <Divider className="bg-gradient-to-r from-transparent via-emerald-300 to-transparent" />

                {/* TLS Configuration */}
                <div className="space-y-6">
                  <div className="flex items-center justify-between p-4 bg-gradient-to-r from-teal-50 to-cyan-50 dark:from-teal-900/20 dark:to-cyan-900/20 rounded-xl border border-teal-200 dark:border-teal-700">
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-xl shadow-lg">
                        <Icon icon="mdi:security" className="text-white text-xl" />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold bg-gradient-to-r from-teal-600 to-cyan-600 bg-clip-text text-transparent">
                          TLS Security
                        </h3>
                        <p className="text-slate-600 dark:text-slate-300 text-sm">
                          Advanced security configuration
                        </p>
                      </div>
                    </div>
                    <label className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-white/50 dark:hover:bg-slate-700/50 transition-colors">
                      <input
                        type="checkbox"
                        checked={formData.use_secure_tls}
                        onChange={(e) => handleInputChange('use_secure_tls', e.target.checked)}
                        disabled={onboarding}
                        className="w-5 h-5 text-teal-600 bg-gray-100 border-gray-300 rounded focus:ring-teal-500 focus:ring-2"
                      />
                      <span className="font-semibold flex items-center gap-2 text-slate-700 dark:text-slate-200">
                        <Icon icon="mdi:lock" className="text-teal-500" />
                        Enable Secure TLS
                      </span>
                    </label>
                  </div>

                  {formData.use_secure_tls && (
                    <div className="space-y-6 p-6 bg-gradient-to-br from-teal-50/50 to-cyan-50/50 dark:from-teal-900/10 dark:to-cyan-900/10 rounded-xl border border-teal-200 dark:border-teal-700">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="p-2 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-lg">
                          <Icon icon="mdi:shield-lock" className="text-white text-lg" />
                        </div>
                        <p className="text-slate-600 dark:text-slate-300 font-medium">
                          Configure TLS certificates for enhanced security
                        </p>
                      </div>

                      <Textarea
                        label="CA Certificate Data"
                        placeholder="-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----"
                        value={formData.ca_data}
                        onValueChange={(value) => handleInputChange('ca_data', value)}
                        minRows={3}
                        maxRows={6}
                        description="Base64 encoded CA certificate (optional)"
                        variant="bordered"
                        isDisabled={onboarding}
                        startContent={<Icon icon="mdi:certificate" className="text-teal-500 mt-2" />}
                        classNames={{
                          inputWrapper: "border-teal-200 hover:border-teal-400 focus-within:border-teal-500"
                        }}
                      />

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <Textarea
                          label="TLS Certificate"
                          placeholder="-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----"
                          value={formData.tls_cert}
                          onValueChange={(value) => handleInputChange('tls_cert', value)}
                          minRows={3}
                          maxRows={6}
                          description="Client certificate (optional)"
                          variant="bordered"
                          isDisabled={onboarding}
                          startContent={<Icon icon="mdi:file-certificate" className="text-teal-500 mt-2" />}
                          classNames={{
                            inputWrapper: "border-teal-200 hover:border-teal-400 focus-within:border-teal-500"
                          }}
                        />

                        <Textarea
                          label="TLS Private Key"
                          placeholder="-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----"
                          value={formData.tls_key}
                          onValueChange={(value) => handleInputChange('tls_key', value)}
                          minRows={3}
                          maxRows={6}
                          description="Private key (optional)"
                          variant="bordered"
                          isDisabled={onboarding}
                          startContent={<Icon icon="mdi:key-variant" className="text-teal-500 mt-2" />}
                          classNames={{
                            inputWrapper: "border-teal-200 hover:border-teal-400 focus-within:border-teal-500"
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </ModalBody>
            <ModalFooter className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border-t border-green-200 dark:border-green-700 p-6">
              <div className="flex gap-4 w-full justify-end">
                <Button
                  color="danger"
                  variant="light"
                  onPress={handleModalClose}
                  isDisabled={onboarding}
                  startContent={<Icon icon="mdi:close" />}
                  className="font-semibold"
                >
                  Cancel
                </Button>
                <Button
                  color="success"
                  onPress={handleOnboardCluster}
                  isLoading={onboarding}
                  startContent={!onboarding ? <Icon icon="mdi:rocket-launch" /> : null}
                  className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 shadow-lg font-semibold px-8"
                  size="lg"
                >
                  {onboarding ? (
                    <div className="flex items-center gap-2">
                      <Icon icon="mdi:loading" className="animate-spin" />
                      Connecting...
                    </div>
                  ) : (
                    "Connect Cluster"
                  )}
                </Button>
              </div>
            </ModalFooter>
          </ModalContent>
        </Modal>

        {/* Delete Confirmation Modal */}
        <Modal
          isOpen={isDeleteOpen}
          onClose={onDeleteClose}
          isDismissable={removing === null}
          hideCloseButton={removing !== null}
          className="bg-white/95 dark:bg-slate-800/95"
          backdrop="blur"
        >
          <ModalContent>
            <ModalHeader className="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/30 dark:to-orange-900/30 border-b border-red-200 dark:border-red-700">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-gradient-to-br from-red-500 to-orange-600 rounded-xl shadow-lg">
                  <Icon icon="mdi:alert" className="text-white text-2xl" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-red-700 dark:text-red-300">
                    Confirm Cluster Removal
                  </h2>
                  <p className="text-red-600 dark:text-red-400 text-sm">
                    This action cannot be undone
                  </p>
                </div>
              </div>
            </ModalHeader>
            <ModalBody className="p-6">
              <div className="space-y-6">
                <div className="text-center">
                  <p className="text-lg text-slate-700 dark:text-slate-200">
                    Are you sure you want to remove the cluster{' '}
                    <strong className="text-red-600 dark:text-red-400 font-bold">
                      {clusterToDelete?.cluster_name}
                    </strong>?
                  </p>
                </div>

                <div className="p-4 bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border-l-4 border-red-500 rounded-lg">
                  <div className="flex items-start gap-3">
                    <Icon icon="mdi:shield-alert" className="text-red-500 mt-0.5 flex-shrink-0 text-xl" />
                    <div>
                      <p className="font-bold text-red-700 dark:text-red-300 mb-2 flex items-center gap-2">
                        <Icon icon="mdi:alert-circle" />
                        Warning
                      </p>
                      <p className="text-red-600 dark:text-red-400 font-medium">
                        This will permanently remove the cluster configuration from KubeSage.
                        All monitoring and management capabilities will be lost.
                      </p>
                    </div>
                  </div>
                </div>

                {clusterToDelete && (
                  <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl border border-slate-200 dark:border-slate-600">
                    <div className="space-y-3 text-slate-600 dark:text-slate-300">
                      <div className="flex items-center gap-3">
                        <Icon icon="mdi:cloud" className="text-blue-500" />
                        <span><strong>Provider:</strong> {clusterToDelete.provider_name}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Icon icon="mdi:calendar" className="text-green-500" />
                        <span><strong>Created:</strong> {formatDate(clusterToDelete.created_at)}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Icon icon="mdi:dns" className="text-purple-500" />
                        <span><strong>Server:</strong> {clusterToDelete.server_url}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </ModalBody>
            <ModalFooter className="bg-gradient-to-r from-slate-50 to-red-50 dark:from-slate-800 dark:to-red-900/30 border-t border-red-200 dark:border-red-700 p-6">
              <div className="flex gap-4 w-full justify-end">
                <Button
                  color="default"
                  variant="light"
                  onPress={onDeleteClose}
                  isDisabled={removing !== null}
                  startContent={<Icon icon="mdi:close" />}
                  className="font-semibold"
                >
                  Cancel
                </Button>
                <Button
                  color="danger"
                  onPress={() => clusterToDelete && handleRemoveCluster(clusterToDelete)}
                  isLoading={removing !== null}
                  startContent={removing === null ? <Icon icon="mdi:delete" /> : null}
                  className="bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700 shadow-lg font-semibold px-8"
                  size="lg"
                >
                  {removing !== null ? (
                    <div className="flex items-center gap-2">
                      <Icon icon="mdi:loading" className="animate-spin" />
                      Removing...
                    </div>
                  ) : (
                    "Remove Cluster"
                  )}
                </Button>
              </div>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </div>
    </div>
  );
};

export default UploadKubeconfig;