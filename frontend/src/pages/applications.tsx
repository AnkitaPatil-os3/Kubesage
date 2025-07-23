import React, { useState, useEffect, useCallback } from "react";
import { useHistory } from "react-router-dom";
import { Icon } from "@iconify/react";
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Select,
  SelectItem,
  Input,
  Chip,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Spinner,
  Tabs,
  Tab,
  Badge,
  Tooltip,
  Switch,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  useDisclosure,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  Progress,
  Divider
} from "@heroui/react";
import { motion, AnimatePresence } from "framer-motion";

const API_BASE_URL = "https://10.0.32.105:8002/kubeconfig";

interface ClusterInfo {
  id: number;
  cluster_name: string;
  server_url: string;
  provider_name: string;
  is_operator_installed: boolean;
  created_at: string;
}

interface Application {
  name: string;
  namespace: string;
  type: 'helm' | 'rancher' | 'argocd' | 'deployment';
  source: string;
  chart: string;
  version: string;
  app_version: string;
  status: string;
  created: string;
  updated: string;
  description: string;
  icon: string;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  repo_url?: string;
  path?: string;
  replicas?: {
    desired: number;
    ready: number;
    available: number;
  };
}

interface ApplicationsProps {
  selectedCluster?: string;
}

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5
    }
  }
};

// Helper function to get provider icon
const getProviderIcon = (provider: string) => {
  switch (provider?.toLowerCase()) {
    case 'aws':
    case 'eks':
      return 'simple-icons:amazonaws';
    case 'gcp':
    case 'gke':
      return 'simple-icons:googlecloud';
    case 'azure':
    case 'aks':
      return 'simple-icons:microsoftazure';
    case 'rancher':
      return 'simple-icons:rancher';
    case 'k3s':
      return 'simple-icons:k3s';
    default:
      return 'simple-icons:kubernetes';
  }
};

export const Applications: React.FC<ApplicationsProps> = ({ selectedCluster }) => {
  const history = useHistory();
  
  // Modal hooks
  const { isOpen: isDetailsOpen, onOpen: onDetailsOpen, onClose: onDetailsClose } = useDisclosure();
  const { isOpen: isLogsOpen, onOpen: onLogsOpen, onClose: onLogsClose } = useDisclosure();
  const { isOpen: isEventsOpen, onOpen: onEventsOpen, onClose: onEventsClose } = useDisclosure();

  // State
  const [clusters, setClusters] = useState<ClusterInfo[]>([]);
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);
  const [namespaces, setNamespaces] = useState<string[]>([]);
  const [selectedNamespace, setSelectedNamespace] = useState<string>("all");
  const [applications, setApplications] = useState<Application[]>([]);
  const [applicationLogs, setApplicationLogs] = useState<string>('');
  const [applicationEvents, setApplicationEvents] = useState<any[]>([]);
  const [copySuccess, setCopySuccess] = useState(false);
  
  // UI State
  const [loading, setLoading] = useState(true);
  const [appsLoading, setAppsLoading] = useState(false);
  const [namespacesLoading, setNamespacesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAppType, setSelectedAppType] = useState<string>("all");
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState<ReturnType<typeof setInterval> | null>(null);
  const [sortBy, setSortBy] = useState<'name' | 'status' | 'type' | 'created'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Modal state
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [appDetails, setAppDetails] = useState<any>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);

  // Get auth token
  const getAuthToken = () => localStorage.getItem('access_token') || '';

  // Fetch clusters
  const fetchClusters = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/clusters`, {
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
      if (data && Array.isArray(data.clusters)) {
        setClusters(data.clusters);
      } else {
        setClusters([]);
      }
    } catch (err: any) {
      console.error("Error fetching clusters:", err);
      setError(err.message || 'Failed to fetch clusters');
      setClusters([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch namespaces
  const fetchNamespaces = useCallback(async (clusterId: number) => {
    setNamespacesLoading(true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/get-namespaces/${clusterId}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.namespaces && Array.isArray(data.namespaces)) {
          setNamespaces(['all', ...data.namespaces]);
          setSelectedNamespace('all');
        }
      } else {
        console.error("Failed to fetch namespaces");
        setNamespaces(['all']);
      }
    } catch (err: any) {
      console.error("Error fetching namespaces:", err);
      setNamespaces(['all']);
    } finally {
      setNamespacesLoading(false);
    }
  }, []);

  // Fetch applications
  const fetchApplications = useCallback(async (clusterId: number, namespace: string, appType: string) => {
    setAppsLoading(true);
    
    try {
      const params = new URLSearchParams();
      if (namespace && namespace !== 'all') {
        params.append('namespace', namespace);
      }
      if (appType && appType !== 'all') {
        params.append('app_type', appType);
      }

      const response = await fetch(`${API_BASE_URL}/clusters/${clusterId}/apps?${params.toString()}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && Array.isArray(data.apps)) {
          setApplications(data.apps);
        } else {
          setApplications([]);
        }
      } else {
        console.error("Failed to fetch applications");
        setApplications([]);
      }
    } catch (err: any) {
      console.error("Error fetching applications:", err);
      setApplications([]);
    } finally {
      setAppsLoading(false);
    }
  }, []);

  // Fetch application details
  const fetchApplicationDetails = useCallback(async (app: Application) => {
    setDetailsLoading(true);
    
    try {
      const params = new URLSearchParams({
        namespace: app.namespace,
        app_type: app.type
      });

      const response = await fetch(
        `${API_BASE_URL}/clusters/${selectedClusterId}/apps/${app.name}/details?${params.toString()}`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${getAuthToken()}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setAppDetails(data);
        }
      } else {
        console.error("Failed to fetch application details");
      }
    } catch (err: any) {
      console.error("Error fetching application details:", err);
    } finally {
      setDetailsLoading(false);
    }
  }, [selectedClusterId]);

  // Handle cluster selection
  const handleClusterSelect = useCallback((clusterId: number) => {
    setSelectedClusterId(clusterId);
    setApplications([]);
    setSelectedNamespace('all');
    setSelectedAppType('all');
    fetchNamespaces(clusterId);
  }, [fetchNamespaces]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    if (selectedClusterId) {
      fetchApplications(selectedClusterId, selectedNamespace, selectedAppType);
    }
  }, [selectedClusterId, selectedNamespace, selectedAppType, fetchApplications]);

  // Auto refresh effect
  useEffect(() => {
    if (autoRefresh && selectedClusterId) {
      const interval = setInterval(() => {
        handleRefresh();
      }, 30000); // Refresh every 30 seconds
      
      setRefreshInterval(interval);
      return () => clearInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  }, [autoRefresh, selectedClusterId, handleRefresh, refreshInterval]);

  // Initial load
  useEffect(() => {
    fetchClusters();
  }, [fetchClusters]);

  // Load applications when cluster/namespace/type changes
  useEffect(() => {
    if (selectedClusterId) {
      fetchApplications(selectedClusterId, selectedNamespace, selectedAppType);
    }
  }, [selectedClusterId, selectedNamespace, selectedAppType, fetchApplications]);

  // Filter and sort applications
  const filteredAndSortedApps = React.useMemo(() => {
    let filtered = applications.filter(app => {
      const matchesSearch = app.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           app.namespace.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           app.chart.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesSearch;
    });

    // Sort applications
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;
      
      switch (sortBy) {
        case 'name':
          aValue = a.name;
          bValue = b.name;
          break;
        case 'status':
          aValue = a.status;
          bValue = b.status;
          break;
        case 'type':
          aValue = a.type;
          bValue = b.type;
          break;
        case 'created':
          aValue = new Date(a.created);
          bValue = new Date(b.created);
          break;
        default:
          aValue = a.name;
          bValue = b.name;
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return filtered;
  }, [applications, searchTerm, sortBy, sortOrder]);

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'deployed':
      case 'healthy':
      case 'synced':
        return 'success';
      case 'failed':
      case 'degraded':
      case 'error':
        return 'danger';
      case 'pending':
      case 'syncing':
      case 'installing':
      case 'upgrading':
        return 'warning';
      default:
        return 'default';
    }
  };

  // Get app type color
  const getAppTypeColor = (type: string) => {
    switch (type) {
      case 'helm':
        return 'primary';
      case 'rancher':
        return 'secondary';
      case 'argocd':
        return 'success';
      case 'deployment':
        return 'default';
      default:
        return 'default';
    }
  };

  // Format age
  const formatAge = (dateString: string) => {
    if (!dateString) return 'Unknown';
    
    const now = new Date();
    const created = new Date(dateString);
    const diffMs = now.getTime() - created.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffDays > 0) {
      return `${diffDays}d`;
    } else if (diffHours > 0) {
      return `${diffHours}h`;
    } else if (diffMinutes > 0) {
      return `${diffMinutes}m`;
    } else {
      return 'Just now';
    }
  };

  // Handle app details
  const handleViewDetails = (app: Application) => {
    setSelectedApp(app);
    fetchApplicationDetails(app);
    onDetailsOpen();
  };

  // Render application card
  const renderAppCard = (app: Application) => (
    <motion.div
      key={`${app.namespace}/${app.name}`}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.2 }}
    >
      {/* <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer" isPressable> */}
        <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer" isPressable style={{ width: '350px', minWidth: '350px', maxWidth: '350px' }}>
        <CardHeader className="flex gap-3 pb-2">
          <div className="flex-shrink-0">

            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center">
              <Icon icon={app.icon} className="text-2xl text-primary-600" />
            </div>
          </div>
          <div className="flex flex-col flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-lg font-semibold truncate">{app.name}</h4>
              <Chip
                size="sm"
                color={getAppTypeColor(app.type)}
                variant="flat"
                className="text-xs"
              >
                {app.type.toUpperCase()}
              </Chip>
            </div>
            <p className="text-sm text-foreground-500 truncate">{app.namespace}</p>
          </div>
          <div className="flex-shrink-0">
            <Chip
              size="sm"
              color={getStatusColor(app.status)}
              variant="dot"
            >
              {app.status}
            </Chip>
          </div>
        </CardHeader>
        <CardBody className="pt-0">
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-foreground-500">Chart</p>
                <p className="font-medium truncate" title={app.chart}>{app.chart}</p>
              </div>
              <div>
                <p className="text-foreground-500">Version</p>
                <p className="font-medium">{app.version}</p>
              </div>
            </div>
            
            {app.description && (
              <p className="text-sm text-foreground-600 line-clamp-2">{app.description}</p>
            )}
            
            <div className="flex items-center justify-between text-xs text-foreground-500">
              <span>Created {formatAge(app.created)}</span>
              {app.replicas && (
                <span>{app.replicas.ready}/{app.replicas.desired} ready</span>
              )}
            </div>
            
            <Divider />
            
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="flat"
                color="primary"
                onPress={() => handleViewDetails(app)}
                startContent={<Icon icon="lucide:eye" />}
              >
                Details
              </Button>
              <Button
                size="sm"
                variant="flat"
                color="secondary"
                onPress={() => {
                  setSelectedApp(app);
                  fetchApplicationLogs(app, setApplicationLogs, setLoading, selectedClusterId);
                  onLogsOpen();
                }}
                startContent={<Icon icon="lucide:file-text" />}
              >
                Logs
              </Button>
              <Button
                size="sm"
                variant="flat"
                color="default"
                onPress={() => {
                  setSelectedApp(app);
                  fetchApplicationEvents(app, setApplicationEvents, setLoading, selectedClusterId);
                  onEventsOpen();
                }}
                startContent={<Icon icon="lucide:calendar" />}
              >
                Events
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>
    </motion.div>
  );

  // Render application table row
  const renderAppTableRow = (app: Application) => (
    <TableRow key={`${app.namespace}/${app.name}`}>
      <TableCell>
        <div className="flex items-center gap-3">
          <Icon icon={app.icon} className="text-xl" />
          <div>
            <p className="font-medium">{app.name}</p>
            <p className="text-sm text-foreground-500">{app.namespace}</p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <Chip
          size="sm"
          color={getAppTypeColor(app.type)}
          variant="flat"
        >
          {app.type.toUpperCase()}
        </Chip>
      </TableCell>
      <TableCell>
        <div>
          <p className="font-medium">{app.chart}</p>
          <p className="text-sm text-foreground-500">{app.version}</p>
        </div>
      </TableCell>
      <TableCell>
        <Chip
          size="sm"
          color={getStatusColor(app.status)}
          variant="dot"
        >
          {app.status}
        </Chip>
      </TableCell>
      <TableCell>
        {app.replicas ? (
          <div className="flex items-center gap-2">
            <Progress
              size="sm"
              value={(app.replicas.ready / app.replicas.desired) * 100}
              color={app.replicas.ready === app.replicas.desired ? 'success' : 'warning'}
              className="w-16"
            />
            <span className="text-sm">{app.replicas.ready}/{app.replicas.desired}</span>
          </div>
        ) : (
          <span className="text-sm text-foreground-500">N/A</span>
        )}
      </TableCell>
      <TableCell>
        <span className="text-sm">{formatAge(app.created)}</span>
      </TableCell>
      <TableCell>
        <div className="flex gap-1">
          <Tooltip content="View Details">
            <Button
              isIconOnly
              size="sm"
              variant="flat"
              color="primary"
              onPress={() => handleViewDetails(app)}
            >
              <Icon icon="lucide:eye" />
            </Button>
          </Tooltip>
          <Tooltip content="View Logs">
              <Button
                isIconOnly
                size="sm"
                variant="flat"
                color="secondary"
                onPress={() => {
                  setSelectedApp(app);
                  fetchApplicationLogs(app, setApplicationLogs, setLoading, selectedClusterId);
                  onLogsOpen();
                }}
              >
                <Icon icon="lucide:file-text" />
              </Button>
          </Tooltip>
          <Tooltip content="View Events">
              <Button
                isIconOnly
                size="sm"
                variant="flat"
                color="default"
                onPress={() => {
                  setSelectedApp(app);
                  fetchApplicationEvents(app, setApplicationEvents, setLoading, selectedClusterId);
                  onEventsOpen();
                }}
              >
                <Icon icon="lucide:calendar" />
              </Button>
          </Tooltip>
        </div>
      </TableCell>
    </TableRow>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div variants={itemVariants}>
        <Card className="shadow-sm">
          <CardHeader className="flex flex-col gap-4">
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-gradient-to-br from-primary-100 to-primary-200">
                  <Icon icon="lucide:package" className="text-2xl text-primary-600" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold">Applications</h1>
                  <p className="text-foreground-500">
                    Manage and monitor your deployed applications
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Tooltip content="Auto Refresh">
                  <Switch
                    isSelected={autoRefresh}
                    onValueChange={setAutoRefresh}
                    size="sm"
                    color="primary"
                    startContent={<Icon icon="lucide:refresh-cw" />}
                  />
                </Tooltip>
                <Button
                  color="primary"
                  variant="flat"
                  onPress={handleRefresh}
                  isLoading={appsLoading}
                  startContent={<Icon icon="lucide:refresh-cw" />}
                >
                  Refresh
                </Button>
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-4 w-full">
              <Select
                placeholder="Select Cluster"
                selectedKeys={selectedClusterId ? [selectedClusterId.toString()] : []}
                onSelectionChange={(keys) => {
                  const clusterId = Array.from(keys)[0] as string;
                  if (clusterId) {
                    handleClusterSelect(parseInt(clusterId));
                  }
                }}
                className="w-64"
                startContent={
                  selectedClusterId ? (
                    <div className="flex items-center gap-2">
                      <Icon
                        icon={getProviderIcon(
                          clusters.find((c) => c.id === selectedClusterId)?.provider_name || ''
                        )}
                        className="text-lg"
                      />
                      <span>
                        {(() => {
                          const name = clusters.find((c) => c.id === selectedClusterId)?.cluster_name || '';
                          if (name.length < 3) return name;
                          if (name.length > 10) return name.slice(0, 10) + '...';
                          return name;
                        })()}
                      </span>
                    </div>
                  ) : (
                    <Icon icon="lucide:database" />
                  )
                }
              >
                {clusters.map((cluster) => (
                  <SelectItem key={cluster.id.toString()}>
                    <div className="flex items-center gap-2">
                      <Icon icon={getProviderIcon(cluster.provider_name)} className="text-lg" />
                      <span>
                        {cluster.cluster_name.length < 3
                          ? cluster.cluster_name
                          : cluster.cluster_name.length > 10
                          ? cluster.cluster_name.slice(0, 10) + '...'
                          : cluster.cluster_name}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </Select>

              {selectedClusterId && (
                <>
                  <Select
                    placeholder="All Namespaces"
                    selectedKeys={[selectedNamespace]}
                    onSelectionChange={(keys) => {
                      const namespace = Array.from(keys)[0] as string;
                      setSelectedNamespace(namespace);
                    }}
                    className="w-48"
                    isLoading={namespacesLoading}
                    startContent={<Icon icon="lucide:folder" />}
                  >
                    {namespaces.map((namespace) => (
                  <SelectItem key={namespace}>
                    {namespace === 'all' ? 'All Namespaces' : namespace}
                  </SelectItem>
                    ))}
                  </Select>

                  <Select
                    placeholder="All Types"
                    selectedKeys={[selectedAppType]}
                    onSelectionChange={(keys) => {
                      const appType = Array.from(keys)[0] as string;
                      setSelectedAppType(appType);
                    }}
                    className="w-40"
                    startContent={
                      selectedAppType === 'all' ? (
                        <div className="flex items-center gap-2">
                          <Icon icon="lucide:filter" />
                          {/* <span>All Types</span> */}
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Icon
                            icon={
                              selectedAppType === 'helm'
                                ? 'simple-icons:helm'
                                : selectedAppType === 'rancher'
                                ? 'simple-icons:rancher'
                                : selectedAppType === 'argocd'
                                ? 'simple-icons:argo'
                                : selectedAppType === 'deployment'
                                ? 'lucide:box'
                                : 'lucide:filter'
                            }
                          />
                          <span>{selectedAppType.charAt(0).toUpperCase() + selectedAppType.slice(1)}</span>
                        </div>
                      )
                    }
                  >
                    <SelectItem key="all">All Types</SelectItem>
                    <SelectItem key="helm">
                      <div className="flex items-center gap-2">
                        <Icon icon="simple-icons:helm" />
                        <span>Helm</span>
                      </div>
                    </SelectItem>
                    <SelectItem key="rancher">
                      <div className="flex items-center gap-2">
                        <Icon icon="simple-icons:rancher" />
                        <span>Rancher</span>
                      </div>
                    </SelectItem>
                    <SelectItem key="argocd">
                      <div className="flex items-center gap-2">
                        <Icon icon="simple-icons:argo" />
                        <span>ArgoCD</span>
                      </div>
                    </SelectItem>
                    <SelectItem key="deployment">
                      <div className="flex items-center gap-2">
                        <Icon icon="lucide:box" />
                        <span>Deployment</span>
                      </div>
                    </SelectItem>
                  </Select>

                  <Input
                    placeholder="Search applications..."
                    value={searchTerm}
                    onValueChange={setSearchTerm}
                    className="w-64"
                    startContent={<Icon icon="lucide:search" />}
                    isClearable
                  />

                  <div className="flex items-center gap-2 ml-auto">
                    <Tooltip content="Grid View">
                      <Button
                        isIconOnly
                        variant={viewMode === 'grid' ? 'solid' : 'flat'}
                        color="primary"
                        onPress={() => setViewMode('grid')}
                      >
                        <Icon icon="lucide:grid-3x3" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="Table View">
                      <Button
                        isIconOnly
                        variant={viewMode === 'table' ? 'solid' : 'flat'}
                        color="primary"
                        onPress={() => setViewMode('table')}
                      >
                        <Icon icon="lucide:table" />
                      </Button>
                    </Tooltip>
                    <Dropdown>
                      <DropdownTrigger>
                        <Button
                          variant="flat"
                          endContent={<Icon icon="lucide:chevron-down" />}
                        >
                          Sort by {sortBy}
                        </Button>
                      </DropdownTrigger>
                      <DropdownMenu
                        selectedKeys={[sortBy]}
                        onSelectionChange={(keys) => {
                          const key = Array.from(keys)[0] as string;
                          setSortBy(key as any);
                        }}
                      >
                        <DropdownItem key="name">Name</DropdownItem>
                        <DropdownItem key="status">Status</DropdownItem>
                        <DropdownItem key="type">Type</DropdownItem>
                        <DropdownItem key="created">Created</DropdownItem>
                      </DropdownMenu>
                    </Dropdown>
                    <Button
                      isIconOnly
                      variant="flat"
                      onPress={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                    >
                      <Icon icon={sortOrder === 'asc' ? 'lucide:arrow-up' : 'lucide:arrow-down'} />
                    </Button>
                  </div>
                </>
              )}
            </div>
          </CardHeader>
        </Card>
      </motion.div>

      {/* Stats Cards */}
      {selectedClusterId && applications.length > 0 && (
        <motion.div variants={itemVariants}>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              {
                label: 'Total Apps',
                count: applications.length,
                icon: 'lucide:package',
                color: 'primary'
              },
              {
                label: 'Deployed',
                count: applications.filter(app => 
                  ['deployed', 'healthy', 'synced'].includes(app.status.toLowerCase())
                ).length,
                icon: 'lucide:check-circle',
                color: 'success'
              },
              {
                label: 'Failed',
                count: applications.filter(app => 
                  ['failed', 'degraded', 'error'].includes(app.status.toLowerCase())
                ).length,
                icon: 'lucide:x-circle',
                color: 'danger'
              },
              {
                label: 'Pending',
                count: applications.filter(app => 
                  ['pending', 'syncing', 'installing', 'upgrading'].includes(app.status.toLowerCase())
                ).length,
                icon: 'lucide:clock',
                color: 'warning'
              }
            ].map((stat) => (
              <Card key={stat.label} className="shadow-sm">
                <CardBody className="p-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg bg-${stat.color}-100`}>
                      <Icon icon={stat.icon} className={`text-xl text-${stat.color}-600`} />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">{stat.count}</p>
                      <p className="text-sm text-foreground-500">{stat.label}</p>
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        </motion.div>
      )}

      {/* Applications Content */}
      <motion.div variants={itemVariants}>
        <Card className="shadow-sm">
          <CardBody className="p-0">
            {!selectedClusterId ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Icon icon="lucide:database" className="text-6xl text-foreground-300 mb-4" />
                <h3 className="text-xl font-semibold mb-2">Select a Cluster</h3>
                <p className="text-foreground-500">Choose a cluster to view its applications</p>
              </div>
            ) : appsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Icon icon="lucide:alert-circle" className="text-6xl text-danger mb-4" />
                <h3 className="text-xl font-semibold mb-2">Error Loading Applications</h3>
                <p className="text-foreground-500 mb-4">{error}</p>
                <Button color="primary" onPress={handleRefresh}>
                  Try Again
                </Button>
              </div>
            ) : filteredAndSortedApps.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Icon icon="lucide:package-x" className="text-6xl text-foreground-300 mb-4" />
                <h3 className="text-xl font-semibold mb-2">No Applications Found</h3>
                <p className="text-foreground-500">
                  {searchTerm ? 'No applications match your search criteria' : 'No applications are deployed in this cluster'}
                </p>
              </div>
            ) : viewMode === 'grid' ? (
              <div className="p-6">
                <AnimatePresence>
                  <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fill, 350px)', justifyContent: 'center' }}>
                  {/* <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"> */}
                    {filteredAndSortedApps.map(renderAppCard)}
                  </div>
                </AnimatePresence>
              </div>
            ) : (
              <Table aria-label="Applications table">
                <TableHeader>
                  <TableColumn>APPLICATION</TableColumn>
                  <TableColumn>TYPE</TableColumn>
                  <TableColumn>CHART/VERSION</TableColumn>
                  <TableColumn>STATUS</TableColumn>
                  <TableColumn>REPLICAS</TableColumn>
                  <TableColumn>AGE</TableColumn>
                  <TableColumn>ACTIONS</TableColumn>
                </TableHeader>
                <TableBody>
                  {filteredAndSortedApps.map(renderAppTableRow)}
                </TableBody>
              </Table>
            )}
          </CardBody>
        </Card>
      </motion.div>

      {/* Application Details Modal */}
      <Modal 
        isOpen={isDetailsOpen} 
        onClose={onDetailsClose}
        size="5xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              {selectedApp && (
                <>
                  <Icon icon={selectedApp.icon} className="text-2xl" />
                  <div>
                    <h3 className="text-xl font-semibold">{selectedApp.name}</h3>
                    <p className="text-sm text-foreground-500">{selectedApp.namespace}</p>
                  </div>
                  <Chip
                    color={getAppTypeColor(selectedApp.type)}
                    variant="flat"
                    size="sm"
                  >
                    {selectedApp.type.toUpperCase()}
                  </Chip>
                  <Chip
                    color={getStatusColor(selectedApp.status)}
                    variant="dot"
                    size="sm"
                  >
                    {selectedApp.status}
                  </Chip>
                </>
              )}
            </div>
          </ModalHeader>
          <ModalBody>
            {detailsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Spinner size="lg" />
              </div>
            ) : selectedApp ? (
              <div className="space-y-6">
                {/* Basic Information */}
                <div>
                  <h4 className="text-lg font-semibold mb-3">Basic Information</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-foreground-500">Name</p>
                      <p className="font-medium">{selectedApp.name}</p>
                    </div>
                    <div>
                      <p className="text-sm text-foreground-500">Namespace</p>
                      <p className="font-medium">{selectedApp.namespace}</p>
                    </div>
                    <div>
                      <p className="text-sm text-foreground-500">Type</p>
                      <p className="font-medium">{selectedApp.type}</p>
                    </div>
                    <div>
                      <p className="text-sm text-foreground-500">Chart</p>
                      <p className="font-medium">{selectedApp.chart}</p>
                    </div>
                    <div>
                      <p className="text-sm text-foreground-500">Version</p>
                      <p className="font-medium">{selectedApp.version}</p>
                    </div>
                    <div>
                      <p className="text-sm text-foreground-500">App Version</p>
                      <p className="font-medium">{selectedApp.app_version}</p>
                    </div>
                  </div>
                </div>

                {/* Description */}
                {selectedApp.description && (
                  <div>
                    <h4 className="text-lg font-semibold mb-3">Description</h4>
                    <p className="text-foreground-600">{selectedApp.description}</p>
                  </div>
                )}

                {/* ArgoCD specific info */}
                {selectedApp.type === 'argocd' && selectedApp.repo_url && (
                  <div>
                    <h4 className="text-lg font-semibold mb-3">Repository Information</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-foreground-500">Repository URL</p>
                        <p className="font-medium break-all">{selectedApp.repo_url}</p>
                      </div>
                      {selectedApp.path && (
                        <div>
                          <p className="text-sm text-foreground-500">Path</p>
                          <p className="font-medium">{selectedApp.path}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Replicas info */}
                {selectedApp.replicas && (
                  <div>
                    <h4 className="text-lg font-semibold mb-3">Replica Status</h4>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-sm text-foreground-500">Desired</p>
                        <p className="text-2xl font-bold">{selectedApp.replicas.desired}</p>
                      </div>
                      <div>
                        <p className="text-sm text-foreground-500">Ready</p>
                        <p className="text-2xl font-bold text-success">{selectedApp.replicas.ready}</p>
                      </div>
                      <div>
                        <p className="text-sm text-foreground-500">Available</p>
                        <p className="text-2xl font-bold text-primary">{selectedApp.replicas.available}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Labels */}
                {selectedApp.labels && Object.keys(selectedApp.labels).length > 0 && (
                  <div>
                    <h4 className="text-lg font-semibold mb-3">Labels</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(selectedApp.labels).map(([key, value]) => (
                        <Chip key={key} size="sm" variant="flat">
                          {key}: {String(value)}
                        </Chip>
                      ))}
                    </div>
                  </div>
                )}

                {/* Annotations */}
                {selectedApp.annotations && Object.keys(selectedApp.annotations).length > 0 && (
                  <div>
                    <h4 className="text-lg font-semibold mb-3">Annotations</h4>
                    <div className="space-y-2">
                      {Object.entries(selectedApp.annotations).map(([key, value]) => (
                        <div key={key} className="flex flex-col gap-1">
                          <p className="text-sm text-foreground-500">{key}</p>
                          <p className="text-sm font-mono bg-content2 p-2 rounded break-all">{String(value)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Related Resources */}
                {appDetails?.related_resources && (
                  <div>
                    <h4 className="text-lg font-semibold mb-3">Related Resources</h4>
                    <Tabs>
                      <Tab key="pods" title={`Pods (${appDetails.related_resources.pods?.length || 0})`}>
                        <div className="space-y-2">
                          {appDetails.related_resources.pods?.map((pod: any, index: number) => (
                            <div key={index} className="p-3 bg-content2 rounded-lg">
                              <div className="flex items-center justify-between">
                                <span className="font-medium">{pod.metadata?.name || 'Unknown'}</span>
                                <Chip size="sm" color={pod.status?.phase === 'Running' ? 'success' : 'warning'}>
                                  {pod.status?.phase || 'Unknown'}
                                </Chip>
                              </div>
                            </div>
                          )) || <p className="text-foreground-500">No pods found</p>}
                        </div>
                      </Tab>
                      <Tab key="services" title={`Services (${appDetails.related_resources.services?.length || 0})`}>
                        <div className="space-y-2">
                          {appDetails.related_resources.services?.map((service: any, index: number) => (
                            <div key={index} className="p-3 bg-content2 rounded-lg">
                              <div className="flex items-center justify-between">
                                <span className="font-medium">{service.metadata?.name || 'Unknown'}</span>
                                <Chip size="sm">{service.spec?.type || 'Unknown'}</Chip>
                              </div>
                            </div>
                          )) || <p className="text-foreground-500">No services found</p>}
                        </div>
                      </Tab>
                      <Tab key="configmaps" title={`ConfigMaps (${appDetails.related_resources.configmaps?.length || 0})`}>
                        <div className="space-y-2">
                          {appDetails.related_resources.configmaps?.map((cm: any, index: number) => (
                            <div key={index} className="p-3 bg-content2 rounded-lg">
                              <span className="font-medium">{cm.metadata?.name || 'Unknown'}</span>
                            </div>
                          )) || <p className="text-foreground-500">No configmaps found</p>}
                        </div>
                      </Tab>
                      <Tab key="secrets" title={`Secrets (${appDetails.related_resources.secrets?.length || 0})`}>
                        <div className="space-y-2">
                          {appDetails.related_resources.secrets?.map((secret: any, index: number) => (
                            <div key={index} className="p-3 bg-content2 rounded-lg">
                              <div className="flex items-center justify-between">
                                <span className="font-medium">{secret.metadata?.name || 'Unknown'}</span>
                                <Chip size="sm">{secret.type || 'Unknown'}</Chip>
                              </div>
                            </div>
                          )) || <p className="text-foreground-500">No secrets found</p>}
                        </div>
                      </Tab>
                    </Tabs>
                  </div>
                )}
              </div>
            ) : null}
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={onDetailsClose}>
              Close
            </Button>
            <Button color="primary" onPress={() => {
              // TODO: Implement edit functionality
              console.log('Edit application:', selectedApp);
            }}>
              Edit
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Logs Modal */}
      <Modal 
        isOpen={isLogsOpen} 
        onClose={onLogsClose}
        size="5xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          <ModalHeader>
            <div className="flex items-center gap-3">
              <Icon icon="lucide:file-text" className="text-xl" />
              <div>
                <h3 className="text-lg font-semibold">Application Logs</h3>
                <p className="text-sm text-foreground-500">
                  {selectedApp?.name} - {selectedApp?.namespace}
                </p>
              </div>
            </div>
          </ModalHeader>
          <ModalBody>
            <div className="space-y-4">
              <div className="flex gap-2">
                <Button
                  size="sm"
                  color="primary"
                  onPress={() => selectedApp && fetchApplicationLogs(selectedApp, setApplicationLogs, setLoading, selectedClusterId)}
                  startContent={<Icon icon="lucide:refresh-cw" />}
                  isLoading={loading}
                >
                  Refresh Logs
                </Button>
                  <Button
                    size="sm"
                    variant="flat"
                    onPress={() => {
                      navigator.clipboard.writeText(applicationLogs);
                      setCopySuccess(true);
                      setTimeout(() => setCopySuccess(false), 2000);
                    }}
                    startContent={<Icon icon="lucide:copy" />}
                  >
                    Copy Logs
                  </Button>
                  {copySuccess && (
                    <div className="ml-4 px-3 py-1 bg-green-100 text-green-800 rounded-md text-sm select-none">
                      Logs copied to clipboard
                    </div>
                  )}
              </div>
              
              <div className="bg-content2 rounded-lg p-4 max-h-96 overflow-auto">
                <pre className="text-sm font-mono whitespace-pre-wrap text-foreground">
                  {applicationLogs || 'Click "Refresh Logs" to load application logs...'}
                </pre>
              </div>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={onLogsClose}>
              Close
            </Button>
            <Button
              color="primary"
              onPress={() => {
                const blob = new Blob([applicationLogs], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${selectedApp?.name}-logs.txt`;
                a.click();
                URL.revokeObjectURL(url);
              }}
              startContent={<Icon icon="lucide:download" />}
            >
              Download Logs
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

     {/* // Line 900 ke around, Events Modal ko find kariye aur replace kariye: */}

{/* Events Modal */}
<Modal 
  isOpen={isEventsOpen} 
  onClose={onEventsClose}
  size="5xl"
  scrollBehavior="inside"
>
  <ModalContent>
    <ModalHeader>
      <div className="flex items-center gap-3">
        <Icon icon="lucide:calendar" className="text-xl" />
        <div>
          <h3 className="text-lg font-semibold">Application Events</h3>
          <p className="text-sm text-foreground-500">
            {selectedApp?.name} - {selectedApp?.namespace}
          </p>
        </div>
      </div>
    </ModalHeader>
    <ModalBody>
      <div className="space-y-4">
        <div className="flex gap-2">
          <Button
            size="sm"
            color="primary"
            onPress={() => selectedApp && fetchApplicationEvents(selectedApp, setApplicationEvents, setLoading, selectedClusterId)}
            startContent={<Icon icon="lucide:refresh-cw" />}
            isLoading={loading}
          >
            Refresh Events
          </Button>
        </div>
        
        {applicationEvents.length > 0 ? (
          <div className="space-y-2">
            {applicationEvents.map((event, index) => (
              <Card key={index} className="p-4">
                <div className="flex items-start gap-3">
                  <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                    event.type === 'Warning' ? 'bg-warning' : 
                    event.type === 'Error' ? 'bg-danger' : 'bg-success'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-sm font-medium ${
                        event.type === 'Warning' ? 'text-warning' : 
                        event.type === 'Error' ? 'text-danger' : 'text-success'
                      }`}>
                        {event.type}
                      </span>
                      <span className="text-xs text-foreground-500">
                        {event.reason}
                      </span>
                      <span className="text-xs text-foreground-400 ml-auto">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm text-foreground-700">{event.message}</p>
                    {event.source && (
                      <p className="text-xs text-foreground-500 mt-1">
                        Source: {event.source.component}
                      </p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Icon icon="lucide:calendar-x" className="text-4xl text-foreground-400 mb-2" />
            <p className="text-foreground-500">No events found</p>
            <p className="text-sm text-foreground-400">Click "Refresh Events" to load events</p>
          </div>
        )}
      </div>
    </ModalBody>
    <ModalFooter>
      <Button color="danger" variant="light" onPress={onEventsClose}>
        Close
      </Button>
    </ModalFooter>
  </ModalContent>
</Modal>

    </motion.div>
  );
};

const fetchApplicationLogs = async (app: Application, setApplicationLogs: React.Dispatch<React.SetStateAction<string>>, setLoading: React.Dispatch<React.SetStateAction<boolean>>, selectedClusterId: number | null) => {
  if (!selectedClusterId) return;
  
  setLoading(true);
  try {
    const token = localStorage.getItem('access_token');
    const response = await fetch(
      `${API_BASE_URL}/clusters/${selectedClusterId}/apps/${app.name}/logs?namespace=${app.namespace}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (response.ok) {
      const data = await response.json();
      setApplicationLogs(data.logs || 'No logs available');
    } else {
      setApplicationLogs('Failed to fetch logs');
    }
  } catch (error) {
    console.error('Error fetching logs:', error);
    setApplicationLogs('Error fetching logs');
  } finally {
    setLoading(false);
  }
};

const fetchApplicationEvents = async (app: Application, setApplicationEvents: React.Dispatch<React.SetStateAction<any[]>>, setLoading: React.Dispatch<React.SetStateAction<boolean>>, selectedClusterId: number | null) => {
  if (!selectedClusterId) return;
  
  setLoading(true);
  try {
    const token = localStorage.getItem('access_token');
    const response = await fetch(
      `${API_BASE_URL}/clusters/${selectedClusterId}/apps/${app.name}/events?namespace=${app.namespace}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (response.ok) {
      const data = await response.json();
      setApplicationEvents(data.events || []);
    } else {
      setApplicationEvents([]);
    }
  } catch (error) {
    console.error('Error fetching events:', error);
    setApplicationEvents([]);
  } finally {
    setLoading(false);
  }
};

export default Applications;
