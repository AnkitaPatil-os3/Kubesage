import React, { useState, useEffect } from 'react';
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Input,
  Textarea,
  Select,
  SelectItem,
  Tabs,
  Tab,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  useDisclosure,
  Spinner,
  Progress,
  Divider,
  Code,
  Accordion,
  AccordionItem,
  Badge,
  Avatar,
  Tooltip,
  Switch,
  ScrollShadow,
  Spacer,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  ButtonGroup,
  Pagination
} from '@heroui/react';
import { Icon } from '@iconify/react';
import axios from 'axios';

// Types
interface IncidentData {
  alert_name?: string;
  namespace?: string;
  pod_name?: string;
  resource_name?: string;
  usage?: string;
  threshold?: string;
  duration?: string;
  status?: string;
  reason?: string;
  node_name?: string;
  container_name?: string;
  deployment_name?: string;
  message?: string;
  type?: string;
  metadata_name?: string;
  involved_object_kind?: string;
  involved_object_name?: string;
  source_component?: string;
  count?: number;
}

interface Incident {
  id: string;
  metadata_name: string;
  metadata_namespace?: string;
  metadata_creation_timestamp?: string;
  type: string;
  reason: string;
  message: string;
  count?: number;
  first_timestamp?: string;
  last_timestamp?: string;
  source_component?: string;
  source_host?: string;
  involved_object_kind?: string;
  involved_object_name?: string;
  involved_object_labels?: Record<string, any>;
  involved_object_annotations?: Record<string, any>;
  reporting_component?: string;
}

interface SolutionStep {
  step_id: number;
  action_type: string;
  description: string;
  target_resource: Record<string, any>;
  command_or_payload: Record<string, any>;
  expected_outcome: string;
  executor: string;
}

interface IncidentSolution {
  solution_id: string;
  incident_id: string;
  incident_type: string;
  summary: string;
  analysis: string;
  steps: SolutionStep[];
  confidence_score: number;
  estimated_time_to_resolve_mins: number;
  severity_level: string;
  recommendations: string[];
  active_executors: string[];
}

interface RemediationSolution {
  issue_summary: string;
  suggestion: string;
  command: string;
  is_executable: boolean;
  severity_level: string;
  estimated_time_mins: number;
  confidence_score: number;
  active_executors: string[];
}

interface ExecutionResult {
  status: string;
  command?: string;
  output?: string;
  error?: string;
  reason?: string;
  suggestion?: string;
}

interface HistoryRecord {
  id: string;
  alert_name: string;
  namespace: string;
  resource_name?: string;
  command: string;
  status: string;
  executed_at: string;
  confidence_score?: number;
  severity_level: string;
  execution_time_ms?: number;
  error_message?: string;
}

interface ExecutorStatus {
  name: string;
  status: number;
  status_text: string;
  updated_at: string;
}

interface Stats {
  execution_stats: Record<string, number>;
  top_alerts: Array<{ alert_name: string; count: number }>;
  recent_activity: { last_24_hours: number };
}

interface Recommendation {
  step_id: number;
  description: string;
  command: string;
  action_type: string;
  target_resource: string;
  expected_outcome: string;
  executor: string;
  is_executable: boolean;
}

interface CommandExecutionHistory {
  id: string;
  command: string;
  executor: string;
  status: string;
  executed_at: string;
  execution_time_ms?: number;
  step_id?: number;
  expected_outcome?: string;
  output?: string;
  error?: string;
}

const API_BASE_URL = 'https://10.0.32.108:8004';

const RemediationPage: React.FC = () => {
  // State management
  const [activeTab, setActiveTab] = useState('incidents');
  const [loading, setLoading] = useState(false);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [incidentSolution, setIncidentSolution] = useState<IncidentSolution | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [commandHistory, setCommandHistory] = useState<CommandExecutionHistory[]>([]);
  
  // Incident creation form
  const [incidentData, setIncidentData] = useState<IncidentData>({
    alert_name: '',
    namespace: 'default',
    pod_name: '',
    usage: '',
    threshold: '',
    duration: '',
    message: '',
    type: 'Warning',
    reason: ''
  });

  // Remediation states
  const [alertData, setAlertData] = useState<IncidentData>({
    alert_name: '',
    namespace: 'default',
    pod_name: '',
    usage: '',
    threshold: '',
    duration: ''
  });
  const [remediationSolution, setRemediationSolution] = useState<RemediationSolution | null>(null);
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [executors, setExecutors] = useState<ExecutorStatus[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [autoExecute, setAutoExecute] = useState(false);
  const [confirmExecution, setConfirmExecution] = useState(false);

  // Pagination and filtering
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [filterType, setFilterType] = useState('');
  const [filterNamespace, setFilterNamespace] = useState('');

  // Modal controls
  const { isOpen: isIncidentModalOpen, onOpen: onIncidentModalOpen, onClose: onIncidentModalClose } = useDisclosure();
  const { isOpen: isAnalysisModalOpen, onOpen: onAnalysisModalOpen, onClose: onAnalysisModalClose } = useDisclosure();
  const { isOpen: isExecuteModalOpen, onOpen: onExecuteModalOpen, onClose: onExecuteModalClose } = useDisclosure();
  const { isOpen: isResultModalOpen, onOpen: onResultModalOpen, onClose: onResultModalClose } = useDisclosure();
  const { isOpen: isRecommendationsModalOpen, onOpen: onRecommendationsModalOpen, onClose: onRecommendationsModalClose } = useDisclosure();

  // Load data on component mount
  useEffect(() => {
    loadIncidents();
    loadHistory();
    loadExecutors();
    loadStats();
  }, []);

  // API 1: Create/Process Incidents
  const createIncident = async () => {
    if (!incidentData.alert_name) {
      alert('Please provide an alert name');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        incidents: [{
          metadata: {
            name: `${incidentData.alert_name}-${Date.now()}`,
            namespace: incidentData.namespace,
            creationTimestamp: new Date().toISOString()
          },
          type: incidentData.type,
          reason: incidentData.reason || incidentData.alert_name,
          message: incidentData.message || `Alert: ${incidentData.alert_name}`,
          count: 1,
          firstTimestamp: new Date().toISOString(),
          lastTimestamp: new Date().toISOString(),
          source: {
            component: 'kubesage-ui',
            host: 'localhost'
          },
          involvedObject: {
            kind: 'Pod',
            name: incidentData.pod_name || 'unknown-pod',
            namespace: incidentData.namespace,
            labels: {},
            annotations: {}
          },
          reportingComponent: 'kubesage-analyzer',
          reportingInstance: 'analyzer-1'
        }]
      };

      await axios.post(`${API_BASE_URL}/incidents`, payload);
      alert('Incident created successfully!');
      onIncidentModalClose();
      loadIncidents(); // Refresh incidents list
      
      // Reset form
      setIncidentData({
        alert_name: '',
        namespace: 'default',
        pod_name: '',
        usage: '',
        threshold: '',
        duration: '',
        message: '',
        type: 'Warning',
        reason: ''
      });
    } catch (error: any) {
      console.error('Failed to create incident:', error);
      alert(`Failed to create incident: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // API 2: Get All Incidents
  const loadIncidents = async () => {
    try {
      const params = new URLSearchParams();
      if (filterType) params.append('type', filterType);
      if (filterNamespace) params.append('namespace', filterNamespace);
      params.append('skip', ((currentPage - 1) * itemsPerPage).toString());
      params.append('limit', itemsPerPage.toString());

      const response = await axios.get(`${API_BASE_URL}/incidents?${params}`);
      setIncidents(response.data || []);
    } catch (error) {
      console.error('Failed to load incidents:', error);
    }
  };

  // API 3: Get Incident by ID
  const getIncidentById = async (incidentId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/incidents/${incidentId}`);
      setSelectedIncident(response.data);
      return response.data;
    } catch (error) {
      console.error('Failed to get incident:', error);
      return null;
    }
  };

  // API 4: Analyze Incident
  const analyzeIncident = async (incident: Incident) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/analyze-incident`, incident);
      setIncidentSolution(response.data.solution);
      setSelectedIncident(incident);
      onAnalysisModalOpen();
    } catch (error: any) {
      console.error('Analysis failed:', error);
      alert(`Analysis failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // API 5: Analyze Incident by ID  
  const analyzeIncidentById = async (incidentId: string) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/analyze-incident/${incidentId}`);
      setIncidentSolution(response.data.solution);
      onAnalysisModalOpen();
    } catch (error: any) {
      console.error('Analysis failed:', error);
      alert(`Analysis failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // API 6-8: Executor Management
  const loadExecutors = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/executors/status`);
      setExecutors(response.data.executors || []);
    } catch (error) {
      console.error('Failed to load executors:', error);
    }
  };

  const updateExecutorStatus = async (executorName: string, status: number) => {
    try {
      await axios.post(`${API_BASE_URL}/executors/${executorName}/status`, status);
      loadExecutors();
    } catch (error: any) {
      console.error('Failed to update executor:', error);
      alert(`Failed to update executor: ${error.response?.data?.detail || error.message}`);
    }
  };

  // API 9: Remediate (Analyze Alert)
  const analyzeAlert = async () => {
    if (!alertData.alert_name) {
      alert('Please provide an alert name');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/remediate`, { alert_data: alertData });
      setRemediationSolution(response.data.remediation);
      setExecutionResult(null);
    } catch (error: any) {
      console.error('Analysis failed:', error);
      alert(`Analysis failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // API 10: Execute Remediation
  const executeRemediationCommand = async () => {
    if (!remediationSolution) return;

    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/remediate/execute`, {
        command: remediationSolution.command,
        is_executable: remediationSolution.is_executable,
        executor: 'kubectl',
        confirm_execution: true,
        alert_name: alertData.alert_name,
        namespace: alertData.namespace,
        resource_name: alertData.pod_name || alertData.resource_name,
        confidence_score: remediationSolution.confidence_score,
        severity_level: remediationSolution.severity_level
      });
      
      setExecutionResult(response.data.execution_result);
      onExecuteModalClose();
      onResultModalOpen();
      loadHistory();
    } catch (error: any) {
      console.error('Execution failed:', error);
      alert(`Execution failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // API 11: Analyze and Execute
  const analyzeAndExecute = async () => {
    if (!alertData.alert_name) {
      alert('Please provide an alert name');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/remediate/analyze-and-execute`, {
        alert_data: alertData,
        auto_execute: autoExecute,
        confirm_execution: confirmExecution
      });
      
      setRemediationSolution(response.data.analysis);
      setExecutionResult(response.data.execution_result);
      
      if (response.data.auto_executed) {
        onResultModalOpen();
        loadHistory();
      }
    } catch (error: any) {
      console.error('Analyze and execute failed:', error);
      alert(`Operation failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // API 12: Get Remediation History
  const loadHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/remediation/history`);
      setHistory(response.data.history || []);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  // API 13: Get Remediation Statistics
  const loadStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/remediation/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  // API 14: Get Incident Recommendations
  const getIncidentRecommendations = async (incidentId: string) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/incidents/${incidentId}/recommendations`);
      const recs = response.data.recommendations.map((rec: any) => ({
        step_id: rec.step_id,
        description: rec.description,
        command: rec.command,
        action_type: rec.action_type,
        target_resource: rec.target_resource,
        expected_outcome: rec.expected_outcome,
        executor: rec.executor,
        is_executable: rec.is_executable
      }));
      setRecommendations(recs);
      onRecommendationsModalOpen();
    } catch (error: any) {
      console.error('Failed to get recommendations:', error);
      alert(`Failed to get recommendations: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // API 15: Execute Command
  const executeCommand = async (incidentId: string, command: string, stepId?: number) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/execute-command`, {
        incident_id: incidentId,
        command: command,
        executor: 'kubectl',
        confirm_execution: true,
        step_id: stepId,
        expected_outcome: 'Command execution'
      });
      
      setExecutionResult(response.data.execution_result);
      onResultModalOpen();
      loadCommandHistory(incidentId);
    } catch (error: any) {
      console.error('Command execution failed:', error);
      alert(`Command execution failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // API 16: Get Command Execution History
  const loadCommandHistory = async (incidentId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/incidents/${incidentId}/execution-history`);
      setCommandHistory(response.data.execution_history || []);
    } catch (error) {
      console.error('Failed to load command history:', error);
    }
  };

  // Helper functions
  const getSeverityColor = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL': return 'danger';
      case 'HIGH': return 'warning';
      case 'MEDIUM': return 'primary';
      case 'LOW': return 'success';
      default: return 'default';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'success': return 'success';
      case 'failed': return 'danger';
      case 'skipped': return 'warning';
      case 'blocked': return 'secondary';
      default: return 'default';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'warning': return 'warning';
      case 'normal': return 'success';
      default: return 'default';
    }
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return 'N/A';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const commonAlerts = [
    'HighCPUUsage',
    'HighMemoryUsage',
    'PodCrashLooping',
    'ImagePullBackOff',
    'NodeNotReady',
    'DiskSpaceHigh',
    'NetworkLatencyHigh',
    'ServiceUnavailable'
  ];

  // Filter incidents based on current filters
  const filteredIncidents = incidents.filter(incident => {
    if (filterType && incident.type !== filterType) return false;
    if (filterNamespace && incident.metadata_namespace !== filterNamespace) return false;
    return true;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">KubeSage Remediation Center</h1>
          <p className="text-default-500 mt-1">Comprehensive Kubernetes incident management and AI-powered remediation</p>
        </div>
        <div className="flex items-center gap-4">
          <Badge content={stats?.recent_activity.last_24_hours || 0} color="primary">
            <Icon icon="solar:activity-bold" className="text-2xl text-primary" />
          </Badge>
          <Button
            color="primary"
            variant="solid"
            onPress={onIncidentModalOpen}
            startContent={<Icon icon="solar:add-circle-bold" />}
          >
            Create Incident
          </Button>
        </div>
      </div>

      {/* Main Tabs */}
      <Tabs 
        selectedKey={activeTab} 
        onSelectionChange={(key) => setActiveTab(key as string)}
        variant="bordered"
        classNames={{
          tabList: "gap-6 w-full relative rounded-none p-0 border-b border-divider",
          cursor: "w-full bg-primary",
          tab: "max-w-fit px-0 h-12",
          tabContent: "group-data-[selected=true]:text-primary"
        }}
      >
        {/* Tab 1: Incidents Management */}
        <Tab
          key="incidents"
          title={
            <div className="flex items-center space-x-2">
              <Icon icon="solar:bug-minimalistic-bold" />
              <span>Incidents</span>
              <Badge content={incidents.length} size="sm" color="primary" />
            </div>
          }
        >
          <div className="mt-6 space-y-6">
            {/* Filters */}
            <Card>
              <CardBody>
                <div className="flex items-center gap-4 flex-wrap">
                  <Select
                    placeholder="Filter by type"
                    className="max-w-xs"
                    selectedKeys={filterType ? [filterType] : []}
                    onSelectionChange={(keys) => setFilterType(Array.from(keys)[0] as string || '')}
                  >
                    <SelectItem key="Warning">Warning</SelectItem>
                    <SelectItem key="Normal">Normal</SelectItem>
                  </Select>
                  <Select
                    placeholder="Filter by namespace"
                    className="max-w-xs"
                    selectedKeys={filterNamespace ? [filterNamespace] : []}
                    onSelectionChange={(keys) => setFilterNamespace(Array.from(keys)[0] as string || '')}
                  >
                    <SelectItem key="default">default</SelectItem>
                    <SelectItem key="kube-system">kube-system</SelectItem>
                    <SelectItem key="monitoring">monitoring</SelectItem>
                  </Select>
                  <Button
                    color="primary"
                    variant="flat"
                    onPress={loadIncidents}
                    startContent={<Icon icon="solar:refresh-bold" />}
                  >
                    Refresh
                  </Button>
                  <Button
                    color="danger"
                    variant="light"
                    onPress={() => {
                      setFilterType('');
                      setFilterNamespace('');
                      loadIncidents();
                    }}
                    startContent={<Icon icon="solar:close-circle-bold" />}
                  >
                    Clear Filters
                  </Button>
                </div>
              </CardBody>
            </Card>

            {/* Incidents Table */}
            <Card>
              <CardHeader className="flex justify-between">
                <h3 className="text-lg font-semibold">Kubernetes Incidents</h3>
                <div className="flex items-center gap-2">
                  <Chip size="sm" variant="flat" color="primary">
                    Total: {filteredIncidents.length}
                  </Chip>
                </div>
              </CardHeader>
              <CardBody className="p-0">
                <Table aria-label="Incidents table">
                  <TableHeader>
                    <TableColumn>INCIDENT</TableColumn>
                    <TableColumn>TYPE</TableColumn>
                    <TableColumn>NAMESPACE</TableColumn>
                    <TableColumn>OBJECT</TableColumn>
                    <TableColumn>CREATED</TableColumn>
                    <TableColumn>COUNT</TableColumn>
                    <TableColumn>ACTIONS</TableColumn>
                  </TableHeader>
                  <TableBody emptyContent="No incidents found">
                    {filteredIncidents.map((incident) => (
                      <TableRow key={incident.id}>
                        <TableCell>
                          <div className="flex flex-col">
                            <p className="font-medium">{incident.reason}</p>
                            <p className="text-xs text-default-500 truncate max-w-xs">
                              {incident.message}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="sm"
                            color={getTypeColor(incident.type)}
                            variant="flat"
                          >
                            {incident.type}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          <Chip size="sm" variant="flat" color="primary">
                            {incident.metadata_namespace || 'N/A'}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <p className="text-sm font-medium">
                              {incident.involved_object_kind || 'N/A'}
                            </p>
                            <p className="text-xs text-default-500">
                              {incident.involved_object_name || 'N/A'}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <p className="text-sm">
                            {formatDate(incident.metadata_creation_timestamp)}
                          </p>
                        </TableCell>
                        <TableCell>
                          <Badge content={incident.count || 1} color="secondary">
                            <Icon icon="solar:repeat-bold" />
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Tooltip content="Analyze Incident">
                              <Button
                                isIconOnly
                                size="sm"
                                variant="light"
                                color="primary"
                                onPress={() => analyzeIncident(incident)}
                                isLoading={loading}
                              >
                                <Icon icon="solar:cpu-bolt-line-duotone" />
                              </Button>
                            </Tooltip>
                            <Tooltip content="Get Recommendations">
                              <Button
                                isIconOnly
                                size="sm"
                                variant="light"
                                color="secondary"
                                onPress={() => getIncidentRecommendations(incident.id)}
                              >
                                <Icon icon="solar:lightbulb-bold" />
                              </Button>
                            </Tooltip>
                            <Tooltip content="View Details">
                              <Button
                                isIconOnly
                                size="sm"
                                variant="light"
                                color="default"
                                onPress={() => getIncidentById(incident.id)}
                              >
                                <Icon icon="solar:eye-bold" />
                              </Button>
                            </Tooltip>
                            <Tooltip content="Command History">
                              <Button
                                isIconOnly
                                size="sm"
                                variant="light"
                                color="warning"
                                onPress={() => loadCommandHistory(incident.id)}
                              >
                                <Icon icon="solar:history-bold" />
                              </Button>
                            </Tooltip>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardBody>
            </Card>

            {/* Pagination */}
            <div className="flex justify-center">
              <Pagination
                total={Math.ceil(filteredIncidents.length / itemsPerPage)}
                page={currentPage}
                onChange={setCurrentPage}
                color="primary"
                showControls
              />
            </div>
          </div>
        </Tab>

        {/* Tab 2: Alert Remediation */}
        <Tab
          key="remediation"
          title={
            <div className="flex items-center space-x-2">
              <Icon icon="solar:cpu-bolt-line-duotone" />
              <span>Alert Remediation</span>
            </div>
          }
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
            {/* Alert Input Form */}
            <Card className="h-fit">
              <CardHeader className="flex gap-3">
                <Avatar
                  icon={<Icon icon="solar:danger-triangle-bold" />}
                  classNames={{
                    base: "bg-gradient-to-br from-warning to-danger",
                    icon: "text-white",
                  }}
                />
                <div className="flex flex-col">
                  <p className="text-md font-semibold">Alert Analysis</p>
                  <p className="text-small text-default-500">AI-powered alert remediation</p>
                </div>
              </CardHeader>
              <CardBody className="space-y-4">
                <Select
                  label="Alert Name"
                  placeholder="Select or type alert name"
                  selectedKeys={alertData.alert_name ? [alertData.alert_name] : []}
                  onSelectionChange={(keys) => {
                    const selected = Array.from(keys)[0] as string;
                    setAlertData(prev => ({ ...prev, alert_name: selected }));
                  }}
                  startContent={<Icon icon="solar:danger-triangle-bold" className="text-warning" />}
                >
                  {commonAlerts.map((alert) => (
                    <SelectItem key={alert} value={alert}>
                      {alert}
                    </SelectItem>
                  ))}
                </Select>

                <Input
                  label="Custom Alert Name"
                  placeholder="Or enter custom alert name"
                  value={alertData.alert_name}
                  onValueChange={(value) => setAlertData(prev => ({ ...prev, alert_name: value }))}
                  startContent={<Icon icon="solar:edit-bold" />}
                />

                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Namespace"
                    placeholder="default"
                    value={alertData.namespace}
                    onValueChange={(value) => setAlertData(prev => ({ ...prev, namespace: value }))}
                    startContent={<Icon icon="solar:folder-bold" />}
                  />
                  <Input
                    label="Pod/Resource Name"
                    placeholder="pod-name"
                    value={alertData.pod_name}
                    onValueChange={(value) => setAlertData(prev => ({ ...prev, pod_name: value }))}
                    startContent={<Icon icon="solar:server-bold" />}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Current Usage"
                    placeholder="95%"
                    value={alertData.usage}
                    onValueChange={(value) => setAlertData(prev => ({ ...prev, usage: value }))}
                    startContent={<Icon icon="solar:chart-bold" />}
                  />
                  <Input
                    label="Threshold"
                    placeholder="80%"
                    value={alertData.threshold}
                    onValueChange={(value) => setAlertData(prev => ({ ...prev, threshold: value }))}
                    startContent={<Icon icon="solar:target-bold" />}
                  />
                </div>

                <Input
                  label="Duration"
                  placeholder="15m"
                  value={alertData.duration}
                  onValueChange={(value) => setAlertData(prev => ({ ...prev, duration: value }))}
                  startContent={<Icon icon="solar:clock-circle-bold" />}
                />

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Switch
                        isSelected={autoExecute}
                        onValueChange={setAutoExecute}
                        color="warning"
                      />
                      <span className="text-sm">Auto Execute</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        isSelected={confirmExecution}
                        onValueChange={setConfirmExecution}
                        color="success"
                      />
                      <span className="text-sm">Confirm Execution</span>
                    </div>
                  </div>

                  {autoExecute && (
                    <div className="p-3 bg-warning/10 rounded-lg border border-warning/20">
                      <div className="flex items-center gap-2 mb-1">
                        <Icon icon="solar:shield-warning-bold" className="text-warning" />
                        <span className="text-sm font-medium text-warning">Auto Execute Enabled</span>
                      </div>
                      <p className="text-xs text-default-600">
                        Commands will be executed automatically if marked as safe and execution is confirmed.
                      </p>
                    </div>
                  )}
                </div>

                <div className="flex gap-2">
                  <Button
                    color="primary"
                    variant="solid"
                    onPress={analyzeAlert}
                    isLoading={loading}
                    startContent={!loading && <Icon icon="solar:cpu-bolt-line-duotone" />}
                    className="flex-1"
                  >
                    Analyze Alert
                  </Button>
                  <Button
                    color="secondary"
                    variant="solid"
                    onPress={analyzeAndExecute}
                    isLoading={loading}
                    startContent={!loading && <Icon icon="solar:play-circle-bold" />}
                    className="flex-1"
                  >
                    Analyze & Execute
                  </Button>
                </div>
              </CardBody>
            </Card>

            {/* Analysis Results */}
            <Card className="h-fit">
              <CardHeader className="flex gap-3">
                <Avatar
                  icon={<Icon icon="solar:brain-bold" />}
                  classNames={{
                    base: "bg-gradient-to-br from-success to-primary",
                    icon: "text-black/80",
                  }}
                />
                <div className="flex flex-col">
                  <p className="text-md font-semibold">AI Analysis Results</p>
                  <p className="text-small text-default-500">LLM-powered solution recommendations</p>
                </div>
              </CardHeader>
              <CardBody>
                {remediationSolution ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Chip
                        color={getSeverityColor(remediationSolution.severity_level)}
                        variant="flat"
                        startContent={<Icon icon="solar:danger-triangle-bold" />}
                      >
                        {remediationSolution.severity_level}
                      </Chip>
                      <Chip
                        color="primary"
                        variant="flat"
                        startContent={<Icon icon="solar:clock-circle-bold" />}
                      >
                        ~{remediationSolution.estimated_time_mins}min
                      </Chip>
                      <Chip
                        color="success"
                        variant="flat"
                        startContent={<Icon icon="solar:shield-check-bold" />}
                      >
                        {Math.round(remediationSolution.confidence_score * 100)}% confidence
                      </Chip>
                    </div>

                    <div>
                      <h4 className="font-semibold text-sm mb-2">Issue Summary</h4>
                      <p className="text-sm text-default-600">{remediationSolution.issue_summary}</p>
                    </div>

                    <div>
                      <h4 className="font-semibold text-sm mb-2">Suggested Solution</h4>
                      <p className="text-sm text-default-600">{remediationSolution.suggestion}</p>
                    </div>

                    <div>
                      <h4 className="font-semibold text-sm mb-2">Remediation Command</h4>
                      <Code className="w-full p-3 text-xs">
                        kubectl {remediationSolution.command}
                      </Code>
                    </div>

                    <div className="flex items-center gap-2">
                      <Chip
                        color={remediationSolution.is_executable ? "success" : "warning"}
                        variant="flat"
                        startContent={
                          <Icon 
                            icon={remediationSolution.is_executable ? "solar:check-circle-bold" : "solar:close-circle-bold"} 
                          />
                        }
                      >
                        {remediationSolution.is_executable ? "Safe to Execute" : "Manual Review Required"}
                      </Chip>
                    </div>

                    {remediationSolution.is_executable && (
                      <Button
                        color="success"
                        variant="solid"
                        onPress={onExecuteModalOpen}
                        startContent={<Icon icon="solar:play-bold" />}
                        className="w-full"
                      >
                        Execute Command
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Icon icon="solar:cpu-bolt-line-duotone" className="text-6xl text-default-300 mb-4" />
                    <p className="text-default-500">No analysis results yet</p>
                    <p className="text-sm text-default-400">Provide alert details and click "Analyze Alert"</p>
                  </div>
                )}
              </CardBody>
            </Card>
          </div>
        </Tab>

        {/* Tab 3: Execution History */}
        <Tab
          key="history"
          title={
            <div className="flex items-center space-x-2">
              <Icon icon="solar:history-bold" />
              <span>Execution History</span>
              <Badge content={history.length} size="sm" color="secondary" />
            </div>
          }
        >
          <div className="mt-6 space-y-6">
            {/* History Filters */}
            <Card>
              <CardBody>
                <div className="flex items-center gap-4 flex-wrap">
                  <Input
                    placeholder="Filter by alert name..."
                    startContent={<Icon icon="solar:magnifer-bold" />}
                    className="max-w-xs"
                  />
                  <Select placeholder="Filter by status" className="max-w-xs">
                    <SelectItem key="success">Success</SelectItem>
                    <SelectItem key="failed">Failed</SelectItem>
                    <SelectItem key="skipped">Skipped</SelectItem>
                    <SelectItem key="blocked">Blocked</SelectItem>
                  </Select>
                  <Select placeholder="Filter by namespace" className="max-w-xs">
                    <SelectItem key="default">default</SelectItem>
                    <SelectItem key="kube-system">kube-system</SelectItem>
                    <SelectItem key="monitoring">monitoring</SelectItem>
                  </Select>
                  <Button
                    color="primary"
                    variant="flat"
                    onPress={loadHistory}
                    startContent={<Icon icon="solar:refresh-bold" />}
                  >
                    Refresh
                  </Button>
                </div>
              </CardBody>
            </Card>

            {/* History Table */}
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold">Recent Executions</h3>
              </CardHeader>
              <CardBody className="p-0">
                <Table aria-label="Execution history table">
                  <TableHeader>
                    <TableColumn>ALERT</TableColumn>
                    <TableColumn>NAMESPACE</TableColumn>
                    <TableColumn>COMMAND</TableColumn>
                    <TableColumn>STATUS</TableColumn>
                    <TableColumn>EXECUTED</TableColumn>
                    <TableColumn>DURATION</TableColumn>
                    <TableColumn>ACTIONS</TableColumn>
                  </TableHeader>
                  <TableBody emptyContent="No execution history found">
                    {history.map((record) => (
                      <TableRow key={record.id}>
                        <TableCell>
                          <div className="flex flex-col">
                            <p className="font-medium">{record.alert_name}</p>
                            <div className="flex items-center gap-1 mt-1">
                              <Chip
                                size="sm"
                                color={getSeverityColor(record.severity_level)}
                                variant="flat"
                              >
                                {record.severity_level}
                              </Chip>
                              {record.confidence_score && (
                                <Chip size="sm" variant="flat">
                                  {Math.round(record.confidence_score * 100)}%
                                </Chip>
                              )}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Chip size="sm" variant="flat" color="primary">
                            {record.namespace}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          <Tooltip content={record.command}>
                            <Code className="max-w-xs truncate text-xs">
                              {record.command.length > 40 
                                ? `${record.command.substring(0, 40)}...` 
                                : record.command
                              }
                            </Code>
                          </Tooltip>
                        </TableCell>
                        <TableCell>
                          <Chip
                            color={getStatusColor(record.status)}
                            variant="flat"
                            startContent={
                              <Icon 
                                icon={
                                  record.status === 'success' ? "solar:check-circle-bold" :
                                  record.status === 'failed' ? "solar:close-circle-bold" :
                                  record.status === 'skipped' ? "solar:skip-next-bold" :
                                  "solar:shield-cross-bold"
                                }
                              />
                            }
                          >
                            {record.status}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          <p className="text-sm">
                            {formatDate(record.executed_at)}
                          </p>
                        </TableCell>
                        <TableCell>
                          <p className="text-sm">{formatDuration(record.execution_time_ms)}</p>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Tooltip content="View Details">
                              <Button
                                isIconOnly
                                size="sm"
                                variant="light"
                                color="primary"
                              >
                                <Icon icon="solar:eye-bold" />
                              </Button>
                            </Tooltip>
                            {record.status === 'failed' && (
                              <Tooltip content="Retry">
                                <Button
                                  isIconOnly
                                  size="sm"
                                  variant="light"
                                  color="warning"
                                >
                                  <Icon icon="solar:refresh-bold" />
                                </Button>
                              </Tooltip>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardBody>
            </Card>
          </div>
        </Tab>

        {/* Tab 4: Executors Management */}
        <Tab
          key="executors"
          title={
            <div className="flex items-center space-x-2">
              <Icon icon="solar:settings-bold" />
              <span>Executors</span>
              <Badge content={executors.filter(e => e.status === 0).length} size="sm" color="success" />
            </div>
          }
        >
          <div className="mt-6 space-y-6">
            {/* Executor Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {executors.map((executor) => (
                <Card key={executor.name} className="border-2" 
                      style={{ borderColor: executor.status === 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)' }}>
                  <CardHeader className="flex gap-3">
                    <Avatar
                      icon={
                        <Icon 
                          icon={
                            executor.name === 'kubectl' ? "solar:terminal-bold" :
                            executor.name === 'argocd' ? "solar:git-branch-bold" :
                            "solar:server-bold"
                          } 
                        />
                      }
                      classNames={{
                        base: executor.status === 0 
                        ? "bg-gradient-to-br from-success to-success-300"
                        : "bg-gradient-to-br from-danger to-danger-300",
                      icon: "text-white",
                    }}
                  />
                  <div className="flex flex-col">
                    <p className="text-md font-semibold capitalize">{executor.name}</p>
                    <p className="text-small text-default-500">
                      {executor.name === 'kubectl' ? 'Kubernetes CLI' :
                       executor.name === 'argocd' ? 'GitOps Deployment' :
                       'Infrastructure Management'}
                    </p>
                  </div>
                </CardHeader>
                <CardBody className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Status</span>
                    <Chip
                      color={executor.status === 0 ? "success" : "danger"}
                      variant="flat"
                      startContent={
                        <Icon 
                          icon={executor.status === 0 ? "solar:check-circle-bold" : "solar:close-circle-bold"} 
                        />
                      }
                    >
                      {executor.status_text}
                    </Chip>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Last Updated</span>
                    <span className="text-xs text-default-500">
                      {formatDate(executor.updated_at)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Toggle Status</span>
                    <Switch
                      isSelected={executor.status === 0}
                      onValueChange={(isSelected) => 
                        updateExecutorStatus(executor.name, isSelected ? 0 : 1)
                      }
                      color="success"
                    />
                  </div>

                  <Divider />

                  <div className="space-y-2">
                    <p className="text-xs font-medium text-default-600">Capabilities:</p>
                    <div className="flex flex-wrap gap-1">
                      {executor.name === 'kubectl' && (
                        <>
                          <Chip size="sm" variant="flat">describe</Chip>
                          <Chip size="sm" variant="flat">logs</Chip>
                          <Chip size="sm" variant="flat">get</Chip>
                          <Chip size="sm" variant="flat">apply</Chip>
                        </>
                      )}
                      {executor.name === 'argocd' && (
                        <>
                          <Chip size="sm" variant="flat">sync</Chip>
                          <Chip size="sm" variant="flat">rollback</Chip>
                          <Chip size="sm" variant="flat">refresh</Chip>
                          <Chip size="sm" variant="flat">diff</Chip>
                        </>
                      )}
                      {executor.name === 'crossplane' && (
                        <>
                          <Chip size="sm" variant="flat">provision</Chip>
                          <Chip size="sm" variant="flat">compose</Chip>
                          <Chip size="sm" variant="flat">configure</Chip>
                          <Chip size="sm" variant="flat">manage</Chip>
                        </>
                      )}
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>

          {/* Executor Details */}
          <Card>
            <CardHeader>
              <h3 className="text-lg font-semibold">Executor Information</h3>
            </CardHeader>
            <CardBody>
              <Accordion variant="splitted">
                <AccordionItem
                  key="kubectl"
                  aria-label="Kubectl"
                  startContent={<Icon icon="solar:terminal-bold" className="text-primary" />}
                  title="Kubectl"
                  subtitle="Kubernetes command-line tool"
                >
                  <div className="space-y-3">
                    <p className="text-sm text-default-600">
                      Primary executor for Kubernetes operations. Handles pod management, 
                      resource inspection, log retrieval, and basic troubleshooting commands.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Chip size="sm" variant="flat">kubectl get</Chip>
                      <Chip size="sm" variant="flat">kubectl describe</Chip>
                      <Chip size="sm" variant="flat">kubectl logs</Chip>
                      <Chip size="sm" variant="flat">kubectl top</Chip>
                      <Chip size="sm" variant="flat">kubectl apply</Chip>
                      <Chip size="sm" variant="flat">kubectl delete</Chip>
                    </div>
                  </div>
                </AccordionItem>
                <AccordionItem
                  key="argocd"
                  aria-label="ArgoCD"
                  startContent={<Icon icon="solar:git-branch-bold" className="text-secondary" />}
                  title="ArgoCD"
                  subtitle="GitOps continuous delivery"
                >
                  <div className="space-y-3">
                    <p className="text-sm text-default-600">
                      Manages GitOps deployments and application synchronization. 
                      Handles application rollbacks, syncing, and configuration drift detection.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Chip size="sm" variant="flat">sync</Chip>
                      <Chip size="sm" variant="flat">rollback</Chip>
                      <Chip size="sm" variant="flat">refresh</Chip>
                      <Chip size="sm" variant="flat">diff</Chip>
                    </div>
                  </div>
                </AccordionItem>
                <AccordionItem
                  key="crossplane"
                  aria-label="Crossplane"
                  startContent={<Icon icon="solar:server-bold" className="text-warning" />}
                  title="Crossplane"
                  subtitle="Cloud infrastructure management"
                >
                  <div className="space-y-3">
                    <p className="text-sm text-default-600">
                      Manages cloud infrastructure resources and compositions. 
                      Handles provider configurations and resource provisioning.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Chip size="sm" variant="flat">provision</Chip>
                      <Chip size="sm" variant="flat">compose</Chip>
                      <Chip size="sm" variant="flat">configure</Chip>
                      <Chip size="sm" variant="flat">manage</Chip>
                    </div>
                  </div>
                </AccordionItem>
              </Accordion>
            </CardBody>
          </Card>
        </div>
      </Tab>

      {/* Tab 5: Statistics & Analytics */}
      <Tab
        key="stats"
        title={
          <div className="flex items-center space-x-2">
            <Icon icon="solar:chart-bold" />
            <span>Analytics</span>
          </div>
        }
      >
        <div className="mt-6 space-y-6">
          {stats && (
            <>
              {/* Overview Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="border-l-4 border-l-primary">
                  <CardBody className="text-center">
                    <Icon icon="solar:activity-bold" className="text-4xl text-primary mb-3 mx-auto" />
                    <p className="text-3xl font-bold text-primary">{stats.recent_activity.last_24_hours}</p>
                    <p className="text-sm text-default-500">Last 24 Hours</p>
                  </CardBody>
                </Card>
                <Card className="border-l-4 border-l-success">
                  <CardBody className="text-center">
                    <Icon icon="solar:check-circle-bold" className="text-4xl text-success mb-3 mx-auto" />
                    <p className="text-3xl font-bold text-success">{stats.execution_stats.success || 0}</p>
                    <p className="text-sm text-default-500">Successful</p>
                  </CardBody>
                </Card>
                <Card className="border-l-4 border-l-danger">
                  <CardBody className="text-center">
                    <Icon icon="solar:close-circle-bold" className="text-4xl text-danger mb-3 mx-auto" />
                    <p className="text-3xl font-bold text-danger">{stats.execution_stats.failed || 0}</p>
                    <p className="text-sm text-default-500">Failed</p>
                  </CardBody>
                </Card>
                <Card className="border-l-4 border-l-warning">
                  <CardBody className="text-center">
                    <Icon icon="solar:skip-next-bold" className="text-4xl text-warning mb-3 mx-auto" />
                    <p className="text-3xl font-bold text-warning">{stats.execution_stats.skipped || 0}</p>
                    <p className="text-sm text-default-500">Skipped</p>
                  </CardBody>
                </Card>
              </div>

              {/* Charts and Analytics */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Execution Status Distribution */}
                <Card>
                  <CardHeader>
                    <h3 className="text-lg font-semibold">Execution Status Distribution</h3>
                  </CardHeader>
                  <CardBody>
                    <div className="space-y-4">
                      {Object.entries(stats.execution_stats).map(([status, count]) => {
                        const total = Object.values(stats.execution_stats).reduce((a, b) => a + b, 0);
                        const percentage = total > 0 ? (count / total) * 100 : 0;
                        
                        return (
                          <div key={status} className="space-y-2">
                            <div className="flex justify-between items-center">
                              <div className="flex items-center gap-3">
                                <Chip
                                  size="sm"
                                  color={getStatusColor(status)}
                                  variant="flat"
                                  startContent={
                                    <Icon 
                                      icon={
                                        status === 'success' ? "solar:check-circle-bold" :
                                        status === 'failed' ? "solar:close-circle-bold" :
                                        status === 'skipped' ? "solar:skip-next-bold" :
                                        "solar:shield-cross-bold"
                                      }
                                    />
                                  }
                                >
                                  {status.charAt(0).toUpperCase() + status.slice(1)}
                                </Chip>
                                <span className="text-sm font-medium">{count}</span>
                              </div>
                              <span className="text-sm text-default-500 font-mono">
                                {percentage.toFixed(1)}%
                              </span>
                            </div>
                            <Progress
                              value={percentage}
                              color={getStatusColor(status)}
                              className="max-w-md"
                              size="sm"
                            />
                          </div>
                        );
                      })}
                    </div>
                  </CardBody>
                </Card>

                {/* Top Alert Types */}
                <Card>
                  <CardHeader>
                    <h3 className="text-lg font-semibold">Top Alert Types</h3>
                  </CardHeader>
                  <CardBody>
                    <div className="space-y-3">
                      {stats.top_alerts.slice(0, 8).map((alert, index) => (
                        <div key={alert.alert_name} className="flex items-center justify-between p-3 rounded-lg bg-default-50">
                          <div className="flex items-center gap-3">
                            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary text-white text-sm font-bold">
                              {index + 1}
                            </div>
                            <div>
                              <p className="text-sm font-medium">{alert.alert_name}</p>
                              <p className="text-xs text-default-500">Alert Type</p>
                            </div>
                          </div>
                          <Chip size="lg" variant="flat" color="primary">
                            {alert.count}
                          </Chip>
                        </div>
                      ))}
                    </div>
                  </CardBody>
                </Card>
              </div>

              {/* Performance Metrics */}
              <Card>
                <CardHeader>
                  <h3 className="text-lg font-semibold">Performance Metrics</h3>
                </CardHeader>
                <CardBody>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="text-center p-4 rounded-lg bg-gradient-to-br from-success/10 to-success/5">
                      <Icon icon="solar:speedometer-bold" className="text-3xl text-success mb-2 mx-auto" />
                      <p className="text-2xl font-bold text-success">
                        {stats.execution_stats.success ? 
                          Math.round((stats.execution_stats.success / Object.values(stats.execution_stats).reduce((a, b) => a + b, 0)) * 100) 
                          : 0}%
                        </p>
                      <p className="text-sm text-default-600">Success Rate</p>
                    </div>
                    <div className="text-center p-4 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5">
                      <Icon icon="solar:clock-circle-bold" className="text-3xl text-primary mb-2 mx-auto" />
                      <p className="text-2xl font-bold text-primary">~2.3s</p>
                      <p className="text-sm text-default-600">Avg Response Time</p>
                    </div>
                    <div className="text-center p-4 rounded-lg bg-gradient-to-br from-warning/10 to-warning/5">
                      <Icon icon="solar:shield-check-bold" className="text-3xl text-warning mb-2 mx-auto" />
                      <p className="text-2xl font-bold text-warning">98.5%</p>
                      <p className="text-sm text-default-600">System Uptime</p>
                    </div>
                  </div>
                </CardBody>
              </Card>
            </>
          )}
        </div>
      </Tab>
    </Tabs>

    {/* Create Incident Modal */}
    <Modal 
        isOpen={isIncidentModalOpen} 
        onClose={onIncidentModalClose}
        size="2xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <Avatar
                icon={<Icon icon="solar:add-circle-bold" />}
                classNames={{
                  base: "bg-gradient-to-br from-primary to-secondary",
                  icon: "text-white",
                }}
              />
              <div>
                <h3 className="text-lg font-semibold">Create New Incident</h3>
                <p className="text-sm text-default-500">Simulate a Kubernetes incident for testing</p>
              </div>
            </div>
          </ModalHeader>
          <ModalBody>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Alert Name"
                  placeholder="e.g., HighCPUUsage"
                  value={incidentData.alert_name}
                  onValueChange={(value) => setIncidentData(prev => ({ ...prev, alert_name: value }))}
                  startContent={<Icon icon="solar:danger-triangle-bold" />}
                  isRequired
                />
                <Select
                  label="Incident Type"
                  selectedKeys={incidentData.type ? [incidentData.type] : []}
                  onSelectionChange={(keys) => {
                    const selected = Array.from(keys)[0] as string;
                    setIncidentData(prev => ({ ...prev, type: selected }));
                  }}
                >
                  <SelectItem key="Warning">Warning</SelectItem>
                  <SelectItem key="Normal">Normal</SelectItem>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Namespace"
                  placeholder="default"
                  value={incidentData.namespace}
                  onValueChange={(value) => setIncidentData(prev => ({ ...prev, namespace: value }))}
                  startContent={<Icon icon="solar:folder-bold" />}
                />
                <Input
                  label="Pod Name"
                  placeholder="backend-pod-123"
                  value={incidentData.pod_name}
                  onValueChange={(value) => setIncidentData(prev => ({ ...prev, pod_name: value }))}
                  startContent={<Icon icon="solar:server-bold" />}
                />
              </div>

              <Input
                label="Reason"
                placeholder="e.g., CrashLoopBackOff"
                value={incidentData.reason}
                onValueChange={(value) => setIncidentData(prev => ({ ...prev, reason: value }))}
                startContent={<Icon icon="solar:info-circle-bold" />}
              />

              <Textarea
                label="Message"
                placeholder="Detailed description of the incident..."
                value={incidentData.message}
                onValueChange={(value) => setIncidentData(prev => ({ ...prev, message: value }))}
                minRows={3}
              />

              <div className="grid grid-cols-3 gap-4">
                <Input
                  label="Usage"
                  placeholder="95%"
                  value={incidentData.usage}
                  onValueChange={(value) => setIncidentData(prev => ({ ...prev, usage: value }))}
                  startContent={<Icon icon="solar:chart-bold" />}
                />
                <Input
                  label="Threshold"
                  placeholder="80%"
                  value={incidentData.threshold}
                  onValueChange={(value) => setIncidentData(prev => ({ ...prev, threshold: value }))}
                  startContent={<Icon icon="solar:target-bold" />}
                />
                <Input
                  label="Duration"
                  placeholder="15m"
                  value={incidentData.duration}
                  onValueChange={(value) => setIncidentData(prev => ({ ...prev, duration: value }))}
                  startContent={<Icon icon="solar:clock-circle-bold" />}
                />
              </div>

              <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
                <div className="flex items-center gap-2 mb-2">
                  <Icon icon="solar:info-circle-bold" className="text-primary" />
                  <span className="text-sm font-medium text-primary">Incident Processing Flow</span>
                </div>
                <div className="text-xs text-default-600 space-y-1">
                  <p>1. Incident will be created and stored in database</p>
                  <p>2. Email notification will be sent automatically</p>
                  <p>3. LLM analysis will be triggered for remediation suggestions</p>
                  <p>4. Enforcer will validate the solution</p>
                  <p>5. Executor will attempt to resolve the issue</p>
                </div>
              </div>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={onIncidentModalClose}>
              Cancel
            </Button>
            <Button 
              color="primary" 
              onPress={createIncident}
              isLoading={loading}
              startContent={!loading && <Icon icon="solar:add-circle-bold" />}
            >
              Create Incident
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Analysis Results Modal */}
      <Modal 
        isOpen={isAnalysisModalOpen} 
        onClose={onAnalysisModalClose}
        size="4xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <Avatar
                icon={<Icon icon="solar:brain-bold" />}
                classNames={{
                  base: "bg-gradient-to-br from-success to-primary",
                  icon: "text-black/80",
                }}
              />
              <div>
                <h3 className="text-lg font-semibold">AI Analysis Results</h3>
                <p className="text-sm text-default-500">LLM-powered incident analysis and solution</p>
              </div>
            </div>
          </ModalHeader>
          <ModalBody>
            {incidentSolution && (
              <div className="space-y-6">
                {/* Solution Overview */}
                <Card>
                  <CardHeader>
                    <h4 className="font-semibold">Solution Overview</h4>
                  </CardHeader>
                  <CardBody className="space-y-4">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Chip
                        color={getSeverityColor(incidentSolution.severity_level)}
                        variant="flat"
                        startContent={<Icon icon="solar:danger-triangle-bold" />}
                      >
                        {incidentSolution.severity_level}
                      </Chip>
                      <Chip
                        color="primary"
                        variant="flat"
                        startContent={<Icon icon="solar:clock-circle-bold" />}
                      >
                        ~{incidentSolution.estimated_time_to_resolve_mins}min
                      </Chip>
                      <Chip
                        color="success"
                        variant="flat"
                        startContent={<Icon icon="solar:shield-check-bold" />}
                      >
                        {Math.round(incidentSolution.confidence_score * 100)}% confidence
                      </Chip>
                    </div>

                    <div>
                      <h5 className="font-medium mb-2">Summary</h5>
                      <p className="text-sm text-default-600">{incidentSolution.summary}</p>
                    </div>

                    <div>
                      <h5 className="font-medium mb-2">Analysis</h5>
                      <p className="text-sm text-default-600">{incidentSolution.analysis}</p>
                    </div>
                  </CardBody>
                </Card>

                {/* Resolution Steps */}
                <Card>
                  <CardHeader>
                    <h4 className="font-semibold">Resolution Steps ({incidentSolution.steps.length})</h4>
                  </CardHeader>
                  <CardBody>
                    <div className="space-y-4">
                      {incidentSolution.steps.map((step, index) => (
                        <div key={step.step_id} className="border rounded-lg p-4 space-y-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-white text-sm font-bold">
                                {step.step_id}
                              </div>
                              <div>
                                <p className="font-medium">{step.action_type}</p>
                                <p className="text-xs text-default-500">Executor: {step.executor}</p>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              color="primary"
                              variant="flat"
                              onPress={() => selectedIncident && executeCommand(
                                selectedIncident.id, 
                                step.command_or_payload.command || '', 
                                step.step_id
                              )}
                              startContent={<Icon icon="solar:play-bold" />}
                            >
                              Execute
                            </Button>
                          </div>

                          <p className="text-sm text-default-600">{step.description}</p>

                          {step.command_or_payload.command && (
                            <Code className="w-full p-3 text-xs">
                              kubectl {step.command_or_payload.command}
                            </Code>
                          )}

                          <div className="text-xs text-default-500">
                            <p><strong>Expected:</strong> {step.expected_outcome}</p>
                            <p><strong>Target:</strong> {step.target_resource.kind}/{step.target_resource.name} in {step.target_resource.namespace}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardBody>
                </Card>

                {/* Recommendations */}
                <Card>
                  <CardHeader>
                    <h4 className="font-semibold">Recommendations</h4>
                  </CardHeader>
                  <CardBody>
                    <div className="space-y-2">
                      {incidentSolution.recommendations.map((rec, index) => (
                        <div key={index} className="flex items-start gap-3">
                          <Icon icon="solar:lightbulb-bold" className="text-warning mt-0.5" />
                          <p className="text-sm text-default-600">{rec}</p>
                        </div>
                      ))}
                    </div>
                  </CardBody>
                </Card>
              </div>
            )}
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={onAnalysisModalClose}>
              Close
            </Button>
            <Button 
              color="primary" 
              onPress={() => {
                if (selectedIncident) {
                  getIncidentRecommendations(selectedIncident.id);
                }
              }}
              startContent={<Icon icon="solar:lightbulb-bold" />}
            >
              Get Recommendations
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Execute Command Modal */}
      <Modal 
        isOpen={isExecuteModalOpen} 
        onClose={onExecuteModalClose}
        size="2xl"
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <Avatar
                icon={<Icon icon="solar:play-bold" />}
                classNames={{
                  base: "bg-gradient-to-br from-warning to-danger",
                  icon: "text-white",
                }}
              />
              <div>
                <h3 className="text-lg font-semibold">Execute Remediation Command</h3>
                <p className="text-sm text-default-500">Confirm command execution</p>
              </div>
            </div>
          </ModalHeader>
          <ModalBody>
            {remediationSolution && (
              <div className="space-y-4">
                <div className="p-4 bg-warning/10 rounded-lg border border-warning/20">
                  <div className="flex items-center gap-2 mb-2">
                    <Icon icon="solar:shield-warning-bold" className="text-warning" />
                    <span className="text-sm font-medium text-warning">Command Execution Warning</span>
                  </div>
                  <p className="text-xs text-default-600">
                    You are about to execute a command on your Kubernetes cluster. 
                    Please review the command carefully before proceeding.
                  </p>
                </div>

                <div>
                  <h4 className="font-medium mb-2">Command to Execute</h4>
                  <Code className="w-full p-4 text-sm">
                    kubectl {remediationSolution.command}
                  </Code>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h5 className="font-medium text-sm mb-1">Severity Level</h5>
                    <Chip
                      color={getSeverityColor(remediationSolution.severity_level)}
                      variant="flat"
                    >
                      {remediationSolution.severity_level}
                    </Chip>
                  </div>
                  <div>
                    <h5 className="font-medium text-sm mb-1">Confidence Score</h5>
                    <Chip color="success" variant="flat">
                      {Math.round(remediationSolution.confidence_score * 100)}%
                    </Chip>
                  </div>
                </div>

                <div>
                  <h5 className="font-medium text-sm mb-2">Expected Outcome</h5>
                  <p className="text-sm text-default-600">{remediationSolution.suggestion}</p>
                </div>

                <div>
                  <h5 className="font-medium text-sm mb-2">Safety Check</h5>
                  <div className="flex items-center gap-2">
                    <Icon 
                      icon={remediationSolution.is_executable ? "solar:check-circle-bold" : "solar:close-circle-bold"}
                      className={remediationSolution.is_executable ? "text-success" : "text-danger"}
                    />
                    <span className={`text-sm ${remediationSolution.is_executable ? "text-success" : "text-danger"}`}>
                      {remediationSolution.is_executable ? "Safe to execute" : "Requires manual review"}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={onExecuteModalClose}>
              Cancel
            </Button>
            <Button 
              color="warning" 
              onPress={() => {
                if (remediationSolution) {
                  executeRemediationCommand({
                    command: remediationSolution.command,
                    is_executable: remediationSolution.is_executable,
                    executor: 'kubectl',
                    confirm_execution: true
                  });
                }
              }}
              isLoading={loading}
              startContent={!loading && <Icon icon="solar:play-bold" />}
            >
              Execute Command
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Execution Result Modal */}
      <Modal 
        isOpen={isResultModalOpen} 
        onClose={onResultModalClose}
        size="3xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <Avatar
                icon={<Icon icon="solar:terminal-bold" />}
                classNames={{
                  base: executionResult?.status === 'success' 
                    ? "bg-gradient-to-br from-success to-success-300"
                    : "bg-gradient-to-br from-danger to-danger-300",
                  icon: "text-white",
                }}
              />
              <div>
                <h3 className="text-lg font-semibold">Execution Result</h3>
                <p className="text-sm text-default-500">Command execution output</p>
              </div>
            </div>
          </ModalHeader>
          <ModalBody>
            {executionResult && (
              <div className="space-y-4">
                <div className="flex items-center gap-4 flex-wrap">
                  <Chip
                    color={getStatusColor(executionResult.status)}
                    variant="flat"
                    startContent={
                      <Icon 
                        icon={
                          executionResult.status === 'success' ? "solar:check-circle-bold" :
                          executionResult.status === 'failed' ? "solar:close-circle-bold" :
                          executionResult.status === 'blocked' ? "solar:shield-cross-bold" :
                          "solar:skip-next-bold"
                        }
                      />
                    }
                  >
                    {executionResult.status.toUpperCase()}
                  </Chip>
                  {executionResult.execution_time && (
                    <Chip color="primary" variant="flat">
                      {executionResult.execution_time}
                    </Chip>
                  )}
                </div>

                {executionResult.command && (
                  <div>
                    <h4 className="font-medium mb-2">Executed Command</h4>
                    <Code className="w-full p-3 text-sm">
                      {executionResult.command}
                    </Code>
                  </div>
                )}

                {executionResult.output && (
                  <div>
                    <h4 className="font-medium mb-2">Output</h4>
                    <Card className="bg-default-50">
                      <CardBody>
                        <pre className="text-xs whitespace-pre-wrap font-mono text-default-700">
                          {executionResult.output}
                        </pre>
                      </CardBody>
                    </Card>
                  </div>
                )}

                {executionResult.error && (
                  <div>
                    <h4 className="font-medium mb-2 text-danger">Error</h4>
                    <Card className="bg-danger-50 border border-danger-200">
                      <CardBody>
                        <pre className="text-xs whitespace-pre-wrap font-mono text-danger-700">
                          {executionResult.error}
                        </pre>
                      </CardBody>
                    </Card>
                  </div>
                )}

                {executionResult.suggestion && (
                  <div>
                    <h4 className="font-medium mb-2">Suggestion</h4>
                    <div className="p-3 bg-primary/10 rounded-lg border border-primary/20">
                      <p className="text-sm text-default-600">{executionResult.suggestion}</p>
                    </div>
                  </div>
                )}

                {executionResult.reason && (
                  <div>
                    <h4 className="font-medium mb-2">Reason</h4>
                    <p className="text-sm text-default-600">{executionResult.reason}</p>
                  </div>
                )}
              </div>
            )}
          </ModalBody>
          <ModalFooter>
            <Button color="primary" onPress={onResultModalClose}>
              Close
            </Button>
            {executionResult?.status === 'failed' && (
              <Button 
                color="warning" 
                variant="flat"
                startContent={<Icon icon="solar:refresh-bold" />}
              >
                Retry
              </Button>
            )}
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Recommendations Modal */}
      <Modal 
        isOpen={isRecommendationsModalOpen} 
        onClose={onRecommendationsModalClose}
        size="4xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <Avatar
                icon={<Icon icon="solar:lightbulb-bold" />}
                classNames={{
                  base: "bg-gradient-to-br from-warning to-warning-300",
                  icon: "text-black/80",
                }}
              />
              <div>
                <h3 className="text-lg font-semibold">AI Recommendations</h3>
                <p className="text-sm text-default-500">Executable commands for incident resolution</p>
              </div>
            </div>
          </ModalHeader>
          <ModalBody>
            <div className="space-y-4">
              {recommendations.map((rec, index) => (
                <Card key={rec.step_id} className="border-2 border-default-200">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary text-white text-sm font-bold">
                          {rec.step_id}
                        </div>
                        <div>
                          <p className="font-medium">{rec.action_type}</p>
                          <p className="text-xs text-default-500">Executor: {rec.executor}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Chip
                          size="sm"
                          color={rec.is_executable ? "success" : "warning"}
                          variant="flat"
                          startContent={
                            <Icon 
                              icon={rec.is_executable ? "solar:check-circle-bold" : "solar:shield-warning-bold"} 
                            />
                          }
                        >
                          {rec.is_executable ? "Executable" : "Review Required"}
                        </Chip>
                        <Button
                          size="sm"
                          color="primary"
                          variant="flat"
                          onPress={() => selectedIncident && executeCommand(
                            selectedIncident.id, 
                            rec.command.replace('kubectl ', ''), 
                            rec.step_id
                          )}
                          startContent={<Icon icon="solar:play-bold" />}
                          isDisabled={!rec.is_executable}
                        >
                          Execute
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardBody className="pt-0 space-y-3">
                    <p className="text-sm text-default-600">{rec.description}</p>

                    <div>
                      <h5 className="font-medium text-sm mb-1">Command</h5>
                      <Code className="w-full p-3 text-xs">
                        {rec.command}
                      </Code>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                      <div>
                        <h6 className="font-medium mb-1">Target Resource</h6>
                        <p className="text-default-500">
                          {rec.target_resource.kind}/{rec.target_resource.name} 
                          {rec.target_resource.namespace && ` in ${rec.target_resource.namespace}`}
                        </p>
                      </div>
                      <div>
                        <h6 className="font-medium mb-1">Expected Outcome</h6>
                        <p className="text-default-500">{rec.expected_outcome}</p>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              ))}

              {recommendations.length === 0 && (
                <div className="text-center py-8">
                  <Icon icon="solar:lightbulb-bold" className="text-6xl text-default-300 mb-4" />
                  <p className="text-default-500">No recommendations available</p>
                  <p className="text-sm text-default-400">Try analyzing an incident first</p>
                </div>
              )}
            </div>
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={onRecommendationsModalClose}>
              Close
            </Button>
            <Button 
              color="primary" 
              startContent={<Icon icon="solar:download-bold" />}
            >
              Export Recommendations
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Command History Modal */}
      <Modal 
        isOpen={commandHistory.length > 0} 
        onClose={() => setCommandHistory([])}
        size="3xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <Avatar
                icon={<Icon icon="solar:history-bold" />}
                classNames={{
                  base: "bg-gradient-to-br from-secondary to-secondary-300",
                  icon: "text-white",
                }}
              />
              <div>
                <h3 className="text-lg font-semibold">Command Execution History</h3>
                <p className="text-sm text-default-500">Recent command executions for this incident</p>
              </div>
            </div>
          </ModalHeader>
          <ModalBody>
            <div className="space-y-4">
              {commandHistory.map((cmd, index) => (
                <Card key={cmd.id} className="border-l-4" 
                      style={{ borderLeftColor: 
                        cmd.status === 'success' ? 'rgb(34, 197, 94)' :
                        cmd.status === 'failed' ? 'rgb(239, 68, 68)' :
                        'rgb(245, 158, 11)'
                      }}>
                  <CardBody className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-6 h-6 rounded-full bg-default-200 text-xs font-bold">
                          {index + 1}
                        </div>
                        <Chip
                          size="sm"
                          color={getStatusColor(cmd.status)}
                          variant="flat"
                          startContent={
                            <Icon 
                              icon={
                                cmd.status === 'success' ? "solar:check-circle-bold" :
                                cmd.status === 'failed' ? "solar:close-circle-bold" :
                                "solar:skip-next-bold"
                              }
                            />
                          }
                        >
                          {cmd.status.toUpperCase()}
                        </Chip>
                      </div>
                      <div className="text-right text-xs text-default-500">
                        <p>{formatDate(cmd.executed_at)}</p>
                        <p>{formatDuration(cmd.execution_time_ms)}</p>
                      </div>
                    </div>

                    <div>
                      <h5 className="font-medium text-sm mb-1">Command</h5>
                      <Code className="w-full p-2 text-xs">
                        {cmd.command}
                      </Code>
                    </div>

                    {cmd.output && (
                      <div>
                        <h5 className="font-medium text-sm mb-1">Output</h5>
                        <Card className="bg-default-50">
                          <CardBody className="p-2">
                            <pre className="text-xs whitespace-pre-wrap font-mono text-default-700">
                              {cmd.output}
                            </pre>
                          </CardBody>
                        </Card>
                      </div>
                    )}

                    {cmd.error && (
                      <div>
                        <h5 className="font-medium text-sm mb-1 text-danger">Error</h5>
                        <Card className="bg-danger-50 border border-danger-200">
                          <CardBody className="p-2">
                            <pre className="text-xs whitespace-pre-wrap font-mono text-danger-700">
                              {cmd.error}
                            </pre>
                          </CardBody>
                        </Card>
                      </div>
                    )}

                    {cmd.expected_outcome && (
                      <div className="text-xs">
                        <span className="font-medium">Expected: </span>
                        <span className="text-default-500">{cmd.expected_outcome}</span>
                      </div>
                    )}
                  </CardBody>
                </Card>
              ))}
            </div>
          </ModalBody>
          <ModalFooter>
            <Button color="primary" onPress={() => setCommandHistory([])}>
              Close
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="p-6">
            <CardBody className="flex items-center gap-4">
              <Spinner size="lg" color="primary" />
              <div>
                <p className="font-medium">Processing...</p>
                <p className="text-sm text-default-500">Please wait while we analyze the data</p>
              </div>
            </CardBody>
          </Card>
        </div>
      )}
    </div>
  );
};

export default RemediationPage;



