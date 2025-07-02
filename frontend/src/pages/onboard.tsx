import React from "react";
import { motion } from "framer-motion";
import { Icon } from "@iconify/react";
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Textarea,
  Progress,
  Chip,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Tabs,
  Tab,
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
  Checkbox,
  Badge,
  ScrollShadow,
  Code
} from "@heroui/react";
import { useHistory } from "react-router-dom";

interface KubeconfigFile {
  filename: string;
  original_filename: string;
  cluster_name: string;
  context_name: string;
  active: boolean;
  upload_date: string;
  provider_name?: string; // Add this field to match backend response
}
interface ClusterInfo {
  filename: string;
  cluster_name: string;
  active: boolean;
  provider?: string;
}

interface OnboardingData {
  clusterName: string;
  serverUrl: string;
  bearerToken: string;
  provider: string; // Add provider field
}

export const UploadKubeconfig: React.FC = () => {
  const history = useHistory();
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [kubeconfigContent, setKubeconfigContent] = React.useState("");
  const [isUploading, setIsUploading] = React.useState(false);
  const [uploadProgress, setUploadProgress] = React.useState(0);
  const [kubeconfigFiles, setKubeconfigFiles] = React.useState<KubeconfigFile[]>([]);
  const [clusters, setClusters] = React.useState<ClusterInfo[]>([]);
  const [selectedTab, setSelectedTab] = React.useState("manage");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  // Modal controls for Add Cluster
  const { isOpen: isAddClusterModalOpen, onOpen: onAddClusterModalOpen, onClose: onAddClusterModalClose } = useDisclosure();
  const [addClusterMethod, setAddClusterMethod] = React.useState("upload");

  // Delete confirmation modal
  const { isOpen: isDeleteModalOpen, onOpen: onDeleteModalOpen, onClose: onDeleteModalClose } = useDisclosure();
  const [clusterToDelete, setClusterToDelete] = React.useState<KubeconfigFile | null>(null);

  // Cluster details modal
  const { isOpen: isDetailsModalOpen, onOpen: onDetailsModalOpen, onClose: onDetailsModalClose } = useDisclosure();
  const [selectedClusterDetails, setSelectedClusterDetails] = React.useState<KubeconfigFile | null>(null);

  const { isOpen: isCommandsModalOpen, onOpen: onCommandsModalOpen, onClose: onCommandsModalClose } = useDisclosure();

  // Onboarding form state
  const [isOnboardingLoading, setIsOnboardingLoading] = React.useState(false);
  const [onboardingData, setOnboardingData] = React.useState<OnboardingData>({
    clusterName: '',
    serverUrl: '',
    bearerToken: '',
    provider: 'Standard' // Add default provider
  });

  const [selectedProvider, setSelectedProvider] = React.useState<string>('Standard');

  // Add provider options
  const providerOptions = [
    { key: 'Standard', label: 'Standard Kubernetes' },
    { key: 'EKS', label: 'Amazon EKS' },
    { key: 'GKE', label: 'Google GKE' },
    { key: 'AKS', label: 'Azure AKS' },
    { key: 'RKE2', label: 'Rancher RKE2' },
    { key: 'Edge', label: 'Edge/K3s' },
    { key: 'OpenShift', label: 'Red Hat OpenShift' },
    { key: 'MicroK8s', label: 'Canonical MicroK8s' },
    { key: 'Kind', label: 'Kind (Local)' },
    { key: 'Minikube', label: 'Minikube (Local)' }
  ];

  const getAuthToken = () => {
    return localStorage.getItem('access_token') || '';
  }

  // Helper function to detect provider from cluster name or context
  const detectProvider = (clusterName: string, contextName: string): string => {
    const name = (clusterName + ' ' + contextName).toLowerCase();
    if (name.includes('rke2') || name.includes('rancher')) return 'RKE2';
    if (name.includes('edge') || name.includes('k3s')) return 'Edge';
    if (name.includes('eks') || name.includes('amazon')) return 'EKS';
    if (name.includes('gke') || name.includes('google')) return 'GKE';
    if (name.includes('aks') || name.includes('azure')) return 'AKS';
    if (name.includes('openshift')) return 'OpenShift';
    if (name.includes('microk8s')) return 'MicroK8s';
    if (name.includes('kind')) return 'Kind';
    if (name.includes('minikube')) return 'Minikube';
    return 'Standard';
  };

  // Helper function to format date safely
  const formatDate = (dateString: string): { date: string; time: string } => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return { date: 'Unknown', time: 'Unknown' };
      }
      return {
        date: date.toLocaleDateString(),
        time: date.toLocaleTimeString()
      };
    } catch (error) {
      return { date: 'Unknown', time: 'Unknown' };
    }
  };

  // Fetch existing kubeconfigs on component mount
  React.useEffect(() => {
    fetchKubeconfigList();
    fetchClusters();
  }, []);
  const fetchKubeconfigList = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/kubeconfig/list", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch cluster list: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Cluster list response:', data);

      if (data && Array.isArray(data.kubeconfigs)) {
        // Use provider_name from backend response instead of detecting it
        const clustersWithProvider = data.kubeconfigs.map((cluster: any) => ({
          filename: cluster.filename,
          original_filename: cluster.original_filename,
          cluster_name: cluster.cluster_name,
          context_name: cluster.context_name,
          active: cluster.active,
          upload_date: cluster.created_at, // Use created_at as upload_date
          provider_name: cluster.provider_name || 'Standard' // Use actual provider_name from backend
        }));
        setKubeconfigFiles(clustersWithProvider);
      } else {
        console.warn('Unexpected cluster list format:', data);
        setKubeconfigFiles([]);
      }
    } catch (err: any) {
      console.error("Error fetching cluster list:", err);
      setError(err.message || 'Failed to fetch cluster list');
      setKubeconfigFiles([]);
    } finally {
      setLoading(false);
    }
  };
  const fetchClusters = async () => {
    setError(null);

    try {
      const response = await fetch("/kubeconfig/clusters", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch clusters: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Clusters response:', data);

      if (data && Array.isArray(data.cluster_names)) {
        setClusters(data.cluster_names);
      } else {
        console.warn('Unexpected clusters format:', data);
        setClusters([]);
      }
    } catch (err: any) {
      console.error("Error fetching clusters:", err);
      setError(err.message || 'Failed to fetch clusters');
      setClusters([]);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setKubeconfigContent(e.target?.result as string);
      };
      reader.readAsText(file);
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file && (file.name.endsWith('.yaml') || file.name.endsWith('.yml') || file.name.includes('config'))) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setKubeconfigContent(e.target?.result as string);
      };
      reader.readAsText(file);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const triggerFileInput = () => {
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    if (fileInput) {
      fileInput.click();
    }
  };

  const resetModalState = () => {
    setSelectedFile(null);
    setKubeconfigContent("");
    setSelectedProvider('Standard'); // Reset provider
    setOnboardingData({
      clusterName: '',
      serverUrl: '',
      bearerToken: '',
      provider: 'Standard' // Reset provider
    });
    setAddClusterMethod("upload");
    setError(null);
    setUploadProgress(0);
  };

  const handleModalClose = () => {
    if (!isUploading && !isOnboardingLoading) {
      resetModalState();
      onAddClusterModalClose();
    }
  };
  // Update the uploadKubeconfig function to include provider_name instead of provider
  const uploadKubeconfig = async () => {
    if (!selectedFile && !kubeconfigContent) return;

    setIsUploading(true);
    setUploadProgress(0);
    setError(null);

    try {
      const formData = new FormData();

      if (selectedFile) {
        formData.append('file', selectedFile);
      } else {
        const blob = new Blob([kubeconfigContent], { type: 'application/x-yaml' });
        formData.append('file', blob, 'kubeconfig.yaml');
      }

      // Change 'provider' to 'provider_name' to match backend
      formData.append('provider_name', selectedProvider);

      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const response = await fetch("/kubeconfig/upload", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`
        },
        body: formData
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Upload failed: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const data = await response.json();
      console.log("Upload successful:", data);

      await fetchKubeconfigList();
      await fetchClusters();

      resetModalState();
      onAddClusterModalClose();

    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
      setTimeout(() => setUploadProgress(0), 1000);
    }
  };



  const activateKubeconfig = async (filename: string) => {
    try {
      const response = await fetch(`/kubeconfig/activate/${filename}`, {
        method: "PUT",
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      if (response.ok) {
        await fetchKubeconfigList();
        await fetchClusters();
      }
    } catch (error) {
      console.error("Failed to activate cluster:", error);
    }
  };

  const openDeleteModal = (file: KubeconfigFile) => {
    setClusterToDelete(file);
    onDeleteModalOpen();
  };

  const openDetailsModal = (file: KubeconfigFile) => {
    setSelectedClusterDetails(file);
    onDetailsModalOpen();
  };

  const confirmDelete = async () => {
    if (!clusterToDelete) return;

    try {
      setError(null);
      console.log("Attempting to remove:", clusterToDelete.filename);

      const response = await fetch(`/kubeconfig/remove?filename=${encodeURIComponent(clusterToDelete.filename)}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Remove failed:", errorText);
        throw new Error(`Failed to remove cluster: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      console.log("Remove successful:", result);

      await fetchKubeconfigList();
      await fetchClusters();

      onDeleteModalClose();
      setClusterToDelete(null);

    } catch (error: any) {
      console.error("Failed to remove cluster:", error);
      setError(error.message || 'Failed to remove cluster');
    }
  };

  const handleOnboardingSubmit = async () => {
    setIsOnboardingLoading(true);
    setError(null);

    try {
      // Generate kubeconfig YAML from the provided credentials
      const kubeconfigYaml = `apiVersion: v1
  kind: Config
  clusters:
  - cluster:
      server: ${onboardingData.serverUrl}
      insecure-skip-tls-verify: true
    name: ${onboardingData.clusterName}
  contexts:
  - context:
      cluster: ${onboardingData.clusterName}
      user: ${onboardingData.clusterName}-user
    name: ${onboardingData.clusterName}
  current-context: ${onboardingData.clusterName}
  users:
  - name: ${onboardingData.clusterName}-user
    user:
      token: ${onboardingData.bearerToken}`;

      const formData = new FormData();
      const blob = new Blob([kubeconfigYaml], { type: 'application/x-yaml' });
      formData.append('file', blob, `${onboardingData.clusterName}-kubeconfig.yaml`);

      // Add provider information
      formData.append('provider', onboardingData.provider);

      const response = await fetch("/kubeconfig/upload", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to add cluster: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const data = await response.json();
      console.log("Cluster added successfully:", data);

      await fetchKubeconfigList();
      await fetchClusters();

      resetModalState();
      onAddClusterModalClose();

    } catch (err: any) {
      console.error("Add cluster error:", err);
      setError(err.message || 'Failed to add cluster');
    } finally {
      setIsOnboardingLoading(false);
    }
  };

  const renderOnboardingContent = () => {
    // Generate dynamic script command
    const generateDynamicScript = () => {
      const clusterName = onboardingData.clusterName || "cluster_should_appeare_here";
      return `curl -O http://10.0.34.169/onboard.sh && bash onboard.sh "${clusterName}" --webhook-endpoint "https://10.0.32.106:8004/remediation/webhook/incidents"`;
    };
  
    const copyToClipboard = async (text: string) => {
      try {
        await navigator.clipboard.writeText(text);
        // You can add a toast notification here if you have a toast system
        console.log('Command copied to clipboard');
      } catch (err) {
        console.error('Failed to copy text: ', err);
      }
    };
  
    return (
      <div className="space-y-6">
        <div className="text-center">
          {/* <h3 className="text-2xl font-bold text-gray-800 mb-2">Add Cluster with Credentials</h3> */}
          <p className="text-gray-600 dark:text-gray-400">Enter your cluster details to connect</p>
        </div>
        
        <div className="space-y-4">
          <Input
            label="Cluster Name"
            placeholder="e.g., production-cluster"
            value={onboardingData.clusterName}
            onValueChange={(value) => setOnboardingData(prev => ({ ...prev, clusterName: value }))}
            startContent={<Icon icon="lucide:tag" className="text-foreground-400" />}
            variant="bordered"
            size="lg"
            isRequired
          />
  
          {/* Dynamic Script Generation Section - Dark Mode Fixed */}
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
                      <li>• Creates a service account for cluster: <strong className="text-indigo-800 dark:text-indigo-200">{onboardingData.clusterName || "your-cluster"}</strong></li>
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
          
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-foreground">Server URL *</label>
              <Button
                size="sm"
                variant="light"
                color="primary"
                className="text-xs h-6 min-w-0 px-2"
                onPress={onCommandsModalOpen}
              >
                How to get?
              </Button>
            </div>
            <Input
              placeholder="e.g., https://kubernetes.example.com:6443"
              value={onboardingData.serverUrl}
              onValueChange={(value) => setOnboardingData(prev => ({ ...prev, serverUrl: value }))}
              startContent={<Icon icon="lucide:server" className="text-foreground-400" />}
              variant="bordered"
              size="lg"
              isRequired
            />
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-foreground">Bearer Token *</label>
              <Button
                size="sm"
                variant="light"
                color="primary"
                className="text-xs h-6 min-w-0 px-2"
                onPress={onCommandsModalOpen}
              >
                How to get?
              </Button>
            </div>
            <Textarea
              placeholder="Enter your bearer token here..."
              value={onboardingData.bearerToken}
              onValueChange={(value) => setOnboardingData(prev => ({ ...prev, bearerToken: value }))}
              minRows={4}
              variant="bordered"
              classNames={{
                input: "font-mono text-sm"
              }}
              isRequired
            />
          </div>
        </div>
  
       
      </div>
    );
  };


  // Calculate stats
  const totalKubeconfigs = kubeconfigFiles.length;
  const activeKubeconfigs = kubeconfigFiles.filter(f => f.active).length;
  const totalClusters = clusters.length;
  const activeClusters = clusters.filter(c => c.active).length;

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header with gradient background */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-4xl font-bold flex items-center gap-3">
              Cluster Management Hub
            </h1>
            <p className="text-gray-600 mt-2">
              Manage your container orchestration clusters with AI-powered insights
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              color="primary"
              variant="shadow"
              size="lg"
              onPress={onAddClusterModalOpen}
              startContent={<Icon icon="mdi:plus-circle" />}
            >
              Add Cluster
            </Button>
          </div>
        </div>

        {/* Stats Cards with gradients */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <motion.div whileHover={{ scale: 1.02 }}>
            <Card className="bg-gradient-to-r from-purple-500 to-pink-600 text-white">
              <CardBody className="flex flex-row items-center gap-4">
                <Icon icon="mdi:cloud" className="text-3xl" />
                <div>
                  <p className="text-sm opacity-80">Total Clusters</p>
                  <p className="text-2xl font-bold">{totalClusters}</p>
                </div>
              </CardBody>
            </Card>
          </motion.div>
          <motion.div whileHover={{ scale: 1.02 }}>
            <Card className="bg-gradient-to-r from-green-500 to-teal-600 text-white">
              <CardBody className="flex flex-row items-center gap-4">
                <Icon icon="mdi:server" className="text-3xl" />
                <div>
                  <p className="text-sm opacity-80">Active Clusters</p>
                  <p className="text-2xl font-bold">{activeClusters}</p>
                </div>
              </CardBody>
            </Card>
          </motion.div>

        </div>
      </motion.div>

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <Card className="bg-red-50 border-red-200">
            <CardBody className="flex flex-row items-center gap-3">
              <Icon icon="mdi:alert-circle" className="text-red-500 text-xl flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-semibold text-red-800">Error</p>
                <p className="text-xs text-red-700">{error}</p>
              </div>
              <Button
                size="sm"
                variant="light"
                isIconOnly
                onPress={() => setError(null)}
              >
                <Icon icon="mdi:close" className="text-red-500" />
              </Button>
            </CardBody>
          </Card>
        </motion.div>
      )}

      {/* Main Content */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <Card>
          <CardBody>
            {/* Clusters Table with All Details */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Icon icon="mdi:view-dashboard" />
                    Cluster Overview
                  </h3>
                  <p className="text-sm text-foreground-500">Complete information about your clusters</p>
                </div>
                <Button
                  color="primary"
                  variant="flat"
                  size="sm"
                  onPress={fetchKubeconfigList}
                  isLoading={loading}
                  startContent={<Icon icon="mdi:refresh" />}
                >
                  Refresh
                </Button>
              </div>

              {loading ? (
                <div className="flex justify-center py-8">
                  <div className="text-center">
                    <Spinner size="lg" color="primary" />
                    <p className="mt-4 text-lg">Loading cluster information...</p>
                  </div>
                </div>
              ) : (
                <Table aria-label="Clusters table with full details">
                  <TableHeader>
                    <TableColumn>CLUSTER NAME</TableColumn>
                    <TableColumn>PROVIDER</TableColumn>
                    <TableColumn>STATUS</TableColumn>
                    <TableColumn>ACTIONS</TableColumn>
                  </TableHeader>
                  <TableBody>
                    {kubeconfigFiles.map((file, index) => {
                      const { date, time } = formatDate(file.upload_date);
                      return (
                        <TableRow key={index}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Icon icon="mdi:kubernetes" className="text-blue-500" />
                              <div>
                                <span className="font-medium">{file.cluster_name}</span>
                                <p className="text-xs text-foreground-500">Container Cluster</p>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Chip
                              color="primary"
                              variant="flat"
                              size="sm"
                              startContent={<Icon icon="mdi:cloud-outline" className="text-xs" />}
                            >
                              {file.provider_name || 'Standard'} {/* Use provider_name instead of provider */}
                            </Chip>
                          </TableCell>
                          <TableCell>
                            <Chip
                              color={file.active ? 'success' : 'default'}
                              variant="flat"
                              size="sm"
                              startContent={
                                <Icon
                                  icon={file.active ? "mdi:check-circle" : "mdi:circle-outline"}
                                  className="text-xs"
                                />
                              }
                            >
                              {file.active ? 'Active' : 'Inactive'}
                            </Chip>
                          </TableCell>

                          <TableCell>
                            <div className="flex items-center gap-2 justify-start">
                              <Button
                                size="sm"
                                variant="flat"
                                color={file.active ? 'default' : 'success'}
                                onPress={() => activateKubeconfig(file.filename)}
                                isDisabled={file.active}
                                className="min-w-[80px]"
                              >
                                {file.active ? 'Active' : 'Activate'}
                              </Button>
                              <Button
                                size="sm"
                                variant="flat"
                                color="primary"
                                onPress={() => openDetailsModal(file)}
                                startContent={<Icon icon="mdi:eye" />}
                              >
                                Details
                              </Button>
                              <Button
                                size="sm"
                                variant="flat"
                                color="secondary"
                                isDisabled={!file.active}
                                onPress={() => history.push('/dashboard/observability')} // Change this line
                                startContent={<Icon icon="mdi:monitor" />}
                              >
                                Monitor
                              </Button>
                              <Button
                                size="sm"
                                variant="flat"
                                color="danger"
                                onPress={() => openDeleteModal(file)}
                                startContent={<Icon icon="mdi:delete" />}
                              >
                                Delete
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </div>
          </CardBody>
        </Card>
      </motion.div>

      {/* Add Cluster Modal - Dark Theme */}
      <Modal
        isOpen={isAddClusterModalOpen}
        onClose={handleModalClose}
        size="5xl"
        scrollBehavior="inside"
        isDismissable={!isUploading && !isOnboardingLoading}
        hideCloseButton={isUploading || isOnboardingLoading}
        classNames={{
          backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20",
          base: "bg-content1 dark:bg-content1",
          header: "bg-content1 dark:bg-content1 border-b border-divider",
          body: "bg-content1 dark:bg-content1",
          footer: "bg-content1 dark:bg-content1 border-t border-divider"
        }}
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <Icon icon="mdi:plus-circle" className="text-2xl text-primary" />
              <span className="text-xl font-bold">Add New Cluster</span>
            </div>
            <p className="text-sm text-foreground-500 font-normal">
              Choose how you want to add your cluster to KubeSage
            </p>
          </ModalHeader>
          <ModalBody className="p-6">
            <Tabs
              aria-label="Add cluster options"
              selectedKey={addClusterMethod}
              onSelectionChange={setAddClusterMethod as any}
              variant="underlined"
              color="primary"
              classNames={{
                tabList: "gap-6 w-full relative rounded-none p-0 border-b border-divider",
                cursor: "w-full bg-primary",
                tab: "max-w-fit px-0 h-12",
              }}
            >
              <Tab
                key="upload"
                title={
                  <div className="flex items-center gap-2">
                    <Icon icon="mdi:upload" />
                    <span>Upload Kubeconfig</span>
                  </div>
                }
              >
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="mt-6 space-y-6"
                >
                  {/* Upload Instructions */}
                  <Card className="bg-content2 border border-divider">
                    <CardBody>
                      <div className="flex items-start gap-4">
                        <Icon icon="mdi:information" className="text-2xl text-primary mt-1" />
                        <div>
                          <h4 className="font-semibold text-foreground">Upload Instructions</h4>
                          <p className="text-foreground-500 mt-1">
                            Upload your existing kubeconfig file or paste the YAML content directly.
                            We'll automatically detect cluster information and configure access.
                          </p>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                  {/* Provider Selection */}
                  <Card className="bg-content2 border border-divider">
                    <CardHeader>
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Icon icon="mdi:cloud-outline" className="text-secondary" />
                        Select Provider Type
                      </h3>
                    </CardHeader>
                    <CardBody>
                      <Select
                        label="Kubernetes Provider"
                        placeholder="Choose your cluster provider"
                        selectedKeys={[selectedProvider]}
                        onSelectionChange={(keys) => {
                          const selected = Array.from(keys)[0] as string;
                          setSelectedProvider(selected);
                        }}
                        variant="bordered"
                        size="lg"
                        startContent={<Icon icon="mdi:kubernetes" className="text-primary" />}
                        classNames={{
                          trigger: "bg-content1"
                        }}
                      >
                        {providerOptions.map((provider) => (
                          <SelectItem key={provider.key} value={provider.key}>
                            {provider.label}
                          </SelectItem>
                        ))}
                      </Select>

                    </CardBody>
                  </Card>


                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* File Upload Section */}
                    <Card className="border-2 border-dashed border-divider hover:border-primary transition-colors">
                      <CardHeader className="bg-content2">
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                          <Icon icon="mdi:file-upload" className="text-success" />
                          Upload Kubeconfig File
                        </h3>
                      </CardHeader>
                      <CardBody className="space-y-4">
                        <div
                          className="p-8 border-2 border-dashed border-divider rounded-lg text-center hover:border-primary transition-colors cursor-pointer bg-content2"
                          onDrop={handleDrop}
                          onDragOver={handleDragOver}
                          onClick={triggerFileInput}
                        >
                          <input
                            id="file-input"
                            type="file"
                            accept=".yaml,.yml,.config"
                            onChange={handleFileSelect}
                            className="hidden"
                            style={{ display: 'none' }}
                          />
                          <div className="flex flex-col items-center gap-3">
                            <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center">
                              <Icon icon="mdi:cloud-upload" className="text-3xl text-white" />
                            </div>
                            <h4 className="font-medium text-lg text-foreground">
                              {selectedFile ? selectedFile.name : "Drop kubeconfig file here"}
                            </h4>
                            <p className="text-sm text-foreground-500">
                              {selectedFile ? "File selected successfully" : "or click to browse files"}
                            </p>
                            {!selectedFile && (
                              <Button
                                variant="shadow"
                                color="primary"
                                size="lg"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  triggerFileInput();
                                }}
                                startContent={<Icon icon="mdi:folder-open" />}
                              >
                                Browse Files
                              </Button>
                            )}
                          </div>
                        </div>

                        {selectedFile && (
                          <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="flex items-center justify-between p-4 bg-success-50 dark:bg-success/10 text-success rounded-lg border border-success/20"
                          >
                            <div className="flex items-center gap-3">
                              <Icon icon="mdi:check-circle" className="text-xl" />
                              <div>
                                <span className="font-medium">{selectedFile.name}</span>
                                <p className="text-xs opacity-80">Ready to upload</p>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              variant="light"
                              color="danger"
                              onPress={() => {
                                setSelectedFile(null);
                                setKubeconfigContent("");
                              }}
                              startContent={<Icon icon="mdi:close" />}
                            >
                              Remove
                            </Button>
                          </motion.div>
                        )}
                      </CardBody>
                    </Card>

                    {/* Manual Input Section */}
                    <Card className="border-2 border-dashed border-divider hover:border-secondary transition-colors">
                      <CardHeader className="bg-content2">
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                          <Icon icon="mdi:code-braces" className="text-secondary" />
                          Paste Kubeconfig Content
                        </h3>
                      </CardHeader>
                      <CardBody>
                        <Textarea
                          label="Kubeconfig YAML"
                          placeholder="apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: ...
    server: https://..."
                          value={kubeconfigContent}
                          onValueChange={setKubeconfigContent}
                          minRows={10}
                          maxRows={15}
                          classNames={{
                            input: "font-mono text-sm",
                            inputWrapper: "bg-content2"
                          }}
                        />
                      </CardBody>
                    </Card>
                  </div>

                  {/* Upload Progress */}
                  {isUploading && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                    >
                      <Card className="bg-primary-50 dark:bg-primary/10 border border-primary/20">
                        <CardBody>
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                                  <Icon icon="mdi:upload" className="text-white" />
                                </div>
                                <span className="font-medium text-foreground">Uploading kubeconfig...</span>
                              </div>
                              <span className="text-sm text-foreground-500 font-mono">{uploadProgress}%</span>
                            </div>
                            <Progress
                              value={uploadProgress}
                              color="primary"
                            />
                          </div>
                        </CardBody>
                      </Card>
                    </motion.div>
                  )}
                </motion.div>
              </Tab>

              <Tab
                key="onboarding"
                title={
                  <div className="flex items-center gap-2">
                    <Icon icon="mdi:rocket-launch" />
                    <span>Onboard Cluster</span>
                  </div>
                }
              >
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="mt-6"
                >
                  
                           <Card>
              <CardBody className="p-6">
                      {renderOnboardingContent()}
                    </CardBody>
                  </Card>
   
                </motion.div>
              </Tab>
            </Tabs>
          </ModalBody>
          <ModalFooter>
            <Button
              color="danger"
              variant="light"
              onPress={handleModalClose}
              isDisabled={isUploading || isOnboardingLoading}
              startContent={<Icon icon="mdi:close" />}
            >
              Cancel
            </Button>

            {addClusterMethod === "upload" ? (
              <Button
                color="primary"
                variant="shadow"
                onPress={uploadKubeconfig}
                isLoading={isUploading}
                isDisabled={!selectedFile && !kubeconfigContent.trim()}
                endContent={<Icon icon="mdi:upload" />}
              >
                Upload Kubeconfig
              </Button>
            ) : (
              <Button
                color="primary"
                variant="shadow"
                onPress={handleOnboardingSubmit}
                isLoading={isOnboardingLoading}
                isDisabled={!onboardingData.clusterName || !onboardingData.serverUrl || !onboardingData.bearerToken}
                endContent={<Icon icon="mdi:check" />}
              >
                Add Cluster
              </Button>
            )}
          </ModalFooter>
        </ModalContent>
      </Modal>


      {/* Cluster Details Modal - Dark Theme */}
      <Modal
        isOpen={isDetailsModalOpen}
        onClose={onDetailsModalClose}
        size="3xl"
        scrollBehavior="inside"
        classNames={{
          backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20",
          base: "bg-content1 dark:bg-content1",
          header: "bg-content1 dark:bg-content1 border-b border-divider",
          body: "bg-content1 dark:bg-content1",
          footer: "bg-content1 dark:bg-content1 border-t border-divider"
        }}
      >
        <ModalContent>
          <ModalHeader>
            <div className="flex items-center gap-3">
              <Icon icon="mdi:information-outline" className="text-2xl text-primary" />
              <span className="text-xl font-bold">Cluster Details</span>
            </div>
          </ModalHeader>
          <ModalBody className="p-6">
            {selectedClusterDetails && (
              <div className="space-y-6">
                {/* Cluster Summary */}
                <Card className="bg-success-50 dark:bg-success/10 border border-success/20">
                  <CardBody>
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-success rounded-full flex items-center justify-center">
                        <Icon icon="mdi:kubernetes" className="text-2xl text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-bold text-success text-lg">{selectedClusterDetails.cluster_name}</h4>
                        <p className="text-success/80 mt-1">
                          Kubernetes Cluster Configuration
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <Chip
                            color={selectedClusterDetails.active ? 'success' : 'default'}
                            variant="flat"
                            size="sm"
                            startContent={<Icon icon={selectedClusterDetails.active ? "mdi:check-circle" : "mdi:circle-outline"} />}
                          >
                            {selectedClusterDetails.active ? 'Active' : 'Inactive'}
                          </Chip>
                        </div>
                      </div>
                    </div>
                  </CardBody>
                </Card>

                {/* Detailed Information */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">


                  <Card className="bg-content2">
                    <CardHeader className="pb-2">
                      <h4 className="font-semibold text-foreground flex items-center gap-2">
                        <Icon icon="mdi:shield-check" />
                        Status & Health
                      </h4>
                    </CardHeader>
                    <CardBody className="pt-0">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-foreground-500 font-medium">Connection Status</span>
                          <Chip size="sm" color={selectedClusterDetails.active ? 'success' : 'default'} variant="flat">
                            {selectedClusterDetails.active ? 'Connected' : 'Disconnected'}
                          </Chip>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-foreground-500 font-medium">Configuration Valid</span>
                          <Chip size="sm" color="success" variant="flat">
                            Valid
                          </Chip>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                </div>

                {/* Actions Section */}
                <Card className="bg-content2">
                  <CardHeader>
                    <h4 className="font-semibold text-foreground flex items-center gap-2">
                      <Icon icon="mdi:lightning-bolt" />
                      Quick Actions
                    </h4>
                  </CardHeader>
                  <CardBody>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <Button
                        color={selectedClusterDetails.active ? 'default' : 'success'}
                        variant="flat"
                        onPress={() => {
                          activateKubeconfig(selectedClusterDetails.filename);
                          onDetailsModalClose();
                        }}
                        isDisabled={selectedClusterDetails.active}
                        startContent={<Icon icon="mdi:power" />}
                      >
                        {selectedClusterDetails.active ? 'Already Active' : 'Activate Cluster'}
                      </Button>
                      <Button
                        color="secondary"
                        variant="flat"
                        isDisabled={!selectedClusterDetails.active}
                        onPress={() => {
                          history.push('/dashboard/observability');
                          onDetailsModalClose();
                        }}
                        startContent={<Icon icon="mdi:monitor" />}
                      >
                        Monitor Cluster
                      </Button>

                    </div>
                  </CardBody>
                </Card>

                {/* Warning Section */}
                <Card className="bg-warning-50 dark:bg-warning/10 border border-warning/20">
                  <CardBody>
                    <div className="flex items-start gap-3">
                      <Icon icon="mdi:information" className="text-warning text-xl mt-0.5" />
                      <div>
                        <h4 className="font-semibold text-warning">Important Information</h4>
                        <ul className="text-sm text-warning/80 mt-2 space-y-1">
                          <li>• Only one cluster can be active at a time</li>
                          <li>• Activating this cluster will deactivate others</li>
                          <li>• Ensure you have proper access permissions</li>
                          <li>• Monitor cluster health regularly</li>
                        </ul>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              </div>
            )}
          </ModalBody>
          <ModalFooter>
            <Button
              color="danger"
              variant="light"
              onPress={onDetailsModalClose}
              startContent={<Icon icon="mdi:close" />}
            >
              Close
            </Button>
            <Button
              color="primary"
              variant="shadow"
              onPress={() => {
                if (selectedClusterDetails) {
                  onDetailsModalClose();
                  openDeleteModal(selectedClusterDetails);
                }
              }}
              startContent={<Icon icon="mdi:cog" />}
            >
              Manage Cluster
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>


      {/* Delete Confirmation Modal - Dark Mode Fixed & Simplified */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={onDeleteModalClose}
        size="2xl"
        classNames={{
          backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20",
          base: "bg-content1 dark:bg-content1",
          header: "bg-content1 dark:bg-content1 border-b border-divider",
          body: "bg-content1 dark:bg-content1",
          footer: "bg-content1 dark:bg-content1 border-t border-divider"
        }}
      >
        <ModalContent>
          <ModalHeader className="bg-gradient-to-r from-red-500 to-pink-600 text-white">
            <div className="flex items-center gap-3">
              <Icon icon="mdi:alert-circle" className="text-2xl" />
              <span className="text-xl font-bold">Confirm Deletion</span>
            </div>
          </ModalHeader>
          <ModalBody className="p-6">
            <div className="space-y-6">
              {/* Warning Header */}
              <Card className="bg-danger-50 dark:bg-danger/10 border-l-4 border-danger">
                <CardBody>
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-gradient-to-r from-red-500 to-pink-600 rounded-full flex items-center justify-center">
                      <Icon icon="mdi:alert-triangle" className="text-2xl text-white" />
                    </div>
                    <div>
                      <h4 className="font-bold text-danger">Permanent Deletion Warning</h4>
                      <p className="text-danger/80 mt-1">
                        You are about to permanently delete this cluster configuration. This action cannot be undone.
                      </p>
                    </div>
                  </div>
                </CardBody>
              </Card>

              {/* Cluster Information */}
              {clusterToDelete && (
                <Card className="bg-content2 border border-divider">
                  <CardHeader>
                    <h4 className="font-semibold flex items-center gap-2">
                      <Icon icon="mdi:kubernetes" className="text-primary" />
                      Cluster to be Deleted
                    </h4>
                  </CardHeader>
                  <CardBody>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-foreground">{clusterToDelete.cluster_name}</p>
                        <p className="text-sm text-foreground-500">{clusterToDelete.provider || 'Standard'} Cluster</p>
                      </div>
                      <Chip
                        color={clusterToDelete.active ? 'success' : 'default'}
                        variant="flat"
                        size="sm"
                      >
                        {clusterToDelete.active ? 'Active' : 'Inactive'}
                      </Chip>
                    </div>

                    {clusterToDelete.active && (
                      <div className="mt-4 p-3 bg-warning-50 dark:bg-warning/10 rounded-lg border border-warning/20">
                        <div className="flex items-center gap-2">
                          <Icon icon="mdi:alert" className="text-warning" />
                          <span className="text-sm font-medium text-warning">
                            This is your currently active cluster!
                          </span>
                        </div>
                      </div>
                    )}
                  </CardBody>
                </Card>
              )}

              {/* Consequences */}
              <Card className="bg-warning-50 dark:bg-warning/10 border-l-4 border-warning">
                <CardBody>
                  <div className="flex items-start gap-3">
                    <Icon icon="mdi:information" className="text-warning text-xl mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-warning mb-2">What will happen:</h4>
                      <ul className="text-sm text-foreground-600 space-y-1">
                        <li className="flex items-center gap-2">
                          <Icon icon="mdi:close-circle" className="text-danger" />
                          The cluster configuration will be permanently removed
                        </li>
                        <li className="flex items-center gap-2">
                          <Icon icon="mdi:close-circle" className="text-danger" />
                          You will lose access to this cluster through KubeSage
                        </li>
                        <li className="flex items-center gap-2">
                          <Icon icon="mdi:information" className="text-primary" />
                          The actual cluster infrastructure will remain unaffected
                        </li>
                      </ul>
                    </div>
                  </div>
                </CardBody>
              </Card>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button
              color="default"
              variant="light"
              onPress={onDeleteModalClose}
              startContent={<Icon icon="mdi:close" />}
            >
              Cancel
            </Button>
            <Button
              color="danger"
              variant="shadow"
              onPress={confirmDelete}
              startContent={<Icon icon="mdi:delete-forever" />}
            >
              Delete Permanently
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>


      {/* Commands Help Modal - Fixed Screen Stuck Issue */}

      <Modal
        isOpen={isCommandsModalOpen}
        onClose={onCommandsModalClose}
        size="4xl"
        scrollBehavior="inside"
        isDismissable={true}
        isKeyboardDismissDisabled={false}
        hideCloseButton={false}
        closeButton={
          <Button
            isIconOnly
            variant="light"
            onPress={onCommandsModalClose}
            className="text-white hover:bg-white/20"
          >
            <Icon icon="mdi:close" />
          </Button>
        }
        classNames={{
          backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20",
          base: "bg-content1 dark:bg-content1",
          header: "bg-content1 dark:bg-content1 border-b border-divider",
          body: "bg-content1 dark:bg-content1",
          footer: "bg-content1 dark:bg-content1 border-t border-divider"
        }}
      >
        <ModalContent>
          <ModalHeader className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white">
            <div className="flex items-center gap-3">
              <Icon icon="mdi:terminal" className="text-2xl" />
              <span className="text-xl font-bold">How to Get Server URL & Bearer Token</span>
            </div>
          </ModalHeader>
          <ModalBody className="p-6">
            <div className="space-y-6">
              {/* Step 1 - Updated Command */}
              <Card className="bg-success-50 dark:bg-success/10 border-l-4 border-success">
                <CardHeader className="bg-content2">
                  <h4 className="font-bold text-success flex items-center gap-2">
                    <div className="w-8 h-8 bg-success text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
                    Run the Command
                  </h4>
                </CardHeader>
                <CardBody>
                  <p className="text-success mb-3">Execute this command in your terminal to extract the credentials:</p>
                  <div className="bg-gray-900 dark:bg-gray-800 p-4 rounded-lg border border-divider">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-success text-sm font-mono">Terminal</span>
                      <Button
                        size="sm"
                        variant="flat"
                        color="success"
                        onPress={() => {
                          navigator.clipboard.writeText('echo "TOKEN: $(grep \'token:\' ~/.kube/config | awk \'{print $2}\' | tr -d \'\"\')" && echo "SERVER_URL: $(grep -A 2 \'cluster:\' ~/.kube/config | grep \'server:\' | awk \'{print $2}\' | tr -d \'\"\')"');
                        }}
                        startContent={<Icon icon="mdi:content-copy" />}
                      >
                        Copy
                      </Button>
                    </div>
                    <ScrollShadow className="max-h-32">
                      <Code className="block text-success bg-transparent p-0 text-sm whitespace-pre-wrap break-all">
                        {`echo "TOKEN: $(grep 'token:' ~/.kube/config | awk '{print $2}' | tr -d '"')" && echo "SERVER_URL: $(grep -A 2 'cluster:' ~/.kube/config | grep 'server:' | awk '{print $2}' | tr -d '"')"`}
                      </Code>
                    </ScrollShadow>
                  </div>
                </CardBody>
              </Card>

              {/* Step 2 - Expected Output */}
              <Card className="bg-primary-50 dark:bg-primary/10 border-l-4 border-primary">
                <CardHeader className="bg-content2">
                  <h4 className="font-bold text-primary flex items-center gap-2">
                    <div className="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
                    Expected Output
                  </h4>
                </CardHeader>
                <CardBody>
                  <p className="text-primary mb-3">The command will output your credentials in this format:</p>
                  <div className="bg-gray-900 dark:bg-gray-800 p-4 rounded-lg border border-divider">
                    <div className="mb-2">
                      <span className="text-success text-sm font-mono">Sample Output:</span>
                    </div>
                    <div className="space-y-2">
                      <div>
                        <span className="text-warning text-sm">TOKEN:</span>
                        <ScrollShadow className="max-h-20 mt-1">
                          <Code className="block text-success bg-transparent p-0 text-sm ml-4 whitespace-pre-wrap break-all">
                            eyJhbGciOiJSUzI1NiIsImtpZCI6IjVRV...</Code>
                        </ScrollShadow>
                      </div>
                      <div>
                        <span className="text-warning text-sm">SERVER_URL:</span>
                        <Code className="block text-success bg-transparent p-0 text-sm ml-4 mt-1">
                          https://your-cluster-api-server:6443
                        </Code>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 p-3 bg-primary-50 dark:bg-primary/10 rounded-lg border border-primary/20">
                    <h5 className="font-semibold text-primary mb-2">Usage Instructions:</h5>
                    <ul className="text-sm text-foreground-600 space-y-1">
                      <li><strong>Copy the TOKEN value</strong> and paste it in the Bearer Token field</li>
                      <li><strong>Copy the SERVER_URL value</strong> and paste it in the Server URL field</li>
                      <li><strong>Make sure</strong> your configuration file is accessible at ~/.kube/config</li>
                      <li><strong>Verify</strong> you have the necessary permissions to read the configuration</li>
                    </ul>
                  </div>
                </CardBody>
              </Card>

            </div>
          </ModalBody>
          <ModalFooter>
            <Button
              color="primary"
              variant="shadow"
              onPress={onCommandsModalClose}
              startContent={<Icon icon="mdi:check" />}
            >
              Got it!
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>



      {/* Loading Overlay - Optimized */}
      {(isUploading || isOnboardingLoading) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="p-8 bg-gradient-to-br from-white to-gray-50">
            <CardBody className="flex flex-col items-center gap-6">
              <div className="relative">
                <Spinner size="lg" color="primary" />
                <div className="absolute inset-0 animate-ping">
                  <div className="w-12 h-12 border-2 border-primary-300 rounded-full"></div>
                </div>
              </div>
              <div className="text-center">
                <p className="font-semibold text-lg">
                  {isUploading && 'Uploading Configuration...'}
                  {isOnboardingLoading && 'Adding Cluster...'}
                </p>
                <p className="text-sm text-gray-600 mt-2">
                  {isUploading && 'Processing your cluster configuration file'}
                  {isOnboardingLoading && 'Creating configuration from your credentials'}
                </p>
                <div className="mt-4 flex items-center justify-center gap-2">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* Floating Action Buttons */}
      <div className="fixed bottom-6 right-6 flex flex-col gap-3">
        <motion.div
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
        >
          <Button
            isIconOnly
            color="secondary"
            variant="shadow"
            size="lg"
            onPress={() => {
              fetchKubeconfigList();
              fetchClusters();
            }}
            className="w-14 h-14 bg-gradient-to-r from-purple-500 to-pink-600"
          >
            <Icon icon="mdi:refresh" className="text-xl" />
          </Button>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
        >
          <Button
            isIconOnly
            color="primary"
            variant="shadow"
            size="lg"
            onPress={onAddClusterModalOpen}
            className="w-14 h-14 bg-gradient-to-r from-blue-500 to-purple-600"
          >
            <Icon icon="mdi:plus" className="text-xl" />
          </Button>
        </motion.div>
      </div>
    </div>
  );
};

export default UploadKubeconfig;


