import React, { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import {
    Card,
    CardBody,
    CardHeader,
    Button,
    Spinner,
    Chip,
    Divider,
    Select,
    SelectItem,
    Checkbox,
    CheckboxGroup,
    Accordion,
    AccordionItem,
    Progress,
    Alert,
    Badge,
    Tooltip,
    Modal,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    useDisclosure,
    Code,
    Snippet
} from '@heroui/react';
import { Icon } from '@iconify/react';
import { motion, AnimatePresence } from 'framer-motion';

// Types
interface KubernetesError {
    Text: string;
    KubernetesDoc: string;
    Sensitive: string[];
}

interface Problem {
    kind: string;
    name: string;
    namespace: string;
    errors: KubernetesError[];
    details: string;
    parentObject: string;
}

interface RemediationStep {
    step_id: number;
    action_type: string;
    description: string;
    command?: string;
    expected_outcome: string;
}

interface Solution {
    solution_summary: string;
    detailed_solution: string;
    remediation_steps: RemediationStep[];
    confidence_score: number;
    estimated_time_mins: number;
    additional_notes: string;
}

interface ProblemWithSolution {
    problem: Problem;
    solution: Solution;
}

interface AnalysisResponse {
    cluster_name: string;
    namespace: string;
    analyzed_resource_types: string[];
    total_problems: number;
    problems_with_solutions: ProblemWithSolution[];
}

// Add new interfaces for cluster management
interface ClusterInfo {
    id: number;
    cluster_name: string;
    server_url: string;
    context_name: string;
    provider_name: string;
    tags: string[];
    use_secure_tls: boolean;
    is_operator_installed: boolean;
    active: boolean;
    created_at: string;
    updated_at: string;
}

interface ClusterAnalyzeProps {
    selectedCluster?: string;
}

const RESOURCE_TYPES = [
    {
        key: 'pods',
        label: 'Pods',
        icon: 'mdi:cube-outline',
        description: 'Running containers and their status',
        color: 'bg-gradient-to-br from-blue-500 to-blue-600',
        lightColor: 'bg-blue-50 border-blue-200',
        textColor: 'text-blue-600',
        iconBg: 'bg-blue-100'
    },
    {
        key: 'deployments',
        label: 'Deployments',
        icon: 'mdi:rocket-launch-outline',
        description: 'Application deployments and replicas',
        color: 'bg-gradient-to-br from-green-500 to-green-600',
        lightColor: 'bg-green-50 border-green-200',
        textColor: 'text-green-600',
        iconBg: 'bg-green-100'
    },
    {
        key: 'services',
        label: 'Services',
        icon: 'mdi:network-outline',
        description: 'Network services and endpoints',
        color: 'bg-gradient-to-br from-purple-500 to-purple-600',
        lightColor: 'bg-purple-50 border-purple-200',
        textColor: 'text-purple-600',
        iconBg: 'bg-purple-100'
    },
    {
        key: 'secrets',
        label: 'Secrets',
        icon: 'mdi:key-outline',
        description: 'Sensitive configuration data',
        color: 'bg-gradient-to-br from-red-500 to-red-600',
        lightColor: 'bg-red-50 border-red-200',
        textColor: 'text-red-600',
        iconBg: 'bg-red-100'
    },
    {
        key: 'storageclasses',
        label: 'Storage Classes',
        icon: 'mdi:database-outline',
        description: 'Storage provisioning classes',
        color: 'bg-gradient-to-br from-orange-500 to-orange-600',
        lightColor: 'bg-orange-50 border-orange-200',
        textColor: 'text-orange-600',
        iconBg: 'bg-orange-100'
    },
    {
        key: 'ingress',
        label: 'Ingress',
        icon: 'mdi:web',
        description: 'External access and routing',
        color: 'bg-gradient-to-br from-teal-500 to-teal-600',
        lightColor: 'bg-teal-50 border-teal-200',
        textColor: 'text-teal-600',
        iconBg: 'bg-teal-100'
    },
    {
        key: 'pvc',
        label: 'Persistent Volume Claims',
        icon: 'mdi:harddisk',
        description: 'Storage volume requests',
        color: 'bg-gradient-to-br from-indigo-500 to-indigo-600',
        lightColor: 'bg-indigo-50 border-indigo-200',
        textColor: 'text-indigo-600',
        iconBg: 'bg-indigo-100'
    }
];

const ACTION_TYPE_ICONS = {
    'KUBECTL_DESCRIBE': 'mdi:information-outline',
    'KUBECTL_GET_LOGS': 'mdi:text-box-outline',
    'KUBECTL_APPLY': 'mdi:check-circle-outline',
    'KUBECTL_DELETE': 'mdi:delete-outline',
    'KUBECTL_SCALE': 'mdi:resize',
    'KUBECTL_PATCH': 'mdi:pencil-outline',
    'MANUAL_CHECK': 'mdi:eye-outline',
    'CONFIGURATION_CHANGE': 'mdi:cog-outline'
};

const SEVERITY_COLORS = {
    'Pod': 'danger',
    'Deployment': 'warning',
    'Service': 'primary',
    'Secret': 'secondary',
    'StorageClass': 'success',
    'Ingress': 'warning',
    'PersistentVolumeClaim': 'primary'
} as const;

export const ClusterAnalyze: React.FC<ClusterAnalyzeProps> = ({ selectedCluster }) => {
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null);
    const [selectedNamespace, setSelectedNamespace] = useState<string>('default');
    const [selectedResourceType, setSelectedResourceType] = useState<string>('pods');
    const [namespaces, setNamespaces] = useState<string[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
    const [currentProblemIndex, setCurrentProblemIndex] = useState(0);
    const [showAllProblems, setShowAllProblems] = useState(false);
    const [currentResourceIndex, setCurrentResourceIndex] = useState(0);

    // Add new state variables for cluster management
    const [clusters, setClusters] = useState<ClusterInfo[]>([]);
    const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);
    const [isLoadingClusters, setIsLoadingClusters] = useState(false);
    const [isActivatingCluster, setIsActivatingCluster] = useState(false);

    // Add these state variables at the top of your component
    const [editingCommands, setEditingCommands] = useState<Record<number, boolean>>({});
    const [editedCommands, setEditedCommands] = useState<Record<number, string>>({});
    const { isOpen: isCommandModalOpen, onOpen: onCommandModalOpen, onClose: onCommandModalClose } = useDisclosure();
    const [selectedCommand, setSelectedCommand] = useState<string>('');
    // Add these state variables at the top of your component
    const [commandOutputs, setCommandOutputs] = useState<Record<number, any>>({});

    // Add these functions
    const toggleEditCommand = (stepId: number, originalCommand: string) => {
        setEditingCommands(prev => ({
            ...prev,
            [stepId]: !prev[stepId]
        }));

        // Initialize edited command with original if not already set
        if (!editedCommands[stepId]) {
            setEditedCommands(prev => ({
                ...prev,
                [stepId]: originalCommand
            }));
        }
    };

    const handleCommandChange = (stepId: number, newCommand: string) => {
        setEditedCommands(prev => ({
            ...prev,
            [stepId]: newCommand
        }));
    };

    const saveEditedCommand = (stepId: number) => {
        setEditingCommands(prev => ({
            ...prev,
            [stepId]: false
        }));
    };

    // Add this function
    const executeCommand = async (command: string, stepId: number) => {
        try {
            // Use the cluster-specific kubectl execution endpoint
            const response = await fetch(`https://10.0.2.30:8002/kubeconfig/execute-kubectl-direct/${selectedClusterId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    command: command
                })
            });

            if (response.ok) {
                const result = await response.json();

                setCommandOutputs(prev => ({
                    ...prev,
                    [stepId]: {
                        success: result.success !== false,
                        output: result.output || result.stdout || '',
                        error: result.error || result.stderr || null,
                        executed_at: new Date().toISOString()
                    }
                }));
            } else {
                const errorData = await response.json();
                setCommandOutputs(prev => ({
                    ...prev,
                    [stepId]: {
                        success: false,
                        output: errorData.output || '',
                        error: errorData.error || errorData.detail || 'Command execution failed',
                        executed_at: new Date().toISOString()
                    }
                }));
            }
        } catch (error) {
            setCommandOutputs(prev => ({
                ...prev,
                [stepId]: {
                    success: false,
                    output: '',
                    error: `Network error: ${error}`,
                    executed_at: new Date().toISOString()
                }
            }));
        }
    };


    // Fetch clusters and namespaces on component mount
    useEffect(() => {
        fetchClusters();
    }, []);

    // Fetch namespaces when selected cluster changes
    useEffect(() => {
        if (selectedClusterId) {
            fetchNamespaces();
        }
    }, [selectedClusterId]);

    // New function to fetch all onboarded clusters
    const fetchClusters = async () => {
        setIsLoadingClusters(true);
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('https://10.0.2.30:8002/kubeconfig/clusters', {  // Make sure this matches your backend endpoint
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                setClusters(data.clusters || []);

                // Find and set the active cluster as default selected
                const activeCluster = data.clusters.find((cluster: ClusterInfo) => cluster.active);
                if (activeCluster) {
                    setSelectedClusterId(activeCluster.id);
                } else if (data.clusters.length > 0) {
                    // If no active cluster, select the first one
                    setSelectedClusterId(data.clusters[0].id);
                }
            } else {
                console.error('Failed to fetch clusters:', response.status);
                setError('Failed to fetch clusters');
            }
        } catch (error) {
            console.error('Error fetching clusters:', error);
            setError('Failed to fetch clusters');
        } finally {
            setIsLoadingClusters(false);
        }
    };

    // New function to activate selected cluster and fetch namespaces
    const handleClusterSelection = async (clusterId: string) => {
        const clusterIdNum = parseInt(clusterId);
        if (clusterIdNum === selectedClusterId) return; // No change needed

        setIsActivatingCluster(true);
        setError(null);

        try {
            setSelectedClusterId(clusterIdNum);

            // Update cluster list to reflect the new active status (UI only)
            setClusters(prev => prev.map(cluster => ({
                ...cluster,
                active: cluster.id === clusterIdNum
            })));

            // Fetch namespaces for the selected cluster
            const token = localStorage.getItem('access_token');
            const response = await fetch(`https://10.0.2.30:8002/kubeconfig/get-namespaces/${clusterIdNum}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                setNamespaces(data.namespaces || []);
                setSelectedNamespace('default');
            } else {
                setError('Failed to fetch namespaces for selected cluster');
                setNamespaces([]);
            }
        } catch (error) {
            console.error('Error selecting cluster:', error);
            setError('Failed to select cluster');
        } finally {
            setIsActivatingCluster(false);
        }
    };


    const fetchNamespaces = async () => {
        if (!selectedClusterId) return;

        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`https://10.0.2.30:8002/kubeconfig/get-namespaces/${selectedClusterId}`, {  // Use the GET endpoint
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                setNamespaces(data.namespaces || []);
            } else {
                console.error('Failed to fetch namespaces:', response.status);
                setNamespaces([]);
            }
        } catch (error) {
            console.error('Error fetching namespaces:', error);
            setNamespaces([]);
        }
    };

    const performAnalysis = async () => {
        setIsAnalyzing(true);
        setError(null);
        setAnalysisData(null);
        setCurrentProblemIndex(0);
        setCurrentResourceIndex(0);
        setCommandOutputs({}); // Clear previous command outputs

        try {
            const token = localStorage.getItem('access_token');
            const params = new URLSearchParams();

            if (selectedNamespace) {
                params.append('namespace', selectedNamespace);
            }

            params.append('resource_types', selectedResourceType);

            // Use the cluster-specific analysis endpoint with cluster ID
            const response = await fetch(`https://10.0.2.30:8002/kubeconfig/analyze-k8s-with-solutions/${selectedClusterId}?${params}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Analysis failed');
            }

            const data: AnalysisResponse = await response.json();
            setAnalysisData(data);

            if (data.total_problems === 0) {
                setError('No problems found in the cluster. Your cluster appears to be healthy!');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An unexpected error occurred');
        } finally {
            setIsAnalyzing(false);
        }
    };


    const getConfidenceColor = (score: number) => {
        if (score >= 0.8) return 'success';
        if (score >= 0.6) return 'warning';
        return 'danger';
    };

    const getSeverityIcon = (kind: string) => {
        const iconMap = {
            'Pod': 'mdi:cube-outline',
            'Deployment': 'mdi:rocket-launch-outline',
            'Service': 'mdi:network-outline',
            'Secret': 'mdi:key-outline',
            'StorageClass': 'mdi:database-outline',
            'Ingress': 'mdi:web',
            'PersistentVolumeClaim': 'mdi:harddisk'
        };
        return iconMap[kind as keyof typeof iconMap] || 'mdi:alert-circle-outline';
    };

    const handleCommandClick = (command: string) => {
        setSelectedCommand(command);
        onCommandModalOpen();
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    // Group problems by resource type
    const groupProblemsByResourceType = () => {
        if (!analysisData) return {};

        const grouped: { [key: string]: ProblemWithSolution[] } = {};

        analysisData.problems_with_solutions.forEach(item => {
            const resourceType = item.problem.kind;
            if (!grouped[resourceType]) {
                grouped[resourceType] = [];
            }
            grouped[resourceType].push(item);
        });

        return grouped;
    };

    const renderProblemCard = (item: ProblemWithSolution, index: number) => {
        const { problem, solution } = item;

        return (
            <motion.div
                key={`problem-${index}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
            >
                <Card className="mb-6 border-l-4" style={{ borderLeftColor: `var(--heroui-colors-${SEVERITY_COLORS[problem.kind as keyof typeof SEVERITY_COLORS] || 'default'})` }}>
                    <CardHeader className="pb-2">
                        <div className="flex items-center justify-between w-full">
                            <div className="flex items-center gap-3">
                                <Icon
                                    icon={getSeverityIcon(problem.kind)}
                                    className="text-2xl"
                                    color={`var(--heroui-colors-${SEVERITY_COLORS[problem.kind as keyof typeof SEVERITY_COLORS] || 'default'})`}
                                />
                                <div>
                                    <h3 className="text-lg font-semibold">
                                        {problem.kind}: {problem.name}
                                    </h3>
                                    <div className="flex items-center gap-2 mt-1">
                                        {problem.namespace && (
                                            <Chip size="sm" variant="flat" color="primary">
                                                {problem.namespace}
                                            </Chip>
                                        )}
                                        <Chip
                                            size="sm"
                                            variant="flat"
                                            color={SEVERITY_COLORS[problem.kind as keyof typeof SEVERITY_COLORS] || 'default'}
                                        >
                                            {problem.kind}
                                        </Chip>
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <Tooltip content={`Confidence: ${Math.round(solution.confidence_score * 100)}%`}>
                                    <Chip
                                        size="sm"
                                        variant="flat"
                                        color={getConfidenceColor(solution.confidence_score)}
                                    >
                                        {Math.round(solution.confidence_score * 100)}%
                                    </Chip>
                                </Tooltip>
                                <Tooltip
                                    content={`Estimated time: ${solution.estimated_time_mins} minutes`}
                                    placement="top"
                                    className="text-center"
                                    classNames={{
                                        content: "text-center"
                                    }}
                                >
                                    <Chip size="sm" variant="flat">
                                        <Icon icon="mdi:clock-outline" className="mr-1" />
                                        {solution.estimated_time_mins}m
                                    </Chip>
                                </Tooltip>
                            </div>
                        </div>
                    </CardHeader>

                    <CardBody>
                        {/* Problem Details */}
                        <div className="mb-4">
                            <h4 className="text-md font-semibold mb-2 flex items-center gap-2">
                                <Icon icon="mdi:alert-circle-outline" className="text-danger" />
                                Problem Details
                            </h4>
                            <div className="space-y-2">
                                {problem.errors.map((error, errorIndex) => (
                                    <Alert
                                        key={errorIndex}
                                        color="danger"
                                        variant="flat"
                                        startContent={<Icon icon="mdi:alert" />}
                                    >
                                        {error.Text}
                                    </Alert>
                                ))}
                            </div>
                        </div>

                        <Divider className="my-4" />

                        {/* Solution */}
                        <div className="mb-4">
                            <h4 className="text-md font-semibold mb-2 flex items-center gap-2">
                                <Icon icon="mdi:lightbulb-outline" className="text-success" />
                                Solution
                            </h4>

                            <Alert color="success" variant="flat" className="mb-3">
                                <strong>Summary:</strong> {solution.solution_summary}
                            </Alert>

                            <div className="bg-content2 p-3 rounded-lg mb-3">
                                <p className="text-sm">{solution.detailed_solution}</p>
                            </div>

                            {/* Remediation Steps */}
                            {solution.remediation_steps.length > 0 && (
                                <div>
                                    <h5 className="font-semibold mb-2 flex items-center gap-2">
                                        <Icon icon="mdi:list-box-outline" />
                                        Remediation Steps
                                    </h5>
                                    <div className="space-y-3">
                                        {solution.remediation_steps.map((step, stepIndex) => (
                                            <Card key={stepIndex} className="bg-content2">
                                                <CardBody className="p-3">
                                                    <div className="flex items-start gap-3">
                                                        <div className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-medium mt-0">
                                                            {step.step_id}
                                                        </div>

                                                        <div className="flex-1">
                                                            <div className="flex items-center gap-2 mb-2">
                                                                <Icon
                                                                    icon={ACTION_TYPE_ICONS[step.action_type as keyof typeof ACTION_TYPE_ICONS] || 'mdi:cog-outline'}
                                                                    className="text-primary"
                                                                />
                                                                <Chip size="sm" variant="flat" color="primary">
                                                                    {step.action_type.replace('_', ' ')}
                                                                </Chip>
                                                            </div>
                                                            <p className="text-sm mb-2">{step.description}</p>

                                                            <div className="text-xs text-default-500">
                                                                <strong>Expected outcome:</strong> {step.expected_outcome}
                                                            </div>
                                                            {step.command && (
                                                                <div className="mb-2">
                                                                    <div className="flex items-center gap-2 mb-2">
                                                                        {editingCommands[step.step_id] ? (
                                                                            // Edit mode
                                                                            <div className="flex-1 flex items-center gap-2">
                                                                                <input
                                                                                    type="text"
                                                                                    value={editedCommands[step.step_id] || step.command}
                                                                                    onChange={(e) => handleCommandChange(step.step_id, e.target.value)}
                                                                                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm font-mono bg-gray-50 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                                                                                    autoFocus
                                                                                />
                                                                                <button
                                                                                    onClick={() => saveEditedCommand(step.step_id)}
                                                                                    className="p-2 bg-blue-600 hover:bg-blue-500 rounded text-white transition-colors"
                                                                                    title="Save Command"
                                                                                >
                                                                                    <Icon icon="mdi:check" className="w-4 h-4" />
                                                                                </button>
                                                                                <button
                                                                                    onClick={() => toggleEditCommand(step.step_id, step.command!)}
                                                                                    className="p-2 bg-gray-600 hover:bg-gray-500 rounded text-white transition-colors"
                                                                                    title="Cancel Edit"
                                                                                >
                                                                                    <Icon icon="mdi:close" className="w-4 h-4" />
                                                                                </button>
                                                                            </div>
                                                                        ) : (
                                                                            // View mode
                                                                            <>
                                                                                <Snippet
                                                                                    symbol=""
                                                                                    variant="flat"
                                                                                    color="primary"
                                                                                    className="flex-1"
                                                                                    onCopy={() => copyToClipboard(editedCommands[step.step_id] || step.command!)}
                                                                                >
                                                                                    {editedCommands[step.step_id] || step.command}
                                                                                </Snippet>
                                                                                <button
                                                                                    onClick={() => toggleEditCommand(step.step_id, step.command!)}
                                                                                    className="p-2 bg-blue-600 hover:bg-blue-500 rounded text-white transition-colors"
                                                                                    title="Edit Command"
                                                                                >
                                                                                    <Icon icon="mdi:pencil" className="w-4 h-4" />
                                                                                </button>
                                                                                <button
                                                                                    onClick={() => executeCommand(editedCommands[step.step_id] || step.command!, step.step_id)}
                                                                                    className="p-2 bg-green-600 hover:bg-green-500 rounded text-white transition-colors"
                                                                                    title="Execute Command"
                                                                                >
                                                                                    <Icon icon="mdi:play" className="w-4 h-4" />
                                                                                </button>
                                                                            </>
                                                                        )}
                                                                    </div>

                                                                    {/* Command Output Display */}
                                                                    {commandOutputs[step.step_id] ? (
                                                                        <div className="mt-3">
                                                                            <div className={`p-3 rounded-lg border ${commandOutputs[step.step_id].success
                                                                                ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-700'
                                                                                : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-700'
                                                                                }`}>
                                                                                <div className="flex items-center gap-2 mb-2">
                                                                                    <Icon
                                                                                        icon={commandOutputs[step.step_id].success ? "mdi:check-circle" : "mdi:alert-circle"}
                                                                                        className={commandOutputs[step.step_id].success ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}
                                                                                    />
                                                                                    <span className={`text-sm font-medium ${commandOutputs[step.step_id].success
                                                                                        ? 'text-green-800 dark:text-green-300'
                                                                                        : 'text-red-800 dark:text-red-300'
                                                                                        }`}>
                                                                                        {commandOutputs[step.step_id].success ? 'Success' : 'Failed'}
                                                                                    </span>
                                                                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                                                                        {new Date(commandOutputs[step.step_id].executed_at).toLocaleTimeString()}
                                                                                    </span>
                                                                                    {/* Close Icon */}
                                                                                    <button
                                                                                        onClick={() => {
                                                                                            setCommandOutputs(prev => {
                                                                                                const newOutputs = { ...prev };
                                                                                                delete newOutputs[step.step_id];
                                                                                                return newOutputs;
                                                                                            });
                                                                                        }}
                                                                                        className="ml-auto p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
                                                                                        title="Close output"
                                                                                    >
                                                                                        <Icon icon="mdi:close" className="w-4 h-4 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200" />
                                                                                    </button>
                                                                                </div>

                                                                                {commandOutputs[step.step_id].output && (
                                                                                    <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-x-auto whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                                                                                        {commandOutputs[step.step_id].output}
                                                                                    </pre>
                                                                                )}

                                                                                {commandOutputs[step.step_id].error && (
                                                                                    <div className="mt-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                                                                                        {commandOutputs[step.step_id].error}
                                                                                    </div>
                                                                                )}
                                                                            </div>
                                                                        </div>
                                                                    ) : (
                                                                        <div className="mt-3 text-sm text-gray-500 dark:text-gray-400 italic">
                                                                            Click execute button to run this command and see output
                                                                        </div>
                                                                    )}


                                                                </div>

                                                            )}
                                                        </div>
                                                    </div>
                                                </CardBody>
                                            </Card>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Additional Notes */}
                            {solution.additional_notes && (
                                <Alert color="warning" variant="flat" className="mt-3">
                                    <strong>Additional Notes:</strong> {solution.additional_notes}
                                </Alert>
                            )}
                        </div>
                    </CardBody>
                </Card>
            </motion.div>
        );
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Cluster Analysis</h1>
                    <p className="text-default-500 mt-1">
                        Analyze your Kubernetes cluster for issues and get AI-powered solutions
                    </p>
                </div>
                {analysisData && (
                    <div className="flex items-center gap-2">
                        <Chip color="success" variant="flat">
                            {analysisData.cluster_name}
                        </Chip>
                        <Chip color="primary" variant="flat">
                            {analysisData.total_problems} Issues Found
                        </Chip>
                    </div>
                )}
            </div>

            {/* Configuration Panel */}
            <Card className="dark:bg-gray-800 dark:border-gray-700">
                <CardHeader className="dark:bg-gray-800">
                    <div className="flex justify-between items-center w-full">
                        <div>
                            <h2 className="text-lg font-semibold flex items-center gap-2 dark:text-gray-100">
                                <Icon icon="mdi:cog-outline" />
                                Analysis Configuration
                            </h2>
                        </div>

                        {/* Add Refresh Button in right corner */}
                        <button
                            type="button"
                            onClick={() => window.location.reload()}
                            className="flex items-center space-x-2 px-3 py-2 text-gray-600 hover:text-green-600 hover:bg-gray-50 rounded-lg transition-all duration-300 dark:text-gray-300 dark:hover:text-green-400 dark:hover:bg-gray-700 transform hover:scale-105 active:scale-95 group hover:shadow-md"
                        >
                            <RefreshCw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500 ease-in-out" />
                            <span className="relative overflow-hidden">
                                Refresh
                                <span className="absolute inset-0 bg-gradient-to-r from-transparent via-green-400/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-out"></span>
                            </span>
                        </button>
                    </div>
                </CardHeader>

                <CardBody className="dark:bg-gray-800">
                    <div className="space-y-6">
                        {/* Cluster and Namespace Selection Row */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Cluster Selection */}
                            {/* Cluster Selection */}
                            <div>
                                <label className="block text-sm font-medium mb-2 dark:text-gray-300">
                                    Select Cluster
                                </label>
                                <div className="relative">
                                    <Select
                                        placeholder={isLoadingClusters ? "Loading clusters..." : clusters.length === 0 ? "No clusters available" : "Select a cluster"}
                                        selectedKeys={selectedClusterId ? [selectedClusterId.toString()] : []}
                                        onSelectionChange={(keys) => {
                                            const selected = Array.from(keys)[0] as string;
                                            if (selected) {
                                                handleClusterSelection(selected);
                                            }
                                        }}
                                        startContent={
                                            <div className="flex items-center gap-2">
                                                <Icon icon="mdi:kubernetes" className="text-blue-500" />
                                                {isActivatingCluster && <Spinner size="sm" />}
                                            </div>
                                        }
                                        isLoading={isLoadingClusters}
                                        isDisabled={isActivatingCluster || clusters.length === 0}
                                        classNames={{
                                            trigger: "bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 hover:border-blue-300 dark:from-blue-900/20 dark:to-indigo-900/20 dark:border-blue-700",
                                            value: "text-blue-700 dark:text-blue-300 font-medium"
                                        }}
                                    >
                                        {clusters.map((cluster) => (
                                            <SelectItem
                                                key={cluster.id.toString()}
                                                value={cluster.id.toString()}
                                                textValue={cluster.cluster_name}
                                            >
                                                <div className="flex items-center justify-between w-full">
                                                    <span>{cluster.cluster_name}</span>
                                                    <div className="flex items-center gap-1">
                                                        <Chip size="sm" variant="flat" color="primary">
                                                            {cluster.provider_name}
                                                        </Chip>
                                                        {cluster.active && (
                                                            <div className="w-2 h-2 bg-green-500 rounded-full" />
                                                        )}
                                                    </div>
                                                </div>
                                            </SelectItem>
                                        ))}
                                    </Select>

                                    {/* Active Cluster Indicator */}
                                    {selectedClusterId && (
                                        <div className="absolute -top-1 -right-1">
                                            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse shadow-lg" />
                                        </div>
                                    )}
                                </div>

                                {/* Show message if no clusters */}
                                {!isLoadingClusters && clusters.length === 0 && (
                                    <div className="mt-2 text-sm text-orange-600 dark:text-orange-400">
                                        <Icon icon="mdi:information-outline" className="inline mr-1" />
                                        No clusters onboarded yet. Please onboard a cluster first.
                                    </div>
                                )}

                                {/* Cluster Info Display */}
                                {selectedClusterId && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="mt-2"
                                    >
                                        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 dark:from-blue-900/20 dark:to-indigo-900/20 dark:border-blue-700">
                                            <CardBody className="p-3">
                                                {(() => {
                                                    const selectedCluster = clusters.find(c => c.id === selectedClusterId);
                                                    return selectedCluster ? (
                                                        <div className="flex items-center gap-3">
                                                            <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-white">
                                                                <Icon icon="mdi:kubernetes" className="text-lg" />
                                                            </div>
                                                            <div className="flex-1">
                                                                <h4 className="font-bold text-sm text-blue-700 dark:text-blue-300">
                                                                    {selectedCluster.cluster_name}
                                                                </h4>
                                                                <p className="text-xs text-blue-600 dark:text-blue-400 truncate">
                                                                    {selectedCluster.context_name || 'Default Context'}
                                                                </p>
                                                            </div>
                                                            <div className="flex items-center gap-2">
                                                                <Chip size="sm" color="success" variant="flat">
                                                                    {selectedCluster.provider_name}
                                                                </Chip>
                                                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                                            </div>
                                                        </div>
                                                    ) : null;
                                                })()}
                                            </CardBody>
                                        </Card>
                                    </motion.div>
                                )}
                            </div>


                            {/* Namespace Selection */}
                            <div>
                                <label className="block text-sm font-medium mb-2 dark:text-gray-300">
                                    Namespace
                                </label>
                                <Select
                                    placeholder={selectedClusterId ? "Select namespace" : "Select cluster first"}
                                    selectedKeys={selectedNamespace ? [selectedNamespace] : ['default']}
                                    onSelectionChange={(keys) => {
                                        const selected = Array.from(keys)[0] as string;
                                        setSelectedNamespace(selected || 'default');
                                    }}
                                    startContent={<Icon icon="mdi:folder-outline" className="text-purple-500" />}
                                    isDisabled={!selectedClusterId || namespaces.length === 0}
                                    classNames={{
                                        trigger: "bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200 hover:border-purple-300 dark:from-purple-900/20 dark:to-pink-900/20 dark:border-purple-700",
                                        value: "text-purple-700 dark:text-purple-300 font-medium"
                                    }}
                                >
                                    <SelectItem key="" value="">All namespaces</SelectItem>
                                    {namespaces.map((ns) => (
                                        <SelectItem key={ns} value={ns}>
                                            {ns}
                                        </SelectItem>
                                    ))}
                                </Select>


                                {/* Namespace Count Display */}
                                {namespaces.length > 0 && (
                                    <div className="mt-2 text-xs text-purple-600 dark:text-purple-400">
                                        <Icon icon="mdi:information-outline" className="inline mr-1" />
                                        {namespaces.length} namespace{namespaces.length !== 1 ? 's' : ''} available
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Resource Types Selection - Beautified Cards */}
                        <div>
                            <label className="block text-sm font-medium mb-4 dark:text-gray-300">Resource Type</label>
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
                                {RESOURCE_TYPES.map((type) => (
                                    <motion.div
                                        key={type.key}
                                        whileHover={{ scale: 1.05, y: -2 }}
                                        whileTap={{ scale: 0.98 }}
                                        className="relative group"
                                    >
                                        <Card
                                            isPressable
                                            isHoverable
                                            className={`cursor-pointer transition-all duration-300 h-28 w-full overflow-hidden dark:bg-gray-800 dark:border-gray-600 ${selectedResourceType === type.key
                                                ? `border-2 ${type.lightColor} shadow-lg transform scale-105 dark:shadow-gray-900/50`
                                                : 'hover:border-default-300 hover:shadow-md dark:hover:border-gray-500'
                                                }`}
                                            onPress={() => setSelectedResourceType(type.key)}
                                        >

                                            {/* Background Gradient for Selected Card */}
                                            {selectedResourceType === type.key && (
                                                <div className={`absolute inset-0 ${type.color} opacity-10 dark:opacity-20`} />
                                            )}

                                            {/* Hover Glow Effect - moved to top level */}
                                            <div className={`absolute inset-0 rounded-lg opacity-0 group-hover:opacity-20 transition-opacity duration-300 ${type.color} z-0 dark:group-hover:opacity-30`} />

                                            <CardBody className="p-3 relative z-10 dark:bg-transparent">
                                                <div className="flex flex-col items-center justify-center text-center h-full space-y-2">
                                                    {/* Icon Container */}
                                                    <div className={`relative p-2.5 rounded-xl transition-all duration-300 ${selectedResourceType === type.key
                                                        ? `${type.color} text-white shadow-lg dark:shadow-gray-900/50`
                                                        : `${type.iconBg} ${type.textColor} dark:bg-gray-700 dark:text-gray-300`
                                                        }`}>

                                                        <Icon
                                                            icon={type.icon}
                                                            className="text-xl"
                                                        />

                                                        {/* Pulse Animation for Selected */}
                                                        {selectedResourceType === type.key && (
                                                            <div className={`absolute inset-0 ${type.color} rounded-xl animate-ping opacity-20 dark:opacity-30`} />
                                                        )}

                                                    </div>

                                                    {/* Label */}
                                                    <div className="flex-1 flex flex-col justify-center">
                                                        <h3 className={`font-bold text-xs leading-tight transition-colors duration-300 ${selectedResourceType === type.key
                                                            ? type.textColor
                                                            : 'text-default-700 dark:text-gray-300'
                                                            }`}>

                                                            {type.label}
                                                        </h3>
                                                    </div>

                                                    {/* Selection Indicator */}
                                                    {selectedResourceType === type.key && (
                                                        <motion.div
                                                            initial={{ scale: 0, opacity: 0 }}
                                                            animate={{ scale: 1, opacity: 1 }}
                                                            className="absolute top-2 right-2"
                                                        >
                                                            <div className={`${type.color} rounded-full p-1 shadow-lg`}>
                                                                <Icon
                                                                    icon="mdi:check"
                                                                    className="text-white text-xs"
                                                                />
                                                            </div>
                                                        </motion.div>
                                                    )}

                                                    {/* Hover Glow Effect */}
                                                    <div className={`absolute inset-0 rounded-lg opacity-0 hover:opacity-20 transition-opacity duration-300 ${type.color} dark:hover:opacity-30`} />
                                                </div>
                                            </CardBody>
                                        </Card>
                                    </motion.div>
                                ))}
                            </div>

                            {/* Enhanced Selected Resource Description */}
                            <motion.div
                                key={selectedResourceType}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="mt-4"
                            >
                                <Card className={`${RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.lightColor} border-2 dark:bg-gray-800 dark:border-gray-600`}>
                                    <CardBody className="p-4 dark:bg-gray-800">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-lg ${RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.color} text-white dark:shadow-gray-900/50`}>
                                                <Icon
                                                    icon={RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.icon || 'mdi:cube-outline'}
                                                    className="text-lg"
                                                />
                                            </div>
                                            <div className="flex-1">
                                                <h4 className={`font-bold text-sm ${RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.textColor} dark:text-gray-200`}>
                                                    {RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.label}
                                                </h4>
                                                <p className="text-xs text-default-600 mt-1 dark:text-gray-400">
                                                    {RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.description}
                                                </p>
                                            </div>
                                            <Chip
                                                size="sm"
                                                variant="flat"
                                                className={`${RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.textColor} bg-white/50 dark:bg-gray-700/50 dark:text-gray-200`}
                                            >
                                                Selected
                                            </Chip>
                                        </div>
                                    </CardBody>
                                </Card>
                            </motion.div>
                        </div>
                    </div>

                    <div className="flex justify-between items-center mt-6 dark:border-gray-600">
                        <div className="flex items-center space-x-4">
                            <div className="text-sm text-default-500 dark:text-gray-400">
                                Selected: <span className="font-medium text-primary dark:text-green-400">
                                    {RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.label}
                                </span>
                                {selectedNamespace && <span className="dark:text-gray-400"> in namespace: <span className="font-medium text-purple-600 dark:text-purple-400">{selectedNamespace}</span></span>}
                                {selectedClusterId && (
                                    <span className="dark:text-gray-400"> on cluster: <span className="font-medium text-blue-600 dark:text-blue-400">{
                                        clusters.find(c => c.id === selectedClusterId)?.cluster_name || 'Unknown'
                                    }</span></span>
                                )}
                            </div>
                        </div>

                        <Button
                            color="primary"
                            onPress={performAnalysis}
                            isLoading={isAnalyzing}
                            startContent={!isAnalyzing && <Icon icon="mdi:magnify" />}
                            size="lg"
                            isDisabled={!selectedClusterId}
                        >
                            {isAnalyzing ? 'Analyzing...' : 'Start Analysis'}
                        </Button>
                    </div>

                </CardBody>
            </Card>

            {/* Loading State */}
            {isAnalyzing && (
                <Card className="dark:bg-gray-800 dark:border-gray-700">
                    <CardBody className="text-center py-8 dark:bg-gray-800">
                        <Spinner size="lg" color="primary" className="mb-4" />
                        <h3 className="text-lg font-semibold mb-2 dark:text-gray-100">Analyzing Cluster</h3>
                        <p className="text-default-500 mb-4 dark:text-gray-400">
                            Scanning {RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.label}
                            {selectedNamespace && ` in namespace "${selectedNamespace}"`}
                            {selectedClusterId && ` on cluster "${clusters.find(c => c.id === selectedClusterId)?.cluster_name}"`}
                            <br />
                            Generating AI solutions...
                        </p>
                        <div className="bg-warning-50 border border-warning-200 rounded-lg p-4 mb-4 max-w-md mx-auto dark:bg-yellow-900/20 dark:border-yellow-700">
                            <div className="flex items-center gap-2 mb-2">
                                <Icon icon="mdi:clock-outline" className="text-warning-600" />
                                <span className="text-sm font-medium text-warning-800 dark:text-yellow-300">Estimated Time</span>
                            </div>
                            <p className="text-sm text-warning-700 dark:text-yellow-200">
                                This process will take approximately <strong className="dark:text-yellow-100">2-3 minutes</strong> to analyze cluster issues and generate AI-powered solutions.
                            </p>
                        </div>
                        <Progress
                            size="sm"
                            isIndeterminate
                            color="primary"
                            className="max-w-md mx-auto"
                        />
                        <p className="text-xs text-default-400 mt-3 dark:text-gray-500">
                            Please wait while we examine your cluster resources...
                        </p>
                    </CardBody>
                </Card>
            )}


            {/* Error State */}
            {error && !isAnalyzing && (
                <Alert
                    color={error.includes('healthy') ? 'success' : 'danger'}
                    variant="flat"
                    className="dark:bg-gray-800 dark:border-gray-600"
                    startContent={
                        <Icon
                            icon={error.includes('healthy') ? 'mdi:check-circle' : 'mdi:alert-circle'}
                            className="dark:text-current"
                        />
                    }
                >
                    <span className="dark:text-gray-100">{error}</span>
                </Alert>
            )}

            {/* Analysis Results */}
            {analysisData && analysisData.total_problems > 0 && (
                <div className="space-y-4">
                    {/* Summary Card */}
                    <Card className="dark:bg-gray-800 dark:border-gray-700">
                        <CardHeader className="dark:bg-gray-800">
                            <div className="flex items-center justify-between w-full">
                                <h2 className="text-lg font-semibold flex items-center gap-2 dark:text-gray-100">
                                    <Icon icon="mdi:chart-line" />
                                    Analysis Summary
                                </h2>
                                <div className="flex items-center gap-2">
                                    <Button
                                        size="sm"
                                        variant="flat"
                                        onPress={() => setShowAllProblems(!showAllProblems)}
                                        startContent={<Icon icon={showAllProblems ? 'mdi:view-sequential' : 'mdi:view-grid'} />}
                                        className="dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                                    >
                                        {showAllProblems ? 'One by One' : 'Show All'}
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardBody className="dark:bg-gray-800">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-danger dark:text-red-400">
                                        {analysisData.total_problems}
                                    </div>
                                    <div className="text-sm text-default-500">Total Issues</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-primary dark:text-blue-400">
                                        {analysisData.analyzed_resource_types.length}
                                    </div>
                                    <div className="text-sm text-default-500 dark:text-gray-400">Resource Types</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-success dark:text-green-400">
                                        {Math.round(
                                            analysisData.problems_with_solutions.reduce(
                                                (acc, item) => acc + item.solution.confidence_score, 0
                                            ) / analysisData.problems_with_solutions.length * 100
                                        )}%
                                    </div>
                                    <div className="text-sm text-default-500 dark:text-gray-400">Avg Confidence</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-warning dark:text-yellow-400">
                                        {Math.round(
                                            analysisData.problems_with_solutions.reduce(
                                                (acc, item) => acc + item.solution.estimated_time_mins, 0
                                            ) / analysisData.problems_with_solutions.length
                                        )}m
                                    </div>
                                    <div className="text-sm text-default-500 dark:text-gray-400">Avg Fix Time</div>
                                </div>
                            </div>
                        </CardBody>
                    </Card>

                    {/* Problems Display */}
                    <AnimatePresence mode="wait">
                        {showAllProblems ? (
                            // Show all problems at once
                            <motion.div
                                key="all-problems"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="space-y-4"
                            >
                                {analysisData.problems_with_solutions.map((item, index) =>
                                    renderProblemCard(item, index)
                                )}
                            </motion.div>
                        ) : (
                            // Show one problem at a time with resource type navigation
                            <motion.div
                                key="single-problem"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                {(() => {
                                    const groupedProblems = groupProblemsByResourceType();
                                    const resourceTypes = Object.keys(groupedProblems);

                                    if (resourceTypes.length === 0) return null;

                                    const currentResourceType = resourceTypes[currentResourceIndex];
                                    const currentResourceProblems = groupedProblems[currentResourceType];

                                    return (
                                        <>
                                            {/* Resource Type Navigation */}
                                            <Card className="mb-4 dark:bg-gray-800 dark:border-gray-700">
                                                <CardHeader className="dark:bg-gray-800">
                                                    <div className="flex items-center justify-between w-full">
                                                        <h3 className="text-lg font-semibold flex items-center gap-2 dark:text-gray-100">
                                                            <Icon icon={getSeverityIcon(currentResourceType)} />
                                                            {currentResourceType} Issues
                                                        </h3>
                                                        <div className="flex items-center gap-2">
                                                            <Chip size="sm" variant="flat" color="primary">
                                                                {currentResourceProblems.length} Issues
                                                            </Chip>
                                                            <Button
                                                                size="sm"
                                                                variant="flat"
                                                                isDisabled={currentResourceIndex === 0}
                                                                onPress={() => {
                                                                    setCurrentResourceIndex(currentResourceIndex - 1);
                                                                    setCurrentProblemIndex(0);
                                                                }}
                                                                startContent={<Icon icon="mdi:chevron-left" />}
                                                                className="dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 dark:disabled:bg-gray-800 dark:disabled:text-gray-500"
                                                            >
                                                                Previous Resource
                                                            </Button>
                                                            <Button
                                                                size="sm"
                                                                variant="flat"
                                                                isDisabled={currentResourceIndex === resourceTypes.length - 1}
                                                                onPress={() => {
                                                                    setCurrentResourceIndex(currentResourceIndex + 1);
                                                                    setCurrentProblemIndex(0);
                                                                }}
                                                                endContent={<Icon icon="mdi:chevron-right" />}
                                                                className="dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 dark:disabled:bg-gray-800 dark:disabled:text-gray-500"
                                                            >
                                                                Next Resource
                                                            </Button>
                                                        </div>
                                                    </div>
                                                </CardHeader>
                                                <CardBody className="dark:bg-gray-800">
                                                    <div className="flex items-center justify-between">
                                                        <div className="text-sm text-default-500 dark:text-gray-400">
                                                            Resource {currentResourceIndex + 1} of {resourceTypes.length}: {currentResourceType}
                                                        </div>
                                                        <Progress
                                                            value={(currentResourceIndex + 1) / resourceTypes.length * 100}
                                                            color="primary"
                                                            className="max-w-xs dark:bg-gray-700"
                                                        />
                                                    </div>
                                                </CardBody>
                                            </Card>

                                            {/* Problem Navigation within Resource Type */}
                                            {/* Problem Navigation within Resource Type */}
                                            {currentResourceProblems.length > 1 && (
                                                <Card className="mb-4 dark:bg-gray-800 dark:border-gray-700">
                                                    <CardHeader className="dark:bg-gray-800">
                                                        <div className="flex items-center justify-between w-full">
                                                            <h4 className="text-md font-semibold dark:text-gray-100">
                                                                Problem {currentProblemIndex + 1} of {currentResourceProblems.length}
                                                            </h4>
                                                            <div className="flex items-center gap-2">
                                                                <Button
                                                                    size="sm"
                                                                    variant="flat"
                                                                    isDisabled={currentProblemIndex === 0}
                                                                    onPress={() => setCurrentProblemIndex(currentProblemIndex - 1)}
                                                                    startContent={<Icon icon="mdi:chevron-left" />}
                                                                    className="dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 dark:disabled:bg-gray-800 dark:disabled:text-gray-500"
                                                                >
                                                                    Previous
                                                                </Button>
                                                                <Button
                                                                    size="sm"
                                                                    variant="flat"
                                                                    isDisabled={currentProblemIndex === currentResourceProblems.length - 1}
                                                                    onPress={() => setCurrentProblemIndex(currentProblemIndex + 1)}
                                                                    endContent={<Icon icon="mdi:chevron-right" />}
                                                                    className="dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 dark:disabled:bg-gray-800 dark:disabled:text-gray-500"
                                                                >
                                                                    Next Problem
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    </CardHeader>
                                                    <CardBody className="dark:bg-gray-800">
                                                        <Progress
                                                            value={(currentProblemIndex + 1) / currentResourceProblems.length * 100}
                                                            color="secondary"
                                                            className="mb-2 dark:bg-gray-700"
                                                        />
                                                    </CardBody>
                                                </Card>
                                            )}


                                            {/* Current Problem Display */}
                                            {renderProblemCard(
                                                currentResourceProblems[currentProblemIndex],
                                                currentProblemIndex
                                            )}
                                        </>
                                    );
                                })()}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            )}

            {/* Command Modal */}
            <Modal
                isOpen={isCommandModalOpen}
                onClose={onCommandModalClose}
                size="2xl"
                scrollBehavior="inside"
                className="dark:bg-gray-900"
            >
                <ModalContent className="dark:bg-gray-800 dark:border-gray-700">
                    <ModalHeader className="dark:bg-gray-800 dark:text-gray-100">
                        <div className="flex items-center gap-2">
                            <Icon icon="mdi:console" />
                            Command Details
                        </div>
                    </ModalHeader>
                    <ModalBody className="dark:bg-gray-800">
                        <div className="space-y-4">
                            <div>
                                <h4 className="font-semibold mb-2 dark:text-gray-100">Command:</h4>
                                <Code className="w-full p-3 text-sm dark:bg-gray-900 dark:text-green-400">
                                    {selectedCommand}
                                </Code>
                            </div>
                            <Alert color="warning" variant="flat" className="dark:bg-yellow-900/20 dark:border-yellow-700">
                                <Icon icon="mdi:alert-triangle" className="mr-2 dark:text-yellow-300" />
                                <span className="dark:text-yellow-200">Always review commands before executing them in your cluster.</span>
                            </Alert>
                        </div>
                    </ModalBody>
                    <ModalFooter className="dark:bg-gray-800">
                        <Button
                            color="primary"
                            variant="flat"
                            onPress={() => copyToClipboard(selectedCommand)}
                            startContent={<Icon icon="mdi:content-copy" />}
                            className="dark:bg-blue-700 dark:text-blue-200 dark:hover:bg-blue-600"
                        >
                            Copy Command
                        </Button>
                        <Button color="primary" onPress={onCommandModalClose} className="dark:bg-blue-600 dark:hover:bg-blue-700">
                            Close
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>
        </div>
    );
};

export default ClusterAnalyze;