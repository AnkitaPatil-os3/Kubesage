import React, { useState, useEffect } from 'react';
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

interface ClusterAnalyzeProps {
    selectedCluster?: string;
}

const RESOURCE_TYPES = [
    { key: 'pods', label: 'Pods', icon: 'mdi:cube-outline', description: 'Running containers and their status' },
    { key: 'deployments', label: 'Deployments', icon: 'mdi:rocket-launch-outline', description: 'Application deployments and replicas' },
    { key: 'services', label: 'Services', icon: 'mdi:network-outline', description: 'Network services and endpoints' },
    { key: 'secrets', label: 'Secrets', icon: 'mdi:key-outline', description: 'Sensitive configuration data' },
    { key: 'storageclasses', label: 'Storage Classes', icon: 'mdi:database-outline', description: 'Storage provisioning classes' },
    { key: 'ingress', label: 'Ingress', icon: 'mdi:web', description: 'External access and routing' },
    { key: 'pvc', label: 'Persistent Volume Claims', icon: 'mdi:harddisk', description: 'Storage volume requests' }
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
    const [selectedNamespace, setSelectedNamespace] = useState<string>('');
    const [selectedResourceType, setSelectedResourceType] = useState<string>('pods');
    const [namespaces, setNamespaces] = useState<string[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
    const [currentProblemIndex, setCurrentProblemIndex] = useState(0);
    const [showAllProblems, setShowAllProblems] = useState(false);
    const [currentResourceIndex, setCurrentResourceIndex] = useState(0);

    const { isOpen: isCommandModalOpen, onOpen: onCommandModalOpen, onClose: onCommandModalClose } = useDisclosure();
    const [selectedCommand, setSelectedCommand] = useState<string>('');

    // Fetch namespaces on component mount
    useEffect(() => {
        fetchNamespaces();
    }, []);

    const fetchNamespaces = async () => {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('https://10.0.32.106:8002/kubeconfig/namespaces', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                setNamespaces(data.namespaces || []);
            }
        } catch (error) {
            console.error('Error fetching namespaces:', error);
        }
    };

    const performAnalysis = async () => {
        setIsAnalyzing(true);
        setError(null);
        setAnalysisData(null);
        setCurrentProblemIndex(0);
        setCurrentResourceIndex(0);

        try {
            const token = localStorage.getItem('access_token');
            const params = new URLSearchParams();

            if (selectedNamespace) {
                params.append('namespace', selectedNamespace);
            }

            params.append('resource_types', selectedResourceType);

            const response = await fetch(`https://10.0.32.106:8002/kubeconfig/analyze-k8s-with-solutions?${params}`, {
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
                                <Tooltip content={`Estimated time: ${solution.estimated_time_mins} minutes`}>
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
                                                        <Badge
                                                            content={step.step_id}
                                                            color="primary"
                                                            shape="circle"
                                                            className="flex-shrink-0 mt-1"
                                                        />
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

                                                            {step.command && (
                                                                <div className="mb-2">
                                                                    <Snippet
                                                                        symbol=""
                                                                        variant="flat"
                                                                        color="primary"
                                                                        className="w-full"
                                                                        onCopy={() => copyToClipboard(step.command!)}
                                                                    >
                                                                        {step.command}
                                                                    </Snippet>
                                                                </div>
                                                            )}

                                                            <div className="text-xs text-default-500">
                                                                <strong>Expected outcome:</strong> {step.expected_outcome}
                                                            </div>
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
            <Card>
                <CardHeader>
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                        <Icon icon="mdi:cog-outline" />
                        Analysis Configuration
                    </h2>
                </CardHeader>
                <CardBody>
                    <div className="space-y-6">
                        {/* Namespace Selection */}
                        <div>
                            <label className="block text-sm font-medium mb-2">Namespace</label>
                            <Select
                                placeholder="All namespaces"
                                selectedKeys={selectedNamespace ? [selectedNamespace] : []}
                                onSelectionChange={(keys) => {
                                    const selected = Array.from(keys)[0] as string;
                                    setSelectedNamespace(selected || '');
                                }}
                                startContent={<Icon icon="mdi:folder-outline" />}
                            >
                                <SelectItem key="" value="">All namespaces</SelectItem>
                                {namespaces.map((ns) => (
                                    <SelectItem key={ns} value={ns}>
                                        {ns}
                                    </SelectItem>
                                ))}
                            </Select>
                        </div>

                        {/* Resource Types Selection - Fixed Cards */}
                        <div>
                            <label className="block text-sm font-medium mb-3">Resource Type</label>
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-2">
                                {RESOURCE_TYPES.map((type) => (
                                    <motion.div
                                        key={type.key}
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                    >
                                        <Card
                                            isPressable
                                            isHoverable
                                            className={`cursor-pointer transition-all duration-200 h-24 w-full ${
                                                selectedResourceType === type.key
                                                    ? 'border-2 border-primary bg-primary/10'
                                                    : 'border border-default-200 hover:border-primary/50'
                                            }`}
                                            onPress={() => setSelectedResourceType(type.key)}
                                        >
                                            <CardBody className="p-2 relative">
                                                <div className="flex flex-col items-center justify-center text-center h-full space-y-1">
                                                    <div className={`p-1.5 rounded-full ${
                                                        selectedResourceType === type.key
                                                            ? 'bg-primary text-white'
                                                            : 'bg-default-100 text-default-600'
                                                    }`}>
                                                        <Icon 
                                                            icon={type.icon} 
                                                            className="text-lg"
                                                        />
                                                    </div>
                                                    <div className="flex-1 flex flex-col justify-center">
                                                        <h3 className={`font-semibold text-xs leading-tight ${
                                                            selectedResourceType === type.key
                                                                ? 'text-primary'
                                                                : 'text-default-700'
                                                        }`}>
                                                            {type.label}
                                                        </h3>
                                                    </div>
                                                    {selectedResourceType === type.key && (
                                                        <div className="absolute top-1 right-1">
                                                            <Icon 
                                                                icon="mdi:check-circle" 
                                                                className="text-primary text-sm"
                                                            />
                                                        </div>
                                                    )}
                                                </div>
                                            </CardBody>
                                        </Card>
                                    </motion.div>
                                ))}
                            </div>
                            {/* Selected Resource Description */}
                            <div className="mt-3 p-3 bg-default-50 rounded-lg">
                                <p className="text-sm text-default-600">
                                    <span className="font-medium">
                                        {RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.label}:
                                    </span>{' '}
                                    {RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.description}
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-between items-center mt-6">
                        <div className="text-sm text-default-500">
                            Selected: <span className="font-medium text-primary">
                                {RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.label}
                            </span>
                            {selectedNamespace && ` in namespace: ${selectedNamespace}`}
                        </div>
                        <Button
                            color="primary"
                            onPress={performAnalysis}
                            isLoading={isAnalyzing}
                            startContent={!isAnalyzing && <Icon icon="mdi:magnify" />}
                            size="lg"
                        >
                            {isAnalyzing ? 'Analyzing...' : 'Start Analysis'}
                        </Button>
                    </div>
                </CardBody>
            </Card>

            {/* Loading State */}
            {isAnalyzing && (
                <Card>
                    <CardBody className="text-center py-8">
                        <Spinner size="lg" color="primary" className="mb-4" />
                        <h3 className="text-lg font-semibold mb-2">Analyzing Cluster</h3>
                        <p className="text-default-500 mb-4">
                            Scanning {RESOURCE_TYPES.find(type => type.key === selectedResourceType)?.label} and generating AI solutions...
                        </p>
                        <Progress
                            size="sm"
                            isIndeterminate
                            color="primary"
                            className="max-w-md mx-auto"
                        />
                    </CardBody>
                </Card>
            )}

            {/* Error State */}
            {error && !isAnalyzing && (
                <Alert 
                    color={error.includes('healthy') ? 'success' : 'danger'}
                    variant="flat"
                    startContent={
                        <Icon 
                            icon={error.includes('healthy') ? 'mdi:check-circle' : 'mdi:alert-circle'} 
                        />
                    }
                >
                    {error}
                </Alert>
            )}

            {/* Analysis Results */}
            {analysisData && analysisData.total_problems > 0 && (
                <div className="space-y-4">
                    {/* Summary Card */}
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between w-full">
                                <h2 className="text-lg font-semibold flex items-center gap-2">
                                    <Icon icon="mdi:chart-line" />
                                    Analysis Summary
                                </h2>
                                <div className="flex items-center gap-2">
                                    <Button
                                        size="sm"
                                        variant="flat"
                                        onPress={() => setShowAllProblems(!showAllProblems)}
                                        startContent={<Icon icon={showAllProblems ? 'mdi:view-sequential' : 'mdi:view-grid'} />}
                                    >
                                        {showAllProblems ? 'One by One' : 'Show All'}
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardBody>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-danger">
                                        {analysisData.total_problems}
                                    </div>
                                    <div className="text-sm text-default-500">Total Issues</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-primary">
                                        {analysisData.analyzed_resource_types.length}
                                    </div>
                                    <div className="text-sm text-default-500">Resource Types</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-success">
                                        {Math.round(
                                            analysisData.problems_with_solutions.reduce(
                                                (acc, item) => acc + item.solution.confidence_score, 0
                                            ) / analysisData.problems_with_solutions.length * 100
                                        )}%
                                    </div>
                                    <div className="text-sm text-default-500">Avg Confidence</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-warning">
                                        {Math.round(
                                            analysisData.problems_with_solutions.reduce(
                                                (acc, item) => acc + item.solution.estimated_time_mins, 0
                                            ) / analysisData.problems_with_solutions.length
                                        )}m
                                    </div>
                                    <div className="text-sm text-default-500">Avg Fix Time</div>
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
                                            <Card className="mb-4">
                                                <CardHeader>
                                                    <div className="flex items-center justify-between w-full">
                                                        <h3 className="text-lg font-semibold flex items-center gap-2">
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
                                                            >
                                                                Next Resource
                                                            </Button>
                                                        </div>
                                                    </div>
                                                </CardHeader>
                                                <CardBody>
                                                    <div className="flex items-center justify-between">
                                                        <div className="text-sm text-default-500">
                                                            Resource {currentResourceIndex + 1} of {resourceTypes.length}: {currentResourceType}
                                                        </div>
                                                        <Progress
                                                            value={(currentResourceIndex + 1) / resourceTypes.length * 100}
                                                            color="primary"
                                                            className="max-w-xs"
                                                        />
                                                    </div>
                                                </CardBody>
                                            </Card>

                                            {/* Problem Navigation within Resource Type */}
                                            {currentResourceProblems.length > 1 && (
                                                <Card className="mb-4">
                                                    <CardHeader>
                                                        <div className="flex items-center justify-between w-full">
                                                            <h4 className="text-md font-semibold">
                                                                Problem {currentProblemIndex + 1} of {currentResourceProblems.length}
                                                            </h4>
                                                            <div className="flex items-center gap-2">
                                                                <Button
                                                                    size="sm"
                                                                    variant="flat"
                                                                    isDisabled={currentProblemIndex === 0}
                                                                    onPress={() => setCurrentProblemIndex(currentProblemIndex - 1)}
                                                                    startContent={<Icon icon="mdi:chevron-left" />}
                                                                >
                                                                    Previous
                                                                </Button>
                                                                <Button
                                                                    size="sm"
                                                                    variant="flat"
                                                                    isDisabled={currentProblemIndex === currentResourceProblems.length - 1}
                                                                    onPress={() => setCurrentProblemIndex(currentProblemIndex + 1)}
                                                                    endContent={<Icon icon="mdi:chevron-right" />}
                                                                >
                                                                    Next
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    </CardHeader>
                                                    <CardBody>
                                                        <Progress
                                                            value={(currentProblemIndex + 1) / currentResourceProblems.length * 100}
                                                            color="secondary"
                                                            className="mb-2"
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
            >
                <ModalContent>
                    <ModalHeader>
                        <div className="flex items-center gap-2">
                            <Icon icon="mdi:console" />
                            Command Details
                        </div>
                    </ModalHeader>
                    <ModalBody>
                        <div className="space-y-4">
                            <div>
                                <h4 className="font-semibold mb-2">Command:</h4>
                                <Code className="w-full p-3 text-sm">
                                    {selectedCommand}
                                </Code>
                            </div>
                            <Alert color="warning" variant="flat">
                                <Icon icon="mdi:alert-triangle" className="mr-2" />
                                Always review commands before executing them in your cluster.
                            </Alert>
                        </div>
                    </ModalBody>
                    <ModalFooter>
                        <Button
                            color="primary"
                            variant="flat"
                            onPress={() => copyToClipboard(selectedCommand)}
                            startContent={<Icon icon="mdi:content-copy" />}
                        >
                            Copy Command
                        </Button>
                        <Button color="primary" onPress={onCommandModalClose}>
                            Close
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>
        </div>
    );
};

export default ClusterAnalyze;
