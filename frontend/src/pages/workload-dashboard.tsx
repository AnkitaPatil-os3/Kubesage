// hi
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

const API_BASE_URL = "/api/v2.0";

interface ClusterInfo {
  id: number;
  cluster_name: string;
  server_url: string;
  provider_name: string;
  is_operator_installed: boolean;
  created_at: string;
}

interface WorkloadData {
  pods: any[];
  deployments: any[];
  services: any[];
  statefulsets: any[];
  daemonsets: any[];
  jobs: any[];
  cronjobs: any[];
}

interface WorkloadDashboardProps {
  selectedCluster?: string;
}

export const WorkloadDashboard: React.FC<WorkloadDashboardProps> = ({ selectedCluster }) => {
  // State
  const [clusters, setClusters] = useState<ClusterInfo[]>([]);
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);
  const [namespaces, setNamespaces] = useState<string[]>([]);
  const [selectedNamespace, setSelectedNamespace] = useState<string>("");
  const [workloads, setWorkloads] = useState<WorkloadData>({
    pods: [],
    deployments: [],
    services: [],
    statefulsets: [],
    daemonsets: [],
    jobs: [],
    cronjobs: []
  });
  
  // UI State
  const [loading, setLoading] = useState(true);
  const [workloadsLoading, setWorkloadsLoading] = useState(false);
  const [namespacesLoading, setNamespacesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedTab, setSelectedTab] = useState("pods");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState<ReturnType<typeof setInterval> | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [sortBy, setSortBy] = useState<'name' | 'status' | 'age'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
const [showStats, setShowStats] = useState(true);

  // Events State
  const [selectedWorkloadEvents, setSelectedWorkloadEvents] = useState<any[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [selectedWorkloadName, setSelectedWorkloadName] = useState<string>("");
  const [selectedWorkloadType, setSelectedWorkloadType] = useState<string>("");

  // Logs State
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);
  const [selectedLogs, setSelectedLogs] = useState<string>("");

  // Modal States
  const { isOpen: isDetailsOpen, onOpen: onDetailsOpen, onClose: onDetailsClose } = useDisclosure();
  const { isOpen: isStatsOpen, onOpen: onStatsOpen, onClose: onStatsClose } = useDisclosure();
  const { isOpen: isEventsOpen, onOpen: onEventsOpen, onClose: onEventsClose } = useDisclosure();
  const [selectedWorkload, setSelectedWorkload] = useState<any>(null);

  // Helper function to get auth token
  const getAuthToken = () => {
    return localStorage.getItem("access_token") || "";
  };

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
    visible: { opacity: 1, y: 0 }
  };

  // Fetch clusters on component mount
  useEffect(() => {
    fetchClusters();
  }, []);

  // Fetch namespaces when cluster is selected
  useEffect(() => {
    if (selectedClusterId) {
      fetchNamespaces(selectedClusterId);
    }
  }, [selectedClusterId]);

  // Fetch workloads when cluster and namespace are selected
  useEffect(() => {
    if (selectedClusterId && selectedNamespace) {
      fetchWorkloads(selectedClusterId, selectedNamespace);
    }
  }, [selectedClusterId, selectedNamespace]);

  // Auto-refresh logic
  useEffect(() => {
    if (autoRefresh && selectedClusterId && selectedNamespace) {
      const interval = setInterval(() => {
        fetchWorkloads(selectedClusterId, selectedNamespace);
      }, 30000); // Refresh every 30 seconds
      setRefreshInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }

    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  }, [autoRefresh, selectedClusterId, selectedNamespace]);

  // Fetch clusters
  const fetchClusters = async () => {
    try {
      const response = await fetch(`/api/v2.0/clusters`, {
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch clusters: ${response.statusText}`);
      }

      const data = await response.json();
      if (!selectedClusterId && data.clusters && data.clusters.length > 0) {
        setSelectedClusterId(data.clusters[0].id);
      }
      setClusters(data.clusters || []);
    } catch (err: any) {
      setError(`Error fetching clusters: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Fetch namespaces
  const fetchNamespaces = async (clusterId: number) => {
    setNamespacesLoading(true);
    try {
      const response = await fetch(`/api/v2.0/get-namespaces/${clusterId}`, {
        headers: {
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch namespaces: ${response.statusText}`);
      }

      const data = await response.json();
      const fetchedNamespaces = data.namespaces || [];
      setNamespaces(fetchedNamespaces);
      
      // Auto-select first namespace if none is selected
      if (fetchedNamespaces.length > 0 && !selectedNamespace) {
        setSelectedNamespace(fetchedNamespaces[0]);
      }
    } catch (err: any) {
      setError(`Error fetching namespaces: ${err.message}`);
      setNamespaces([]);
    } finally {
      setNamespacesLoading(false);
    }
  };

  // Fetch workloads using kubectl commands
  const fetchWorkloads = async (clusterId: number, namespace: string) => {
    setWorkloadsLoading(true);
    setError(null);

    try {
      const workloadCommands = {
        pods: `kubectl get pods -n ${namespace} -o json`,
        deployments: `kubectl get deployments -n ${namespace} -o json`,
        services: `kubectl get services -n ${namespace} -o json`,
        statefulsets: `kubectl get statefulsets -n ${namespace} -o json`,
        daemonsets: `kubectl get daemonsets -n ${namespace} -o json`,
        jobs: `kubectl get jobs -n ${namespace} -o json`,
        cronjobs: `kubectl get cronjobs -n ${namespace} -o json`
      };

      const workloadData: WorkloadData = {
        pods: [],
        deployments: [],
        services: [],
        statefulsets: [],
        daemonsets: [],
        jobs: [],
        cronjobs: []
      };

      // Fetch all workload types concurrently
      const promises = Object.entries(workloadCommands).map(async ([type, command]) => {
        try {
          const response = await fetch(`/api/v2.0/execute-kubectl-direct/${clusterId}`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({ command })
          });

          if (!response.ok) {
            throw new Error(`Failed to fetch ${type}: ${response.statusText}`);
          }

          const data = await response.json();
          if (data.success && data.output) {
            const parsedData = JSON.parse(data.output);
            workloadData[type as keyof WorkloadData] = parsedData.items || [];
          }
        } catch (err) {
          console.error(`Error fetching ${type}:`, err);
        }
      });

      await Promise.all(promises);
      setWorkloads(workloadData);
    } catch (err: any) {
      setError(`Error fetching workloads: ${err.message}`);
    } finally {
      setWorkloadsLoading(false);
    }
  };

  // Fetch workload events
  const fetchWorkloadEvents = async (workloadName: string, workloadType: string, namespace: string) => {
    if (!selectedClusterId || !workloadName || !namespace) return;
    
    setEventsLoading(true);
    setSelectedWorkloadName(workloadName);
    setSelectedWorkloadType(workloadType);
    
    try {
      const response = await fetch(`/api/v2.0/execute-kubectl-direct/${selectedClusterId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        },
        body: JSON.stringify({
          command: `kubectl get events --field-selector involvedObject.name=${workloadName} -n ${namespace} --sort-by='.lastTimestamp' -o json`
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch events: ${response.statusText}`);
      }

      const data = await response.json();
      if (data.success && data.output) {
        try {
          const eventsData = JSON.parse(data.output);
          if (eventsData.items) {
            setSelectedWorkloadEvents(eventsData.items.reverse()); // Show latest first
          } else {
            setSelectedWorkloadEvents([]);
          }
        } catch (parseError) {
          console.error("Error parsing events data:", parseError);
          setSelectedWorkloadEvents([]);
        }
      } else {
        setSelectedWorkloadEvents([]);
      }
      onEventsOpen();
    } catch (err: any) {
      console.error("Error fetching workload events:", err);
      setSelectedWorkloadEvents([]);
      onEventsOpen(); // Still open modal to show "No events found"
    } finally {
      setEventsLoading(false);
    }
  };

  // Helper functions
  const getProviderIcon = (provider: string) => {
    switch (provider?.toLowerCase()) {
      case 'aws': return 'logos:aws';
      case 'gcp': return 'logos:google-cloud';
      case 'azure': return 'logos:microsoft-azure';
      case 'kubernetes': return 'logos:kubernetes';
      default: return 'lucide:server';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'running': return 'success';
      case 'pending': return 'warning';
      case 'failed': return 'danger';
      case 'succeeded': return 'success';
      case 'error': return 'danger';
      default: return 'default';
    }
  };

  const formatAge = (timestamp: string) => {
    if (!timestamp) return 'Unknown';
    const now = new Date();
    const created = new Date(timestamp);
    const diffMs = now.getTime() - created.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (diffDays > 0) return `${diffDays}d`;
    if (diffHours > 0) return `${diffHours}h`;
    return `${diffMinutes}m`;
  };

  const getEventTypeColor = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'warning': return 'warning';
      case 'error': return 'danger';
      case 'normal': return 'success';
      default: return 'default';
    }
  };

  const formatEventTime = (timestamp: string) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const filterWorkloads = (workloadList: any[]) => {
    if (!searchTerm) return workloadList;
    return workloadList.filter(workload =>
      workload.metadata?.name?.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  const sortWorkloads = (workloadList: any[]) => {
    return [...workloadList].sort((a, b) => {
      let aValue, bValue;
      
      switch (sortBy) {
        case 'name':
          aValue = a.metadata?.name || '';
          bValue = b.metadata?.name || '';
          break;
        case 'status':
          aValue = a.status?.phase || a.status?.conditions?.[0]?.type || '';
          bValue = b.status?.phase || b.status?.conditions?.[0]?.type || '';
          break;
        case 'age':
          aValue = new Date(a.metadata?.creationTimestamp || 0).getTime();
          bValue = new Date(b.metadata?.creationTimestamp || 0).getTime();
          break;
        default:
          aValue = a.metadata?.name || '';
          bValue = b.metadata?.name || '';
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  };

  const getWorkloadCount = (type: string) => {
    return workloads[type as keyof WorkloadData]?.length || 0;
  };

  const getWorkloadStats = () => {
    const allWorkloads = Object.values(workloads).flat();
    const stats = {
      total: allWorkloads.length,
      running: 0,
      pending: 0,
      failed: 0,
            succeeded: 0
    };

    allWorkloads.forEach(workload => {
      const status = workload.status?.phase || workload.status?.conditions?.[0]?.type || '';
      switch (status?.toLowerCase() ?? '') {
        case 'running':
          stats.running++;
          break;
        case 'pending':
          stats.pending++;
          break;
        case 'failed':
        case 'error':
          stats.failed++;
          break;
        case 'succeeded':
        case 'complete':
          stats.succeeded++;
          break;
      }
    });

    return stats;
  };

  const getWorkloadTypeIcon = (type: string) => {
    switch (type) {
      case 'pods': return 'lucide:box';
      case 'deployments': return 'lucide:layers';
      case 'services': return 'lucide:globe';
      case 'statefulsets': return 'lucide:database';
      case 'daemonsets': return 'lucide:server';
      case 'jobs': return 'lucide:play';
      case 'cronjobs': return 'lucide:clock';
      default: return 'lucide:box';
    }
  };

  const getWorkloadTypeColor = (type: string) => {
    switch (type) {
      case 'pods': return 'primary';
      case 'deployments': return 'secondary';
      case 'services': return 'success';
      case 'statefulsets': return 'warning';
      case 'daemonsets': return 'danger';
      case 'jobs': return 'default';
      case 'cronjobs': return 'default';
      default: return 'primary';
    }
  };

  const handleWorkloadClick = (workload: any, type: string) => {
    setSelectedWorkload({ ...workload, type });
    onDetailsOpen();
  };

  // Render clickable workload name component
  const renderClickableWorkloadName = (workload: any, type: string, icon: string, color: string) => {
    const workloadName = workload.metadata?.name || workload.name || 'Unknown';
    
    return (
      <div className="flex items-center gap-2">
        <Icon icon={icon} className={`text-${color}`} />
        <Button
          variant="light"
          className={`p-0 h-auto min-w-0 font-medium text-${color} hover:text-${color}-600 justify-start`}
          onPress={() => fetchWorkloadEvents(workloadName, type, selectedNamespace)}
          isLoading={eventsLoading && selectedWorkloadName === workloadName}
        >
          <div className="flex items-center gap-2">
            <Icon icon="lucide:calendar" className="text-sm" />
            {workloadName}
          </div>
        </Button>
      </div>
    );
  };

  // Enhanced table renderers for all workload types
  const renderPodsTable = () => {
    const filteredPods = sortWorkloads(filterWorkloads(workloads.pods));
    
    return (
      <Table aria-label="Pods table" className="min-h-[400px]">
        <TableHeader>
          <TableColumn>NAME</TableColumn>
          <TableColumn>READY</TableColumn>
          <TableColumn>STATUS</TableColumn>
          <TableColumn>STATE</TableColumn>
          <TableColumn>RESTARTS</TableColumn>
          <TableColumn>AGE</TableColumn>
          <TableColumn>NODE</TableColumn>
          <TableColumn>ACTIONS</TableColumn>
        </TableHeader>
        <TableBody emptyContent="No pods found">
          {filteredPods.map((pod, index) => {
            const podName = pod.metadata?.name || 'Unknown';
            const ready = pod.status?.containerStatuses?.filter((c: any) => c.ready).length || 0;
            const total = pod.status?.containerStatuses?.length || 0;
            const status = pod.status?.phase || 'Unknown';
            const restarts = pod.status?.containerStatuses?.reduce((acc: number, c: any) => acc + (c.restartCount || 0), 0) || 0;
            const age = formatAge(pod.metadata?.creationTimestamp);
            const node = pod.spec?.nodeName || 'Unknown';

            // Determine state and error message
            let state = 'Active';
            let errorMsg = '';
            if ((status?.toLowerCase() ?? '') === 'failed') {
              state = 'Failed';
              // Try to get error message from containerStatuses or conditions
              const containerStatus = pod.status?.containerStatuses?.find((c: any) => c.state?.terminated?.exitCode !== 0);
              if (containerStatus && containerStatus.state?.terminated?.message) {
                errorMsg = containerStatus.state.terminated.message;
              } else if (pod.status?.message) {
                errorMsg = pod.status.message;
              }
            }

            return (
              <TableRow key={index}>
                <TableCell>
                  {renderClickableWorkloadName(pod, 'pods', 'lucide:box', 'primary')}
                </TableCell>
                <TableCell>{ready}/{total}</TableCell>
                <TableCell>
                  <Chip color={getStatusColor(status)} size="sm" variant="flat">
                    {status}
                  </Chip>
                </TableCell>
                <TableCell>
                  {state === 'Failed' ? (
                    <Tooltip content={errorMsg || 'Failed'}>
                      <Chip color="danger" size="sm" variant="flat">
                        {state}
                      </Chip>
                    </Tooltip>
                  ) : (
                    <Chip color="success" size="sm" variant="flat">
                      {state}
                    </Chip>
                  )}
                </TableCell>
                <TableCell>
                  {restarts > 0 ? (
                    <Badge color="warning">
                      <span>{restarts}</span>
                    </Badge>
                  ) : (
                    <span>{restarts}</span>
                  )}
                </TableCell>
                <TableCell>{age}</TableCell>
                <TableCell>{node}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Tooltip content="View Details">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={() => handleWorkloadClick(pod, 'pods')}
                      >
                        <Icon icon="lucide:eye" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="View Events">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="secondary"
                        onPress={() => fetchWorkloadEvents(podName, 'pods', selectedNamespace)}
                        isLoading={eventsLoading && selectedWorkloadName === podName}
                      >
                        <Icon icon="lucide:calendar" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="View Logs">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="warning"
                        onPress={() => handleViewLogsClick(pod)}
                      >
                        <Icon icon="lucide:file-text" />
                      </Button>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    );
  };

  const renderDeploymentsTable = () => {
    const filteredDeployments = sortWorkloads(filterWorkloads(workloads.deployments));
    
    return (
      <Table aria-label="Deployments table" className="min-h-[400px]">
        <TableHeader>
          <TableColumn>NAME</TableColumn>
          <TableColumn>READY</TableColumn>
          <TableColumn>UP-TO-DATE</TableColumn>
          <TableColumn>AVAILABLE</TableColumn>
          <TableColumn>STATE</TableColumn>
          <TableColumn>AGE</TableColumn>
          <TableColumn>ACTIONS</TableColumn>
        </TableHeader>
        <TableBody emptyContent="No deployments found">
          {filteredDeployments.map((deployment, index) => {
            const deploymentName = deployment.metadata?.name || 'Unknown';
            const ready = deployment.status?.readyReplicas || 0;
            const desired = deployment.spec?.replicas || 0;
            const upToDate = deployment.status?.updatedReplicas || 0;
            const available = deployment.status?.availableReplicas || 0;
            const age = formatAge(deployment.metadata?.creationTimestamp);

            // Determine state and error message
            let state = 'Active';
            let errorMsg = '';
            if (available < desired) {
              state = 'Failed';
              if (deployment.status?.conditions) {
                const failedCondition = deployment.status.conditions.find((c: any) => c.status === 'False' && c.type === 'Available');
                if (failedCondition && failedCondition.message) {
                  errorMsg = failedCondition.message;
                }
              }
            }

            return (
              <TableRow key={index}>
                <TableCell>
                  {renderClickableWorkloadName(deployment, 'deployments', 'lucide:layers', 'secondary')}
                </TableCell>
                <TableCell>{ready}/{desired}</TableCell>
                <TableCell>{upToDate}</TableCell>
                <TableCell>{available}</TableCell>
                <TableCell>
                  {state === 'Failed' ? (
                    <Tooltip content={errorMsg || 'Failed'}>
                      <Chip color="danger" size="sm" variant="flat">
                        {state}
                      </Chip>
                    </Tooltip>
                  ) : (
                    <Chip color="success" size="sm" variant="flat">
                      {state}
                    </Chip>
                  )}
                </TableCell>
                <TableCell>{age}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Tooltip content="View Details">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={() => handleWorkloadClick(deployment, 'deployments')}
                      >
                        <Icon icon="lucide:eye" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="View Events">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="secondary"
                        onPress={() => fetchWorkloadEvents(deploymentName, 'deployments', selectedNamespace)}
                        isLoading={eventsLoading && selectedWorkloadName === deploymentName}
                      >
                        <Icon icon="lucide:calendar" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="Scale">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="warning"
                      >
                        <Icon icon="lucide:maximize" />
                      </Button>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    );
  };

  const renderServicesTable = () => {
    const filteredServices = sortWorkloads(filterWorkloads(workloads.services));
    
    return (
      <Table aria-label="Services table" className="min-h-[400px]">
        <TableHeader>
          <TableColumn>NAME</TableColumn>
          <TableColumn>TYPE</TableColumn>
          <TableColumn>CLUSTER-IP</TableColumn>
          <TableColumn>EXTERNAL-IP</TableColumn>
          <TableColumn>PORT(S)</TableColumn>
          <TableColumn>AGE</TableColumn>
          <TableColumn>ACTIONS</TableColumn>
        </TableHeader>
        <TableBody emptyContent="No services found">
          {filteredServices.map((service, index) => {
            const serviceName = service.metadata?.name || 'Unknown';
            const type = service.spec?.type || 'ClusterIP';
            const clusterIP = service.spec?.clusterIP || 'None';
            const externalIP = service.status?.loadBalancer?.ingress?.[0]?.ip || 
                             service.spec?.externalIPs?.[0] || 
                             (type === 'NodePort' ? '<nodes>' : '<none>');
            const ports = service.spec?.ports?.map((p: any) => 
              `${p.port}${p.nodePort ? `:${p.nodePort}` : ''}/${p.protocol}`
            ).join(',') || 'None';
            const age = formatAge(service.metadata?.creationTimestamp);

            return (
              <TableRow key={index}>
                <TableCell>
                  {renderClickableWorkloadName(service, 'services', 'lucide:globe', 'success')}
                </TableCell>
                <TableCell>
                  <Chip color="success" size="sm" variant="flat">
                    {type}
                  </Chip>
                </TableCell>
                <TableCell>{clusterIP}</TableCell>
                <TableCell>{externalIP}</TableCell>
                <TableCell>
                  <code className="text-sm bg-content2 px-2 py-1 rounded">{ports}</code>
                </TableCell>
                <TableCell>{age}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Tooltip content="View Details">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={() => handleWorkloadClick(service, 'services')}
                      >
                        <Icon icon="lucide:eye" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="View Events">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="secondary"
                        onPress={() => fetchWorkloadEvents(serviceName, 'services', selectedNamespace)}
                        isLoading={eventsLoading && selectedWorkloadName === serviceName}
                      >
                        <Icon icon="lucide:calendar" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="Edit">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="warning"
                      >
                        <Icon icon="lucide:edit" />
                      </Button>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    );
  };

  const renderStatefulSetsTable = () => {
    const filteredStatefulSets = sortWorkloads(filterWorkloads(workloads.statefulsets));
    
    return (
      <Table aria-label="StatefulSets table" className="min-h-[400px]">
        <TableHeader>
          <TableColumn>NAME</TableColumn>
          <TableColumn>READY</TableColumn>
          <TableColumn>AGE</TableColumn>
          <TableColumn>ACTIONS</TableColumn>
        </TableHeader>
        <TableBody emptyContent="No statefulsets found">
          {filteredStatefulSets.map((sts, index) => {
            const stsName = sts.metadata?.name || 'Unknown';
            const ready = sts.status?.readyReplicas || 0;
            const desired = sts.spec?.replicas || 0;
            const age = formatAge(sts.metadata?.creationTimestamp);

            return (
              <TableRow key={index}>
                <TableCell>
                  {renderClickableWorkloadName(sts, 'statefulsets', 'lucide:database', 'warning')}
                </TableCell>
                <TableCell>{ready}/{desired}</TableCell>
                <TableCell>{age}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Tooltip content="View Details">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={() => handleWorkloadClick(sts, 'statefulsets')}
                      >
                        <Icon icon="lucide:eye" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="View Events">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="secondary"
                        onPress={() => fetchWorkloadEvents(stsName, 'statefulsets', selectedNamespace)}
                        isLoading={eventsLoading && selectedWorkloadName === stsName}
                      >
                        <Icon icon="lucide:calendar" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="Scale">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="warning"
                      >
                        <Icon icon="lucide:maximize" />
                      </Button>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    );
  };

  const renderDaemonSetsTable = () => {
    const filteredDaemonSets = sortWorkloads(filterWorkloads(workloads.daemonsets));
    
    return (
      <Table aria-label="DaemonSets table" className="min-h-[400px]">
        <TableHeader>
          <TableColumn>NAME</TableColumn>
          <TableColumn>DESIRED</TableColumn>
          <TableColumn>CURRENT</TableColumn>
          <TableColumn>READY</TableColumn>
          <TableColumn>UP-TO-DATE</TableColumn>
          <TableColumn>AVAILABLE</TableColumn>
          <TableColumn>AGE</TableColumn>
          <TableColumn>ACTIONS</TableColumn>
        </TableHeader>
        <TableBody emptyContent="No daemonsets found">
          {filteredDaemonSets.map((ds, index) => {
            const dsName = ds.metadata?.name || 'Unknown';
            const desired = ds.status?.desiredNumberScheduled || 0;
            const current = ds.status?.currentNumberScheduled || 0;
            const ready = ds.status?.numberReady || 0;
            const upToDate = ds.status?.updatedNumberScheduled || 0;
            const available = ds.status?.numberAvailable || 0;
            const age = formatAge(ds.metadata?.creationTimestamp);

            return (
              <TableRow key={index}>
                <TableCell>
                  {renderClickableWorkloadName(ds, 'daemonsets', 'lucide:server', 'danger')}
                </TableCell>
                <TableCell>{desired}</TableCell>
                <TableCell>{current}</TableCell>
                <TableCell>{ready}</TableCell>
                <TableCell>{upToDate}</TableCell>
                <TableCell>{available}</TableCell>
                <TableCell>{age}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Tooltip content="View Details">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={() => handleWorkloadClick(ds, 'daemonsets')}
                      >
                        <Icon icon="lucide:eye" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="View Events">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="secondary"
                        onPress={() => fetchWorkloadEvents(dsName, 'daemonsets', selectedNamespace)}
                        isLoading={eventsLoading && selectedWorkloadName === dsName}
                      >
                        <Icon icon="lucide:calendar" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="Edit">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="warning"
                      >
                        <Icon icon="lucide:edit" />
                      </Button>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    );
  };

  const renderJobsTable = () => {
    const filteredJobs = sortWorkloads(filterWorkloads(workloads.jobs));
    
    return (
      <Table aria-label="Jobs table" className="min-h-[400px]">
        <TableHeader>
          <TableColumn>NAME</TableColumn>
          <TableColumn>COMPLETIONS</TableColumn>
          <TableColumn>DURATION</TableColumn>
          <TableColumn>AGE</TableColumn>
          <TableColumn>ACTIONS</TableColumn>
        </TableHeader>
        <TableBody emptyContent="No jobs found">
          {filteredJobs.map((job, index) => {
            const jobName = job.metadata?.name || 'Unknown';
            const completions = `${job.status?.succeeded || 0}/${job.spec?.completions || 1}`;
            const startTime = job.status?.startTime;
            const completionTime = job.status?.completionTime;
            const duration = startTime && completionTime ? 
              Math.floor((new Date(completionTime).getTime() - new Date(startTime).getTime()) / 1000) + 's' : 
              (startTime ? Math.floor((Date.now() - new Date(startTime).getTime()) / 1000) + 's' : 'N/A');
            const age = formatAge(job.metadata?.creationTimestamp);

            return (
              <TableRow key={index}>
                <TableCell>
                  {renderClickableWorkloadName(job, 'jobs', 'lucide:play', 'default')}
                </TableCell>
                <TableCell>{completions}</TableCell>
                <TableCell>{duration}</TableCell>
                <TableCell>{age}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Tooltip content="View Details">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={() => handleWorkloadClick(job, 'jobs')}
                      >
                        <Icon icon="lucide:eye" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="View Events">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="secondary"
                        onPress={() => fetchWorkloadEvents(jobName, 'jobs', selectedNamespace)}
                        isLoading={eventsLoading && selectedWorkloadName === jobName}
                      >
                        <Icon icon="lucide:calendar" />
                      </Button>
                    </Tooltip>
                <Tooltip content="View Logs">
                  <Button
                    isIconOnly
                    size="sm"
                    variant="light"
                    color="warning"
                    onPress={() => handleViewLogsClick(job)}
                  >
                    <Icon icon="lucide:file-text" />
                  </Button>
                </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    );
  };

  const renderCronJobsTable = () => {
    const filteredCronJobs = sortWorkloads(filterWorkloads(workloads.cronjobs));
    
    return (
      <Table aria-label="CronJobs table" className="min-h-[400px]">
        <TableHeader>
          <TableColumn>NAME</TableColumn>
          <TableColumn>SCHEDULE</TableColumn>
          <TableColumn>SUSPEND</TableColumn>
          <TableColumn>ACTIVE</TableColumn>
          <TableColumn>LAST SCHEDULE</TableColumn>
          <TableColumn>AGE</TableColumn>
          <TableColumn>ACTIONS</TableColumn>
        </TableHeader>
        <TableBody emptyContent="No cronjobs found">
          {filteredCronJobs.map((cronjob, index) => {
            const cronjobName = cronjob.metadata?.name || 'Unknown';
            const schedule = cronjob.spec?.schedule || 'N/A';
            const suspend = cronjob.spec?.suspend ? 'True' : 'False';
            const active = cronjob.status?.active?.length || 0;
            const lastSchedule = cronjob.status?.lastScheduleTime ? 
              formatAge(cronjob.status.lastScheduleTime) : 'N/A';
            const age = formatAge(cronjob.metadata?.creationTimestamp);

            return (
              <TableRow key={index}>
                <TableCell>
                  {renderClickableWorkloadName(cronjob, 'cronjobs', 'lucide:clock', 'default')}
                </TableCell>
                <TableCell>
                  <code className="text-sm bg-content2 px-2 py-1 rounded">{schedule}</code>
                </TableCell>
                <TableCell>
                  <Chip color={suspend === 'True' ? 'warning' : 'success'} size="sm" variant="flat">
                    {suspend}
                  </Chip>
                </TableCell>
                <TableCell>{active}</TableCell>
                <TableCell>{lastSchedule}</TableCell>
                <TableCell>{age}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Tooltip content="View Details">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={() => handleWorkloadClick(cronjob, 'cronjobs')}
                      >
                        <Icon icon="lucide:eye" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="View Events">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="secondary"
                        onPress={() => fetchWorkloadEvents(cronjobName, 'cronjobs', selectedNamespace)}
                        isLoading={eventsLoading && selectedWorkloadName === cronjobName}
                      >
                        <Icon icon="lucide:calendar" />
                      </Button>
                    </Tooltip>
                    <Tooltip content="Trigger Job">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        color="warning"
                      >
                        <Icon icon="lucide:play" />
                      </Button>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    );
  };

  // Handler for View Logs button
  const handleViewLogsClick = async (workload: any) => {
    setLogsLoading(true);
    setIsLogsOpen(true);
    setSelectedLogs("");

    try {
      // Fetch logs for the workload - example command, adjust as needed
      const response = await fetch(`/api/v2.0/execute-kubectl-direct/${selectedClusterId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        },
        body: JSON.stringify({
          command: `kubectl logs ${workload.metadata?.name} -n ${selectedNamespace} --tail=100`
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch logs: ${response.statusText}`);
      }

      const data = await response.json();
      if (data.success && data.output) {
        setSelectedLogs(data.output);
      } else {
        setSelectedLogs("No logs available.");
      }
    } catch (err: any) {
      setSelectedLogs(`Error fetching logs: ${err.message}`);
    } finally {
      setLogsLoading(false);
    }
  };

  // Main tab content renderer
  const renderTabContent = () => {
    switch (selectedTab) {
      case 'pods':
        return renderPodsTable();
      case 'deployments':
        return renderDeploymentsTable();
      case 'services':
        return renderServicesTable();
      case 'statefulsets':
        return renderStatefulSetsTable();
      case 'daemonsets':
        return renderDaemonSetsTable();
      case 'jobs':
        return renderJobsTable();
      case 'cronjobs':
        return renderCronJobsTable();
      default:
        return renderPodsTable();
    }
  };

  // Stats cards renderer
  const renderStatsCards = () => {
    const stats = getWorkloadStats();
    
    return (
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6"
      >
        <motion.div variants={itemVariants}>
          <Card className="border-l-4 border-l-primary">
            <CardBody className="flex flex-row items-center justify-between p-4">
              <div>
                <p className="text-sm text-foreground-500">Total Workloads</p>
                <p className="text-2xl font-bold text-primary">{stats.total}</p>
              </div>
              <Icon icon="lucide:layers" className="text-3xl text-primary" />
            </CardBody>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="border-l-4 border-l-success">
            <CardBody className="flex flex-row items-center justify-between p-4">
              <div>
                <p className="text-sm text-foreground-500">Running</p>
                <p className="text-2xl font-bold text-success">{stats.running}</p>
              </div>
              <Icon icon="lucide:play-circle" className="text-3xl text-success" />
            </CardBody>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="border-l-4 border-l-warning">
            <CardBody className="flex flex-row items-center justify-between p-4">
              <div>
                <p className="text-sm text-foreground-500">Pending</p>
                <p className="text-2xl font-bold text-warning">{stats.pending}</p>
              </div>
              <Icon icon="lucide:clock" className="text-3xl text-warning" />
            </CardBody>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="border-l-4 border-l-danger">
            <CardBody className="flex flex-row items-center justify-between p-4">
              <div>
                <p className="text-sm text-foreground-500">Failed</p>
                <p className="text-2xl font-bold text-danger">{stats.failed}</p>
              </div>
              <Icon icon="lucide:x-circle" className="text-3xl text-danger" />
            </CardBody>
          </Card>
        </motion.div>
      </motion.div>
    );
  };

  // Workload type cards renderer pods, deployments, services, statefulsets, daemonsets, jobs, cronjobs
const renderWorkloadTypeCards = () => {
    const workloadTypes = [
      { key: 'pods', label: 'Pods', icon: 'lucide:box', color: 'primary' },
      { key: 'deployments', label: 'Deployments', icon: 'lucide:layers', color: 'secondary' },
      { key: 'services', label: 'Services', icon: 'lucide:globe', color: 'success' },
      { key: 'statefulsets', label: 'StatefulSets', icon: 'lucide:database', color: 'warning' },
      { key: 'daemonsets', label: 'DaemonSets', icon: 'lucide:server', color: 'danger' },
      { key: 'jobs', label: 'Jobs', icon: 'lucide:play', color: 'default' },
      { key: 'cronjobs', label: 'CronJobs', icon: 'lucide:clock', color: 'default' }
    ];

    return (
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-3 md:grid-cols-6 lg:grid-cols-7 gap-2 mb-6"


      >
        {workloadTypes.map((type) => (
          <motion.div key={type.key} variants={itemVariants} className="w-full max-w-[120px]">
            <Card 
              className={`cursor-pointer transition-all duration-200 ${
                selectedTab === type.key ? 'ring-2 ring-primary' : ''
              }`}
              isPressable
              onPress={() => setSelectedTab(type.key)}
              style={{ width: '100%', height: '100px'  }}
            >
              <CardBody className="text-center p-3 flex flex-col items-center justify-center gap-1">
                <Icon icon={type.icon} className={`text-2xl text-${type.color}`} />
                <p className="text-xl font-bold">{getWorkloadCount(type.key)}</p>
                <p className="text-xs text-foreground-500">{type.label}</p>
              </CardBody>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    );
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <Spinner size="lg" color="primary" />
          <p className="mt-4 text-foreground-500">Loading clusters...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Card className="max-w-md">

          <CardBody className="text-center p-8">
            <Icon icon="lucide:alert-circle" className="text-6xl text-danger mb-4" />
            <h3 className="text-lg font-semibold text-danger mb-2">Error</h3>
            <p className="text-foreground-500 mb-4">{error}</p>
            <Button color="primary" onPress={() => window.location.reload()}>
              Retry
            </Button>
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="p-6 space-y-6"
    >
      {/* Header */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <Icon icon="lucide:layers" className="text-3xl text-primary" />
              <div>
                <h1 className="text-2xl font-bold">Workloads Dashboard</h1>
                <p className="text-foreground-500">
                  Manage and monitor your Kubernetes workloads
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Switch
                isSelected={autoRefresh}
                onValueChange={setAutoRefresh}
                color="primary"
                startContent={<Icon icon="lucide:refresh-cw" />}
              >
                Auto Refresh
              </Switch>
              <Button
                color="primary"
                variant="flat"
                startContent={<Icon icon="lucide:bar-chart-3" />}
                onPress={onStatsOpen}
              >
                View Stats
              </Button>
            </div>
          </CardHeader>
        </Card>
      </motion.div>

      {/* Filters */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Filters</h3>
          </CardHeader>
          <CardBody>
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex-1 min-w-[250px]">
                <Select
                  label="Select Cluster"
                  placeholder="Choose a cluster"
                  selectedKeys={selectedClusterId ? [selectedClusterId.toString()] : []}
                  onSelectionChange={(keys) => {
                    const key = Array.from(keys)[0] as string;
                    setSelectedClusterId(key ? parseInt(key) : null);
                    setSelectedNamespace(""); // Reset namespace
                  }}
                  startContent={<Icon icon="lucide:server" />}
                  variant="bordered"
                  renderValue={(items) => {
                    return items.map((item) => {
                      const cluster = clusters.find(c => c.id.toString() === item.key);
                      return (
                        <div key={item.key} className="flex items-center gap-2">
                          {/* <Icon icon={getProviderIcon(cluster?.provider_name || "")} className="text-lg" /> */}
                          <span className="font-medium">{cluster?.cluster_name}</span>
                        </div>
                      );
                    });
                  }}
                >
                  {clusters.map((cluster) => (

                    <SelectItem key={cluster.id.toString()}>
                      <div className="flex items-center gap-3">
                        <Icon icon={getProviderIcon(cluster.provider_name)} className="text-lg" />
                        <div>
                          <p className="font-medium">{cluster.cluster_name}</p>
                          <p className="text-sm text-foreground-500">{cluster.provider_name}</p>
                        </div>
                      </div>
                    </SelectItem>
                  ))}
                </Select>
              </div>

              <div className="flex-1 min-w-[200px]">
                <Select
                  label="Select Namespace"
                  placeholder="Choose a namespace"
                  selectedKeys={selectedNamespace ? [selectedNamespace] : []}
                  onSelectionChange={(keys) => {
                    const key = Array.from(keys)[0] as string;
                    setSelectedNamespace(key || "");
                  }}
                  startContent={<Icon icon="lucide:folder" />}
                  isLoading={namespacesLoading}
                  isDisabled={!selectedClusterId}
                  variant="bordered"
                  renderValue={(items) => {
                    return items.map((item) => (
                      <div key={item.key} className="flex items-center gap-2">
                        {/* <Icon icon="lucide:folder" className="text-warning" /> */}

                        <span>{item.key.toString()}</span>
                      </div>
                    ));
                  }}
                >
                  {namespaces.map((namespace) => (
                    <SelectItem key={namespace}>
                      <div className="flex items-center gap-2">
                        <Icon icon="lucide:folder" className="text-warning" />
                        <span>{namespace}</span>
                      </div>
                    </SelectItem>
                  ))}
                </Select>
              </div>

              <div className="flex-1 min-w-[200px]">
                <Input
                  placeholder="Search workloads..."
                  value={searchTerm}
                  onValueChange={setSearchTerm}
                  startContent={<Icon icon="lucide:search" />}
                  isClearable
                  onClear={() => setSearchTerm("")}
                  variant="bordered"
                />
              </div>

              <div className="flex items-center gap-2">
                <Tooltip content="List View">
                  <Button
                    isIconOnly
                    variant={viewMode === 'list' ? 'solid' : 'light'}
                    color="primary"
                    onPress={() => setViewMode('list')}
                  >
                    <Icon icon="lucide:list" />
                  </Button>
                </Tooltip>
                <Tooltip content="Grid View">
                  {/* <Button
                    isIconOnly
                    variant={viewMode === 'grid' ? 'solid' : 'light'}
                    color="primary"
                    onPress={() => setViewMode('grid')}
                  >
                    <Icon icon="lucide:grid-3x3" />
                  </Button> */}
                </Tooltip>
              </div>

              <Dropdown>
                <DropdownTrigger>
                  <Button variant="bordered" startContent={<Icon icon="lucide:arrow-up-down" />}>
                    Sort by {sortBy}
                  </Button>
                </DropdownTrigger>
                <DropdownMenu
                  selectedKeys={[sortBy]}
                  onSelectionChange={(keys) => setSortBy(Array.from(keys)[0] as 'name' | 'status' | 'age')}
                >
                  <DropdownItem key="name">Name</DropdownItem>
                  <DropdownItem key="status">Status</DropdownItem>
                  <DropdownItem key="age">Age</DropdownItem>
                </DropdownMenu>
              </Dropdown>

              <Button
                isIconOnly
                variant="light"
                onPress={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              >
                <Icon icon={sortOrder === 'asc' ? 'lucide:arrow-up' : 'lucide:arrow-down'} />
              </Button>

              <Button
                color="primary"
                variant="flat"
                startContent={<Icon icon="lucide:refresh-cw" />}
                onPress={() => selectedClusterId && selectedNamespace && fetchWorkloads(selectedClusterId, selectedNamespace)}
                isLoading={workloadsLoading}
                isDisabled={!selectedClusterId || !selectedNamespace}
              >
                Refresh
              </Button>
            </div>
          </CardBody>
        </Card>
      </motion.div>

      {/* Stats Cards */}
      {selectedClusterId && selectedNamespace && renderStatsCards()}

      {/* Workload Type Cards */}
      {selectedClusterId && selectedNamespace && renderWorkloadTypeCards()}

      {/* Main Content */}
      {selectedClusterId && selectedNamespace ? (
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="flex items-center gap-3">
                <Icon icon={getWorkloadTypeIcon(selectedTab)} className={`text-2xl text-${getWorkloadTypeColor(selectedTab)}`} />
                <div>
                  <h3 className="text-lg font-semibold capitalize">{selectedTab}</h3>
                  <p className="text-sm text-foreground-500">
                    {getWorkloadCount(selectedTab)} {selectedTab} in {selectedNamespace}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Chip color="primary" variant="flat">
                  {clusters.find(c => c.id === selectedClusterId)?.cluster_name}
                </Chip>
                <Chip color="warning" variant="flat">
                  {selectedNamespace}
                </Chip>
              </div>
            </CardHeader>
            <CardBody>
              <Tabs
                selectedKey={selectedTab}
                onSelectionChange={(key) => setSelectedTab(key as string)}
                color="primary"
                variant="underlined"
                classNames={{
                  tabList: "gap-6 w-full relative rounded-none p-0 border-b border-divider",
                  cursor: "w-full bg-primary",
                  tab: "max-w-fit px-0 h-12",
                  tabContent: "group-data-[selected=true]:text-primary"
                }}
              >
                <Tab
                  key="pods"
                  title={
                    <div className="flex items-center gap-2">
                      <Icon icon="lucide:box" />
                      <span>Pods</span>
                      <Badge color="primary">{getWorkloadCount('pods')}</Badge>
                    </div>
                  }
                />
                <Tab
                  key="deployments"
                  title={
                    <div className="flex items-center gap-2">
                      <Icon icon="lucide:layers" />
                      <span>Deployments</span>
                      <Badge color="secondary">{getWorkloadCount('deployments')}</Badge>
                    </div>
                  }
                />
                <Tab
                  key="services"
                  title={
                    <div className="flex items-center gap-2">
                      <Icon icon="lucide:globe" />
                      <span>Services</span>
                      <Badge color="success">{getWorkloadCount('services')}</Badge>
                    </div>
                  }
                />
                <Tab
                  key="statefulsets"
                  title={
                    <div className="flex items-center gap-2">
                      <Icon icon="lucide:database" />
                      <span>StatefulSets</span>
                      <Badge color="warning">{getWorkloadCount('statefulsets')}</Badge>
                    </div>
                  }
                />
                <Tab
                  key="daemonsets"
                  title={
                    <div className="flex items-center gap-2">
                      <Icon icon="lucide:server" />
                      <span>DaemonSets</span>
                      <Badge color="danger">{getWorkloadCount('daemonsets')}</Badge>
                    </div>
                  }
                />
                <Tab
                  key="jobs"
                  title={
                    <div className="flex items-center gap-2">
                      <Icon icon="lucide:play" />
                      <span>Jobs</span>
                      <Badge color="default">{getWorkloadCount('jobs')}</Badge>
                    </div>
                  }
                />
                <Tab
                  key="cronjobs"
                  title={
                    <div className="flex items-center gap-2">
                      <Icon icon="lucide:clock" />
                      <span>CronJobs</span>
                      <Badge color="default">{getWorkloadCount('cronjobs')}</Badge>
                    </div>
                  }
                />
              </Tabs>

              <div className="mt-6">
                {workloadsLoading ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="text-center">
                      <Spinner size="lg" color="primary" />
                      <p className="mt-4 text-foreground-500">Loading {selectedTab}...</p>
                    </div>
                  </div>
                ) : (
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={selectedTab}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{ duration: 0.3 }}
                    >
                      {renderTabContent()}
                    </motion.div>
                  </AnimatePresence>
                )}
              </div>
            </CardBody>
          </Card>
        </motion.div>
      ) : (
        <motion.div variants={itemVariants}>
          <Card>
            <CardBody className="text-center py-12">
              <Icon icon="lucide:layers" className="text-6xl text-foreground-300 mb-4" />
              <h3 className="text-lg font-semibold text-foreground-500 mb-2">
                Select Cluster and Namespace
              </h3>
              <p className="text-foreground-400 mb-6">
                Choose a cluster and namespace to view workloads
              </p>
              {clusters.length === 0 && (
                <p className="text-sm text-foreground-500">
                  No clusters available. Please onboard a cluster first.
                </p>
              )}
            </CardBody>
          </Card>
        </motion.div>
      )}

      {/* Events Modal */}
      <Modal
        isOpen={isEventsOpen}
        onClose={onEventsClose}
        size="5xl"
        scrollBehavior="inside"
        backdrop="blur"
      >
        <ModalContent>
          <ModalHeader className="flex items-center gap-3">
            <Icon icon="lucide:calendar" className="text-2xl text-primary" />
            <div>
              <h3 className="text-xl font-semibold">Recent Events</h3>
              <p className="text-sm text-foreground-500">
                Events for {selectedWorkloadName} ({selectedWorkloadType}) in {selectedNamespace}
              </p>
            </div>
          </ModalHeader>
          <ModalBody>
            {eventsLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <Spinner size="lg" color="primary" />
                  <p className="mt-4 text-foreground-500">Loading events...</p>
                </div>
              </div>
            ) : selectedWorkloadEvents.length > 0 ? (
              <div className="space-y-4">
                {selectedWorkloadEvents.map((event, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <Card className={`border-l-4 ${
                      event.type === 'Warning' ? 'border-l-warning' : 
                      event.type === 'Error' ? 'border-l-danger' : 'border-l-success'
                    }`}>
                      <CardBody className="p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <Chip
                                color={getEventTypeColor(event.type)}
                                size="sm"
                                variant="flat"
                                startContent={
                                  <Icon 
                                    icon={
                                      event.type === 'Warning' ? 'lucide:alert-triangle' :
                                      event.type === 'Error' ? 'lucide:x-circle' : 'lucide:check-circle'
                                    } 
                                  />
                                }
                              >
                                {event.type}
                              </Chip>
                              <Chip color="primary" size="sm" variant="flat">
                                {event.reason}
                              </Chip>
                              <span className="text-sm text-foreground-500">
                                {formatEventTime(event.firstTimestamp || event.eventTime)}
                              </span>
                            </div>
                            <p className="text-foreground-700 mb-2">{event.message}</p>
                            <div className="flex items-center gap-4 text-sm text-foreground-500">
                              <span>Source: {event.source?.component || 'Unknown'}</span>
                              <span>Count: {event.count || 1}</span>
                              {event.lastTimestamp && event.firstTimestamp !== event.lastTimestamp && (
                                <span>Last: {formatEventTime(event.lastTimestamp)}</span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Tooltip content="Copy Event Details">
                              <Button
                                isIconOnly
                                size="sm"
                                variant="light"
                                onPress={() => {
                                  navigator.clipboard.writeText(JSON.stringify(event, null, 2));
                                }}
                              >
                                <Icon icon="lucide:copy" />
                              </Button>
                            </Tooltip>
                          </div>
                        </div>
                      </CardBody>
                    </Card>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <Icon icon="lucide:calendar-x" className="text-6xl text-foreground-300 mb-4" />
                <h3 className="text-lg font-semibold text-foreground-500 mb-2">No Events Found</h3>
                <p className="text-foreground-400">
                  No recent events found for {selectedWorkloadName}
                </p>
              </div>
            )}
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={onEventsClose}>
              Close
            </Button>
            <Button
              color="primary"
              startContent={<Icon icon="lucide:refresh-cw" />}
              onPress={() => fetchWorkloadEvents(selectedWorkloadName, selectedWorkloadType, selectedNamespace)}
              isLoading={eventsLoading}
            >
              Refresh Events
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Logs Modal */}
      <Modal
        isOpen={isLogsOpen}
        onClose={() => setIsLogsOpen(false)}
        size="5xl"
        scrollBehavior="inside"
        backdrop="blur"
      >
        <ModalContent>
          <ModalHeader className="flex items-center gap-3">
            <Icon icon="lucide:file-text" className="text-2xl text-primary" />
            <div>
              <h3 className="text-xl font-semibold">Workload Logs</h3>
              <p className="text-sm text-foreground-500">
                Logs for selected workload in {selectedNamespace}
              </p>
            </div>
          </ModalHeader>
          <ModalBody>
            {logsLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <Spinner size="lg" color="primary" />
                  <p className="mt-4 text-foreground-500">Loading logs...</p>
                </div>
              </div>
            ) : (
              <pre className="text-sm bg-content2 p-4 rounded overflow-auto whitespace-pre-wrap">
                {selectedLogs}
              </pre>
            )}
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={() => setIsLogsOpen(false)}>
              Close
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Workload Details Modal */}
      <Modal
        isOpen={isDetailsOpen}
        onClose={onDetailsClose}
        size="5xl"
        scrollBehavior="inside"
        backdrop="blur"
      >
        <ModalContent>
          <ModalHeader className="flex items-center gap-3">
            <Icon 
              icon={getWorkloadTypeIcon(selectedWorkload?.type || 'pods')} 
              className={`text-2xl text-${getWorkloadTypeColor(selectedWorkload?.type || 'pods')}`} 
            />
            <div>
              <h3 className="text-xl font-semibold">
                {selectedWorkload?.metadata?.name || 'Workload Details'}
              </h3>
              <p className="text-sm text-foreground-500">
                {selectedWorkload?.type} in {selectedNamespace}
              </p>
            </div>
          </ModalHeader>
          <ModalBody>
            {selectedWorkload && (
              <div className="space-y-6">
                {/* Basic Info */}
                <Card>
                  <CardHeader>
                    <h4 className="text-lg font-semibold">Basic Information</h4>
                  </CardHeader>
                  <CardBody>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-foreground-500">Name</p>
                        <p className="font-medium">{selectedWorkload.metadata?.name}</p>
                      </div>
                      <div>
                        <p className="text-sm text-foreground-500">Namespace</p>
                        <p className="font-medium">{selectedWorkload.metadata?.namespace}</p>
                      </div>
                      <div>
                        <p className="text-sm text-foreground-500">Created</p>
                        <p className="font-medium">{formatAge(selectedWorkload.metadata?.creationTimestamp)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-foreground-500">UID</p>
                        <p className="font-mono text-sm">{selectedWorkload.metadata?.uid}</p>
                      </div>
                    </div>
                  </CardBody>
                </Card>

                {/* Labels */}
                {selectedWorkload.metadata?.labels && (
                  <Card>
                    <CardHeader>
                      <h4 className="text-lg font-semibold">Labels</h4>
                    </CardHeader>
                    <CardBody>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(selectedWorkload.metadata.labels).map(([key, value]) => (
                          <Chip key={key} size="sm" variant="flat" color="primary">
                            {key}: {value as string}
                          </Chip>
                        ))}
                      </div>
                    </CardBody>
                  </Card>
                )}

                {/* Annotations */}
                {selectedWorkload.metadata?.annotations && Object.keys(selectedWorkload.metadata.annotations).length > 0 && (
                  <Card>
                    <CardHeader>
                      <h4 className="text-lg font-semibold">Annotations</h4>
                    </CardHeader>
                    <CardBody>
                      <div className="space-y-2">
                        {Object.entries(selectedWorkload.metadata.annotations).map(([key, value]) => (
                          <div key={key} className="flex flex-col gap-1">
                            <p className="text-sm font-medium text-foreground-600">{key}</p>
                            <p className="text-sm text-foreground-500 font-mono bg-content2 p-2 rounded">
                              {value as string}
                            </p>
                          </div>
                        ))}
                      </div>
                    </CardBody>
                  </Card>
                )}

                {/* Status */}
                {selectedWorkload.status && (
                  <Card>
                    <CardHeader>
                      <h4 className="text-lg font-semibold">Status</h4>
                    </CardHeader>
                    <CardBody>
                      <pre className="text-sm bg-content2 p-4 rounded overflow-auto">
                        {JSON.stringify(selectedWorkload.status, null, 2)}
                      </pre>
                    </CardBody>
                  </Card>
                )}

                {/* Spec */}
                {selectedWorkload.spec && (
                  <Card>
                    <CardHeader>
                      <h4 className="text-lg font-semibold">Specification</h4>
                    </CardHeader>
                    <CardBody>
                      <pre className="text-sm bg-content2 p-4 rounded overflow-auto">
                        {JSON.stringify(selectedWorkload.spec, null, 2)}
                      </pre>
                    </CardBody>
                  </Card>
                )}
              </div>
            )}
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={onDetailsClose}>
              Close
            </Button>
            <Button
              color="primary"
              startContent={<Icon icon="lucide:calendar" />}
              onPress={() => {
                onDetailsClose();
                fetchWorkloadEvents(
                  selectedWorkload?.metadata?.name || '', 
                  selectedWorkload?.type || '', 
                  selectedNamespace
                );
              }}
            >
              View Events
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Stats Modal */}
      <Modal
        isOpen={isStatsOpen}
        onClose={onStatsClose}
        size="4xl"
        scrollBehavior="inside"
        backdrop="blur"
      >
        <ModalContent>
          <ModalHeader className="flex items-center gap-3">
            <Icon icon="lucide:bar-chart-3" className="text-2xl text-primary" />
            <div>
              <h3 className="text-xl font-semibold">Workload Statistics</h3>
              <p className="text-sm text-foreground-500">
                Overview of workloads in {selectedNamespace}
              </p>
            </div>
          </ModalHeader>
          <ModalBody>
            <div className="space-y-6">
              {/* Overall Stats */}
              <Card>
                <CardHeader>
                  <h4 className="text-lg font-semibold">Overall Statistics</h4>
                </CardHeader>
                <CardBody>
                  <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6"
                  >
                    {(() => {
                      const stats = getWorkloadStats();
                      return [
                        { label: 'Total', value: stats.total, color: 'primary', icon: 'lucide:layers' },
                        { label: 'Running', value: stats.running, color: 'success', icon: 'lucide:play-circle' },
                        { label: 'Pending', value: stats.pending, color: 'warning', icon: 'lucide:clock' },
                        { label: 'Failed', value: stats.failed, color: 'danger', icon: 'lucide:x-circle' }
                      ].map((stat, index) => (
                        <motion.div
                          key={stat.label}
                          variants={itemVariants}
                          style={{ animationDelay: `${index * 0.1}s` }}
                          className="text-center"
                        >
                          <Card className={`border-l-4 border-l-${stat.color}`}>
                            <CardBody className="flex flex-row items-center justify-between p-4">
                              <div>
                                <p className="text-sm text-foreground-500">{stat.label}</p>
                                <p className={`text-2xl font-bold text-${stat.color}`}>{stat.value}</p>
                              </div>
                              <Icon icon={stat.icon} className={`text-3xl text-${stat.color}`} />
                            </CardBody>
                          </Card>
                        </motion.div>
                      ));
                    })()}
                  </motion.div>
                </CardBody>
              </Card>

              {/* Workload Type Breakdown */}
              <Card>
                <CardHeader>
                  <h4 className="text-lg font-semibold">Workload Type Breakdown</h4>
                </CardHeader>
                <CardBody>
                  <div className="space-y-4">
                    {[
                      { key: 'pods', label: 'Pods', icon: 'lucide:box', color: 'primary' },
                      { key: 'deployments', label: 'Deployments', icon: 'lucide:layers', color: 'secondary' },
                      { key: 'services', label: 'Services', icon: 'lucide:globe', color: 'success' },
                      { key: 'statefulsets', label: 'StatefulSets', icon: 'lucide:database', color: 'warning' },
                      { key: 'daemonsets', label: 'DaemonSets', icon: 'lucide:server', color: 'danger' },
                      { key: 'jobs', label: 'Jobs', icon: 'lucide:play', color: 'default' },
                      { key: 'cronjobs', label: 'CronJobs', icon: 'lucide:clock', color: 'default' }
                    ].map((type) => {
                      const count = getWorkloadCount(type.key);
                      const total = getWorkloadStats().total;
                      const percentage = total > 0 ? (count / total) * 100 : 0;
                      
                      return (
                        <div key={type.key} className="flex items-center gap-4">
                          <div className="flex items-center gap-3 min-w-[150px]">
                            <Icon icon={type.icon} className={`text-${type.color}`} />
                            <span className="font-medium">{type.label}</span>
                          </div>
                          <div className="flex-1">
                            <Progress
                              value={percentage}
                              color={type.color as any}
                              className="max-w-md"
                              showValueLabel={true}
                              formatOptions={{
                                style: "decimal",
                                minimumFractionDigits: 1,
                                maximumFractionDigits: 1,
                              }}
                            />
                          </div>
                          <span className="font-bold min-w-[40px] text-right">{count}</span>
                        </div>
                      );
                    })}
                  </div>
                </CardBody>
              </Card>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={onStatsClose}>
              Close
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </motion.div>
  );
};

export default WorkloadDashboard;
