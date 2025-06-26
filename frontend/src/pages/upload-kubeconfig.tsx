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
  Code,
  Avatar
} from "@heroui/react";
import { useHistory } from "react-router-dom";

// Updated interfaces to match backend response
interface ClusterConfig {
  id: number;
  cluster_name: string;
  server_url: string;
  context_name: string;
  provider_name: string;
  tags?: string[];
  use_secure_tls: boolean;
  ca_data?: string;
  tls_key?: string;
  tls_cert?: string;
  user_id: number;
  active: boolean;
  is_operator_installed: boolean;
  created_at: string;
  updated_at: string;
  message?: string;
}

interface ClusterConfigList {
  clusters: ClusterConfig[];
}

interface OnboardingData {
  cluster_name: string;
  server_url: string;
  token: string;
  context_name: string;
  provider_name: string;
  tags: string[];
  use_secure_tls: boolean;
  ca_data?: string;
  tls_key?: string;
  tls_cert?: string;
}

export const UploadKubeconfig: React.FC = () => {
  const history = useHistory();
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [kubeconfigContent, setKubeconfigContent] = React.useState("");
  const [isUploading, setIsUploading] = React.useState(false);
  const [uploadProgress, setUploadProgress] = React.useState(0);
  const [clusters, setClusters] = React.useState<ClusterConfig[]>([]);
  const [namespaces, setNamespaces] = React.useState<string[]>([]);
  const [selectedTab, setSelectedTab] = React.useState("manage");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [activeClusterId, setActiveClusterId] = React.useState<number | null>(null);

  // Modal controls for Add Cluster
  const { isOpen: isAddClusterModalOpen, onOpen: onAddClusterModalOpen, onClose: onAddClusterModalClose } = useDisclosure();
  const [addClusterMethod, setAddClusterMethod] = React.useState("upload");

  // Delete confirmation modal
  const { isOpen: isDeleteModalOpen, onOpen: onDeleteModalOpen, onClose: onDeleteModalClose } = useDisclosure();
  const [clusterToDelete, setClusterToDelete] = React.useState<ClusterConfig | null>(null);

  // Cluster details modal
  const { isOpen: isDetailsModalOpen, onOpen: onDetailsModalOpen, onClose: onDetailsModalClose } = useDisclosure();
  const [selectedClusterDetails, setSelectedClusterDetails] = React.useState<ClusterConfig | null>(null);

  // Onboarding form state
  const [isOnboardingLoading, setIsOnboardingLoading] = React.useState(false);
  const [onboardingData, setOnboardingData] = React.useState<OnboardingData>({
    cluster_name: '',
    server_url: '',
    token: '',
    context_name: '',
    provider_name: 'Standard',
    tags: [],
    use_secure_tls: false,
    ca_data: '',
    tls_key: '',
    tls_cert: ''
  });

  const [selectedProvider, setSelectedProvider] = React.useState<string>('Standard');

  // Add provider options with icons
  const providerOptions = [
    { key: 'Standard', label: 'Standard Kubernetes', icon: 'mdi:kubernetes', color: 'primary' },
    { key: 'EKS', label: 'Amazon EKS', icon: 'mdi:aws', color: 'warning' },
    { key: 'GKE', label: 'Google GKE', icon: 'mdi:google-cloud', color: 'primary' },
    { key: 'AKS', label: 'Azure AKS', icon: 'mdi:microsoft-azure', color: 'secondary' },
    { key: 'RKE2', label: 'Rancher RKE2', icon: 'mdi:cow', color: 'success' },
    { key: 'Edge', label: 'Edge/K3s', icon: 'mdi:server-network', color: 'default' },
    { key: 'OpenShift', label: 'Red Hat OpenShift', icon: 'mdi:redhat', color: 'danger' },
    { key: 'MicroK8s', label: 'Canonical MicroK8s', icon: 'mdi:ubuntu', color: 'warning' },
    { key: 'Kind', label: 'Kind (Local)', icon: 'mdi:docker', color: 'primary' },
    { key: 'Minikube', label: 'Minikube (Local)', icon: 'mdi:kubernetes', color: 'success' }
  ];

  const getAuthToken = () => {
    return localStorage.getItem('access_token') || '';
  }

  // Helper function to get API base URL
  const getApiBaseUrl = () => {
    // Try to detect the correct API URL
    const currentUrl = window.location.origin;
    
    // If running on development port 5173, assume API is on 8000
    if (currentUrl.includes(':5173')) {
      return currentUrl.replace(':5173', ':8002');
    }
    
    // Otherwise use the same origin
    return currentUrl;
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

  // Get provider info
  const getProviderInfo = (providerName: string) => {
    return providerOptions.find(p => p.key === providerName) || providerOptions[0];
  };

  // Fetch existing clusters on component mount
  React.useEffect(() => {
    fetchClusters();
  }, []);

  React.useEffect(() => {
    if (activeClusterId) {
      fetchNamespaces();
    }
  }, [activeClusterId]);

  const fetchClusters = async () => {
    setLoading(true);
    setError(null);

    try {
      const apiUrl = `${getApiBaseUrl()}/kubeconfig/clusters`;
      console.log('Fetching clusters from:', apiUrl);
      
      const response = await fetch(apiUrl, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', response.headers);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`Failed to fetch cluster list: ${response.status} ${response.statusText}`);
      }

      const data: ClusterConfigList = await response.json();
      console.log('Cluster list response:', data);

      if (data && Array.isArray(data.clusters)) {
        setClusters(data.clusters);
        
        // Find active cluster
        const activeCluster = data.clusters.find(cluster => cluster.active);
        if (activeCluster) {
          setActiveClusterId(activeCluster.id);
        }
      } else {
        console.warn('Unexpected cluster list format:', data);
        setClusters([]);
      }
    } catch (err: any) {
      console.error("Error fetching cluster list:", err);
      setError(err.message || 'Failed to fetch cluster list');
      setClusters([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchNamespaces = async () => {
    try {
      const apiUrl = `${getApiBaseUrl()}/kubeconfig/namespaces`;
      console.log('Fetching namespaces from:', apiUrl);
      
      const response = await fetch(apiUrl, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      if (!response.ok) {
        if (response.status === 404) {
          // No active cluster
          setNamespaces([]);
          return;
        }
        const errorText = await response.text();
        console.error('Namespace error response:', errorText);
        throw new Error(`Failed to fetch namespaces: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Namespaces response:', data);

      if (data && Array.isArray(data.namespaces)) {
        setNamespaces(data.namespaces);
      } else {
        console.warn('Unexpected namespaces format:', data);
        setNamespaces([]);
      }
    } catch (err: any) {
      console.error("Error fetching namespaces:", err);
      setNamespaces([]);
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
    setSelectedProvider('Standard');
    setOnboardingData({
      cluster_name: '',
      server_url: '',
      token: '',
      context_name: '',
      provider_name: 'Standard',
      tags: [],
      use_secure_tls: false,
      ca_data: '',
      tls_key: '',
      tls_cert: ''
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

  // Updated upload function to use new onboard-cluster endpoint
  const uploadKubeconfig = async () => {
    if (!selectedFile && !kubeconfigContent) return;

    setIsUploading(true);
    setUploadProgress(0);
    setError(null);

    try {
      // Parse kubeconfig to extract cluster information
      let kubeconfigData;
      if (selectedFile) {
        const fileContent = await selectedFile.text();
        kubeconfigData = parseKubeconfig(fileContent);
      } else {
        kubeconfigData = parseKubeconfig(kubeconfigContent);
      }

      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const requestData = {
        cluster_name: kubeconfigData.cluster_name,
        server_url: kubeconfigData.server_url,
        token: kubeconfigData.token,
        context_name: kubeconfigData.context_name,
        provider_name: selectedProvider,
        tags: [],
        use_secure_tls: kubeconfigData.use_secure_tls,
        ca_data: kubeconfigData.ca_data,
        tls_key: kubeconfigData.tls_key,
        tls_cert: kubeconfigData.tls_cert
      };

      const apiUrl = `${getApiBaseUrl()}/kubeconfig/onboard-cluster`;
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(requestData)
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Upload failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log("Upload successful:", data);

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

  // Helper function to parse kubeconfig
  const parseKubeconfig = (content: string) => {
    try {
      const yaml = require('js-yaml');
      const config = yaml.load(content);
      
      const cluster = config.clusters?.[0]?.cluster || {};
      const user = config.users?.[0]?.user || {};
      const context = config.contexts?.[0] || {};
      
      return {
        cluster_name: config.clusters?.[0]?.name || 'unknown-cluster',
        server_url: cluster.server || '',
        token: user.token || '',
        context_name: context.name || 'default',
        use_secure_tls: !cluster['insecure-skip-tls-verify'],
        ca_data: cluster['certificate-authority-data'],
        tls_cert: user['client-certificate-data'],
        tls_key: user['client-key-data']
      };
    } catch (error) {
      console.error('Error parsing kubeconfig:', error);
      throw new Error('Invalid kubeconfig format');
    }
  };

  const activateCluster = async (clusterId: number) => {
    try {
      setLoading(true);
      const apiUrl = `${getApiBaseUrl()}/kubeconfig/select-cluster-and-get-namespaces/${clusterId}`;
      
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`,
          "Content-Type": "application/json"
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Activation error response:', errorText);
        throw new Error(`Failed to activate cluster: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success && data.cluster_activated) {
        setActiveClusterId(clusterId);
        
        if (data.namespaces_retrieved && data.namespaces) {
          setNamespaces(data.namespaces);
        } else {
          setNamespaces([]);
          console.warn('Cluster activated but namespaces not available:', data.error);
        }
        
        // Refresh cluster list to update active status
        await fetchClusters();
        
        console.log(`Switched to cluster: ${data.cluster_info.cluster_name}`);
      } else {
        throw new Error(data.message || 'Failed to activate cluster');
      }
    } catch (error: any) {
      console.error("Failed to activate cluster:", error);
      setError(error.message || 'Failed to activate cluster');
    } finally {
      setLoading(false);
    }
  };

  const openDeleteModal = (cluster: ClusterConfig) => {
    setClusterToDelete(cluster);
    onDeleteModalOpen();
  };

  const openDetailsModal = (cluster: ClusterConfig) => {
    setSelectedClusterDetails(cluster);
    onDetailsModalOpen();
  };

  const deleteCluster = async () => {
    if (!clusterToDelete) return;

    try {
      setLoading(true);
      const apiUrl = `${getApiBaseUrl()}/cluster/remove-cluster/${clusterToDelete.id}`;
      
      const response = await fetch(apiUrl, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`,
          "Content-Type": "application/json"
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Delete error response:', errorText);
        throw new Error(`Failed to delete cluster: ${response.status} ${response.statusText}`);
      }

      await fetchClusters();
      onDeleteModalClose();
      setClusterToDelete(null);
    } catch (error: any) {
      console.error("Failed to delete cluster:", error);
      setError(error.message || 'Failed to delete cluster');
    } finally {
      setLoading(false);
    }
  };

  // Handle manual cluster onboarding
  const handleManualOnboarding = async () => {
    if (!onboardingData.cluster_name || !onboardingData.server_url || !onboardingData.token) {
      setError('Please fill in all required fields');
      return;
    }

    setIsOnboardingLoading(true);
    setError(null);

    try {
      const requestData = {
        ...onboardingData,
        provider_name: selectedProvider,
        tags: onboardingData.tags || []
      };

      const apiUrl = `${getApiBaseUrl()}/cluster/onboard-cluster`;
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Onboarding failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log("Onboarding successful:", data);

      await fetchClusters();

      resetModalState();
      onAddClusterModalClose();

    } catch (err: any) {
      console.error("Onboarding error:", err);
      setError(err.message || 'Onboarding failed');
    } finally {
      setIsOnboardingLoading(false);
    }
  };

  const handleTagsChange = (tagsString: string) => {
    const tags = tagsString.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
    setOnboardingData(prev => ({ ...prev, tags }));
  };

  const renderClusterTable = () => {
    if (loading) {
      return (
        <div className="flex justify-center items-center py-12">
          <div className="text-center">
            <Spinner size="lg" color="primary" />
            <p className="mt-4 text-gray-500">Loading clusters...</p>
          </div>
        </div>
      );
    }

    if (clusters.length === 0) {
      return (
        <div className="text-center py-16">
          <div className="bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-2xl p-8 max-w-md mx-auto">
            <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <Icon icon="mdi:kubernetes" className="text-3xl text-white" />
            </div>
            <h3 className="text-xl font-semibold text-gray-800 dark:text-white mb-2">
              No Clusters Found
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Get started by adding your first Kubernetes cluster
            </p>
            <Button
              color="primary"
              size="lg"
              startContent={<Icon icon="mdi:plus" />}
              onPress={onAddClusterModalOpen}
              className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg hover:shadow-xl transition-all duration-300"
            >
              Add Your First Cluster
            </Button>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {clusters.map((cluster) => {
          const { date, time } = formatDate(cluster.created_at);
          const providerInfo = getProviderInfo(cluster.provider_name);
          
          return (
            <motion.div
              key={cluster.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <Card className={`hover:shadow-lg transition-all duration-300 ${
                cluster.active 
                  ? 'ring-2 ring-blue-500 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20' 
                  : 'hover:ring-1 hover:ring-gray-200'
              }`}>
                <CardBody className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <Avatar
                        icon={<Icon icon={providerInfo.icon} className="text-2xl" />}
                        className={`bg-gradient-to-br ${
                          providerInfo.color === 'primary' ? 'from-blue-500 to-indigo-600' :
                          providerInfo.color === 'warning' ? 'from-orange-500 to-yellow-600' :
                          providerInfo.color === 'success' ? 'from-green-500 to-emerald-600' :
                          providerInfo.color === 'danger' ? 'from-red-500 to-pink-600' :
                          providerInfo.color === 'secondary' ? 'from-purple-500 to-violet-600' :
                          'from-gray-500 to-slate-600'
                        } text-white`}
                        size="lg"
                      />
                      
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
                            {cluster.cluster_name}
                          </h3>
                          {cluster.active && (
                            <Badge 
                              color="success" 
                              variant="flat" 
                              className="bg-gradient-to-r from-green-100 to-emerald-100 text-green-800 border border-green-200"
                            >
                              <Icon icon="mdi:check-circle" className="mr-1" />
                              Active
                            </Badge>
                          )}
                          {cluster.is_operator_installed && (
                            <Badge 
                              color="primary" 
                              variant="flat"
                              className="bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-800 border border-blue-200"
                            >
                              <Icon icon="mdi:robot" className="mr-1" />
                              Operator
                            </Badge>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                          <div className="flex items-center gap-1">
                            <Icon icon="mdi:server" className="text-gray-400" />
                            <span>{cluster.context_name}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Icon icon="mdi:shield-check" className="text-gray-400" />
                            <span>{cluster.use_secure_tls ? 'Secure' : 'Insecure'}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Icon icon="mdi:calendar" className="text-gray-400" />
                            <span>{date}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Chip
                        size="sm"
                        variant="flat"
                        className={`${
                          providerInfo.color === 'primary' ? 'bg-blue-100 text-blue-800' :
                          providerInfo.color === 'warning' ? 'bg-orange-100 text-orange-800' :
                          providerInfo.color === 'success' ? 'bg-green-100 text-green-800' :
                          providerInfo.color === 'danger' ? 'bg-red-100 text-red-800' :
                          providerInfo.color === 'secondary' ? 'bg-purple-100 text-purple-800' :
                          'bg-gray-100 text-gray-800'
                        }`}
                      >
                        <Icon icon={providerInfo.icon} className="mr-1" />
                        {cluster.provider_name}
                      </Chip>

                      <div className="flex items-center gap-1">
                        {!cluster.active && (
                          <Button
                            size="sm"
                            color="primary"
                            variant="flat"
                            onPress={() => activateCluster(cluster.id)}
                            isLoading={loading}
                            className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:from-blue-600 hover:to-indigo-700"
                          >
                            <Icon icon="mdi:play" className="mr-1" />
                            Activate
                          </Button>
                        )}
                        
                        <Button
                          size="sm"
                          variant="light"
                          isIconOnly
                          onPress={() => openDetailsModal(cluster)}
                          className="hover:bg-gray-100 dark:hover:bg-gray-800"
                        >
                          <Icon icon="mdi:eye" />
                        </Button>
                        
                        <Button
                          size="sm"
                          color="danger"
                          variant="light"
                          isIconOnly
                          onPress={() => openDeleteModal(cluster)}
                          className="hover:bg-red-50 dark:hover:bg-red-900/20"
                        >
                          <Icon icon="mdi:delete" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardBody>
              </Card>
            </motion.div>
          );
        })}
      </div>
    );
  };

  const renderNamespacesList = () => {
    if (!activeClusterId) {
      return (
        <div className="text-center py-16">
          <div className="bg-gradient-to-br from-purple-50 to-pink-100 dark:from-purple-900/20 dark:to-pink-900/20 rounded-2xl p-8 max-w-md mx-auto">
            <div className="bg-gradient-to-br from-purple-500 to-pink-600 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <Icon icon="mdi:namespace" className="text-3xl text-white" />
            </div>
            <h3 className="text-xl font-semibold text-gray-800 dark:text-white mb-2">
              No Active Cluster
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Activate a cluster to view its namespaces
            </p>
          </div>
        </div>
      );
    }

    if (namespaces.length === 0) {
      return (
        <div className="text-center py-16">
          <div className="bg-gradient-to-br from-yellow-50 to-orange-100 dark:from-yellow-900/20 dark:to-orange-900/20 rounded-2xl p-8 max-w-md mx-auto">
            <div className="bg-gradient-to-br from-yellow-500 to-orange-600 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <Icon icon="mdi:namespace-outline" className="text-3xl text-white" />
            </div>
            <h3 className="text-xl font-semibold text-gray-800 dark:text-white mb-2">
              No Namespaces Found
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              The active cluster may not have any namespaces or connection failed
              </p>
            <Button
              size="sm"
              variant="flat"
              startContent={<Icon icon="mdi:refresh" />}
              onPress={fetchNamespaces}
              className="bg-gradient-to-r from-yellow-500 to-orange-600 text-white"
            >
              Retry Connection
            </Button>
          </div>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {namespaces.map((namespace, index) => (
          <motion.div
            key={namespace}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
          >
            <Card className="hover:shadow-lg transition-all duration-300 hover:scale-105 bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 border border-gray-200 dark:border-gray-700">
              <CardBody className="p-4">
                <div className="flex items-center gap-3">
                  <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg p-2">
                    <Icon icon="mdi:namespace" className="text-xl text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-800 dark:text-white">{namespace}</p>
                    <p className="text-xs text-gray-500">Namespace</p>
                  </div>
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              </CardBody>
            </Card>
          </motion.div>
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-blue-900">
      <div className="container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header Section */}
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                Kubernetes Clusters
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2 text-lg">
                Manage your Kubernetes cluster configurations and namespaces
              </p>
            </div>
            <Button
              color="primary"
              size="lg"
              startContent={<Icon icon="mdi:plus" className="text-xl" />}
              onPress={onAddClusterModalOpen}
              className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
            >
              Add Cluster
            </Button>
          </div>

          {/* Error Alert */}
          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mb-6"
            >
              <Card className="border-l-4 border-l-red-500 bg-gradient-to-r from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20">
                <CardBody>
                  <div className="flex items-center gap-3">
                    <div className="bg-red-500 rounded-full p-1">
                      <Icon icon="mdi:alert-circle" className="text-white text-lg" />
                    </div>
                    <p className="text-red-700 dark:text-red-300 flex-1">{error}</p>
                    <Button
                      size="sm"
                      variant="light"
                      isIconOnly
                      onPress={() => setError(null)}
                      className="hover:bg-red-100 dark:hover:bg-red-800/20"
                    >
                      <Icon icon="mdi:close" />
                    </Button>
                  </div>
                </CardBody>
              </Card>
            </motion.div>
          )}

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Card className="bg-gradient-to-br from-blue-500 to-indigo-600 text-white">
              <CardBody className="p-6">
                <div className="flex items-center gap-4">
                  <div className="bg-white/20 rounded-lg p-3">
                    <Icon icon="mdi:kubernetes" className="text-2xl" />
                  </div>
                  <div>
                    <p className="text-blue-100">Total Clusters</p>
                    <p className="text-2xl font-bold">{clusters.length}</p>
                  </div>
                </div>
              </CardBody>
            </Card>

            <Card className="bg-gradient-to-br from-green-500 to-emerald-600 text-white">
              <CardBody className="p-6">
                <div className="flex items-center gap-4">
                  <div className="bg-white/20 rounded-lg p-3">
                    <Icon icon="mdi:check-circle" className="text-2xl" />
                  </div>
                  <div>
                    <p className="text-green-100">Active Clusters</p>
                    <p className="text-2xl font-bold">{clusters.filter(c => c.active).length}</p>
                  </div>
                </div>
              </CardBody>
            </Card>

            <Card className="bg-gradient-to-br from-purple-500 to-pink-600 text-white">
              <CardBody className="p-6">
                <div className="flex items-center gap-4">
                  <div className="bg-white/20 rounded-lg p-3">
                    <Icon icon="mdi:namespace" className="text-2xl" />
                  </div>
                  <div>
                    <p className="text-purple-100">Namespaces</p>
                    <p className="text-2xl font-bold">{namespaces.length}</p>
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Main Content Tabs */}
          <Card className="shadow-xl bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
            <CardBody className="p-0">
              <Tabs
                selectedKey={selectedTab}
                onSelectionChange={(key) => setSelectedTab(key as string)}
                className="w-full"
                classNames={{
                  tabList: "bg-gradient-to-r from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 rounded-t-lg",
                  tab: "text-gray-600 dark:text-gray-400 data-[selected=true]:text-blue-600 dark:data-[selected=true]:text-blue-400",
                  tabContent: "group-data-[selected=true]:text-blue-600 dark:group-data-[selected=true]:text-blue-400 font-semibold",
                  panel: "p-6"
                }}
              >
                <Tab 
                  key="manage" 
                  title={
                    <div className="flex items-center gap-2">
                      <Icon icon="mdi:kubernetes" className="text-lg" />
                      <span>Clusters ({clusters.length})</span>
                    </div>
                  }
                >
                  {renderClusterTable()}
                </Tab>

                <Tab 
                  key="namespaces" 
                  title={
                    <div className="flex items-center gap-2">
                      <Icon icon="mdi:namespace" className="text-lg" />
                      <span>Namespaces ({namespaces.length})</span>
                    </div>
                  }
                >
                  <div className="space-y-6">
                    <div className="flex justify-between items-center">
                      <div>
                        <h3 className="text-xl font-semibold text-gray-800 dark:text-white">
                          {activeClusterId ? 
                            `Namespaces - ${clusters.find(c => c.id === activeClusterId)?.cluster_name}` : 
                            'Namespaces'
                          }
                        </h3>
                        <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
                          {activeClusterId ? 
                            `${namespaces.length} namespaces found in active cluster` :
                            'Select an active cluster to view namespaces'
                          }
                        </p>
                      </div>
                      {activeClusterId && (
                        <Button
                          size="sm"
                          variant="flat"
                          startContent={<Icon icon="mdi:refresh" />}
                          onPress={fetchNamespaces}
                          className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white"
                        >
                          Refresh
                        </Button>
                      )}
                    </div>
                    {renderNamespacesList()}
                  </div>
                </Tab>
              </Tabs>
            </CardBody>
          </Card>

          {/* Add Cluster Modal */}
          <Modal
            isOpen={isAddClusterModalOpen}
            onClose={handleModalClose}
            size="3xl"
            scrollBehavior="inside"
            isDismissable={!isUploading && !isOnboardingLoading}
            hideCloseButton={isUploading || isOnboardingLoading}
            classNames={{
              backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20",
              base: "border-[#292f46] bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800",
              header: "border-b-[1px] border-[#292f46]",
              body: "py-6",
              closeButton: "hover:bg-white/5 active:bg-white/10",
            }}
          >
            <ModalContent>
              <ModalHeader className="flex flex-col gap-1">
                <div className="flex items-center gap-3">
                  <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg p-2">
                    <Icon icon="mdi:kubernetes" className="text-2xl text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-800 dark:text-white">Add Kubernetes Cluster</h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Connect your cluster using kubeconfig or manual configuration</p>
                  </div>
                </div>
              </ModalHeader>
              <ModalBody>
                <Tabs
                  selectedKey={addClusterMethod}
                  onSelectionChange={(key) => setAddClusterMethod(key as string)}
                  className="mb-6"
                  classNames={{
                    tabList: "bg-gradient-to-r from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 rounded-lg p-1",
                    tab: "data-[selected=true]:bg-white dark:data-[selected=true]:bg-gray-600 data-[selected=true]:shadow-md",
                    tabContent: "group-data-[selected=true]:text-blue-600 dark:group-data-[selected=true]:text-blue-400 font-medium"
                  }}
                >
                  <Tab key="upload" title={
                    <div className="flex items-center gap-2">
                      <Icon icon="mdi:upload" />
                      <span>Upload Kubeconfig</span>
                    </div>
                  }>
                    <div className="space-y-6">
                      <div
                        className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-12 text-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all duration-300"
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                        onClick={triggerFileInput}
                      >
                        <input
                          id="file-input"
                          type="file"
                          accept=".yaml,.yml"
                          onChange={handleFileSelect}
                          className="hidden"
                        />
                        <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                          <Icon icon="mdi:cloud-upload" className="text-3xl text-white" />
                        </div>
                        <p className="text-xl font-semibold text-gray-800 dark:text-white mb-2">
                          {selectedFile ? selectedFile.name : "Drop your kubeconfig file here"}
                        </p>
                        <p className="text-gray-500">
                          or click to browse files (.yaml, .yml)
                        </p>
                      </div>

                      {kubeconfigContent && (
                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Kubeconfig Content Preview:
                          </label>
                          <Textarea
                            value={kubeconfigContent}
                            onChange={(e) => setKubeconfigContent(e.target.value)}
                            placeholder="Paste your kubeconfig content here..."
                            minRows={8}
                            maxRows={12}
                            className="font-mono text-sm"
                            classNames={{
                              input: "bg-gray-50 dark:bg-gray-800"
                            }}
                          />
                        </div>
                      )}

                      <Select
                        label="Provider"
                        placeholder="Select cluster provider"
                        selectedKeys={[selectedProvider]}
                        onSelectionChange={(keys) => {
                          const selected = Array.from(keys)[0] as string;
                          setSelectedProvider(selected);
                        }}
                        classNames={{
                          trigger: "bg-gray-50 dark:bg-gray-800"
                        }}
                      >
                        {providerOptions.map((provider) => (
                          <SelectItem key={provider.key} value={provider.key}>
                                                        <div className="flex items-center gap-2">
                              <Icon icon={provider.icon} />
                              <span>{provider.label}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </Select>

                      {isUploading && (
                        <div className="space-y-3">
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-600 dark:text-gray-400">Uploading cluster configuration...</span>
                            <span className="font-semibold text-blue-600">{uploadProgress}%</span>
                          </div>
                          <Progress 
                            value={uploadProgress} 
                            color="primary" 
                            className="w-full"
                            classNames={{
                              track: "drop-shadow-md border border-default",
                              indicator: "bg-gradient-to-r from-blue-500 to-indigo-600",
                            }}
                          />
                        </div>
                      )}
                    </div>
                  </Tab>

                  <Tab key="manual" title={
                    <div className="flex items-center gap-2">
                      <Icon icon="mdi:cog" />
                      <span>Manual Configuration</span>
                    </div>
                  }>
                    <ScrollShadow className="max-h-96">
                      <div className="space-y-6 pr-2">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <Input
                            label="Cluster Name"
                            placeholder="Enter cluster name"
                            value={onboardingData.cluster_name}
                            onChange={(e) => setOnboardingData(prev => ({ ...prev, cluster_name: e.target.value }))}
                            isRequired
                            startContent={<Icon icon="mdi:kubernetes" className="text-gray-400" />}
                            classNames={{
                              input: "bg-gray-50 dark:bg-gray-800"
                            }}
                          />

                          <Input
                            label="Context Name"
                            placeholder="Enter context name (optional)"
                            value={onboardingData.context_name}
                            onChange={(e) => setOnboardingData(prev => ({ ...prev, context_name: e.target.value }))}
                            startContent={<Icon icon="mdi:server" className="text-gray-400" />}
                            classNames={{
                              input: "bg-gray-50 dark:bg-gray-800"
                            }}
                          />
                        </div>

                        <Input
                          label="Server URL"
                          placeholder="https://kubernetes.example.com:6443"
                          value={onboardingData.server_url}
                          onChange={(e) => setOnboardingData(prev => ({ ...prev, server_url: e.target.value }))}
                          isRequired
                          startContent={<Icon icon="mdi:web" className="text-gray-400" />}
                          classNames={{
                            input: "bg-gray-50 dark:bg-gray-800"
                          }}
                        />

                        <Textarea
                          label="Bearer Token"
                          placeholder="Enter your bearer token"
                          value={onboardingData.token}
                          onChange={(e) => setOnboardingData(prev => ({ ...prev, token: e.target.value }))}
                          minRows={3}
                          isRequired
                          startContent={<Icon icon="mdi:key" className="text-gray-400" />}
                          classNames={{
                            input: "bg-gray-50 dark:bg-gray-800 font-mono"
                          }}
                        />

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <Select
                            label="Provider"
                            placeholder="Select cluster provider"
                            selectedKeys={[selectedProvider]}
                            onSelectionChange={(keys) => {
                              const selected = Array.from(keys)[0] as string;
                              setSelectedProvider(selected);
                              setOnboardingData(prev => ({ ...prev, provider_name: selected }));
                            }}
                            classNames={{
                              trigger: "bg-gray-50 dark:bg-gray-800"
                            }}
                          >
                            {providerOptions.map((provider) => (
                              <SelectItem key={provider.key} value={provider.key}>
                                <div className="flex items-center gap-2">
                                  <Icon icon={provider.icon} />
                                  <span>{provider.label}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </Select>

                          <Input
                            label="Tags"
                            placeholder="Enter tags separated by commas"
                            value={onboardingData.tags.join(', ')}
                            onChange={(e) => handleTagsChange(e.target.value)}
                            startContent={<Icon icon="mdi:tag" className="text-gray-400" />}
                            classNames={{
                              input: "bg-gray-50 dark:bg-gray-800"
                            }}
                          />
                        </div>

                        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-4">
                          <Checkbox
                            isSelected={onboardingData.use_secure_tls}
                            onValueChange={(checked) => setOnboardingData(prev => ({ ...prev, use_secure_tls: checked }))}
                            classNames={{
                              label: "text-gray-700 dark:text-gray-300 font-medium"
                            }}
                          >
                            <div className="flex items-center gap-2">
                              <Icon icon="mdi:shield-check" />
                              <span>Use Secure TLS</span>
                            </div>
                          </Checkbox>
                          <p className="text-xs text-gray-500 mt-1 ml-6">
                            Enable this for production clusters with proper TLS certificates
                          </p>
                        </div>

                        {onboardingData.use_secure_tls && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="space-y-4 pl-6 border-l-2 border-blue-500 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/10 dark:to-indigo-900/10 rounded-r-lg p-4"
                          >
                            <div className="flex items-center gap-2 mb-4">
                              <Icon icon="mdi:certificate" className="text-blue-600" />
                              <h4 className="font-semibold text-gray-800 dark:text-white">TLS Certificate Configuration</h4>
                            </div>

                            <Textarea
                              label="CA Certificate Data (Base64)"
                              placeholder="Enter CA certificate data"
                              value={onboardingData.ca_data || ''}
                              onChange={(e) => setOnboardingData(prev => ({ ...prev, ca_data: e.target.value }))}
                              minRows={3}
                              classNames={{
                                input: "bg-white dark:bg-gray-800 font-mono text-xs"
                              }}
                            />

                            <Textarea
                              label="Client Certificate Data (Base64)"
                              placeholder="Enter client certificate data"
                              value={onboardingData.tls_cert || ''}
                              onChange={(e) => setOnboardingData(prev => ({ ...prev, tls_cert: e.target.value }))}
                              minRows={3}
                              classNames={{
                                input: "bg-white dark:bg-gray-800 font-mono text-xs"
                              }}
                            />

                            <Textarea
                              label="Client Key Data (Base64)"
                              placeholder="Enter client key data"
                              value={onboardingData.tls_key || ''}
                              onChange={(e) => setOnboardingData(prev => ({ ...prev, tls_key: e.target.value }))}
                              minRows={3}
                              classNames={{
                                input: "bg-white dark:bg-gray-800 font-mono text-xs"
                              }}
                            />
                          </motion.div>
                        )}
                      </div>
                    </ScrollShadow>
                  </Tab>
                </Tabs>

                {error && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                  >
                    <Card className="border-l-4 border-l-red-500 bg-gradient-to-r from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20">
                      <CardBody className="p-4">
                        <div className="flex items-center gap-3">
                          <div className="bg-red-500 rounded-full p-1">
                            <Icon icon="mdi:alert-circle" className="text-white text-lg" />
                          </div>
                          <p className="text-red-700 dark:text-red-300 text-sm flex-1">{error}</p>
                        </div>
                      </CardBody>
                    </Card>
                  </motion.div>
                )}
              </ModalBody>
              <ModalFooter className="border-t border-gray-200 dark:border-gray-700">
                <Button
                  variant="light"
                  onPress={handleModalClose}
                  isDisabled={isUploading || isOnboardingLoading}
                  className="hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Cancel
                </Button>
                {addClusterMethod === "upload" ? (
                  <Button
                    color="primary"
                    onPress={uploadKubeconfig}
                    isLoading={isUploading}
                    isDisabled={!selectedFile && !kubeconfigContent}
                    className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg hover:shadow-xl"
                  >
                    {isUploading ? (
                      <div className="flex items-center gap-2">
                        <Spinner size="sm" color="white" />
                        <span>Uploading...</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Icon icon="mdi:upload" />
                        <span>Upload Cluster</span>
                      </div>
                    )}
                  </Button>
                ) : (
                  <Button
                    color="primary"
                    onPress={handleManualOnboarding}
                    isLoading={isOnboardingLoading}
                    isDisabled={!onboardingData.cluster_name || !onboardingData.server_url || !onboardingData.token}
                    className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg hover:shadow-xl"
                  >
                    {isOnboardingLoading ? (
                      <div className="flex items-center gap-2">
                        <Spinner size="sm" color="white" />
                        <span>Adding...</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Icon icon="mdi:plus" />
                        <span>Add Cluster</span>
                      </div>
                    )}
                  </Button>
                )}
              </ModalFooter>
            </ModalContent>
          </Modal>

          {/* Delete Confirmation Modal */}
          <Modal 
            isOpen={isDeleteModalOpen} 
            onClose={onDeleteModalClose}
            classNames={{
              backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20",
              base: "border-[#292f46] bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800",
            }}
          >
            <ModalContent>
              <ModalHeader>
                <div className="flex items-center gap-3">
                  <div className="bg-gradient-to-br from-red-500 to-pink-600 rounded-lg p-2">
                    <Icon icon="mdi:alert-circle" className="text-2xl text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-800 dark:text-white">Confirm Deletion</h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400">This action cannot be undone</p>
                  </div>
                </div>
              </ModalHeader>
              <ModalBody>
                <div className="bg-gradient-to-r from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20 rounded-lg p-4">
                  <p className="text-gray-800 dark:text-white">
                    Are you sure you want to delete the cluster{" "}
                    <strong className="text-red-600 dark:text-red-400">{clusterToDelete?.cluster_name}</strong>?
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                    The cluster configuration will be permanently removed from your account.
                  </p>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button 
                  variant="light" 
                  onPress={onDeleteModalClose}
                  className="hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Cancel
                </Button>
                <Button
                  color="danger"
                  onPress={deleteCluster}
                  isLoading={loading}
                  className="bg-gradient-to-r from-red-500 to-pink-600 text-white shadow-lg hover:shadow-xl"
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <Spinner size="sm" color="white" />
                      <span>Deleting...</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <Icon icon="mdi:delete" />
                      <span>Delete Cluster</span>
                    </div>
                  )}
                </Button>
              </ModalFooter>
            </ModalContent>
          </Modal>

          {/* Cluster Details Modal */}
          <Modal 
            isOpen={isDetailsModalOpen} 
            onClose={onDetailsModalClose} 
            size="3xl"
            classNames={{
              backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20",
              base: "border-[#292f46] bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800",
            }}
          >
            <ModalContent>
              <ModalHeader>
              <div className="flex items-center gap-3">
                  <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg p-2">
                    <Icon icon="mdi:information" className="text-2xl text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-800 dark:text-white">Cluster Details</h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400">View cluster configuration and status</p>
                  </div>
                </div>
              </ModalHeader>
              <ModalBody>
                {selectedClusterDetails && (
                  <div className="space-y-6">
                    {/* Cluster Header */}
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-6">
                      <div className="flex items-center gap-4">
                        <Avatar
                          icon={<Icon icon={getProviderInfo(selectedClusterDetails.provider_name).icon} className="text-2xl" />}
                          className="bg-gradient-to-br from-blue-500 to-indigo-600 text-white"
                          size="lg"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-2xl font-bold text-gray-800 dark:text-white">
                              {selectedClusterDetails.cluster_name}
                            </h3>
                            {selectedClusterDetails.active && (
                              <Badge color="success" variant="flat" className="bg-green-100 text-green-800">
                                <Icon icon="mdi:check-circle" className="mr-1" />
                                Active
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                            <Chip size="sm" variant="flat" color="primary">
                              <Icon icon={getProviderInfo(selectedClusterDetails.provider_name).icon} className="mr-1" />
                              {selectedClusterDetails.provider_name}
                            </Chip>
                            <div className="flex items-center gap-1">
                              <Icon icon="mdi:calendar" />
                              <span>Created {formatDate(selectedClusterDetails.created_at).date}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Configuration Details */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <Card className="bg-gradient-to-br from-gray-50 to-white dark:from-gray-800 dark:to-gray-700">
                        <CardHeader className="pb-2">
                          <div className="flex items-center gap-2">
                            <Icon icon="mdi:server" className="text-blue-600" />
                            <h4 className="font-semibold text-gray-800 dark:text-white">Connection</h4>
                          </div>
                        </CardHeader>
                        <CardBody className="pt-0 space-y-3">
                          <div>
                            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Server URL</label>
                            <Code className="text-xs mt-1 w-full">{selectedClusterDetails.server_url}</Code>
                          </div>
                          <div>
                            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Context</label>
                            <p className="text-sm text-gray-800 dark:text-white mt-1">{selectedClusterDetails.context_name}</p>
                          </div>
                        </CardBody>
                      </Card>

                      <Card className="bg-gradient-to-br from-gray-50 to-white dark:from-gray-800 dark:to-gray-700">
                        <CardHeader className="pb-2">
                          <div className="flex items-center gap-2">
                            <Icon icon="mdi:shield-check" className="text-green-600" />
                            <h4 className="font-semibold text-gray-800 dark:text-white">Security</h4>
                          </div>
                        </CardHeader>
                        <CardBody className="pt-0 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600 dark:text-gray-400">TLS Security</span>
                            <Chip 
                              size="sm" 
                              variant="flat" 
                              color={selectedClusterDetails.use_secure_tls ? 'success' : 'warning'}
                              className={selectedClusterDetails.use_secure_tls ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}
                            >
                              {selectedClusterDetails.use_secure_tls ? 'Secure' : 'Insecure'}
                            </Chip>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600 dark:text-gray-400">Operator Installed</span>
                            <Chip 
                              size="sm" 
                              variant="flat" 
                              color={selectedClusterDetails.is_operator_installed ? 'success' : 'default'}
                              className={selectedClusterDetails.is_operator_installed ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}
                            >
                              {selectedClusterDetails.is_operator_installed ? 'Yes' : 'No'}
                            </Chip>
                          </div>
                        </CardBody>
                      </Card>
                    </div>

                    {/* Tags */}
                    {selectedClusterDetails.tags && selectedClusterDetails.tags.length > 0 && (
                      <Card className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20">
                        <CardHeader className="pb-2">
                          <div className="flex items-center gap-2">
                            <Icon icon="mdi:tag" className="text-purple-600" />
                            <h4 className="font-semibold text-gray-800 dark:text-white">Tags</h4>
                          </div>
                        </CardHeader>
                        <CardBody className="pt-0">
                          <div className="flex flex-wrap gap-2">
                            {selectedClusterDetails.tags.map((tag, index) => (
                              <Chip 
                                key={index} 
                                size="sm" 
                                variant="flat"
                                className="bg-purple-100 text-purple-800"
                              >
                                {tag}
                              </Chip>
                            ))}
                          </div>
                        </CardBody>
                      </Card>
                    )}

                    <Divider />

                    {/* Quick Actions */}
                    <div className="bg-gradient-to-r from-gray-50 to-white dark:from-gray-800 dark:to-gray-700 rounded-lg p-6">
                      <div className="flex justify-between items-center">
                        <div>
                          <h4 className="font-semibold text-gray-800 dark:text-white mb-1">Quick Actions</h4>
                          <p className="text-sm text-gray-600 dark:text-gray-400">Manage this cluster</p>
                        </div>
                        <div className="flex gap-3">
                          {!selectedClusterDetails.active && (
                            <Button
                              size="sm"
                              color="primary"
                              variant="flat"
                              onPress={() => {
                                activateCluster(selectedClusterDetails.id);
                                onDetailsModalClose();
                              }}
                              className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white"
                            >
                              <Icon icon="mdi:play" className="mr-1" />
                              Activate
                            </Button>
                          )}
                          <Button
                            size="sm"
                            color="danger"
                            variant="flat"
                            onPress={() => {
                              onDetailsModalClose();
                              openDeleteModal(selectedClusterDetails);
                            }}
                            className="bg-gradient-to-r from-red-500 to-pink-600 text-white"
                          >
                            <Icon icon="mdi:delete" className="mr-1" />
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </ModalBody>
              <ModalFooter>
                <Button 
                  variant="light" 
                  onPress={onDetailsModalClose}
                  className="hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Close
                </Button>
              </ModalFooter>
            </ModalContent>
          </Modal>
        </motion.div>
      </div>
    </div>
  );
};

export default UploadKubeconfig;



