import React from 'react';
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Chip,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  useDisclosure,
  Spinner,
  Progress,
  Tabs,
  Tab,
  Select,
  SelectItem,
  Input,
  Textarea,
  Divider,
  Code,
  ScrollShadow
} from '@nextui-org/react';
import { Icon } from '@iconify/react';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from '../components/toast-manager';

interface Incident {
  id: number;
  incident_id: string;
  type: 'Normal' | 'Warning';
  reason: string;
  message: string;
  metadata_namespace?: string;
  involved_object_kind: string;
  involved_object_name: string;
  count: number;
  is_resolved: boolean;
  resolution_attempts: number;
  created_at: string;
  last_timestamp: string;
}

interface Executor {
  id: number;
  name: 'kubectl' | 'argocd' | 'crossplane';
  status: 'active' | 'inactive';
  description: string;
  config?: any;
  created_at: string;
  updated_at: string;
}

interface RemediationStep {
  step_id: number;
  action_type: string;
  description: string;
  command: string;
  expected_outcome: string;
  critical: boolean;
  timeout_seconds: number;
}

interface RemediationSolution {
  solution_summary: string;
  detailed_solution: string;
  remediation_steps: RemediationStep[];
  confidence_score: number;
  estimated_time_mins: number;
  additional_notes: string;
  executor_type: string;
  commands: string[];
}

interface RemediationResponse {
  incident_id: number;
  solution: RemediationSolution;
  execution_status: string;
  timestamp: string;
}

export const RemediationDashboard: React.FC = () => {
  // State
  const [incidents, setIncidents] = React.useState<Incident[]>([]);
  const [executors, setExecutors] = React.useState<Executor[]>([]);
  const [selectedIncident, setSelectedIncident] = React.useState<Incident | null>(null);
  const [remediationSolution, setRemediationSolution] = React.useState<RemediationSolution | null>(null);
  const [isLoadingIncidents, setIsLoadingIncidents] = React.useState(false);
  const [isLoadingExecutors, setIsLoadingExecutors] = React.useState(false);
  const [isGeneratingSolution, setIsGeneratingSolution] = React.useState(false);
  const [isExecutingRemediation, setIsExecutingRemediation] = React.useState(false);
  const [executionResults, setExecutionResults] = React.useState<any[]>([]);
  const [activeTab, setActiveTab] = React.useState('incidents');
  const [filterType, setFilterType] = React.useState('all');
  const [filterResolved, setFilterResolved] = React.useState('all');

  // Modals
  const { isOpen: isIncidentModalOpen, onOpen: onIncidentModalOpen, onClose: onIncidentModalClose } = useDisclosure();
  const { isOpen: isSolutionModalOpen, onOpen: onSolutionModalOpen, onClose: onSolutionModalClose } = useDisclosure();
  const { isOpen: isExecutorModalOpen, onOpen: onExecutorModalOpen, onClose: onExecutorModalClose } = useDisclosure();

  const { addToast } = useToast();

  // Load data on mount
  React.useEffect(() => {
    loadIncidents();
    loadExecutors();
  }, []);

  const loadIncidents = async () => {
    setIsLoadingIncidents(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/remediation/incidents', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setIncidents(data.incidents || []);
      } else {
        throw new Error('Failed to load incidents');
      }
    } catch (error) {
      console.error('Error loading incidents:', error);
      addToast({
        title: 'Error',
        description: 'Failed to load incidents',
        color: 'danger'
      });
    } finally {
      setIsLoadingIncidents(false);
    }
  };

  const loadExecutors = async () => {
    setIsLoadingExecutors(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/remediation/executors', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setExecutors(data.executors || []);
      } else {
        throw new Error('Failed to load executors');
      }
    } catch (error) {
      console.error('Error loading executors:', error);
      addToast({
        title: 'Error',
        description: 'Failed to load executors',
        color: 'danger'
      });
    } finally {
      setIsLoadingExecutors(false);
    }
  };

  const generateRemediationSolution = async (incident: Incident, autoExecute: boolean = false) => {
    setIsGeneratingSolution(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/remediation/incidents/${incident.id}/remediate?execute=${autoExecute}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      });

      if (response.ok) {
        const data: RemediationResponse = await response.json();
        setRemediationSolution(data.solution);
        setSelectedIncident(incident);
        onSolutionModalOpen();
        
        addToast({
          title: 'Solution Generated',
          description: `AI remediation solution generated with ${Math.round(data.solution.confidence_score * 100)}% confidence`,
          color: 'success'
        });

        if (autoExecute) {
          addToast({
            title: 'Execution Started',
            description: 'Remediation is being executed in the background',
            color: 'primary'
          });
        }
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate solution');
      }
    } catch (error) {
      console.error('Error generating solution:', error);
      addToast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to generate remediation solution',
        color: 'danger'
      });
    } finally {
      setIsGeneratingSolution(false);
    }
  };

  const executeRemediationSteps = async (incident: Incident, steps: RemediationStep[]) => {
    setIsExecutingRemediation(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/remediation/incidents/${incident.id}/execute`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(steps)
      });

      if (response.ok) {
        const data = await response.json();
        setExecutionResults(data.results);
        
        addToast({
          title: 'Execution Completed',
          description: `${data.successful_steps}/${data.total_steps} steps completed successfully`,
          color: data.successful_steps === data.total_steps ? 'success' : 'warning'
        });

        // Reload incidents to update status
        loadIncidents();
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to execute remediation');
      }
    } catch (error) {
      console.error('Error executing remediation:', error);
      addToast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to execute remediation',
        color: 'danger'
      });
    } finally {
      setIsExecutingRemediation(false);
    }
  };

  const activateExecutor = async (executorId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/remediation/executors/${executorId}/activate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        addToast({
          title: 'Executor Activated',
          description: 'Executor has been activated successfully',
          color: 'success'
        });
        loadExecutors();
      } else {
        throw new Error('Failed to activate executor');
      }
    } catch (error) {
      console.error('Error activating executor:', error);
      addToast({
        title: 'Error',
        description: 'Failed to activate executor',
        color: 'danger'
      });
    }
  };

  const initializeDefaultExecutors = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/remediation/initialize', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        addToast({
          title: 'Executors Initialized',
          description: 'Default executors have been initialized',
          color: 'success'
        });
        loadExecutors();
      } else {
        throw new Error('Failed to initialize executors');
      }
    } catch (error) {
      console.error('Error initializing executors:', error);
      addToast({
        title: 'Error',
        description: 'Failed to initialize executors',
        color: 'danger'
      });
    }
  };

  const getIncidentTypeColor = (type: string) => {
    switch (type) {
      case 'Warning': return 'warning';
      case 'Normal': return 'primary';
      default: return 'default';
    }
  };

  const getExecutorIcon = (name: string) => {
    switch (name) {
      case 'kubectl': return 'simple-icons:kubernetes';
      case 'argocd': return 'simple-icons:argo';
      case 'crossplane': return 'simple-icons:crossplane';
      default: return 'lucide:settings';
    }
  };

  const getActionTypeIcon = (actionType: string) => {
    switch (actionType) {
      case 'DIAGNOSTIC': return 'lucide:search';
      case 'REMEDIATION': return 'lucide:wrench';
      case 'VERIFICATION': return 'lucide:check-circle';
      case 'ROLLBACK': return 'lucide:undo';
      default: return 'lucide:play';
    }
  };

    const filteredIncidents = React.useMemo(() => {
    return incidents.filter(incident => {
      if (filterType !== 'all' && incident.type !== filterType) return false;
      if (filterResolved === 'resolved' && !incident.is_resolved) return false;
      if (filterResolved === 'unresolved' && incident.is_resolved) return false;
      return true;
    });
  }, [incidents, filterType, filterResolved]);

  const activeExecutor = React.useMemo(() => {
    return executors.find(executor => executor.status === 'active');
  }, [executors]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">AI Remediation Dashboard</h1>
          <p className="text-foreground-500">Automated Kubernetes incident remediation</p>
        </div>
        <div className="flex gap-2">
          <Button
            color="primary"
            variant="flat"
            startContent={<Icon icon="lucide:refresh-cw" />}
            onPress={() => {
              loadIncidents();
              loadExecutors();
            }}
          >
            Refresh
          </Button>
          <Button
            color="success"
            startContent={<Icon icon="lucide:settings" />}
            onPress={initializeDefaultExecutors}
          >
            Initialize Executors
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardBody className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-danger/10 rounded-lg">
                <Icon icon="lucide:alert-triangle" className="text-danger text-xl" />
              </div>
              <div>
                <p className="text-2xl font-bold">{incidents.filter(i => !i.is_resolved).length}</p>
                <p className="text-sm text-foreground-500">Active Incidents</p>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-success/10 rounded-lg">
                <Icon icon="lucide:check-circle" className="text-success text-xl" />
              </div>
              <div>
                <p className="text-2xl font-bold">{incidents.filter(i => i.is_resolved).length}</p>
                <p className="text-sm text-foreground-500">Resolved</p>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Icon icon="lucide:cpu" className="text-primary text-xl" />
              </div>
              <div>
                <p className="text-2xl font-bold">{executors.filter(e => e.status === 'active').length}</p>
                <p className="text-sm text-foreground-500">Active Executors</p>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-warning/10 rounded-lg">
                <Icon icon="lucide:clock" className="text-warning text-xl" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {Math.round(incidents.reduce((acc, i) => acc + i.resolution_attempts, 0) / Math.max(incidents.length, 1))}
                </p>
                <p className="text-sm text-foreground-500">Avg Attempts</p>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Main Content */}
      <Card>
        <CardHeader>
          <Tabs 
            selectedKey={activeTab} 
            onSelectionChange={(key) => setActiveTab(key as string)}
            className="w-full"
          >
            <Tab key="incidents" title="Incidents" />
            <Tab key="executors" title="Executors" />
          </Tabs>
        </CardHeader>
        <CardBody>
          {activeTab === 'incidents' && (
            <div className="space-y-4">
              {/* Filters */}
              <div className="flex gap-4 items-center">
                <Select
                  label="Type"
                  placeholder="All types"
                  selectedKeys={filterType !== 'all' ? [filterType] : []}
                  onSelectionChange={(keys) => setFilterType(Array.from(keys)[0] as string || 'all')}
                  className="w-48"
                >
                  <SelectItem key="all">All Types</SelectItem>
                  <SelectItem key="Warning">Warning</SelectItem>
                  <SelectItem key="Normal">Normal</SelectItem>
                </Select>

                <Select
                  label="Status"
                  placeholder="All statuses"
                  selectedKeys={filterResolved !== 'all' ? [filterResolved] : []}
                  onSelectionChange={(keys) => setFilterResolved(Array.from(keys)[0] as string || 'all')}
                  className="w-48"
                >
                  <SelectItem key="all">All Statuses</SelectItem>
                  <SelectItem key="unresolved">Unresolved</SelectItem>
                  <SelectItem key="resolved">Resolved</SelectItem>
                </Select>
              </div>

              {/* Incidents Table */}
              {isLoadingIncidents ? (
                <div className="flex justify-center py-8">
                  <Spinner size="lg" />
                </div>
              ) : (
                <Table aria-label="Incidents table">
                  <TableHeader>
                    <TableColumn>INCIDENT</TableColumn>
                    <TableColumn>TYPE</TableColumn>
                    <TableColumn>RESOURCE</TableColumn>
                    <TableColumn>NAMESPACE</TableColumn>
                    <TableColumn>COUNT</TableColumn>
                    <TableColumn>STATUS</TableColumn>
                    <TableColumn>ATTEMPTS</TableColumn>
                    <TableColumn>ACTIONS</TableColumn>
                  </TableHeader>
                  <TableBody>
                    {filteredIncidents.map((incident) => (
                      <TableRow key={incident.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{incident.reason}</p>
                            <p className="text-sm text-foreground-500 truncate max-w-xs">
                              {incident.message}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Chip
                            color={getIncidentTypeColor(incident.type)}
                            size="sm"
                            variant="flat"
                          >
                            {incident.type}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          <div>
                            <p className="font-medium">{incident.involved_object_kind}</p>
                            <p className="text-sm text-foreground-500">{incident.involved_object_name}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Chip size="sm" variant="bordered">
                            {incident.metadata_namespace || 'default'}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          <Chip color="warning" size="sm" variant="flat">
                            {incident.count}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          <Chip
                            color={incident.is_resolved ? 'success' : 'danger'}
                            size="sm"
                            variant="flat"
                          >
                            {incident.is_resolved ? 'Resolved' : 'Active'}
                          </Chip>
                        </TableCell>
                        <TableCell>{incident.resolution_attempts}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="flat"
                              color="primary"
                              startContent={<Icon icon="lucide:eye" />}
                              onPress={() => {
                                setSelectedIncident(incident);
                                onIncidentModalOpen();
                              }}
                            >
                              View
                            </Button>
                            {!incident.is_resolved && (
                              <>
                                <Button
                                  size="sm"
                                  variant="flat"
                                  color="success"
                                  startContent={<Icon icon="lucide:brain" />}
                                  isLoading={isGeneratingSolution}
                                  onPress={() => generateRemediationSolution(incident)}
                                >
                                  AI Fix
                                </Button>
                                <Button
                                  size="sm"
                                  variant="flat"
                                  color="warning"
                                  startContent={<Icon icon="lucide:zap" />}
                                  isLoading={isGeneratingSolution}
                                  onPress={() => generateRemediationSolution(incident, true)}
                                >
                                  Auto Fix
                                </Button>
                              </>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          )}

          {activeTab === 'executors' && (
            <div className="space-y-4">
              {/* Active Executor Info */}
              {activeExecutor && (
                <Card className="bg-success/5 border-success/20">
                  <CardBody className="p-4">
                    <div className="flex items-center gap-3">
                      <Icon icon={getExecutorIcon(activeExecutor.name)} className="text-success text-2xl" />
                      <div>
                        <p className="font-semibold text-success">Active Executor: {activeExecutor.name}</p>
                        <p className="text-sm text-foreground-500">{activeExecutor.description}</p>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              )}

              {/* Executors Table */}
              {isLoadingExecutors ? (
                <div className="flex justify-center py-8">
                  <Spinner size="lg" />
                </div>
              ) : (
                <Table aria-label="Executors table">
                  <TableHeader>
                    <TableColumn>EXECUTOR</TableColumn>
                    <TableColumn>STATUS</TableColumn>
                    <TableColumn>DESCRIPTION</TableColumn>
                    <TableColumn>UPDATED</TableColumn>
                    <TableColumn>ACTIONS</TableColumn>
                  </TableHeader>
                  <TableBody>
                    {executors.map((executor) => (
                      <TableRow key={executor.id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <Icon icon={getExecutorIcon(executor.name)} className="text-xl" />
                            <span className="font-medium capitalize">{executor.name}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Chip
                            color={executor.status === 'active' ? 'success' : 'default'}
                            size="sm"
                            variant="flat"
                          >
                            {executor.status}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          <p className="text-sm">{executor.description}</p>
                        </TableCell>
                        <TableCell>
                          <p className="text-sm text-foreground-500">
                            {new Date(executor.updated_at).toLocaleDateString()}
                          </p>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            {executor.status !== 'active' && (
                              <Button
                                size="sm"
                                color="success"
                                variant="flat"
                                startContent={<Icon icon="lucide:play" />}
                                onPress={() => activateExecutor(executor.id)}
                              >
                                Activate
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="flat"
                              startContent={<Icon icon="lucide:settings" />}
                              onPress={() => {
                                // TODO: Open executor config modal
                              }}
                            >
                              Configure
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Incident Details Modal */}
      <Modal 
        isOpen={isIncidentModalOpen} 
        onClose={onIncidentModalClose}
        size="2xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          <ModalHeader>
            <div className="flex items-center gap-3">
              <Icon icon="lucide:alert-triangle" className="text-warning" />
              Incident Details
            </div>
          </ModalHeader>
          <ModalBody>
            {selectedIncident && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-foreground-500">Reason</p>
                    <p className="font-medium">{selectedIncident.reason}</p>
                  </div>
                  <div>
                    <p className="text-sm text-foreground-500">Type</p>
                    <Chip color={getIncidentTypeColor(selectedIncident.type)} size="sm">
                      {selectedIncident.type}
                    </Chip>
                  </div>
                  <div>
                    <p className="text-sm text-foreground-500">Resource</p>
                    <p className="font-medium">
                      {selectedIncident.involved_object_kind}/{selectedIncident.involved_object_name}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-foreground-500">Namespace</p>
                    <p className="font-medium">{selectedIncident.metadata_namespace || 'default'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-foreground-500">Count</p>
                    <p className="font-medium">{selectedIncident.count}</p>
                  </div>
                  <div>
                    <p className="text-sm text-foreground-500">Resolution Attempts</p>
                    <p className="font-medium">{selectedIncident.resolution_attempts}</p>
                  </div>
                </div>
                
                <Divider />
                
                <div>
                  <p className="text-sm text-foreground-500 mb-
