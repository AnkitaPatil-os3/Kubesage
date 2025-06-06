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
  Spinner
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
  operator_installed: boolean;
}

export const UploadKubeconfig: React.FC = () => {
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [kubeconfigContent, setKubeconfigContent] = React.useState("");
  const [isUploading, setIsUploading] = React.useState(false);
  const [uploadProgress, setUploadProgress] = React.useState(0);
  const [kubeconfigFiles, setKubeconfigFiles] = React.useState<KubeconfigFile[]>([]);
  const [clusters, setClusters] = React.useState<ClusterInfo[]>([]);
  const [selectedTab, setSelectedTab] = React.useState("upload");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

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

      // Handle the response structure from your API
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

      // Handle the response structure from your API
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
      setSelectedTab("manage");

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

  const removeKubeconfig = async (filename: string) => {
    try {
      setError(null);
      console.log("Attempting to remove:", filename);
      
      // Use query parameter instead of request body
      const response = await fetch(`/kubeconfig/remove?filename=${encodeURIComponent(filename)}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`
          // Remove Content-Type header since we're not sending JSON body
        }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error("Remove failed:", errorText);
        throw new Error(`Failed to remove kubeconfig: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log("Remove successful:", result);
      
      // Refresh the lists
      await fetchKubeconfigList();
      await fetchClusters();
      
    } catch (error: any) {
      console.error("Failed to remove kubeconfig:", error);
      setError(error.message || 'Failed to remove kubeconfig');
    }
  };
  
  

  // Calculate stats
  const totalKubeconfigs = kubeconfigFiles.length;
  const activeKubeconfigs = kubeconfigFiles.filter(f => f.active).length;
  const totalClusters = clusters.length;
  const activeClusters = clusters.filter(c => c.active).length;
  const operatorInstalledCount = clusters.filter(c => c.operator_installed).length;

  return (
    <div className="space-y-6">
      <Card className="w-full">
        <CardHeader className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Icon icon="lucide:upload-cloud" className="text-primary" />
            <h2 className="text-xl font-semibold">Kubeconfig Management</h2>
          </div>
          <p className="text-sm text-foreground-500">Upload and manage your Kubernetes cluster configurations</p>
        </CardHeader>
        <CardBody>
          {/* Error Display */}
          {error && (
            <Card className="border border-danger mb-4">
              <CardBody>
                <div className="flex items-center gap-2 text-danger">
                  <Icon icon="lucide:alert-circle" />
                  <span className="text-sm">{error}</span>
                  <Button
                    size="sm"
                    variant="light"
                    color="danger"
                    onPress={() => setError(null)}
                  >
                    <Icon icon="lucide:x" />
                  </Button>
                </div>
              </CardBody>
            </Card>
          )}

          <Tabs
            aria-label="Kubeconfig options"
            selectedKey={selectedTab}
            onSelectionChange={setSelectedTab as any}
            variant="underlined"
            color="primary"
          >
            <Tab
              key="upload"
              title={
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:upload" />
                  <span>Upload</span>
                </div>
              }
            >
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="mt-4 space-y-6"
              >
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* File Upload Section */}
                  <Card className="border border-content3">
                    <CardHeader>
                      <h3 className="text-lg font-semibold">Upload Kubeconfig File</h3>
                    </CardHeader>
                    <CardBody className="space-y-4">
                      <div
                        className="p-6 border-2 border-dashed border-content3 rounded-lg text-center hover:border-primary transition-colors cursor-pointer"
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
                        <div className="flex flex-col items-center gap-2">
                          <Icon icon="lucide:file-text" className="text-4xl text-foreground-400" />
                          <h4 className="font-medium">
                            {selectedFile ? selectedFile.name : "Drop kubeconfig file here"}
                          </h4>
                          <p className="text-sm text-foreground-500">
                            {selectedFile ? "File selected" : "or click to browse"}
                          </p>
                          {!selectedFile && (
                            <Button
                              variant="flat"
                              color="primary"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                triggerFileInput();
                              }}
                            >
                              Select File
                            </Button>
                          )}
                        </div>
                      </div>

                      {selectedFile && (
                        <div className="flex items-center justify-between p-3 bg-success-100 text-success-700 rounded-medium">
                          <div className="flex items-center gap-2">
                            <Icon icon="lucide:check-circle" />
                            <span className="text-sm">{selectedFile.name}</span>
                          </div>
                          <Button
                            size="sm"
                            variant="light"
                            color="danger"
                            onPress={() => {
                              setSelectedFile(null);
                              setKubeconfigContent("");
                              const fileInput = document.getElementById('file-input') as HTMLInputElement;
                              if (fileInput) {
                                fileInput.value = '';
                              }
                            }}
                          >
                            <Icon icon="lucide:x" />
                          </Button>
                        </div>
                      )}
                    </CardBody>
                  </Card>

                  {/* Manual Input Section */}
                  <Card className="border border-content3">
                    <CardHeader>
                      <h3 className="text-lg font-semibold">Paste Kubeconfig Content</h3>
                    </CardHeader>
                    <CardBody>
                      <Textarea
                        label="Kubeconfig YAML"
                        placeholder="Paste your kubeconfig YAML content here..."
                        value={kubeconfigContent}
                        onValueChange={setKubeconfigContent}
                        minRows={8}
                        maxRows={12}
                      />
                    </CardBody>
                  </Card>
                </div>

                {/* Upload Progress */}
                {isUploading && (
                  <Card className="border border-primary">
                    <CardBody>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">Uploading kubeconfig...</span>
                          <span className="text-sm text-foreground-500">{uploadProgress}%</span>
                        </div>
                        <Progress value={uploadProgress} color="primary" />
                      </div>
                    </CardBody>
                  </Card>
                )}

                {/* Upload Button */}
                <div className="flex justify-end">
                  <Button
                    color="primary"
                    size="lg"
                    onPress={uploadKubeconfig}
                    isLoading={isUploading}
                    isDisabled={!selectedFile && !kubeconfigContent.trim()}
                    endContent={<Icon icon="lucide:upload" />}
                  >
                    Upload Kubeconfig
                  </Button>
                </div>
              </motion.div>
            </Tab>

            <Tab
              key="manage"
              title={
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:settings" />
                  <span>Manage</span>
                </div>
              }
            >
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="mt-4 space-y-6"
              >
                {/* Overview Cards */}
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                  <Card className="border border-content3">
                    <CardBody className="text-center">
                      <div className="flex flex-col items-center gap-2">
                        <Icon icon="lucide:file-text" className="text-2xl text-primary" />
                        <div>
                          <p className="text-2xl font-bold">{totalKubeconfigs}</p>
                          <p className="text-sm text-foreground-500">Total Kubeconfigs</p>
                        </div>
                      </div>
                    </CardBody>
                  </Card>

                  <Card className="border border-content3">
                    <CardBody className="text-center">
                      <div className="flex flex-col items-center gap-2">
                        <Icon icon="lucide:check-circle" className="text-2xl text-success" />
                        <div>
                          <p className="text-2xl font-bold">{activeKubeconfigs}</p>
                          <p className="text-sm text-foreground-500">Active Kubeconfigs</p>
                        </div>
                      </div>
                    </CardBody>
                  </Card>

                  <Card className="border border-content3">
                    <CardBody className="text-center">
                      <div className="flex flex-col items-center gap-2">
                        <Icon icon="lucide:server" className="text-2xl text-warning" />
                        <div>
                          <p className="text-2xl font-bold">{totalClusters}</p>
                          <p className="text-sm text-foreground-500">Total Clusters</p>
                        </div>
                      </div>
                    </CardBody>
                  </Card>

                  <Card className="border border-content3">
                    <CardBody className="text-center">
                      <div className="flex flex-col items-center gap-2">
                        <Icon icon="lucide:activity" className="text-2xl text-success" />
                        <div>
                          <p className="text-2xl font-bold">{activeClusters}</p>
                          <p className="text-sm text-foreground-500">Active Clusters</p>
                        </div>
                      </div>
                    </CardBody>
                  </Card>

                  <Card className="border border-content3">
                    <CardBody className="text-center">
                      <div className="flex flex-col items-center gap-2">
                        <Icon icon="lucide:bot" className="text-2xl text-secondary" />
                        <div>
                          <p className="text-2xl font-bold">{operatorInstalledCount}</p>
                          <p className="text-sm text-foreground-500">Operators Installed</p>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                </div>

                {/* Loading State */}
                {loading && (
                  <Card>
                    <CardBody className="text-center py-8">
                      <Spinner size="lg" color="primary" />
                      <p className="mt-4 text-foreground-500">Loading data...</p>
                    </CardBody>
                  </Card>
                )}

                {/* Kubeconfig Files Table */}
                {!loading && (
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                      <h3 className="text-lg font-semibold">Kubeconfig Files</h3>
                      <Button
                        color="primary"
                        variant="flat"
                        size="sm"
                        onPress={fetchKubeconfigList}
                        startContent={<Icon icon="lucide:refresh-cw" />}
                      >
                        Refresh
                      </Button>
                    </CardHeader>
                    <CardBody>
                      {kubeconfigFiles.length === 0 ? (
                        <div className="text-center py-8">
                          <Icon icon="lucide:file-x" className="text-4xl text-foreground-400 mb-2" />
                          <p className="text-foreground-500">No kubeconfig files found</p>
                          <p className="text-sm text-foreground-400">Upload a kubeconfig file to get started</p>
                        </div>
                      ) : (
                        <Table aria-label="Kubeconfig files table">
                          <TableHeader>
                            <TableColumn>ORIGINAL FILENAME</TableColumn>
                            <TableColumn>CLUSTER NAME</TableColumn>
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
                                    <Icon icon="lucide:file-text" className="text-foreground-400" />
                                    <span className="font-medium">{file.original_filename}</span>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <Chip size="sm" variant="flat" color="primary">
                                    {file.cluster_name}
                                  </Chip>
                                </TableCell>
                                <TableCell>
                                  <span className="text-sm text-foreground-600">{file.context_name}</span>
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    color={file.active ? 'success' : 'default'}
                                    variant="flat"
                                    size="sm"
                                  >
                                    {file.active ? 'Active' : 'Inactive'}
                                  </Chip>
                                </TableCell>
                                <TableCell>
                                  <span className="text-sm text-foreground-600">
                                    {file.upload_date ? new Date(file.upload_date).toLocaleDateString() : 'N/A'}
                                  </span>
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    <Button
                                      size="sm"
                                      variant="flat"
                                      color={file.active ? 'default' : 'success'}
                                      onPress={() => activateKubeconfig(file.filename)}
                                      isDisabled={file.active}
                                      startContent={<Icon icon={file.active ? "lucide:check" : "lucide:play"} />}
                                    >
                                      {file.active ? 'Active' : 'Activate'}
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="flat"
                                      color="primary"
                                      startContent={<Icon icon="lucide:settings" />}
                                    >
                                      Settings
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="flat"
                                      color="danger"
                                      onPress={() => removeKubeconfig(file.filename)}
                                      startContent={<Icon icon="lucide:trash-2" />}
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
                    </CardBody>
                  </Card>
                )}

                {/* Clusters Table */}
                {!loading && (
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                      <h3 className="text-lg font-semibold">Clusters</h3>
                      <Button
                        color="primary"
                        variant="flat"
                        size="sm"
                        onPress={fetchClusters}
                        startContent={<Icon icon="lucide:refresh-cw" />}
                      >
                        Refresh
                      </Button>
                    </CardHeader>
                    <CardBody>
                      {clusters.length === 0 ? (
                        <div className="text-center py-8">
                          <Icon icon="lucide:server-off" className="text-4xl text-foreground-400 mb-2" />
                          <p className="text-foreground-500">No clusters available</p>
                          <p className="text-sm text-foreground-400">Upload and activate a kubeconfig file first</p>
                        </div>
                      ) : (
                        <Table aria-label="Clusters table">
                          <TableHeader>
                            <TableColumn>CLUSTER NAME</TableColumn>
                            <TableColumn>KUBECONFIG FILE</TableColumn>
                            <TableColumn>STATUS</TableColumn>
                            <TableColumn>OPERATOR</TableColumn>
                            <TableColumn>ACTIONS</TableColumn>
                          </TableHeader>
                          <TableBody>
                            {clusters.map((cluster, index) => (
                              <TableRow key={index}>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    <Icon icon="lucide:server" className="text-primary" />
                                    <span className="font-medium">{cluster.cluster_name}</span>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <code className="text-xs bg-content2 px-2 py-1 rounded">
                                    {cluster.filename}
                                  </code>
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    color={cluster.active ? 'success' : 'default'}
                                    variant="flat"
                                    size="sm"
                                  >
                                    {cluster.active ? 'Active' : 'Inactive'}
                                  </Chip>
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    color={cluster.operator_installed ? 'success' : 'warning'}
                                    variant="flat"
                                    size="sm"
                                  >
                                    {cluster.operator_installed ? 'Installed' : 'Not Installed'}
                                  </Chip>
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    <Button
                                      size="sm"
                                      variant="flat"
                                      color="primary"
                                      startContent={<Icon icon="lucide:edit" />}
                                    >
                                      Edit
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="flat"
                                      color="secondary"
                                      startContent={<Icon icon="lucide:settings" />}
                                    >
                                      Settings
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="flat"
                                      color="danger"
                                      startContent={<Icon icon="lucide:trash-2" />}
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
                    </CardBody>
                  </Card>
                )}
              </motion.div>
            </Tab>
          </Tabs>
        </CardBody>
      </Card>
    </div>
  );
};

