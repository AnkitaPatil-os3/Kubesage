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
 
interface KubeconfigFile {
  filename: string;
  original_filename: string;
  cluster_name: string;
  context_name: string;
  active: boolean;
  upload_date: string;
}
 
interface ClusterInfo {
  filename: string;
  cluster_name: string;
  active: boolean;
}
 
interface OnboardingData {
  clusterName: string;
  serverUrl: string;
  bearerToken: string;
}
 
export const UploadKubeconfig: React.FC = () => {
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
 
  // Onboarding form state
  const [isOnboardingLoading, setIsOnboardingLoading] = React.useState(false);
  const [onboardingData, setOnboardingData] = React.useState<OnboardingData>({
    clusterName: '',
    serverUrl: '',
    bearerToken: ''
  });
 
  const getAuthToken = () => {
    return localStorage.getItem('access_token') || '';
  }
 
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
        throw new Error(`Failed to fetch kubeconfig list: ${response.statusText}`);
      }
 
      const data = await response.json();
      console.log('Kubeconfig list response:', data);
 
      if (data && Array.isArray(data.kubeconfigs)) {
        setKubeconfigFiles(data.kubeconfigs);
      } else {
        console.warn('Unexpected kubeconfig list format:', data);
        setKubeconfigFiles([]);
      }
    } catch (err: any) {
      console.error("Error fetching kubeconfig list:", err);
      setError(err.message || 'Failed to fetch kubeconfig list');
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
 
      setSelectedFile(null);
      setKubeconfigContent("");
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
      console.error("Failed to activate kubeconfig:", error);
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
        throw new Error(`Failed to remove kubeconfig: ${response.status} ${response.statusText}`);
      }
 
      const result = await response.json();
      console.log("Remove successful:", result);
 
      await fetchKubeconfigList();
      await fetchClusters();
 
      onDeleteModalClose();
      setClusterToDelete(null);
 
    } catch (error: any) {
      console.error("Failed to remove kubeconfig:", error);
      setError(error.message || 'Failed to remove kubeconfig');
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
 
      // Reset form
      setOnboardingData({
        clusterName: '',
        serverUrl: '',
        bearerToken: ''
      });
 
      onAddClusterModalClose();
 
    } catch (err: any) {
      console.error("Add cluster error:", err);
      setError(err.message || 'Failed to add cluster');
    } finally {
      setIsOnboardingLoading(false);
    }
  };
 
  const { isOpen: isCommandsModalOpen, onOpen: onCommandsModalOpen, onClose: onCommandsModalClose } = useDisclosure();
 
  const renderOnboardingContent = () => {
    return (
      <div className="space-y-6">
        <div className="text-center">
          {/* <h3 className="text-2xl font-bold text-gray-800 mb-2">Add Cluster with Credentials</h3> */}
          <p className="text-gray-600">Enter your cluster details to connect</p>
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
          
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Server URL *</label>
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
              <label className="text-sm font-medium">Bearer Token *</label>
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
              KubeSage Cluster Management
            </h1>
            <p className="text-gray-600 mt-2">
              Manage your Kubernetes clusters and configurations with AI-powered insights
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
            <Card className="bg-gradient-to-r from-blue-500 to-purple-600 text-white">
              <CardBody className="flex flex-row items-center gap-4">
                <Icon icon="mdi:file-document" className="text-3xl" />
                <div>
                  <p className="text-sm opacity-80">Total Kubeconfigs</p>
                  <p className="text-2xl font-bold">{totalKubeconfigs}</p>
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
 
          <motion.div whileHover={{ scale: 1.02 }}>
            <Card className="bg-gradient-to-r from-orange-500 to-red-600 text-white">
              <CardBody className="flex flex-row items-center gap-4">
                <Icon icon="mdi:check-circle" className="text-3xl" />
                <div>
                  <p className="text-sm opacity-80">Active Configs</p>
                  <p className="text-2xl font-bold">{activeKubeconfigs}</p>
                </div>
              </CardBody>
            </Card>
          </motion.div>
 
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
                    <TableColumn>FILENAME</TableColumn>
                    <TableColumn>CONTEXT</TableColumn>
                    <TableColumn>STATUS</TableColumn>
                    <TableColumn>UPLOAD DATE</TableColumn>
                    <TableColumn>ACTIONS</TableColumn>
                  </TableHeader>
                  <TableBody>
                    {kubeconfigFiles.map((file, index) => (
                      <TableRow key={index}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Icon icon="mdi:kubernetes" className="text-blue-500" />
                            <div>
                              <span className="font-medium">{file.cluster_name}</span>
                              <p className="text-xs text-foreground-500">Cluster</p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Icon icon="mdi:file-document" className="text-foreground-400" />
                            <div>
                              <span className="font-mono text-sm">{file.original_filename}</span>
                              <p className="text-xs text-foreground-500">Config File</p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Code className="text-sm">{file.context_name}</Code>
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
                          <div>
                            <span className="text-sm">{new Date(file.upload_date).toLocaleDateString()}</span>
                            <p className="text-xs text-foreground-500">{new Date(file.upload_date).toLocaleTimeString()}</p>
                          </div>
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
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </CardBody>
        </Card>
      </motion.div>
 
      {/* Add Cluster Modal - Colorful Style */}
      <Modal
        isOpen={isAddClusterModalOpen}
        onClose={onAddClusterModalClose}
        size="5xl"
        scrollBehavior="inside"
        classNames={{
          backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20"
        }}
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1 bg-gradient-to-r from-blue-500 to-purple-600 text-white">
            <div className="flex items-center gap-3">
              <Icon icon="mdi:plus-circle" className="text-2xl" />
              <span className="text-xl font-bold">Add New Cluster</span>
            </div>
            <p className="text-sm opacity-90 font-normal">
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
                cursor: "w-full bg-gradient-to-r from-blue-500 to-purple-600",
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
                  <Card className="bg-gradient-to-r from-blue-100 to-purple-100 border-l-4 border-blue-500">
                    <CardBody>
                      <div className="flex items-start gap-4">
                        <Icon icon="mdi:information" className="text-2xl text-blue-500 mt-1" />
                        <div>
                          <h4 className="font-semibold text-blue-800">Upload Instructions</h4>
                          <p className="text-blue-700 mt-1">
                            Upload your existing kubeconfig file or paste the YAML content directly.
                            We'll automatically detect cluster information and configure access.
                          </p>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
 
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* File Upload Section */}
                    <Card className="border-2 border-dashed border-primary-200 hover:border-primary-400 transition-colors">
                      <CardHeader className="bg-gradient-to-r from-green-50 to-blue-50">
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                          <Icon icon="mdi:file-upload" className="text-green-600" />
                          Upload Kubeconfig File
                        </h3>
                      </CardHeader>
                      <CardBody className="space-y-4">
                        <div
                          className="p-8 border-2 border-dashed border-content3 rounded-lg text-center hover:border-primary transition-colors cursor-pointer bg-gradient-to-br from-gray-50 to-gray-100"
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
                            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                              <Icon icon="mdi:cloud-upload" className="text-3xl text-white" />
                            </div>
                            <h4 className="font-medium text-lg">
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
                            className="flex items-center justify-between p-4 bg-gradient-to-r from-green-100 to-emerald-100 text-green-700 rounded-lg border border-green-200"
                          >
                            <div className="flex items-center gap-3">
                              <Icon icon="mdi:check-circle" className="text-xl" />
                              <div>
                                <span className="font-medium">{selectedFile.name}</span>
                                <p className="text-xs text-green-600">Ready to upload</p>
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
                    <Card className="border-2 border-dashed border-secondary-200 hover:border-secondary-400 transition-colors">
                      <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50">
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                          <Icon icon="mdi:code-braces" className="text-purple-600" />
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
                            inputWrapper: "bg-gradient-to-br from-gray-50 to-gray-100"
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
                      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border border-primary">
                        <CardBody>
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                                  <Icon icon="mdi:upload" className="text-white" />
                                </div>
                                <span className="font-medium">Uploading kubeconfig...</span>
                              </div>
                              <span className="text-sm text-foreground-500 font-mono">{uploadProgress}%</span>
                            </div>
                            <Progress
                              value={uploadProgress}
                              color="primary"
                              classNames={{
                                indicator: "bg-gradient-to-r from-blue-500 to-purple-600"
                              }}
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
          <ModalFooter className="bg-gradient-to-r from-gray-50 to-gray-100">
            <Button
              color="danger"
              variant="light"
              onPress={onAddClusterModalClose}
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
                className="bg-gradient-to-r from-blue-500 to-purple-600"
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
                className="bg-gradient-to-r from-orange-500 to-red-500"
              >
                Add Cluster
              </Button>
            )}
          </ModalFooter>
        </ModalContent>
      </Modal>
 
      {/* Cluster Details Modal - Colorful Style */}
      <Modal
        isOpen={isDetailsModalOpen}
        onClose={onDetailsModalClose}
        size="3xl"
        scrollBehavior="inside"
        classNames={{
          backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20"
        }}
      >
        <ModalContent>
          <ModalHeader className="bg-gradient-to-r from-green-500 to-teal-600 text-white">
            <div className="flex items-center gap-3">
              <Icon icon="mdi:information-outline" className="text-2xl" />
              <span className="text-xl font-bold">Cluster Details</span>
            </div>
          </ModalHeader>
          <ModalBody className="p-6">
            {selectedClusterDetails && (
              <div className="space-y-6">
                {/* Cluster Summary */}
                <Card className="bg-gradient-to-r from-green-100 to-teal-100 border-l-4 border-green-500">
                  <CardBody>
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-full flex items-center justify-center">
                        <Icon icon="mdi:kubernetes" className="text-2xl text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-bold text-green-800 text-lg">{selectedClusterDetails.cluster_name}</h4>
                        <p className="text-green-700 mt-1">
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
                  <Card className="bg-gradient-to-br from-blue-50 to-blue-100">
                    <CardHeader className="pb-2">
                      <h4 className="font-semibold text-blue-800 flex items-center gap-2">
                        <Icon icon="mdi:file-document" />
                        Configuration File
                      </h4>
                    </CardHeader>
                    <CardBody className="pt-0">
                      <div className="space-y-2">
                        <div>
                          <p className="text-xs text-blue-600 font-medium">Original Filename</p>
                          <Code className="text-sm">{selectedClusterDetails.original_filename}</Code>
                        </div>
                        <div>
                          <p className="text-xs text-blue-600 font-medium">Internal Filename</p>
                          <Code className="text-sm">{selectedClusterDetails.filename}</Code>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
 
                  <Card className="bg-gradient-to-br from-purple-50 to-purple-100">
                    <CardHeader className="pb-2">
                      <h4 className="font-semibold text-purple-800 flex items-center gap-2">
                        <Icon icon="mdi:cog" />
                        Context Information
                      </h4>
                    </CardHeader>
                    <CardBody className="pt-0">
                      <div className="space-y-2">
                        <div>
                          <p className="text-xs text-purple-600 font-medium">Context Name</p>
                          <Code className="text-sm">{selectedClusterDetails.context_name}</Code>
                        </div>
                        <div>
                          <p className="text-xs text-purple-600 font-medium">Cluster Name</p>
                          <Code className="text-sm">{selectedClusterDetails.cluster_name}</Code>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
 
                  <Card className="bg-gradient-to-br from-orange-50 to-orange-100">
                    <CardHeader className="pb-2">
                      <h4 className="font-semibold text-orange-800 flex items-center gap-2">
                        <Icon icon="mdi:calendar" />
                        Timeline
                      </h4>
                    </CardHeader>
                    <CardBody className="pt-0">
                      <div className="space-y-2">
                        <div>
                          <p className="text-xs text-orange-600 font-medium">Upload Date</p>
                          <p className="text-sm">{new Date(selectedClusterDetails.upload_date).toLocaleDateString()}</p>
                        </div>
                        <div>
                          <p className="text-xs text-orange-600 font-medium">Upload Time</p>
                          <p className="text-sm">{new Date(selectedClusterDetails.upload_date).toLocaleTimeString()}</p>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
 
                  <Card className="bg-gradient-to-br from-teal-50 to-teal-100">
                    <CardHeader className="pb-2">
                      <h4 className="font-semibold text-teal-800 flex items-center gap-2">
                        <Icon icon="mdi:shield-check" />
                        Status & Health
                      </h4>
                    </CardHeader>
                    <CardBody className="pt-0">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-teal-600 font-medium">Connection Status</span>
                          <Chip size="sm" color={selectedClusterDetails.active ? 'success' : 'default'} variant="flat">
                            {selectedClusterDetails.active ? 'Connected' : 'Disconnected'}
                          </Chip>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-teal-600 font-medium">Configuration Valid</span>
                          <Chip size="sm" color="success" variant="flat">
                            <Icon icon="mdi:check" className="mr-1" />
                            Valid
                          </Chip>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                </div>
 
                {/* Actions Section */}
                <Card className="bg-gradient-to-r from-gray-50 to-gray-100">
                  <CardHeader>
                    <h4 className="font-semibold flex items-center gap-2">
                      <Icon icon="mdi:lightning-bolt" />
                      Quick Actions
                    </h4>
                  </CardHeader>
                  <CardBody>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
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
                        startContent={<Icon icon="mdi:monitor" />}
                      >
                        Monitor Cluster
                      </Button>
                      <Button
                        color="primary"
                        variant="flat"
                        isDisabled={!selectedClusterDetails.active}
                        startContent={<Icon icon="mdi:console" />}
                      >
                        Open Terminal
                      </Button>
                    </div>
                  </CardBody>
                </Card>
 
                {/* Warning Section */}
                <Card className="bg-gradient-to-r from-yellow-50 to-orange-50 border-l-4 border-yellow-500">
                  <CardBody>
                    <div className="flex items-start gap-3">
                      <Icon icon="mdi:information" className="text-yellow-600 text-xl mt-0.5" />
                      <div>
                        <h4 className="font-semibold text-yellow-800">Important Information</h4>
                        <ul className="text-sm text-yellow-700 mt-2 space-y-1">
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
          <ModalFooter className="bg-gradient-to-r from-gray-50 to-gray-100">
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
              className="bg-gradient-to-r from-green-500 to-teal-600"
            >
              Manage Cluster
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
       
      {/* Delete Confirmation Modal - Colorful Style */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={onDeleteModalClose}
        size="2xl"
        classNames={{
          backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20"
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
              <Card className="bg-gradient-to-r from-red-100 to-pink-100 border-l-4 border-red-500">
                <CardBody>
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-gradient-to-r from-red-500 to-pink-600 rounded-full flex items-center justify-center">
                      <Icon icon="mdi:alert-triangle" className="text-2xl text-white" />
                    </div>
                    <div>
                      <h4 className="font-bold text-red-800">Permanent Deletion Warning</h4>
                      <p className="text-red-700 mt-1">
                        You are about to permanently delete this cluster configuration. This action cannot be undone.
                      </p>
                    </div>
                  </div>
                </CardBody>
              </Card>
 
              {/* Cluster Information */}
              {clusterToDelete && (
                <Card className="bg-gradient-to-br from-gray-50 to-gray-100">
                  <CardHeader className="bg-gradient-to-r from-blue-50 to-purple-50">
                    <h4 className="font-semibold flex items-center gap-2">
                      <Icon icon="mdi:kubernetes" className="text-blue-600" />
                      Cluster to be Deleted
                    </h4>
                  </CardHeader>
                  <CardBody>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-1">Cluster Name</p>
                        <div className="flex items-center gap-2">
                          <Icon icon="mdi:server" className="text-primary" />
                          <span className="font-medium">{clusterToDelete.cluster_name}</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-1">Configuration File</p>
                        <div className="flex items-center gap-2">
                          <Icon icon="mdi:file-document" className="text-secondary" />
                          <Code className="text-sm">{clusterToDelete.original_filename}</Code>
                        </div>
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-1">Context</p>
                        <Code className="text-sm">{clusterToDelete.context_name}</Code>
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-1">Upload Date</p>
                        <div className="flex items-center gap-2">
                          <Icon icon="mdi:calendar" className="text-warning" />
                          <span className="text-sm">{new Date(clusterToDelete.upload_date).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
 
                    {clusterToDelete.active && (
                      <div className="mt-4 p-3 bg-gradient-to-r from-orange-100 to-red-100 rounded-lg border border-orange-200">
                        <div className="flex items-center gap-2">
                          <Icon icon="mdi:alert" className="text-orange-600" />
                          <span className="text-sm font-medium text-orange-800">
                            This is your currently active cluster!
                          </span>
                        </div>
                      </div>
                    )}
                  </CardBody>
                </Card>
              )}
 
              {/* Consequences */}
              <Card className="bg-gradient-to-r from-yellow-50 to-orange-50 border-l-4 border-yellow-500">
                <CardBody>
                  <div className="flex items-start gap-3">
                    <Icon icon="mdi:information" className="text-yellow-600 text-xl mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-yellow-800 mb-2">What will happen:</h4>
                      <ul className="text-sm text-yellow-700 space-y-1">
                        <li className="flex items-center gap-2">
                          <Icon icon="mdi:close-circle" className="text-red-500" />
                          The cluster configuration will be permanently removed
                        </li>
                        <li className="flex items-center gap-2">
                          <Icon icon="mdi:close-circle" className="text-red-500" />
                          You will lose access to this cluster through KubeSage
                        </li>
                        <li className="flex items-center gap-2">
                          <Icon icon="mdi:close-circle" className="text-red-500" />
                          All monitoring and management features will be disabled
                        </li>
                        <li className="flex items-center gap-2">
                          <Icon icon="mdi:information" className="text-blue-500" />
                          The actual Kubernetes cluster will remain unaffected
                        </li>
                      </ul>
                    </div>
                  </div>
                </CardBody>
              </Card>
 
              {/* Confirmation Input */}
              <Card className="bg-gradient-to-r from-red-50 to-pink-50">
                <CardBody>
                  <div className="space-y-3">
                    <p className="text-sm font-medium text-red-800">
                      To confirm deletion, please type the cluster name below:
                    </p>
                    <Input
                      placeholder={clusterToDelete?.cluster_name || "cluster-name"}
                      variant="bordered"
                      classNames={{
                        input: "font-mono",
                        inputWrapper: "border-red-200 focus-within:border-red-400"
                      }}
                    />
                    <p className="text-xs text-red-600">
                      Expected: <Code className="text-xs">{clusterToDelete?.cluster_name}</Code>
                    </p>
                  </div>
                </CardBody>
              </Card>
            </div>
          </ModalBody>
          <ModalFooter className="bg-gradient-to-r from-gray-50 to-gray-100">
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
              className="bg-gradient-to-r from-red-500 to-pink-600"
            >
              Delete Permanently
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
 
      {/* Commands Help Modal */}
<Modal
  isOpen={isCommandsModalOpen}
  onClose={onCommandsModalClose}
  size="4xl"
  scrollBehavior="inside"
  classNames={{
    backdrop: "bg-gradient-to-t from-zinc-900 to-zinc-900/10 backdrop-opacity-20"
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
        {/* Step 1 */}
        <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-l-4 border-green-500">
          <CardHeader>
            <h4 className="font-bold text-green-800 flex items-center gap-2">
              <div className="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
              Download the Script
            </h4>
          </CardHeader>
          <CardBody>
            <p className="text-green-700 mb-3">First, download the Kubernetes service account export script:</p>
            <div className="bg-gray-900 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-green-400 text-sm font-mono">Terminal</span>
                <Button
                  size="sm"
                  variant="flat"
                  color="success"
                  onPress={() => {
                    navigator.clipboard.writeText('curl -O http://10.0.34.169:3000/devendra/k8s/raw/branch/main/kubeconfig-exporter/kubernetes_export_sa.sh');
                  }}
                  startContent={<Icon icon="mdi:content-copy" />}
                >
                  Copy
                </Button>
              </div>
              <Code className="block text-green-400 bg-transparent p-0 text-sm">
                curl -O http://10.0.34.169:3000/devendra/k8s/raw/branch/main/kubeconfig-exporter/kubernetes_export_sa.sh
              </Code>
            </div>
          </CardBody>
        </Card>
 
        {/* Step 2 */}
        <Card className="bg-gradient-to-r from-blue-50 to-cyan-50 border-l-4 border-blue-500">
          <CardHeader>
            <h4 className="font-bold text-blue-800 flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
              Run the Script
            </h4>
          </CardHeader>
          <CardBody>
            <p className="text-blue-700 mb-3">Execute the script with your parameters:</p>
            <div className="bg-gray-900 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-green-400 text-sm font-mono">Terminal</span>
                <Button
                  size="sm"
                  variant="flat"
                  color="primary"
                  onPress={() => {
                    navigator.clipboard.writeText('bash kubernetes_export_sa.sh myapp-sa myapp-namespace http://10.0.34.169:3000/devendra/k8s/raw/branch/main/kubeconfig-exporter/clusterrole.yaml https://webhook.site/65d8fe21-ffcc-4ccb-9473-52c4a73e4aca');
                  }}
                  startContent={<Icon icon="mdi:content-copy" />}
                >
                  Copy
                </Button>
              </div>
              <Code className="block text-green-400 bg-transparent p-0 text-sm">
                bash kubernetes_export_sa.sh myapp-sa myapp-namespace http://10.0.34.169:3000/devendra/k8s/raw/branch/main/kubeconfig-exporter/clusterrole.yaml https://webhook.site/65d8fe21-ffcc-4ccb-9473-52c4a73e4aca
              </Code>
            </div>
            
            <div className="mt-4 p-3 bg-blue-100 rounded-lg">
              <h5 className="font-semibold text-blue-800 mb-2">Parameters Explanation:</h5>
              <ul className="text-sm text-blue-700 space-y-1">
                <li><strong>myapp-sa:</strong> Service account name (change as needed)</li>
                <li><strong>myapp-namespace:</strong> Kubernetes namespace (change as needed)</li>
                <li><strong>clusterrole.yaml URL:</strong> Cluster role configuration</li>
                <li><strong>webhook URL:</strong> Endpoint to receive the credentials</li>
              </ul>
            </div>
          </CardBody>
        </Card>
 
        {/* Step 3 */}
        <Card className="bg-gradient-to-r from-purple-50 to-pink-50 border-l-4 border-purple-500">
          <CardHeader>
            <h4 className="font-bold text-purple-800 flex items-center gap-2">
              <div className="w-8 h-8 bg-purple-500 text-white rounded-full flex items-center justify-center text-sm font-bold">3</div>
              Get the Output
            </h4>
          </CardHeader>
          <CardBody>
            <p className="text-purple-700 mb-3">The script will output the Server URL and Bearer Token:</p>
            <div className="bg-gray-900 p-4 rounded-lg">
              <div className="mb-2">
                <span className="text-green-400 text-sm font-mono">Expected Output:</span>
              </div>
              <div className="space-y-2">
                <div>
                  <span className="text-yellow-400 text-sm">Server URL:</span>
                  <Code className="block text-green-400 bg-transparent p-0 text-sm ml-4">
                    https://your-cluster-api-server:6443
                  </Code>
                </div>
                <div>
                  <span className="text-yellow-400 text-sm">Bearer Token:</span>
                  <Code className="block text-green-400 bg-transparent p-0 text-sm ml-4">
                    eyJhbGciOiJSUzI1NiIsImtpZCI6IjVRVE...
                  </Code>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>
 
        
      </div>
    </ModalBody>
    <ModalFooter className="bg-gradient-to-r from-gray-50 to-gray-100">
      <Button
        color="primary"
        variant="shadow"
        onPress={onCommandsModalClose}
        startContent={<Icon icon="mdi:check" />}
        className="bg-gradient-to-r from-blue-500 to-indigo-600"
      >
        Got it!
      </Button>
      </ModalFooter>
  </ModalContent>
</Modal>
 
      {/* Loading Overlay */}
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
                  {isUploading && 'Processing your kubeconfig file'}
                  {isOnboardingLoading && 'Creating kubeconfig from your credentials'}
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
 
 
 
 
 