import React, { useState, useEffect, useCallback } from 'react';
import {
    Card,
    CardBody,
    CardHeader,
    Button,
    Chip,
    Spinner,
    Input,
    Select,
    SelectItem,
    Pagination,
    Modal,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    useDisclosure,
    Tabs,
    Tab,
    Progress,
    Divider,
    Badge,
    Tooltip,
    ScrollShadow,
    Textarea,
    Table,
    TableHeader,
    TableColumn,
    TableBody,
    TableRow,
    TableCell,
    Accordion, 
    AccordionItem, 
    Snippet, 
    Code, 
    Switch,
    Dropdown,
    DropdownTrigger,
    DropdownMenu,
    DropdownItem,
    Kbd
} from "@heroui/react";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "framer-motion";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip as RechartsTooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    BarChart,
    Bar,
    AreaChart,
    Area
} from 'recharts';
import axios from 'axios';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

// Initialize markdown parser
const md = new MarkdownIt({
    highlight: function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(str, { language: lang }).value;
            } catch (__) { }
        }
        return '';
    }
});

// API Base URL
const API_BASE_URL = 'https://10.0.32.123:8006';

// Types
interface KubernetesIncident {
    id: string;
    type: "Warning" | "Normal";
    reason: string;
    message: string;
    involved_object_kind: string | null;
    involved_object_name: string | null;
    metadata_namespace: string | null;
    source_component: string | null;
    count: number;
    first_timestamp: string | null;
    last_timestamp: string | null;
    metadata_creation_timestamp: string | null;
}

interface AIRecommendation {
  step_id: number;
  description: string;
  command?: string;
  command_or_payload?: {
    command: string;
  };
  action_type: string;
  target_resource: string | {
    kind: string;
    name: string;
    namespace: string;
  };
  expected_outcome: string;
  executor: string;
  is_executable: boolean;
}

interface IncidentAnalysis {
    success: boolean;
    incident_id: string;
    solution: {
        summary: string;
        analysis: string;
        severity_level: string;
        confidence_score: number;
        estimated_time_to_resolve_mins: number;
        steps: AIRecommendation[];
        recommendations: string[];
    };
}

interface ExecutorStatus {
    name: string;
    status: number;
    status_text: string;
    updated_at: string;
}

interface RemediationSolution {
    issue_summary: string;
    suggestion: string;
    command: string;
    is_executable: boolean;
    severity_level: string;
    estimated_time_mins: number;
    confidence_score: number;
}

interface ExecutionHistory {
    id: string;
    command: string;
    executor: string;
    status: string;
    executed_at: string;
    execution_time_ms: number;
    step_id?: number;
    expected_outcome?: string;
    output?: string;
    error?: string;
}

interface RemediationHistory {
    history: Array<{
        id: string;
        alert_name: string;
        namespace: string;
        resource_name: string;
        command: string;
        status: string;
        executed_at: string;
        confidence_score: number;
        severity_level: string;
        execution_time_ms: number;
        error_message?: string;
    }>;
    total: number;
}

interface RemediationStats {
    execution_stats: Record<string, number>;
    top_alerts: Array<{ alert_name: string; count: number }>;
    recent_activity: { last_24_hours: number };
    timestamp: string;
}

// Chart colors
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d'];

const RecommendationsPage: React.FC = () => {
    // State management
    const [incidents, setIncidents] = useState<KubernetesIncident[]>([]);
    const [selectedIncident, setSelectedIncident] = useState<KubernetesIncident | null>(null);
    const [incidentAnalysis, setIncidentAnalysis] = useState<IncidentAnalysis | null>(null);
    const [executorStatuses, setExecutorStatuses] = useState<ExecutorStatus[]>([]);
    const [remediationHistory, setRemediationHistory] = useState<RemediationHistory | null>(null);
    const [remediationStats, setRemediationStats] = useState<RemediationStats | null>(null);
    const [executionHistory, setExecutionHistory] = useState<ExecutionHistory[]>([]);
    const [executionResult, setExecutionResult] = useState<any>(null);
    const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

    // UI State
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [executing, setExecuting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterType, setFilterType] = useState<string>('all');
    const [filterSeverity, setFilterSeverity] = useState<string>('all');
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage] = useState(10);
    const [selectedTab, setSelectedTab] = useState('dashboard');

    // Custom Alert State
    const [customAlert, setCustomAlert] = useState({
        alert_name: '',
        namespace: 'default',
        pod_name: '',
        usage: '',
        threshold: '',
        duration: ''
    });

    // Modal controls
    const { isOpen: isDetailOpen, onOpen: onDetailOpen, onClose: onDetailClose } = useDisclosure();
    const { isOpen: isAnalysisOpen, onOpen: onAnalysisOpen, onClose: onAnalysisClose } = useDisclosure();
    const { isOpen: isExecutorOpen, onOpen: onExecutorOpen, onClose: onExecutorClose } = useDisclosure();
    const { isOpen: isRemediationOpen, onOpen: onRemediationOpen, onClose: onRemediationClose } = useDisclosure();
    const { isOpen: isHistoryOpen, onOpen: onHistoryOpen, onClose: onHistoryClose } = useDisclosure();

    // API Functions
    const fetchIncidents = useCallback(async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_BASE_URL}/incidents?skip=0&limit=100`);
            setIncidents(response.data);
        } catch (err) {
            console.error('Error fetching incidents:', err);
            setError('Failed to fetch incidents');
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchExecutorStatuses = useCallback(async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/executors/status`);
            setExecutorStatuses(response.data.executors);
        } catch (err) {
            console.error('Error fetching executor statuses:', err);
        }
    }, []);

    const fetchRemediationHistory = useCallback(async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/remediation/history?limit=50`);
            setRemediationHistory(response.data);
        } catch (err) {
            console.error('Error fetching remediation history:', err);
        }
    }, []);

    const fetchRemediationStats = useCallback(async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/remediation/stats`);
            setRemediationStats(response.data);
        } catch (err) {
            console.error('Error fetching remediation stats:', err);
        }
    }, []);

    const analyzeIncident = async (incident: KubernetesIncident) => {
        try {
            setAnalyzing(true);
            const response = await axios.post(`${API_BASE_URL}/analyze-incident`, incident);
            setIncidentAnalysis(response.data);
            setSelectedIncident(incident);
            onAnalysisOpen();
        } catch (err) {
            console.error('Error analyzing incident:', err);
            setError('Failed to analyze incident');
        } finally {
            setAnalyzing(false);
        }
    };

    const analyzeIncidentById = async (incidentId: string) => {
        try {
            setAnalyzing(true);
            const response = await axios.get(`${API_BASE_URL}/analyze-incident/${incidentId}`);
            setIncidentAnalysis(response.data);
            onAnalysisOpen();
        } catch (err) {
            console.error('Error analyzing incident by ID:', err);
            setError('Failed to analyze incident');
        } finally {
            setAnalyzing(false);
        }
    };

    const analyzeCustomAlert = async () => {
        try {
            setAnalyzing(true);
            const response = await axios.post(`${API_BASE_URL}/remediate`, customAlert);
            console.log('Custom alert analysis:', response.data);
        } catch (err) {
            console.error('Error analyzing custom alert:', err);
            setError('Failed to analyze custom alert');
        } finally {
            setAnalyzing(false);
        }
    };

    const executeCommand = async (command: string, incidentId: string, stepId?: number, expectedOutcome?: string) => {
        try {
            setExecuting(true);
            setExecutionResult(null);
            
            const cleanCommand = command.replace(/^kubectl\s+/, '');
            
            const requestBody = {
                incident_id: incidentId,
                command: cleanCommand,
                executor: 'kubectl',
                confirm_execution: true,
                step_id: stepId,
                expected_outcome: expectedOutcome || 'Command execution'
            };

            console.log('Executing command with request body:', requestBody);
            
            const response = await axios.post(`${API_BASE_URL}/execute-command`, requestBody);
            
            console.log('Command execution response:', response.data);

            setExecutionResult(response.data);

            if (incidentId) {
                fetchExecutionHistory(incidentId);
            }

            return response.data;
        } catch (err) {
            console.error('Error executing command:', err);
            const errorMessage = err.response?.data?.detail || err.message;
            setError(`Failed to execute command: ${errorMessage}`);
            throw err;
        } finally {
            setExecuting(false);
        }
    };

    const fetchExecutionHistory = async (incidentId: string) => {
        try {
            const response = await axios.get(`${API_BASE_URL}/incidents/${incidentId}/execution-history`);
            setExecutionHistory(response.data.execution_history);
        } catch (err) {
            console.error('Error fetching execution history:', err);
        }
    };

    const updateExecutorStatus = async (executorName: string, status: number) => {
        try {
            await axios.post(`${API_BASE_URL}/executors/${executorName}/status`, status);
            fetchExecutorStatuses();
        } catch (err) {
            console.error('Error updating executor status:', err);
        }
    };

    // Keyboard shortcuts effect
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.metaKey || event.ctrlKey) {
                switch (event.key) {
                    case 'r':
                        event.preventDefault();
                        fetchIncidents();
                        break;
                    case 'e':
                        event.preventDefault();
                        onExecutorOpen();
                        break;
                    case 's':
                        event.preventDefault();
                        fetchRemediationStats();
                        onRemediationOpen();
                        break;
                    case 'f':
                        event.preventDefault();
                        document.querySelector('input[placeholder*="Search"]')?.focus();
                        break;
                    case '/':
                        event.preventDefault();
                        setShowKeyboardHelp(true);
                        break;
                }
            } else if (event.key === 'Escape') {
                onDetailClose();
                onAnalysisClose();
                onExecutorClose();
                onRemediationClose();
                setShowKeyboardHelp(false);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onDetailClose, onAnalysisClose, onExecutorClose, onRemediationClose, fetchIncidents, fetchRemediationStats, onExecutorOpen, onRemediationOpen]);

    // Filter and search logic
    const filteredIncidents = incidents.filter(incident => {
        const matchesSearch = incident.reason.toLowerCase().includes(searchTerm.toLowerCase()) ||
            incident.message?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            incident.involved_object_name?.toLowerCase().includes(searchTerm.toLowerCase());

        const matchesType = filterType === 'all' || incident.type === filterType;

        return matchesSearch && matchesType;
    });

    // Pagination
    const totalPages = Math.ceil(filteredIncidents.length / itemsPerPage);
    const currentItems = filteredIncidents.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

    // Chart data
    const incidentTypeData = [
        { name: 'Warning', value: incidents.filter(i => i.type === 'Warning').length, color: '#FF8042' },
        { name: 'Normal', value: incidents.filter(i => i.type === 'Normal').length, color: '#00C49F' }
    ];

    const executorStatusData = executorStatuses.map(executor => ({
        name: executor.name,
        status: executor.status === 0 ? 'Active' : 'Inactive',
        value: executor.status === 0 ? 1 : 0
    }));

    const timelineData = incidents.slice(0, 10).map((incident, index) => ({
        name: `Incident ${index + 1}`,
        count: incident.count,
        timestamp: incident.last_timestamp
    }));

        // Utility functions
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
                case 'completed': return 'success';
                case 'in_progress': return 'warning';
                case 'failed': return 'danger';
                case 'pending': return 'default';
                default: return 'default';
            }
        };
    
        // Effects
        useEffect(() => {
            fetchIncidents();
            fetchExecutorStatuses();
            fetchRemediationHistory();
            fetchRemediationStats();
        }, [fetchIncidents, fetchExecutorStatuses, fetchRemediationHistory, fetchRemediationStats]);
    
        useEffect(() => {
            setCurrentPage(1);
        }, [searchTerm, filterType, filterSeverity, selectedTab]);
    
        if (loading) {
            return (
                <div className="flex justify-center items-center min-h-screen">
                    <div className="text-center">
                        <Spinner size="lg" />
                        <p className="mt-4 text-lg">Loading Kubernetes incidents...</p>
                    </div>
                </div>
            );
        }
    
        if (error && incidents.length === 0) {
            return (
                <div className="flex justify-center items-center min-h-screen">
                    <Card className="max-w-md">
                        <CardBody className="text-center">
                            <Icon icon="mdi:alert-circle" className="text-6xl text-danger mb-4 mx-auto" />
                            <h3 className="text-xl font-bold mb-2">Error Loading Data</h3>
                            <p className="text-gray-600 mb-4">{error}</p>
                            <Button color="primary" onPress={fetchIncidents}>
                                <Icon icon="mdi:refresh" className="mr-2" />
                                Retry
                            </Button>
                        </CardBody>
                    </Card>
                </div>
            );
        }
    
        return (
            <div className="container mx-auto px-4 py-8 pb-24">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <h1 className="text-4xl font-bold flex items-center gap-3">
                                <Icon icon="mdi:kubernetes" className="text-blue-500" />
                                KubeSage AI Recommendations
                            </h1>
                            <p className="text-gray-600 mt-2">
                                AI-powered incident analysis and automated remediation for your Kubernetes cluster
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                color="secondary"
                                variant="flat"
                                onPress={onExecutorOpen}
                                startContent={<Icon icon="mdi:cog" />}
                            >
                                Executors
                            </Button>
                            <Button
                                color="primary"
                                variant="shadow"
                                onPress={fetchIncidents}
                                startContent={<Icon icon="mdi:refresh" />}
                            >
                                Refresh Data
                            </Button>
                        </div>
                    </div>
    
                    {/* Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                        <motion.div whileHover={{ scale: 1.02 }}>
                            <Card className="bg-gradient-to-r from-blue-500 to-purple-600 text-white">
                                <CardBody className="flex flex-row items-center gap-4">
                                    <Icon icon="mdi:alert" className="text-3xl" />
                                    <div>
                                        <p className="text-sm opacity-80">Total Incidents</p>
                                        <p className="text-2xl font-bold">{incidents.length}</p>
                                    </div>
                                </CardBody>
                            </Card>
                        </motion.div>
    
                        <motion.div whileHover={{ scale: 1.02 }}>
                            <Card className="bg-gradient-to-r from-orange-500 to-red-600 text-white">
                                <CardBody className="flex flex-row items-center gap-4">
                                    <Icon icon="mdi:alert-circle" className="text-3xl" />
                                    <div>
                                        <p className="text-sm opacity-80">Warnings</p>
                                        <p className="text-2xl font-bold">
                                            {incidents.filter(i => i.type === 'Warning').length}
                                        </p>
                                    </div>
                                </CardBody>
                            </Card>
                        </motion.div>
    
                        <motion.div whileHover={{ scale: 1.02 }}>
                            <Card className="bg-gradient-to-r from-green-500 to-teal-600 text-white">
                                <CardBody className="flex flex-row items-center gap-4">
                                    <Icon icon="mdi:check-circle" className="text-3xl" />
                                    <div>
                                        <p className="text-sm opacity-80">Active Executors</p>
                                        <p className="text-2xl font-bold">
                                            {executorStatuses.filter(e => e.status === 0).length}
                                        </p>
                                    </div>
                                </CardBody>
                            </Card>
                        </motion.div>
    
                        <motion.div whileHover={{ scale: 1.02 }}>
                            <Card className="bg-gradient-to-r from-purple-500 to-pink-600 text-white">
                                <CardBody className="flex flex-row items-center gap-4">
                                    <Icon icon="mdi:lightning-bolt" className="text-3xl" />
                                    <div>
                                        <p className="text-sm opacity-80">Recent Actions</p>
                                        <p className="text-2xl font-bold">
                                            {remediationStats?.recent_activity?.last_24_hours || 0}
                                        </p>
                                    </div>
                                </CardBody>
                            </Card>
                        </motion.div>
                    </div>
                </motion.div>
    
                {/* Main Tabs */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <Card>
                        <CardHeader>
                            <Tabs
                                selectedKey={selectedTab}
                                onSelectionChange={(key) => setSelectedTab(key as string)}
                                variant="underlined"
                                classNames={{
                                    tabList: "gap-6 w-full relative rounded-none p-0 border-b border-divider",
                                    cursor: "w-full bg-primary",
                                    tab: "max-w-fit px-0 h-12",
                                }}
                            >
                                <Tab
                                    key="dashboard"
                                    title={
                                        <div className="flex items-center space-x-2">
                                            <Icon icon="mdi:view-dashboard" />
                                            <span>Dashboard</span>
                                        </div>
                                    }
                                />
                                <Tab
                                    key="incidents"
                                    title={
                                        <div className="flex items-center space-x-2">
                                            <Icon icon="mdi:alert" />
                                            <span>Incidents ({incidents.length})</span>
                                        </div>
                                    }
                                />
                                <Tab
                                    key="remediation"
                                    title={
                                        <div className="flex items-center space-x-2">
                                            <Icon icon="mdi:auto-fix" />
                                            <span>Quick Remediation</span>
                                        </div>
                                    }
                                />
                                <Tab
                                    key="history"
                                    title={
                                        <div className="flex items-center space-x-2">
                                            <Icon icon="mdi:history" />
                                            <span>History</span>
                                        </div>
                                    }
                                />
                            </Tabs>
                        </CardHeader>
    
                        <CardBody>
                            <AnimatePresence mode="wait">
                                {/* Dashboard Tab */}
                                {selectedTab === 'dashboard' && (
                                    <motion.div
                                        key="dashboard"
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: 20 }}
                                        className="space-y-6"
                                    >
                                        {/* Charts Section */}
                                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                            {/* Incident Types */}
                                            <Card>
                                                <CardHeader>
                                                    <h3 className="text-lg font-semibold">Incident Types</h3>
                                                </CardHeader>
                                                <CardBody>
                                                    <ResponsiveContainer width="100%" height={200}>
                                                        <PieChart>
                                                            <Pie
                                                                data={incidentTypeData}
                                                                cx="50%"
                                                                cy="50%"
                                                                outerRadius={80}
                                                                fill="#8884d8"
                                                                dataKey="value"
                                                                label={({ name, value }) => `${name}: ${value}`}
                                                            >
                                                                {incidentTypeData.map((entry, index) => (
                                                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                                                ))}
                                                            </Pie>
                                                            <RechartsTooltip />
                                                        </PieChart>
                                                    </ResponsiveContainer>
                                                </CardBody>
                                            </Card>
    
                                            {/* Executor Status */}
                                            <Card>
                                                <CardHeader>
                                                    <h3 className="text-lg font-semibold">Executor Status</h3>
                                                </CardHeader>
                                                <CardBody>
                                                    <div className="space-y-3">
                                                        {executorStatuses.map((executor) => (
                                                            <div key={executor.name} className="flex items-center justify-between">
                                                                <div className="flex items-center gap-2">
                                                                    <Icon 
                                                                        icon={
                                                                            executor.name === 'kubectl' ? 'mdi:kubernetes' :
                                                                            executor.name === 'crossplane' ? 'mdi:cloud' :
                                                                            'mdi:git'
                                                                        } 
                                                                        className="text-lg"
                                                                    />
                                                                    <span className="capitalize">{executor.name}</span>
                                                                </div>
                                                                <Chip 
                                                                    size="sm" 
                                                                    color={executor.status === 0 ? 'success' : 'default'}
                                                                    variant="flat"
                                                                >
                                                                    {executor.status_text}
                                                                </Chip>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </CardBody>
                                            </Card>
    
                                            {/* Recent Activity */}
                                            <Card>
                                                <CardHeader>
                                                    <h3 className="text-lg font-semibold">Recent Activity</h3>
                                                </CardHeader>
                                                <CardBody>
                                                    <div className="space-y-3">
                                                        {incidents.slice(0, 5).map((incident) => (
                                                            <div key={incident.id} className="flex items-center justify-between">
                                                                <div className="flex-1 min-w-0">
                                                                    <p className="text-sm font-medium truncate">
                                                                        {incident.reason}
                                                                    </p>
                                                                    <p className="text-xs text-gray-500">
                                                                        {incident.involved_object_name}
                                                                    </p>
                                                                </div>
                                                                <Chip 
                                                                    size="sm" 
                                                                    color={incident.type === 'Warning' ? 'warning' : 'success'}
                                                                    variant="flat"
                                                                >
                                                                    {incident.type}
                                                                </Chip>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </CardBody>
                                            </Card>
                                        </div>
    
                                        {/* Quick Actions */}
                                        <Card>
                                            <CardHeader>
                                                <h3 className="text-lg font-semibold flex items-center gap-2">
                                                    <Icon icon="mdi:lightning-bolt" />
                                                    Quick Actions
                                                </h3>
                                            </CardHeader>
                                            <CardBody>
                                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                                    <Button
                                                        color="primary"
                                                        variant="flat"
                                                        size="lg"
                                                        onPress={() => setSelectedTab('incidents')}
                                                        startContent={<Icon icon="mdi:alert" />}
                                                    >
                                                        View All Incidents
                                                    </Button>
                                                    <Button
                                                        color="success"
                                                        variant="flat"
                                                        size="lg"
                                                        onPress={() => setSelectedTab('remediation')}
                                                        startContent={<Icon icon="mdi:auto-fix" />}
                                                    >
                                                        Quick Remediation
                                                    </Button>
                                                    <Button
                                                        color="secondary"
                                                        variant="flat"
                                                        size="lg"
                                                        onPress={onExecutorOpen}
                                                        startContent={<Icon icon="mdi:cog" />}
                                                    >
                                                        Manage Executors
                                                    </Button>
                                                </div>
                                            </CardBody>
                                        </Card>
                                    </motion.div>
                                )}
    
                                {/* Incidents Tab */}
                                {selectedTab === 'incidents' && (
                                    <motion.div
                                        key="incidents"
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: 20 }}
                                        className="space-y-4"
                                        >
                                            {/* Search and Filters */}
                                            <div className="flex flex-col md:flex-row gap-4">
                                                <Input
                                                    placeholder="Search incidents..."
                                                    value={searchTerm}
                                                    onChange={(e) => setSearchTerm(e.target.value)}
                                                    startContent={<Icon icon="mdi:magnify" />}
                                                    className="flex-1"
                                                />
                                                <Select
                                                    placeholder="Filter by type"
                                                    selectedKeys={filterType ? [filterType] : []}
                                                    onSelectionChange={(keys) => setFilterType(Array.from(keys)[0] as string)}
                                                    className="w-full md:w-48"
                                                >
                                                    <SelectItem key="all">All Types</SelectItem>
                                                    <SelectItem key="Warning">Warning</SelectItem>
                                                    <SelectItem key="Normal">Normal</SelectItem>
                                                </Select>
                                            </div>
        
                                            {/* Incidents List */}
                                            {currentItems.length === 0 ? (
                                                <div className="text-center py-8">
                                                    <Icon icon="mdi:database-search" className="text-6xl text-gray-400 mb-4 mx-auto" />
                                                    <p className="text-gray-600">No incidents found matching your criteria.</p>
                                                </div>
                                            ) : (
                                                currentItems.map((incident, index) => (
                                                    <motion.div
                                                        key={incident.id}
                                                        initial={{ opacity: 0, y: 20 }}
                                                        animate={{ opacity: 1, y: 0 }}
                                                        transition={{ delay: index * 0.1 }}
                                                        whileHover={{ scale: 1.02 }}
                                                    >
                                                        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                                                            <CardBody>
                                                                <div className="flex items-start justify-between">
                                                                    <div className="flex-1">
                                                                        <div className="flex items-center gap-3 mb-2">
                                                                            <Chip
                                                                                color={incident.type === 'Warning' ? 'warning' : 'success'}
                                                                                variant="flat"
                                                                                startContent={
                                                                                    <Icon 
                                                                                        icon={incident.type === 'Warning' ? 'mdi:alert' : 'mdi:information'} 
                                                                                    />
                                                                                }
                                                                            >
                                                                                {incident.type}
                                                                            </Chip>
                                                                            <Badge content={incident.count} color="primary">
                                                                                <Chip variant="flat">{incident.reason}</Chip>
                                                                            </Badge>
                                                                        </div>
                                                                        
                                                                        <h3 className="text-lg font-semibold mb-2">
                                                                            {incident.involved_object_kind} / {incident.involved_object_name || 'Unknown'}
                                                                        </h3>
                                                                        
                                                                        <p className="text-gray-600 mb-3 line-clamp-2">
                                                                            {incident.message}
                                                                        </p>
                                                                        
                                                                        <div className="flex flex-wrap gap-2 text-sm text-gray-500">
                                                                            {incident.metadata_namespace && (
                                                                                <Chip size="sm" variant="bordered">
                                                                                    <Icon icon="mdi:namespace" className="mr-1" />
                                                                                    {incident.metadata_namespace}
                                                                                </Chip>
                                                                            )}
                                                                            {incident.source_component && (
                                                                                <Chip size="sm" variant="bordered">
                                                                                    <Icon icon="mdi:component" className="mr-1" />
                                                                                    {incident.source_component}
                                                                                </Chip>
                                                                            )}
                                                                        </div>
                                                                    </div>
                                                                    
                                                                    <div className="flex flex-col gap-2">
                                                                        <Button
                                                                            size="sm"
                                                                            color="primary"
                                                                            variant="flat"
                                                                            onPress={() => {
                                                                                setSelectedIncident(incident);
                                                                                onDetailOpen();
                                                                            }}
                                                                        >
                                                                            <Icon icon="mdi:eye" />
                                                                            Details
                                                                        </Button>
                                                                        
                                                                        <Button
                                                                            size="sm"
                                                                            color="secondary"
                                                                            variant="flat"
                                                                            onPress={() => analyzeIncident(incident)}
                                                                            isLoading={analyzing}
                                                                        >
                                                                            <Icon icon="mdi:brain" />
                                                                            AI Analyze
                                                                        </Button>
                                                                    </div>
                                                                </div>
                                                            </CardBody>
                                                        </Card>
                                                    </motion.div>
                                                ))
                                            )}
        
                                            {/* Pagination */}
                                            {totalPages > 1 && (
                                                <div className="flex justify-center mt-8">
                                                    <Pagination
                                                        total={totalPages}
                                                        page={currentPage}
                                                        onChange={setCurrentPage}
                                                        showControls
                                                        showShadow
                                                        color="primary"
                                                    />
                                                </div>
                                            )}
                                        </motion.div>
                                    )}
        
                                    {/* Quick Remediation Tab */}
                                    {selectedTab === 'remediation' && (
                                        <motion.div
                                            key="remediation"
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            exit={{ opacity: 0, x: 20 }}
                                            className="space-y-6"
                                        >
                                            <Card>
                                                <CardHeader>
                                                    <h3 className="text-lg font-semibold flex items-center gap-2">
                                                        <Icon icon="mdi:auto-fix" />
                                                        Quick Alert Remediation
                                                    </h3>
                                                </CardHeader>
                                                <CardBody>
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                        <Input
                                                            label="Alert Name"
                                                            placeholder="e.g., HighCPUUsage"
                                                            value={customAlert.alert_name}
                                                            onChange={(e) => setCustomAlert({...customAlert, alert_name: e.target.value})}
                                                        />
                                                        <Input
                                                            label="Namespace"
                                                            placeholder="default"
                                                            value={customAlert.namespace}
                                                            onChange={(e) => setCustomAlert({...customAlert, namespace: e.target.value})}
                                                        />
                                                        <Input
                                                            label="Pod/Resource Name"
                                                            placeholder="e.g., backend-xyz-123"
                                                            value={customAlert.pod_name}
                                                            onChange={(e) => setCustomAlert({...customAlert, pod_name: e.target.value})}
                                                        />
                                                        <Input
                                                            label="Current Usage"
                                                            placeholder="e.g., 95%"
                                                            value={customAlert.usage}
                                                            onChange={(e) => setCustomAlert({...customAlert, usage: e.target.value})}
                                                        />
                                                        <Input
                                                            label="Threshold"
                                                            placeholder="e.g., 80%"
                                                            value={customAlert.threshold}
                                                            onChange={(e) => setCustomAlert({...customAlert, threshold: e.target.value})}
                                                        />
                                                        <Input
                                                            label="Duration"
                                                            placeholder="e.g., 15m"
                                                            value={customAlert.duration}
                                                            onChange={(e) => setCustomAlert({...customAlert, duration: e.target.value})}
                                                        />
                                                    </div>
                                                    <div className="flex gap-2 mt-4">
                                                        <Button
                                                            color="primary"
                                                            onPress={analyzeCustomAlert}
                                                            isLoading={analyzing}
                                                            startContent={<Icon icon="mdi:brain" />}
                                                        >
                                                            Analyze & Get Remediation
                                                        </Button>
                                                        <Button
                                                            color="secondary"
                                                            variant="flat"
                                                            onPress={() => setCustomAlert({
                                                                alert_name: '',
                                                                namespace: 'default',
                                                                pod_name: '',
                                                                usage: '',
                                                                threshold: '',
                                                                duration: ''
                                                            })}
                                                        >
                                                            Clear
                                                        </Button>
                                                    </div>
                                                </CardBody>
                                            </Card>
        
                                            {/* Common Issues Quick Fix */}
                                            <Card>
                                                <CardHeader>
                                                    <h3 className="text-lg font-semibold flex items-center gap-2">
                                                        <Icon icon="mdi:lightning-bolt" />
                                                        Common Issues Quick Fix
                                                    </h3>
                                                </CardHeader>
                                                <CardBody>
                                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                                        {[
                                                            { name: 'High CPU Usage', icon: 'mdi:cpu-64-bit', alert: { alert_name: 'HighCPUUsage', usage: '90%', threshold: '80%' } },
                                                            { name: 'High Memory Usage', icon: 'mdi:memory', alert: { alert_name: 'HighMemoryUsage', usage: '85%', threshold: '75%' } },
                                                            { name: 'Pod CrashLoop', icon: 'mdi:restart', alert: { alert_name: 'PodCrashLoopBackOff', reason: 'CrashLoopBackOff' } },
                                                            { name: 'ImagePull Error', icon: 'mdi:download-off', alert: { alert_name: 'ImagePullBackOff', reason: 'ImagePullBackOff' } },
                                                            { name: 'Disk Space Low', icon: 'mdi:harddisk', alert: { alert_name: 'DiskSpaceLow', usage: '95%', threshold: '85%' } },
                                                            { name: 'Service Unavailable', icon: 'mdi:server-network-off', alert: { alert_name: 'ServiceUnavailable', status: 'Unavailable' } }
                                                        ].map((issue) => (
                                                            <Card key={issue.name} className="hover:shadow-md transition-shadow cursor-pointer">
                                                                <CardBody className="text-center p-4">
                                                                    <Icon icon={issue.icon} className="text-3xl text-primary mb-2 mx-auto" />
                                                                    <h4 className="font-semibold mb-2">{issue.name}</h4>
                                                                    <Button
                                                                        size="sm"
                                                                        color="primary"
                                                                        variant="flat"
                                                                        onPress={() => {
                                                                            setCustomAlert({
                                                                                ...customAlert,
                                                                                ...issue.alert,
                                                                                namespace: customAlert.namespace || 'default',
                                                                                pod_name: customAlert.pod_name || 'example-pod'
                                                                            });
                                                                        }}
                                                                    >
                                                                        Use Template
                                                                    </Button>
                                                                </CardBody>
                                                            </Card>
                                                        ))}
                                                    </div>
                                                </CardBody>
                                            </Card>
                                        </motion.div>
                                    )}
        
                                    {/* History Tab */}
                                    {selectedTab === 'history' && (
                                        <motion.div
                                            key="history"
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            exit={{ opacity: 0, x: 20 }}
                                            className="space-y-6"
                                        >
                                            {/* Remediation Stats */}
                                            {remediationStats && (
                                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                                    <Card>
                                                        <CardHeader>
                                                            <h4 className="font-semibold">Execution Stats</h4>
                                                        </CardHeader>
                                                        <CardBody>
                                                            <div className="space-y-2">
                                                                {Object.entries(remediationStats.execution_stats).map(([status, count]) => (
                                                                    <div key={status} className="flex justify-between">
                                                                        <span className="capitalize">{status}:</span>
                                                                        <span className="font-semibold">{count}</span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </CardBody>
                                                    </Card>
        
                                                    <Card>
                                                        <CardHeader>
                                                            <h4 className="font-semibold">Top Alerts</h4>
                                                        </CardHeader>
                                                        <CardBody>
                                                            <div className="space-y-2">
                                                                {remediationStats.top_alerts.slice(0, 5).map((alert) => (
                                                                    <div key={alert.alert_name} className="flex justify-between">
                                                                        <span className="truncate">{alert.alert_name}:</span>
                                                                        <span className="font-semibold">{alert.count}</span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </CardBody>
                                                    </Card>
        
                                                    <Card>
                                                        <CardHeader>
                                                            <h4 className="font-semibold">Recent Activity</h4>
                                                        </CardHeader>
                                                        <CardBody>
                                                            <div className="text-center">
                                                                <div className="text-3xl font-bold text-primary">
                                                                    {remediationStats.recent_activity.last_24_hours}
                                                                </div>
                                                                <div className="text-sm text-gray-600">
                                                                    Actions in last 24 hours
                                                                </div>
                                                            </div>
                                                        </CardBody>
                                                    </Card>
                                                </div>
                                            )}
        
                                                                              {/* Remediation History */}
                                    <Card>
                                        <CardHeader>
                                            <div className="flex items-center justify-between w-full">
                                                <h3 className="text-lg font-semibold flex items-center gap-2">
                                                    <Icon icon="mdi:history" />
                                                    Remediation History
                                                </h3>
                                                <Button
                                                    size="sm"
                                                    color="primary"
                                                    variant="flat"
                                                    onPress={fetchRemediationHistory}
                                                    startContent={<Icon icon="mdi:refresh" />}
                                                >
                                                    Refresh
                                                </Button>
                                            </div>
                                        </CardHeader>
                                        <CardBody>
                                            {remediationHistory && remediationHistory.history.length > 0 ? (
                                                <div className="space-y-3">
                                                    {remediationHistory.history.map((record, index) => (
                                                        <motion.div
                                                            key={record.id}
                                                            initial={{ opacity: 0, y: 10 }}
                                                            animate={{ opacity: 1, y: 0 }}
                                                            transition={{ delay: index * 0.05 }}
                                                            className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                                                        >
                                                            <div className="flex items-start justify-between">
                                                                <div className="flex-1">
                                                                    <div className="flex items-center gap-3 mb-2">
                                                                        <Chip 
                                                                            size="sm" 
                                                                            color={getStatusColor(record.status) as any}
                                                                            variant="flat"
                                                                        >
                                                                            {record.status}
                                                                        </Chip>
                                                                        <Chip size="sm" variant="bordered">
                                                                            {record.alert_name}
                                                                        </Chip>
                                                                        <span className="text-xs text-gray-500">
                                                                            {new Date(record.executed_at).toLocaleString()}
                                                                        </span>
                                                                    </div>
                                                                    
                                                                    <div className="mb-2">
                                                                        <Code className="text-sm">{record.command}</Code>
                                                                    </div>
                                                                    
                                                                    <div className="flex items-center gap-4 text-xs text-gray-600">
                                                                        <span>Namespace: {record.namespace}</span>
                                                                        <span>Resource: {record.resource_name}</span>
                                                                        <span>Time: {record.execution_time_ms}ms</span>
                                                                        <span>Confidence: {Math.round((record.confidence_score || 0) * 100)}%</span>
                                                                    </div>
                                                                </div>
                                                                
                                                                <div className="flex gap-1">
                                                                    <Button
                                                                        size="sm"
                                                                        variant="light"
                                                                        isIconOnly
                                                                        onPress={() => navigator.clipboard.writeText(record.command)}
                                                                    >
                                                                        <Icon icon="mdi:content-copy" />
                                                                    </Button>
                                                                    {record.error_message && (
                                                                        <Tooltip content={record.error_message}>
                                                                            <Button size="sm" variant="light" isIconOnly color="danger">
                                                                                <Icon icon="mdi:alert-circle" />
                                                                            </Button>
                                                                        </Tooltip>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </motion.div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="text-center py-8">
                                                    <Icon icon="mdi:history" className="text-4xl text-gray-400 mb-2 mx-auto" />
                                                    <p className="text-gray-600">No remediation history available</p>
                                                    <p className="text-sm text-gray-500 mt-1">Executed commands will appear here</p>
                                                </div>
                                            )}
                                        </CardBody>
                                    </Card>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </CardBody>
                </Card>
            </motion.div>

            {/* Incident Detail Modal */}
            <Modal
                isOpen={isDetailOpen}
                onClose={onDetailClose}
                size="2xl"
                scrollBehavior="inside"
            >
                <ModalContent>
                    <ModalHeader className="flex flex-col gap-1">
                        <div className="flex items-center gap-3">
                            <Icon icon="mdi:information-outline" className="text-2xl" />
                            <span>Incident Details</span>
                        </div>
                    </ModalHeader>
                    <ModalBody>
                        {selectedIncident && (
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm font-semibold text-gray-600">Type</p>
                                        <Chip color={selectedIncident.type === 'Warning' ? 'warning' : 'success'}>
                                            {selectedIncident.type}
                                        </Chip>
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-gray-600">Reason</p>
                                        <p className="text-lg">{selectedIncident.reason}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-gray-600">Object Kind</p>
                                        <p className="text-lg">{selectedIncident.involved_object_kind || 'N/A'}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-gray-600">Object Name</p>
                                        <p className="text-lg">{selectedIncident.involved_object_name || 'N/A'}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-gray-600">Namespace</p>
                                        <p className="text-lg">{selectedIncident.metadata_namespace || 'N/A'}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-gray-600">Count</p>
                                        <Badge content={selectedIncident.count} color="primary">
                                            <span className="text-lg">Occurrences</span>
                                        </Badge>
                                    </div>
                                </div>
                                
                                <Divider />
                                
                                <div>
                                    <p className="text-sm font-semibold text-gray-600 mb-2">Message</p>
                                    <ScrollShadow className="max-h-32">
                                        <Card className="bg-gray-50">
                                            <CardBody>
                                                <code className="text-sm whitespace-pre-wrap">
                                                    {selectedIncident.message}
                                                </code>
                                            </CardBody>
                                        </Card>
                                    </ScrollShadow>
                                </div>
                                
                                {selectedIncident.source_component && (
                                    <div>
                                        <p className="text-sm font-semibold text-gray-600">Source Component</p>
                                        <p className="text-lg">{selectedIncident.source_component}</p>
                                    </div>
                                )}
                                
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm font-semibold text-gray-600">First Timestamp</p>
                                        <p className="text-sm">{selectedIncident.first_timestamp || 'N/A'}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-gray-600">Last Timestamp</p>
                                        <p className="text-sm">{selectedIncident.last_timestamp || 'N/A'}</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </ModalBody>
                    <ModalFooter>
                        <Button color="danger" variant="light" onPress={onDetailClose}>
                            Close
                        </Button>
                        <Button 
                            color="primary" 
                            onPress={() => {
                                if (selectedIncident) {
                                    onDetailClose();
                                    analyzeIncident(selectedIncident);
                                }
                            }}
                            startContent={<Icon icon="mdi:brain" />}
                        >
                            AI Analyze
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>

            {/* AI Analysis Modal */}
            <Modal
                isOpen={isAnalysisOpen}
                onClose={onAnalysisClose}
                size="5xl"
                scrollBehavior="inside"
            >
                <ModalContent>
                    <ModalHeader className="flex flex-col gap-1">
                        <div className="flex items-center gap-3">
                            <Icon icon="mdi:brain" className="text-2xl text-purple-500" />
                            <span>AI Analysis & Recommendations</span>
                        </div>
                    </ModalHeader>
                    <ModalBody>
                        {incidentAnalysis && selectedIncident && (
                            <div className="space-y-6">
                                {/* Incident Summary */}
                                <Card className="bg-blue-50 border-l-4 border-blue-500">
                                    <CardBody>
                                        <div className="flex items-start gap-4">
                                            <Icon icon="mdi:information" className="text-2xl text-blue-500 mt-1" />
                                            <div>
                                                <h4 className="font-semibold text-blue-800">Incident Summary</h4>
                                                <p className="text-blue-700 mt-1">
                                                    {selectedIncident.reason} in {selectedIncident.involved_object_kind}/{selectedIncident.involved_object_name}
                                                </p>
                                                <p className="text-sm text-blue-600 mt-2">
                                                    Namespace: {selectedIncident.metadata_namespace || 'default'}
                                                </p>
                                            </div>
                                        </div>
                                    </CardBody>
                                </Card>

                                {/* AI Analysis */}
                                <Card>
                                    <CardHeader>
                                        <h4 className="text-lg font-semibold flex items-center gap-2">
                                            <Icon icon="mdi:brain" className="text-purple-500" />
                                            AI Analysis
                                        </h4>
                                    </CardHeader>
                                    <CardBody>
                                        <div className="space-y-4">
                                            <div className="bg-gradient-to-r from-purple-100 to-pink-100 p-4 rounded-lg">
                                                <p className="text-gray-800">
                                                    <strong>Summary:</strong> {incidentAnalysis.solution.summary}
                                                </p>
                                                <p className="text-gray-800 mt-2">
                                                    <strong>Analysis:</strong> {incidentAnalysis.solution.analysis}
                                                </p>
                                            </div>
                                            
                                            <div className="grid grid-cols-3 gap-4">
                                                <div className="text-center">
                                                    <div className="bg-green-100 p-3 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-2">
                                                        <Icon icon="mdi:target" className="text-2xl text-green-600" />
                                                    </div>
                                                    <p className="text-sm font-semibold">{Math.round((incidentAnalysis.solution.confidence_score || 0) * 100)}% Confidence</p>
                                                    <p className="text-xs text-gray-600">Success Rate</p>
                                                </div>
                                                <div className="text-center">
                                                    <div className="bg-blue-100 p-3 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-2">
                                                        <Icon icon="mdi:clock" className="text-2xl text-blue-600" />
                                                    </div>
                                                    <p className="text-sm font-semibold">{incidentAnalysis.solution.estimated_time_to_resolve_mins} Minutes</p>
                                                    <p className="text-xs text-gray-600">Est. Resolution</p>
                                                </div>
                                                <div className="text-center">
                                                    <div className="bg-orange-100 p-3 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-2">
                                                        <Icon icon="mdi:alert" className="text-2xl text-orange-600" />
                                                    </div>
                                                    <p className="text-sm font-semibold">{incidentAnalysis.solution.severity_level}</p>
                                                    <p className="text-xs text-gray-600">Priority Level</p>
                                                </div>
                                            </div>
                                        </div>
                                    </CardBody>
                                </Card>

                                {/* Resolution Steps */}
                                <Card>
                                    <CardHeader>
                                        <div className="flex items-center justify-between w-full">
                                            <h4 className="text-lg font-semibold flex items-center gap-2">
                                                <Icon icon="mdi:list-box" className="text-green-500" />
                                                Resolution Steps ({incidentAnalysis.solution.steps.length})
                                            </h4>
                                            <div className="flex gap-2">
                                                <Button
                                                    size="sm"
                                                    color="success"
                                                    variant="flat"
                                                    onPress={() => {
                                                        // Execute all safe steps
                                                        incidentAnalysis.solution.steps.forEach((step, index) => {
                                                            if (step.is_executable) {
                                                                setTimeout(() => {
                                                                    const command = step.command_or_payload?.command || step.command || '';
                                                                    executeCommand(
                                                                        command,
                                                                        incidentAnalysis.incident_id,
                                                                        step.step_id,
                                                                        step.expected_outcome
                                                                    );
                                                                }, index * 2000); // 2 second delay between commands
                                                            }
                                                        });
                                                    }}
                                                    startContent={<Icon icon="mdi:play-circle" />}
                                                >
                                                    Execute All Safe
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    color="primary"
                                                    variant="flat"
                                                    onPress={() => {
                                                        // Copy all commands to clipboard
                                                        const commands = incidentAnalysis.solution.steps
                                                            .map(step => {
                                                                const command = step.command_or_payload?.command || step.command || '';
                                                                return `# Step ${step.step_id}: ${step.description}\nkubectl ${command}`;
                                                            })
                                                            .join('\n\n');
                                                        navigator.clipboard.writeText(commands);
                                                    }}
                                                    startContent={<Icon icon="mdi:content-copy" />}
                                                >
                                                    Copy All
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    color="secondary"
                                                    variant="flat"
                                                    onPress={() => {
                                                        // Download as script
                                                        const commands = incidentAnalysis.solution.steps
                                                            .map(step => {
                                                                const command = step.command_or_payload?.command || step.command || '';
                                                                return `# Step ${step.step_id}: ${step.description}\n# Expected: ${step.expected_outcome}\nkubectl ${command}`;
                                                            })
                                                            .join('\n\n');
                                                        
                                                        const script = `#!/bin/bash\n# KubeSage Remediation Script\n# Incident: ${selectedIncident.reason}\n# Generated: ${new Date().toISOString()}\n\n${commands}`;
                                                        
                                                        const blob = new Blob([script], { type: 'text/plain' });
                                                        const url = URL.createObjectURL(blob);
                                                        const a = document.createElement('a');
                                                        a.href = url;
                                                        a.download = `remediation-${incidentAnalysis.incident_id}.sh`;
                                                        a.click();
                                                        URL.revokeObjectURL(url);
                                                    }}
                                                    startContent={<Icon icon="mdi:download" />}
                                                >
                                                    Download Script
                                                </Button>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardBody>
                                        <Accordion variant="splitted">
                                            {incidentAnalysis.solution.steps.map((step, index) => {
                                                const command = step.command_or_payload?.command || step.command || '';
                                                const isExecutable = step.is_executable !== false && 
                                                    ['KUBECTL_GET_LOGS', 'KUBECTL_DESCRIBE', 'KUBECTL_GET', 'MONITOR', 'VERIFY'].includes(step.action_type);
                                                
                                                return (
                                                    <AccordionItem
                                                        key={step.step_id}
                                                        aria-label={`Step ${step.step_id}`}
                                                        title={
                                                            <div className="flex items-center justify-between w-full pr-4">
                                                                <div className="flex items-center gap-3">
                                                                    <div className="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-bold">
                                                                        {step.step_id}
                                                                    </div>
                                                                    <div>
                                                                        <p className="font-semibold text-left">{step.description}</p>
                                                                        <div className="flex items-center gap-2 mt-1">
                                                                            <Chip size="sm" color="secondary" variant="flat">
                                                                                {step.action_type}
                                                                            </Chip>
                                                                            <Chip size="sm" variant="bordered">
                                                                                {step.executor}
                                                                            </Chip>
                                                                            {isExecutable && (
                                                                                <Chip size="sm" color="success" variant="flat">
                                                                                    Safe to Execute
                                                                                </Chip>
                                                                            )}
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        }
                                                    >
                                                        <div className="space-y-4">
                                                            {/* Target Resource */}
                                                            <div>
                                                                <p className="text-sm font-semibold text-gray-600 mb-2">Target Resource:</p>
                                                                <div className="bg-gray-50 p-3 rounded-lg">
                                                                    {typeof step.target_resource === 'string' ? (
                                                                        <p className="text-sm">{step.target_resource}</p>
                                                                    ) : (
                                                                        <div className="grid grid-cols-3 gap-4 text-sm">
                                                                            <div>
                                                                                <span className="font-medium">Kind:</span> {step.target_resource?.kind || 'N/A'}
                                                                            </div>
                                                                            <div>
                                                                                <span className="font-medium">Name:</span> {step.target_resource?.name || 'N/A'}
                                                                            </div>
                                                                            <div>
                                                                                <span className="font-medium">Namespace:</span> {step.target_resource?.namespace || 'N/A'}
                                                                            </div>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>

                                                            {/* Command */}
                                                            <div>
                                                                <p className="text-sm font-semibold text-gray-600 mb-2">Command:</p>
                                                                <div className="relative">
                                                                    <Snippet 
                                                                        symbol=""
                                                                        color="primary"
                                                                        className="w-full"
                                                                    >
                                                                        kubectl {command}
                                                                    </Snippet>
                                                                </div>
                                                            </div>

                                                            {/* Expected Outcome */}
                                                            <div>
                                                                <p className="text-sm font-semibold text-gray-600 mb-2">Expected Outcome:</p>
                                                                <div className="bg-blue-50 p-3 rounded-lg">
                                                                    <p className="text-sm text-blue-800">{step.expected_outcome}</p>
                                                                </div>
                                                            </div>

                                                            {/* Execution Controls */}
                                                            <div className="flex items-center justify-between pt-2 border-t">
                                                                <div className="flex items-center gap-2">
                                                                    {isExecutable ? (
                                                                        <Chip size="sm" color="success" variant="flat" startContent={<Icon icon="mdi:check-circle" />}>
                                                                            Safe to Execute
                                                                        </Chip>
                                                                    ) : (
                                                                        <Chip size="sm" color="warning" variant="flat" startContent={<Icon icon="mdi:alert" />}>
                                                                            Manual Review Required
                                                                        </Chip>
                                                                    )}
                                                                </div>
                                                                
                                                                <div className="flex gap-2">
                                                                    <Button
                                                                        size="sm"
                                                                        variant="light"
                                                                        onPress={() => navigator.clipboard.writeText(`kubectl ${command}`)}
                                                                        startContent={<Icon icon="mdi:content-copy" />}
                                                                    >
                                                                        Copy
                                                                    </Button>
                                                                    
                                                                    {isExecutable && (
                                                                        <Button
                                                                            size="sm"
                                                                            color="primary"
                                                                            onPress={() => executeCommand(
                                                                                command,
                                                                                incidentAnalysis.incident_id,
                                                                                step.step_id,
                                                                                step.expected_outcome
                                                                            )}
                                                                            isLoading={executing}
                                                                            startContent={<Icon icon="mdi:play" />}
                                                                        >
                                                                            Execute
                                                                        </Button>
                                                                    )}
                                                                </div>
                                                            </div>

                                                            {/* Execution Result */}
                                                            {executionResult && executionResult.incident_id === incidentAnalysis.incident_id && (
                                                                <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                                                                    <div className="flex items-center gap-2 mb-2">
                                                                        <Icon 
                                                                            icon={executionResult.success ? "mdi:check-circle" : "mdi:alert-circle"} 
                                                                            className={executionResult.success ? "text-green-500" : "text-red-500"}
                                                                        />
                                                                        <span className="font-semibold">
                                                                            {executionResult.success ? "Execution Successful" : "Execution Failed"}
                                                                        </span>
                                                                        <span className="text-xs text-gray-500">
                                                                            ({executionResult.execution_time_ms}ms)
                                                                        </span>
                                                                    </div>
                                                                    
                                                                    {executionResult.execution_result?.output && (
                                                                        <div className="mt-2">
                                                                            <p className="text-xs font-semibold text-gray-600 mb-1">Output:</p>
                                                                            <Code className="text-xs max-h-32 overflow-y-auto block w-full">
                                                                                {executionResult.execution_result.output}
                                                                            </Code>
                                                                        </div>
                                                                    )}
                                                                    
                                                                    {executionResult.execution_result?.error && (
                                                                        <div className="mt-2">
                                                                            <p className="text-xs font-semibold text-red-600 mb-1">Error:</p>
                                                                            <Code className="text-xs text-red-700">
                                                                                {executionResult.execution_result.error}
                                                                            </Code>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </AccordionItem>
                                                );
                                            })}
                                        </Accordion>
                                    </CardBody>
                                </Card>

                                {/* General Recommendations */}
                                <Card>
                                    <CardHeader>
                                        <h4 className="text-lg font-semibold flex items-center gap-2">
                                            <Icon icon="mdi:shield-check" className="text-blue-500" />
                                            Prevention & Best Practices
                                        </h4>
                                    </CardHeader>
                                    <CardBody>
                                        <div className="space-y-3">
                                            {incidentAnalysis.solution.recommendations.map((recommendation, index) => (
                                                <div key={index} className="flex items-start gap-3">
                                                    <Icon icon="mdi:check-circle" className="text-green-500 mt-1 flex-shrink-0" />
                                                    <p className="text-sm">{recommendation}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </CardBody>
                                </Card>

                                {/* Execution History for this Incident */}
                                {executionHistory.length > 0 && (
                                    <Card>
                                        <CardHeader>
                                            <h4 className="text-lg font-semibold flex items-center gap-2">
                                                <Icon icon="mdi:history" className="text-purple-500" />
                                                Execution History
                                            </h4>
                                        </CardHeader>
                                        <CardBody>
                                            <div className="space-y-2">
                                                {executionHistory.map((record) => (
                                                    <div key={record.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                                                        <div className="flex items-center gap-3">
                                                            <Chip size="sm" color={getStatusColor(record.status) as any} variant="flat">
                                                                {record.status}
                                                            </Chip>
                                                            <Code className="text-xs">{record.command}</Code>
                                                        </div>
                                                        <div className="text-xs text-gray-500">
                                                            {new Date(record.executed_at).toLocaleTimeString()} ({record.execution_time_ms}ms)
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </CardBody>
                                    </Card>
                                )}
                            </div>
                        )}
                    </ModalBody>
                    <ModalFooter>
                        <Button color="danger" variant="light" onPress={onAnalysisClose}>
                            Close
                        </Button>
                        <Button 
                            color="warning" 
                            variant="flat"
                            onPress={() => {
                                if (selectedIncident) {
                                    fetchExecutionHistory(selectedIncident.id);
                                }
                            }}
                            startContent={<Icon icon="mdi:history" />}
                        >
                            View History
                        </Button>
                        <Button 
                            color="success"
                            onPress={() => {
                                // Mark as resolved logic here
                                onAnalysisClose();
                            }}
                            startContent={<Icon icon="mdi:check" />}
                        >
                            Mark as Resolved
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>

            {/* Executor Management Modal */}
            <Modal
                isOpen={isExecutorOpen}
                onClose={onExecutorClose}
                size="2xl"
            >
                <ModalContent>
                    <ModalHeader>
                        <div className="flex items-center gap-2">
                        <Icon icon="mdi:cog" className="text-2xl" />
                            <span>Executor Management</span>
                        </div>
                    </ModalHeader>
                    <ModalBody>
                        <div className="space-y-4">
                            <div className="bg-blue-50 p-4 rounded-lg">
                                <div className="flex items-center gap-2 mb-2">
                                    <Icon icon="mdi:information" className="text-blue-500" />
                                    <span className="font-semibold text-blue-800">Executor Information</span>
                                </div>
                                <p className="text-sm text-blue-700">
                                    Executors are responsible for running commands in your Kubernetes cluster. 
                                    Enable or disable executors based on your infrastructure setup.
                                </p>
                            </div>

                            <div className="space-y-3">
                                {executorStatuses.map((executor) => (
                                    <Card key={executor.name} className="p-4">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                                                    <Icon 
                                                        icon={
                                                            executor.name === 'kubectl' ? 'mdi:kubernetes' :
                                                            executor.name === 'crossplane' ? 'mdi:cloud' :
                                                            'mdi:git'
                                                        } 
                                                        className="text-2xl text-primary"
                                                    />
                                                </div>
                                                <div>
                                                    <h4 className="font-semibold capitalize">{executor.name}</h4>
                                                    <p className="text-sm text-gray-600">
                                                        {executor.name === 'kubectl' && 'Native Kubernetes command-line tool'}
                                                        {executor.name === 'crossplane' && 'Cloud infrastructure management'}
                                                        {executor.name === 'argocd' && 'GitOps continuous delivery'}
                                                    </p>
                                                    <p className="text-xs text-gray-500">
                                                        Last updated: {new Date(executor.updated_at).toLocaleString()}
                                                    </p>
                                                </div>
                                            </div>
                                            
                                            <div className="flex items-center gap-3">
                                                <Chip 
                                                    color={executor.status === 0 ? 'success' : 'default'}
                                                    variant="flat"
                                                >
                                                    {executor.status_text}
                                                </Chip>
                                                <Switch
                                                    isSelected={executor.status === 0}
                                                    onValueChange={(isSelected) => 
                                                        updateExecutorStatus(executor.name, isSelected ? 0 : 1)
                                                    }
                                                    color="success"
                                                />
                                            </div>
                                        </div>
                                    </Card>
                                ))}
                            </div>

                            <div className="bg-yellow-50 p-4 rounded-lg">
                                <div className="flex items-center gap-2 mb-2">
                                    <Icon icon="mdi:alert" className="text-yellow-600" />
                                    <span className="font-semibold text-yellow-800">Important Notes</span>
                                </div>
                                <ul className="text-sm text-yellow-700 space-y-1">
                                    <li>• At least one executor should be active for command execution</li>
                                    <li>• kubectl is the primary executor for most Kubernetes operations</li>
                                    <li>• Disable executors that are not available in your environment</li>
                                    <li>• Changes take effect immediately for new operations</li>
                                </ul>
                            </div>
                        </div>
                    </ModalBody>
                    <ModalFooter>
                        <Button color="danger" variant="light" onPress={onExecutorClose}>
                            Close
                        </Button>
                        <Button color="primary" onPress={fetchExecutorStatuses}>
                            <Icon icon="mdi:refresh" />
                            Refresh Status
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>

            {/* Keyboard Help Modal */}
            <Modal
                isOpen={showKeyboardHelp}
                onClose={() => setShowKeyboardHelp(false)}
                size="lg"
            >
                <ModalContent>
                    <ModalHeader>
                        <div className="flex items-center gap-2">
                            <Icon icon="mdi:keyboard" className="text-2xl" />
                            <span>Keyboard Shortcuts</span>
                        </div>
                    </ModalHeader>
                    <ModalBody>
                        <div className="space-y-4">
                            {[
                                { keys: ['Cmd/Ctrl', 'R'], description: 'Refresh incidents data' },
                                { keys: ['Cmd/Ctrl', 'E'], description: 'Open executor management' },
                                { keys: ['Cmd/Ctrl', 'S'], description: 'Open remediation stats' },
                                { keys: ['Cmd/Ctrl', 'F'], description: 'Focus search input' },
                                { keys: ['Cmd/Ctrl', '/'], description: 'Show this help' },
                                { keys: ['Esc'], description: 'Close modals' }
                            ].map((shortcut, index) => (
                                <div key={index} className="flex items-center justify-between">
                                    <span className="text-sm">{shortcut.description}</span>
                                    <div className="flex gap-1">
                                        {shortcut.keys.map((key, keyIndex) => (
                                            <Kbd key={keyIndex} className="text-xs">
                                                {key}
                                            </Kbd>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </ModalBody>
                    <ModalFooter>
                        <Button color="primary" onPress={() => setShowKeyboardHelp(false)}>
                            Got it
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>

            {/* Floating Action Button */}
            <div className="fixed bottom-6 right-6 flex flex-col gap-3">
                <Tooltip content="Keyboard shortcuts (Cmd/Ctrl + /)">
                    <Button
                        isIconOnly
                        color="secondary"
                        variant="shadow"
                        onPress={() => setShowKeyboardHelp(true)}
                        className="w-12 h-12"
                    >
                        <Icon icon="mdi:keyboard" className="text-xl" />
                    </Button>
                </Tooltip>
                
                <Tooltip content="Refresh all data (Cmd/Ctrl + R)">
                    <Button
                        isIconOnly
                        color="primary"
                        variant="shadow"
                        onPress={() => {
                            fetchIncidents();
                            fetchExecutorStatuses();
                            fetchRemediationHistory();
                            fetchRemediationStats();
                        }}
                        className="w-12 h-12"
                    >
                        <Icon icon="mdi:refresh" className="text-xl" />
                    </Button>
                </Tooltip>
            </div>

            {/* Error Toast */}
            {error && (
                <div className="fixed top-4 right-4 z-50">
                    <Card className="bg-red-50 border-red-200 max-w-md">
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
                </div>
            )}

            {/* Loading Overlay */}
            {(analyzing || executing) && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <Card className="p-6">
                        <CardBody className="flex flex-col items-center gap-4">
                            <Spinner size="lg" color="primary" />
                            <div className="text-center">
                                <p className="font-semibold">
                                    {analyzing && 'AI is analyzing the incident...'}
                                    {executing && 'Executing command...'}
                                </p>
                                <p className="text-sm text-gray-600 mt-1">
                                    {analyzing && 'This may take a few moments'}
                                    {executing && 'Please wait for the operation to complete'}
                                </p>
                            </div>
                        </CardBody>
                    </Card>
                </div>
            )}
        </div>
    );
};

export default RecommendationsPage;


        
    
