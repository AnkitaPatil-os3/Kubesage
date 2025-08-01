import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  // Add this line
  AlertTriangle,
  CheckCircle,
  BoltIcon,
  Clock,
  Play,
  RefreshCw,
  Settings,
  Activity,
  Zap,
  Shield,
  Server,
  Database,
  Network,
  AlertCircle,
  Eye,
  Filter,
  Search,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Cpu,
  Memory,
  HardDrive,
  Globe,
  GitBranch,
  Terminal,
  Layers,
  Target,
  TrendingUp,
  Calendar,
  User,
  Hash,
  Tag,
  MapPin,
  Info,
  Loader2,
  X,
  Check,
  Lightbulb,
  FileText,


} from 'lucide-react';

// Types
interface Incident {
  id: number;
  incident_id: string;
  type: 'Warning' | 'Normal';
  reason: string;
  message: string;
  metadata_namespace: string;
  metadata_creation_timestamp: string;
  involved_object_kind: string;
  involved_object_name: string;
  source_component: string;
  source_host: string;
  reporting_component: string;
  count: number;
  first_timestamp: string;
  last_timestamp: string;
  involved_object_labels: Record<string, string> | null;
  involved_object_annotations: Record<string, string> | null;
  is_resolved: boolean;
  resolution_attempts: number;
  last_resolution_attempt: string;
  executor_id: number | null;
  created_at: string;
  updated_at: string;
}

interface Executor {
  id: number;
  name: 'kubectl' | 'argocd' | 'crossplane';
  status: 'active' | 'inactive';
  description: string;
  config: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

interface RemediationSolution {
  solution_summary: string;
  detailed_solution: string;
  remediation_steps: Array<{
    step_id: number;
    action_type: string;
    description: string;
    command: string;
    expected_outcome: string;
    critical: boolean;
    timeout_seconds: number;
  }>;
  confidence_score: number;
  estimated_time_mins: number;
  additional_notes: string;
  executor_type: string;
  commands: string[];
}


interface RemediationResponse {
  incident_id: number;
  incident_reason?: string; // Add this line

  solution: RemediationSolution;
  execution_status: 'generated' | 'executing' | 'completed_successfully' | 'partially_completed' | 'failed';
  execution_results: any;
  timestamp: string;
}


interface HealthStatus {
  status: string;
  database: string;
  llm_service: string;
  active_executor: string | null;
  timestamp: string;
}

interface RemediationsProps {
  selectedCluster: string;
}

export const Remediations: React.FC<RemediationsProps> = ({ selectedCluster }) => {
  // State
  const [executionModal, setExecutionModal] = useState(false);
  const [executionResults, setExecutionResults] = useState<any>(null);
  const [showSolutionModal, setShowSolutionModal] = useState(false);
  // Add this line with other state variables near the top of the component
  const [commandOutputs, setCommandOutputs] = useState<Record<string, any>>({});



  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [executors, setExecutors] = useState<Executor[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [remediationSolution, setRemediationSolution] = useState<RemediationResponse | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingRemediation, setGeneratingRemediation] = useState<number | null>(null); // Changed from boolean to number | null
  const [executingRemediation, setExecutingRemediation] = useState(false);
  const [activeTab, setActiveTab] = useState<'incidents' | 'executors' | 'health'>('incidents');
  // const [hasExecuted, setHasExecuted] = useState(false);

  const [filters, setFilters] = useState({
    type: '',
    namespace: '',
    resolved: '',
    search: ''
  });
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 5,
    total: 0
  });
  const [expandedIncident, setExpandedIncident] = useState<number | null>(null);
  const [showRemediationModal, setShowRemediationModal] = useState(false);

  // API Base URL
  const API_BASE = 'https://10.0.2.30:8004/remediation';

  // Fetch data functions
const fetchIncidents = async () => {
  try {
    const params = new URLSearchParams({
      page: pagination.page.toString(),
      per_page: pagination.per_page.toString(),
    });

    // Add filters only if they have values
    if (filters.type) {
      params.append('incident_type', filters.type);
    }
    if (filters.namespace) {
      params.append('namespace', filters.namespace);
    }
    if (filters.resolved) {
      params.append('resolved', filters.resolved);
    }

    const response = await fetch(`${API_BASE}/incidents?${params}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        'X-API-Key': localStorage.getItem('access_token') // ADD THIS LINE
      }
    });
    const data = await response.json();

    if (response.ok) {
      setIncidents(data.incidents || []);
      setPagination(prev => ({ ...prev, total: data.total || 0 }));
    }
  } catch (error) {
    console.error('Error fetching incidents:', error);
  }
};


  const fetchExecutors = async () => {
    try {
      const response = await fetch(`${API_BASE}/executors`);
      const data = await response.json();

      if (response.ok) {
        setExecutors(data.executors || []);
      }
    } catch (error) {
      console.error('Error fetching executors:', error);
    }
  };

  const fetchHealthStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/health`);
      const data = await response.json();
      setHealthStatus(data);
    } catch (error) {
      console.error('Error fetching health status:', error);
    }
  };

  const initializeExecutors = async () => {
    try {
      const response = await fetch(`${API_BASE}/initialize`, {
        method: 'POST'
      });

      if (response.ok) {
        await fetchExecutors();
      }
    } catch (error) {
      console.error('Error initializing executors:', error);
    }
  };

  const activateExecutor = async (executorId: number) => {
    try {
      const response = await fetch(`${API_BASE}/executors/${executorId}/activate`, {
        method: 'POST'
      });

      if (response.ok) {
        await fetchExecutors();
        await fetchHealthStatus();
      }
    } catch (error) {
      console.error('Error activating executor:', error);
    }
  };

  // MODIFY the generateRemediation function (replace the existing one)
  const generateRemediation = async (incidentId: number, executeDirectly: boolean = false) => {
    setGeneratingRemediation(incidentId); // Set to specific incident ID
    try {
      let endpoint;
      let method;

      if (executeDirectly) {
        // Direct execution - single API call
        endpoint = `https://10.0.2.30:8004/remediation/incidents/${incidentId}/remediate?execute=true`;
        method = 'POST';
      } else {
        // Just generate solution
        endpoint = `https://10.0.2.30:8004/remediation/incidents/${incidentId}/remediate`;
        method = 'POST';
      }

      const response = await fetch(endpoint, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          incident_id: incidentId
        }),
        // Add timeout and signal handling
        signal: AbortSignal.timeout(120000) // 2 minutes timeout
      });

      if (response.ok) {
        const result = await response.json();

        // Add incident reason to the response
        const incident = incidents.find(inc => inc.id === incidentId);
        result.incident_reason = incident?.reason || 'Unknown Reason';

        if (executeDirectly) {
          // Show execution results in modal
          setExecutionResults(result);
          setExecutionModal(true);
        } else {
          // Just show the solution
          setRemediationSolution(result);
          setShowSolutionModal(true); // CHANGE: Use setShowSolutionModal instead of setShowRemediationModal
        }
      } else {
        const errorText = await response.text();
        console.error('Failed to process remediation:', errorText);
        showToast(`Failed to generate remediation: ${response.status}`, 'error');
      }
    } catch (error) {
      console.error('Error:', error);
      if (error.name === 'TimeoutError') {
        showToast('Request timed out. The AI service may be slow. Please try again.', 'error');
      } else if (error.name === 'AbortError') {
        showToast('Request was cancelled due to timeout.', 'error');
      } else {
        showToast('Network error. Please check your connection and try again.', 'error');
      }
    } finally {
      setGeneratingRemediation(null); // Reset to null
    }
  };


  const executeRemediationSteps = async (incidentId: number) => {
    setExecutingRemediation(true);
    // setHasExecuted(true); // ADD THIS LINE
    try {
      const response = await fetch(`https://10.0.2.30:8004/remediation/incidents/${incidentId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          remediation_steps: remediationSolution.solution.remediation_steps
        })
      });

      if (response.ok) {
        const result = await response.json();
        setRemediationSolution(prev => ({
          ...prev,
          execution_results: result.results
        }));
      } else {
        const errorText = await response.text();
        console.error('Failed to execute remediation steps:', errorText);
      }
    } catch (error) {
      console.error('Error executing steps:', error);
    } finally {
      setExecutingRemediation(false);
    }
  };

  // Effects
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchIncidents(),
        fetchExecutors(),
        fetchHealthStatus()
      ]);
      setLoading(false);
    };

    loadData();
  }, [pagination.page, filters.type, filters.namespace, filters.resolved]);

  // Filter incidents based on search
  const filteredIncidents = incidents.filter(incident => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      const matchesSearch = (
        incident.reason.toLowerCase().includes(searchLower) ||
        incident.message.toLowerCase().includes(searchLower) ||
        incident.involved_object_name.toLowerCase().includes(searchLower) ||
        incident.metadata_namespace.toLowerCase().includes(searchLower) ||
        incident.involved_object_kind.toLowerCase().includes(searchLower) ||
        incident.source_component?.toLowerCase().includes(searchLower) ||
        incident.reporting_component?.toLowerCase().includes(searchLower)
      );
      if (!matchesSearch) return false;
    }

    return true;
  });

  // Helper functions
  const getIncidentIcon = (type: string, isResolved: boolean) => {
    if (isResolved) return <CheckCircle className="w-5 h-5 text-green-500" />;
    return type === 'Warning' ?
      <AlertTriangle className="w-5 h-5 text-amber-500" /> :
      <Info className="w-5 h-5 text-green-500" />;
  };

  const getExecutorIcon = (name: string) => {
    switch (name) {
      case 'kubectl': return <Terminal className="w-5 h-5" />;
      case 'argocd': return <GitBranch className="w-5 h-5" />;
      case 'crossplane': return <Layers className="w-5 h-5" />;
      default: return <Settings className="w-5 h-5" />;
    }
  };
  const getUniqueNamespaces = () => {
    const namespaces = [...new Set(incidents.map(incident => incident.metadata_namespace).filter(Boolean))];
    return namespaces.sort();
  };
  const clearAllFilters = () => {
    setFilters({
      type: '',
      namespace: '',
      resolved: '',
      search: ''
    });
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'low': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-amber-600 bg-amber-100';
      case 'high': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const [commandStatus, setCommandStatus] = useState<Record<string, string>>({});

  // Add this function near the top with other utility functions
  const showToast = (message: string, type: 'success' | 'error' | 'warning' = 'success') => {
    // Simple toast implementation - you can replace with a proper toast library
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${type === 'success' ? 'bg-green-500' :
      type === 'error' ? 'bg-red-500' : 'bg-yellow-500'
      } text-white`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
      if (document.body.contains(toast)) {
        document.body.removeChild(toast);
      }
    }, 3000);
  };

  // Update the copy function
  const copyToClipboard = async (command: string, stepId: number) => {
    try {
      await navigator.clipboard.writeText(command);
      setCommandStatus(prev => ({ ...prev, [`${stepId}`]: 'copy' }));
      showToast('Command copied to clipboard', 'success');

      // Reset status after 2 seconds
      setTimeout(() => {
        setCommandStatus(prev => ({ ...prev, [`${stepId}`]: '' }));
      }, 2000);
    } catch (error) {
      showToast('Failed to copy command', 'error');
    }
  };

  const executeCommand = async (command: string, stepId: number) => {
    try {
      setCommandStatus(prev => ({ ...prev, [`${stepId}`]: 'execute' }));

      // Find the incident ID from the current remediation solution
      const incidentId = remediationSolution?.incident_id;
      if (!incidentId) {
        throw new Error('No incident ID found');
      }

      // Execute the command via the correct API endpoint
      const response = await fetch(`${API_BASE}/incidents/${incidentId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          remediation_steps: [{
            step_id: stepId,
            action_type: "REMEDIATION",
            description: `Execute command: ${command}`,
            command: command,
            expected_outcome: "Command executed successfully",
            critical: false,
            timeout_seconds: 300
          }]
        })
      });

      if (response.ok) {
        const result = await response.json();

        // Store the command output
        setCommandOutputs(prev => ({
          ...prev,
          [`${stepId}`]: {
            success: result.successful_steps > 0,
            output: result.results?.[0]?.output || 'Command executed successfully',
            error: result.results?.[0]?.error || null,
            executed_at: new Date().toISOString()
          }
        }));

        showToast(
          result.successful_steps > 0 ? 'Command executed successfully' : 'Command execution failed',
          result.successful_steps > 0 ? 'success' : 'error'
        );
      } else {
        const errorData = await response.json();
        console.error('API Error:', errorData);
        throw new Error(errorData.detail || 'Failed to execute command');
      }

      // Reset status after 2 seconds
      setTimeout(() => {
        setCommandStatus(prev => ({ ...prev, [`${stepId}`]: '' }));
      }, 2000);
    } catch (error) {
      console.error('Execute command error:', error);
      showToast('Failed to execute command', 'error');
      setCommandStatus(prev => ({ ...prev, [`${stepId}`]: '' }));
    }
  };



  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.4 } }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex items-center space-x-3">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <span className="text-lg text-gray-600">Loading remediations...</span>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="space-y-6 dark:bg-gray-900 min-h-screen"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="bg-gradient-to-r from-green-500 to-emerald-500 rounded-2xl p-6 text-white dark:from-green-600 dark:to-emerald-600">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Kubernetes Remediations</h1>
            <p className="text-blue-100 dark:text-green-100">AI-powered incident resolutions </p>

            {/* <p className="text-blue-100">AI-powered incident resolution for {selectedCluster}</p> */}
          </div>
          <div className="flex items-center space-x-4">
            <div className="bg-white/20 backdrop-blur-sm rounded-lg p-3 dark:bg-black/20">
              <Shield className="w-8 h-8" />
            </div>
            {healthStatus && (
              <div className={`px-4 py-2 rounded-full text-sm font-medium ${healthStatus.status === 'healthy' ? 'bg-green-500/20 text-green-100  dark:bg-green-400/30 dark:text-green-200 ' : 'bg-red-500/20 text-red-100 dark:bg-red-400/30 dark:text-red-200'
                }`}>
                {healthStatus.status === 'healthy' ? 'System Healthy' : 'System Issues'}
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Navigation Tabs */}
      <motion.div variants={itemVariants} className="bg-white rounded-xl shadow-sm border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
        <div className="flex space-x-1 p-1">
          {[
            { id: 'incidents', label: 'Incidents', icon: AlertTriangle, count: pagination.total },
            { id: 'executors', label: 'Executors', icon: Settings, count: executors.length },
            { id: 'health', label: 'Health', icon: Activity, count: null }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-3 rounded-lg font-medium transition-all ${activeTab === tab.id
                ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-md dark:from-green-600 dark:to-emerald-600'
                : 'text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700'
                }`}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.count !== null && (
                <span className={`px-2 py-1 rounded-full text-xs ${activeTab === tab.id ? 'bg-white/20 dark:bg-black/20' : 'bg-gray-200 text-gray-600 dark:bg-gray-600 dark:text-gray-300'
                  }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Incidents Tab */}
      {activeTab === 'incidents' && (
        <motion.div variants={itemVariants} className="space-y-6">
          {/* Filters */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Filter Incidents</h3>
              <div className="flex items-center space-x-3">
                <button
                  onClick={clearAllFilters}
                  className="text-sm text-gray-500 hover:text-green-600 dark:text-gray-400 dark:hover:text-green-400 "
                >
                  Clear All Filters
                </button>
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
            </div>


            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">Search</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
                  <input
                    type="text"
                    placeholder="Search incidents..."
                    value={filters.search}
                    onChange={(e) => {
                      setFilters(prev => ({ ...prev, search: e.target.value }));
                      // Reset pagination when searching
                      setPagination(prev => ({ ...prev, page: 1 }));
                    }}
                    className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400"
                  />
                  {filters.search && (
                    <button
                      onClick={() => {
                        setFilters(prev => ({ ...prev, search: '' }));
                        setPagination(prev => ({ ...prev, page: 1 }));
                      }}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">Type</label>
                <select
                  value={filters.type}
                  onChange={(e) => {
                    setFilters(prev => ({ ...prev, type: e.target.value }));
                    setPagination(prev => ({ ...prev, page: 1 }));
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                >
                  <option value="">All Types</option>
                  <option value="Warning">Warning</option>
                  <option value="Normal">Normal</option>
                  <option value="Error">Error</option>
                  <option value="Critical">Critical</option>
                  <option value="Info">Info</option>
                  <option value="Debug">Debug</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">Namespace</label>
                <select
                  value={filters.namespace}
                  onChange={(e) => {
                    setFilters(prev => ({ ...prev, namespace: e.target.value }));
                    setPagination(prev => ({ ...prev, page: 1 }));
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                >
                  <option value="">All Namespaces</option>
                  {getUniqueNamespaces().map((namespace) => (
                    <option key={namespace} value={namespace}>
                      {namespace}
                    </option>
                  ))}
                </select>
              </div>


            </div>

            {/* Filter Summary */}
            {(filters.search || filters.type || filters.namespace || filters.resolved) && (
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
                <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-300">
                  <span>Active filters:</span>
                  {filters.search && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200">

                      Search: "{filters.search}"
                      <button
                        onClick={() => setFilters(prev => ({ ...prev, search: '' }))}
                        className="ml-1 text-green-600 hover:text-green-800 dark:text-green-300 dark:hover:text-green-100"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {filters.type && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200">

                      Type: {filters.type}
                      <button
                        onClick={() => setFilters(prev => ({ ...prev, type: '' }))}
                        className="ml-1 text-green-600 hover:text-green-800 dark:text-green-300 dark:hover:text-green-100"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {filters.namespace && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200">

                      Namespace: {filters.namespace}
                      <button
                        onClick={() => setFilters(prev => ({ ...prev, namespace: '' }))}
                        className="ml-1 text-green-600 hover:text-green-800"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {filters.resolved && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200">

                      Status: {filters.resolved === 'true' ? 'Resolved' : 'Unresolved'}
                      <button
                        onClick={() => setFilters(prev => ({ ...prev, resolved: '' }))}
                        className="ml-1 text-green-600 hover:text-green-800 dark:text-green-300 dark:hover:text-green-100"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                </div>
                <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  Showing {filteredIncidents.length} of {incidents.length} incidents
                </div>
              </div>
            )}
          </div>


          {/* Incidents List */}
          <div className="space-y-4">
            {filteredIncidents.length === 0 ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center dark:bg-gray-800 dark:border-gray-700">
                <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4 dark:text-gray-500" />
                <h3 className="text-lg font-medium text-gray-900 mb-2 dark:text-gray-100">No incidents found</h3>
                <p className="text-gray-500  dark:text-gray-400">Try adjusting your filters or check back later.</p>
              </div>
            ) : (
              filteredIncidents.map((incident) => (
                <motion.div
                  key={incident.id}
                  layout
                  className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow dark:bg-gray-800 dark:border-gray-700"
                >
                  <div className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-4 flex-1">
                        <div className="flex-shrink-0">
                          {getIncidentIcon(incident.type, incident.is_resolved)}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-3 mb-2">
                            <h3 className="text-lg font-semibold text-gray-900 truncate dark:text-gray-100">
                              {incident.reason}
                            </h3>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${incident.type === 'Warning' ? 'bg-amber-100 text-amber-800 dark:bg-amber-800 dark:text-amber-200' : 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200'
                              }`}>

                              {incident.type}
                            </span>
                            {incident.is_resolved && (
                              <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                Resolved
                              </span>
                            )}
                          </div>

                          <p className="text-gray-600 mb-3 line-clamp-2 dark:text-gray-300">{incident.message}</p>

                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div className="flex items-center space-x-2">
                              <MapPin className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                              <span className="text-gray-600 dark:text-gray-300">
                                {incident.metadata_namespace || 'default'}
                              </span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Server className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                              <span className="text-gray-600 dark:text-gray-300">
                                {incident.involved_object_kind}
                              </span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Tag className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                              <span className="text-gray-600 dark:text-gray-300">
                                {incident.involved_object_name}
                              </span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Hash className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                              <span className="text-gray-600 dark:text-gray-300">
                                Count: {incident.count}
                              </span>
                            </div>
                          </div>

                          {incident.resolution_attempts > 0 && (
                            <div className="mt-3 flex items-center space-x-2 text-sm text-amber-600">
                              <RefreshCw className="w-4 h-4" />
                              <span>{incident.resolution_attempts} resolution attempts</span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 ml-4">
                        <button
                          onClick={() => setExpandedIncident(
                            expandedIncident === incident.id ? null : incident.id
                          )}
                          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-lg transition-colors dark:bg-gray-800 "
                        >
                          {expandedIncident === incident.id ?
                            <ChevronDown className="w-5 h-5" /> :
                            <ChevronRight className="w-5 h-5" />
                          }
                        </button>

                        {!incident.is_resolved && (
                          <div className="flex flex-col items-end space-y-2">
                            <button
                              onClick={() => generateRemediation(incident.id)}
                              disabled={generatingRemediation !== null}
                              className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-lg hover:from-green-600 hover:to-emerald-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed dark:from-green-600 dark:to-emerald-600 dark:hover:from-green-700 dark:hover:to-emerald-700"
                            >
                              {generatingRemediation === incident.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Zap className="w-4 h-4" />
                              )}
                              <span>Generate Fix</span>
                            </button>
                            {generatingRemediation === incident.id && (
                              <div className="text-xs text-gray-500 animate-pulse dark:text-gray-400">
                                Analyzing... This may take 1-2 minutes
                              </div>
                            )}
                          </div>
                        )}


                      </div>
                    </div>

                    {/* Expanded Details */}
                    <AnimatePresence>
                      {expandedIncident === incident.id && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-600"
                        >
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                              <h4 className="font-medium text-gray-900 mb-3 dark:text-gray-100">Incident Details</h4>
                              <div className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Incident ID:</span>
                                  <span className="font-mono text-gray-900 dark:text-gray-100">{incident.incident_id}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 text-gray-500 dark:text-gray-400">Source Component:</span>
                                  <span className="text-gray-900 dark:text-gray-100">{incident.source_component || 'N/A'}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 text-gray-500 dark:text-gray-400">Source Host:</span>
                                  <span className="text-gray-900 dark:text-gray-100">{incident.source_host || 'N/A'}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Reporting Component:</span>
                                  <span className="text-gray-900 dark:text-gray-100">{incident.reporting_component || 'N/A'}</span>
                                </div>
                              </div>
                            </div>

                            <div>
                              <h4 className="font-medium text-gray-900 mb-3 dark:text-gray-100">Timestamps</h4>
                              <div className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">First Seen:</span>
                                  <span className="text-gray-900 dark:text-gray-100">
                                    {incident.first_timestamp ? formatTimestamp(incident.first_timestamp) : 'N/A'}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Last Seen:</span>
                                  <span className="text-gray-900 dark:text-gray-100">
                                    {incident.last_timestamp ? formatTimestamp(incident.last_timestamp) : 'N/A'}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Created:</span>
                                  <span className="text-gray-900 dark:text-gray-100">{formatTimestamp(incident.created_at)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Updated:</span>
                                  <span className="text-gray-900 dark:text-gray-100">{formatTimestamp(incident.updated_at)}</span>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Labels and Annotations */}
                          {(incident.involved_object_labels || incident.involved_object_annotations) && (
                            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                              {incident.involved_object_labels && (
                                <div>
                                  <h4 className="font-medium text-gray-900 mb-3 dark:text-gray-100">Labels</h4>
                                  <div className="space-y-1">
                                    {Object.entries(incident.involved_object_labels).map(([key, value]) => (
                                      <div key={key} className="flex items-center space-x-2 text-sm">
                                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded font-mono dark:bg-gray-800 dark:text-yellow-300">
                                          {key}
                                        </span>
                                        <span className="text-gray-600 dark:bg-gray-800 dark:text-yellow-300">=</span>
                                        <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded font-mono dark:bg-gray-800 dark:text-yellow-300">
                                          {value}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {incident.involved_object_annotations && (
                                <div>
                                  <h4 className="font-medium text-gray-900 mb-3 dark:text-gray-100">Annotations</h4>
                                  <div className="space-y-1">
                                    {Object.entries(incident.involved_object_annotations).slice(0, 3).map(([key, value]) => (
                                      <div key={key} className="text-sm">
                                        <div className="font-mono text-purple-800 bg-purple-100 px-2 py-1 rounded mb-1 dark:bg-gray-800 dark:text-yellow-300">
                                          {key}
                                        </div>
                                        <div className="text-gray-600 pl-2 truncate dark:text-gray-300">
                                          {typeof value === 'string' ? value : JSON.stringify(value)}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              ))
            )}
          </div>

          {/* Pagination */}
          {pagination.total > pagination.per_page && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 dark:bg-gray-800 dark:border-gray-700">

              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  Showing {((pagination.page - 1) * pagination.per_page) + 1} to{' '}
                  {Math.min(pagination.page * pagination.per_page, pagination.total)} of{' '}
                  {pagination.total} incidents
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
                    disabled={pagination.page <= 1}
                    className="px-3 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700 dark:text-gray-300"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-2 bg-blue-50 text-blue-600 rounded-lg font-medium dark:bg-gray-800">
                    {pagination.page}
                  </span>
                  <button
                    onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                    disabled={pagination.page * pagination.per_page >= pagination.total}
                    className="px-3 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700 dark:text-gray-300"

                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Executors Tab */}
      {activeTab === 'executors' && (
        <motion.div variants={itemVariants} className="space-y-6">
          {/* Executors Header */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2 dark:text-gray-300">Remediation Executors</h2>
                <p className="text-gray-600 dark:text-gray-500">Manage and configure remediation execution engines</p>
              </div>
              <button
                onClick={initializeExecutors}
                className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-lg hover:from-green-600 hover:to-emerald-600 transition-all transform hover:scale-105 hover:shadow-lg active:scale-95 group"
              >
                <Settings className="w-4 h-4 group-hover:rotate-180 transition-transform duration-300" />
                <span className="relative">
                  Initialize Executors
                  <span className="absolute rounded opacity-0 group-hover:opacity-100 group-hover:animate-pulse transition-opacity duration-300"></span>
                </span>
              </button>

            </div>
          </div>

          {/* Executors Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 ">
            {executors.map((executor) => (
              <motion.div
                key={executor.id}
                layout
                className={`bg-white rounded-xl shadow-sm border-2 transition-all hover:shadow-md dark:bg-gray-800 ${executor.status === 'active'
                  ? 'border-green-200 bg-gradient-to-br from-green-50 to-emerald-50 dark:border-green-600 dark:from-green-900/30 dark:to-emerald-900/30'
                  : 'border-gray-200 hover:border-gray-300 dark:border-gray-600 dark:hover:border-gray-500'
                  }`}

              >
                <div className="p-6 ">
                  <div className="flex items-center justify-between mb-4 ">
                    <div className="flex items-center space-x-3">
                      <div className={`p-3 rounded-lg ${executor.status === 'active'
                        ? 'bg-green-100 text-green-600 dark:bg-green-800/50 dark:text-green-400'
                        : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                        }`}>

                        {getExecutorIcon(executor.name)}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 capitalize dark:text-gray-100">{executor.name}</h3>
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${executor.status === 'active'
                          ? 'bg-green-100 text-green-800 dark:bg-green-800/50 dark:text-green-200'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                          }`}>

                          {executor.status}
                        </span>
                      </div>
                    </div>

                    {executor.status !== 'active' && (
                      <button
                        onClick={() => activateExecutor(executor.id)}
                        className="flex items-center space-x-1 px-3 py-1 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors text-sm dark:bg-green-600 dark:hover:bg-green-700"

                      >
                        <Play className="w-3 h-3" />
                        <span>Activate</span>
                      </button>
                    )}
                  </div>

                  <p className="text-gray-600 text-sm mb-4 dark:text-gray-300">{executor.description}</p>

                  {/* Configuration */}
                  {executor.config && (
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">Configuration</h4>
                      <div className="bg-gray-50 rounded-lg p-3  dark:bg-gray-800 dark:border-gray-700 ">
                        <pre className="text-xs text-black-600 overflow-x-auto ">
                          {JSON.stringify(executor.config, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                  <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
                    <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span>Updated: {formatTimestamp(executor.updated_at)}</span>
                      {executor.status === 'active' && (
                        <div className="flex items-center space-x-1 text-green-600 dark:text-green-400">
                          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse dark:bg-green-400"></div>
                          <span>Active</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {executors.length === 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center dark:bg-gray-800 dark:border-gray-700">
              <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4 dark:text-gray-500" />
              <h3 className="text-lg font-medium text-gray-900 mb-2 dark:text-gray-100">No executors configured</h3>
              <p className="text-gray-500 mb-4 dark:text-gray-400">Initialize default executors to get started with remediation.</p>
              <button
                onClick={initializeExecutors}
                className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all mx-auto dark:from-blue-600 dark:to-purple-600 dark:hover:from-blue-700 dark:hover:to-purple-700"

              >
                <Settings className="w-4 h-4" />
                <span>Initialize Executors</span>
              </button>
            </div>
          )}
        </motion.div>
      )}

      {/* Health Tab */}
      {activeTab === 'health' && (
        <motion.div variants={itemVariants} className="space-y-6">
          {healthStatus && (
            <>
              {/* System Status Overview */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 dark:bg-gray-800 dark:border-gray-700">

                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">System Health</h2>
                  <button
                    onClick={fetchHealthStatus}
                    className="flex items-center space-x-2 px-3 py-2 text-gray-600 hover:text-green-600 hover:bg-gray-50 rounded-lg transition-all duration-300 dark:text-gray-300 dark:hover:text-green-400 dark:hover:bg-gray-700 transform hover:scale-105 active:scale-95 group hover:shadow-md"
                  >
                    <RefreshCw className="w-4 h-4 dark:hover:text-green-400 dark:hover:bg-gray-700 dark:text-gray-300 group-hover:rotate-180 transition-transform duration-500 ease-in-out" />
                    <span className="relative overflow-hidden">
                      Refresh
                      <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-out"></span>
                    </span>
                  </button>
                </div>



                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {/* Overall Status */}
                  <div className={`p-4 rounded-xl ${healthStatus.status === 'healthy'
                    ? 'bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 dark:from-green-900/30 dark:to-emerald-900/30 dark:border-green-700'
                    : 'bg-gradient-to-br from-red-50 to-rose-50 border border-red-200 dark:from-red-900/30 dark:to-rose-900/30 dark:border-red-700'
                    }`}>

                    <div className="flex items-center space-x-3">
                      <div className={`p-4 rounded-xl ${healthStatus.status === 'healthy'
                        ? 'bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 dark:from-green-900/30 dark:to-emerald-900/30 dark:border-green-700'
                        : 'bg-gradient-to-br from-red-50 to-rose-50 border border-red-200 dark:from-red-900/30 dark:to-rose-900/30 dark:border-red-700'
                        }`}>

                        {healthStatus.status === 'healthy' ?
                          <CheckCircle className="w-5 h-5" /> :
                          <AlertTriangle className="w-5 h-5" />
                        }
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-300">System Status</p>
                        <p className={`font-semibold capitalize ${healthStatus.status === 'healthy' ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'
                          }`}>

                          {healthStatus.status}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Database Status */}
                  <div className={`p-4 rounded-xl ${healthStatus.database === 'connected'
                    ? 'bg-gradient-to-br from-blue-50 to-cyan-50 border border-blue-200 dark:from-blue-900/30 dark:to-cyan-900/30 dark:border-blue-700'
                    : 'bg-gradient-to-br from-red-50 to-rose-50 border border-red-200 dark:from-red-900/30 dark:to-rose-900/30 dark:border-red-700'
                    }`}>

                    <div className="flex items-center space-x-3">
                      <div className={`p-2 rounded-lg ${healthStatus.database === 'connected' ? 'bg-blue-100 text-blue-600 dark:bg-blue-800/50 dark:text-blue-400' : 'bg-red-100 text-red-600 dark:bg-red-800/50 dark:text-red-400'
                        }`}>

                        <Database className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-300">Database</p>
                        <p className={`font-semibold capitalize ${healthStatus.database === 'connected' ? 'text-blue-800 dark:text-blue-300' : 'text-red-800 dark:text-red-300'
                          }`}>

                          {healthStatus.database}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* LLM Service Status */}
                  <div className={`p-4 rounded-xl ${healthStatus.llm_service === 'enabled'
                    ? 'bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-200 dark:from-purple-900/30 dark:to-indigo-900/30 dark:border-purple-700'
                    : 'bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 dark:from-amber-900/30 dark:to-orange-900/30 dark:border-amber-700'
                    }`}>

                    <div className="flex items-center space-x-3">
                      <div className={`p-2 rounded-lg ${healthStatus.llm_service === 'enabled' ? 'bg-purple-100 text-purple-600 dark:bg-purple-800/50 dark:text-purple-400' : 'bg-amber-100 text-amber-600 dark:bg-amber-800/50 dark:text-amber-400'
                        }`}>

                        <Zap className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-300">LLM Service</p>
                        <p className={`font-semibold capitalize ${healthStatus.llm_service === 'enabled' ? 'text-purple-800 dark:text-purple-300' : 'text-amber-800 dark:text-amber-300'
                          }`}>

                          {healthStatus.llm_service}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Active Executor */}
                  <div className="p-4 rounded-xl bg-gradient-to-br from-gray-50 to-slate-50 border border-gray-200 dark:from-gray-800/50 dark:to-slate-800/50 dark:border-gray-600">

                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-lg bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                        <Target className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-300">Active Executor</p>
                        <p className="font-semibold text-gray-800 capitalize dark:text-gray-200">
                          {healthStatus.active_executor || 'None'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-600">
                  <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
                    <span>Last updated: {formatTimestamp(healthStatus.timestamp)}</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse dark:bg-green-400"></div>
                      <span>Live monitoring</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* System Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 dark:bg-gray-800 dark:border-gray-700">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 dark:text-gray-300">Service Components</h3>
                  <div className="space-y-4">
                    {[
                      { name: 'Remediation Service', status: 'running', icon: Shield, color: 'green' },
                      { name: 'Incident Processor', status: 'running', icon: Activity, color: 'blue' },
                      { name: 'LLM Integration', status: healthStatus.llm_service === 'enabled' ? 'running' : 'disabled', icon: Zap, color: healthStatus.llm_service === 'enabled' ? 'purple' : 'amber' },
                      { name: 'Database Connection', status: healthStatus.database === 'connected' ? 'running' : 'error', icon: Database, color: healthStatus.database === 'connected' ? 'blue' : 'red' }
                    ].map((component) => (
                      <div key={component.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg dark:bg-gray-700">

                        <div className="flex items-center space-x-3">
                          <div className={`p-2 rounded-lg bg-${component.color}-100 text-${component.color}-600`}>
                            <component.icon className="w-4 h-4" />
                          </div>
                          <span className="font-medium text-gray-900 dark:text-gray-100">{component.name}</span>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${component.status === 'running' ? 'bg-green-100 text-green-800' :
                          component.status === 'disabled' ? 'bg-amber-100 text-amber-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                          {component.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 dark:bg-gray-800 dark:border-gray-700">

                  <h3 className="text-lg font-semibold text-gray-900 mb-4 dark:text-gray-100">Quick Stats</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg dark:bg-blue-900/30">
                      <div className="flex items-center space-x-3">
                        <AlertTriangle className="w-5 h-5 text-blue-600" />
                        <span className="font-medium text-gray-900 dark:text-gray-100">Total Incidents</span>
                      </div>
                      <span className="text-xl font-bold text-blue-600 dark:text-blue-400">{pagination.total}</span>
                    </div>
                    {/* <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <CheckCircle className="w-5 h-5 text-green-600" />
                        <span className="font-medium text-gray-900">Resolved</span>
                      </div>
                      <span className="text-xl font-bold text-green-600">
                        {incidents.filter(i => i.is_resolved).length}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-amber-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <Clock className="w-5 h-5 text-amber-600" />
                        <span className="font-medium text-gray-900">Pending</span>
                      </div>
                      <span className="text-xl font-bold text-amber-600">
                        {incidents.filter(i => !i.is_resolved).length}
                      </span>
                    </div> */}

                    <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg dark:bg-purple-900/30">
                      <div className="flex items-center space-x-3">
                        <Settings className="w-5 h-5 text-purple-600" />
                        <span className="font-medium text-gray-900 dark:text-gray-100">Active Executors</span>
                      </div>
                      <span className="text-xl font-bold text-purple-600 dark:text-purple-400">
                        {executors.filter(e => e.status === 'active').length}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </motion.div>
      )}


      {/* Remediation Solution Modal */}
      <AnimatePresence>
        {showSolutionModal && remediationSolution && ( // CHANGE: Use showSolutionModal instead of showRemediationModal
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 dark:bg-black dark:bg-opacity-70"
            onClick={() => setShowSolutionModal(false)} // CHANGE: Use setShowSolutionModal
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden dark:bg-gray-800"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="bg-gradient-to-r  from-green-500 to-emerald-500 p-6 text-white">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-white/20 rounded-lg">
                      <BoltIcon className="w-6 h-6" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold">AI Remediation Solution</h2>
                      <p className="text-green-100">Reason: {remediationSolution.incident_reason}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => setShowSolutionModal(false)}
                    className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

              </div>


              {/* Modal Body */}
              <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
                <div className="space-y-6">
                  {/* Confidence and Metadata */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-green-50 p-4 rounded-lg text-center dark:bg-green-900/20">
                      <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                        {Math.round(remediationSolution.solution.confidence_score * 100)}%
                      </div>
                      <div className="text-green-700 text-sm dark:text-green-300">Confidence</div>
                    </div>
                    <div className="bg-blue-50 p-4 rounded-lg text-center dark:bg-blue-900/20">
                      <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                        {remediationSolution.solution.estimated_time_mins}m
                      </div>
                      <div className="text-blue-700 text-sm dark:text-blue-300">Est. Time</div>
                    </div>
                    <div className="bg-purple-50 p-4 rounded-lg text-center dark:bg-purple-900/20">
                      <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                        {remediationSolution.solution.executor_type}
                      </div>
                      <div className="text-purple-700 text-sm dark:text-purple-300">Executor</div>
                    </div>
                  </div>
                  {/* Solution Summary */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-xl border border-blue-200 dark:from-blue-900/20 dark:to-indigo-900/20 dark:border-blue-700">
                    <h3 className="font-semibold text-blue-900 mb-2 flex items-center dark:text-blue-100">
                      <Lightbulb className="w-5 h-5 mr-2" />
                      Solution Summary
                    </h3>
                    <p className="text-blue-800 dark:text-blue-200">{remediationSolution.solution.solution_summary}</p>
                  </div>

                  {/* Detailed Solution */}
                  <div className="bg-gray-50 p-4 rounded-xl dark:bg-gray-700">
                    <h3 className="font-semibold text-gray-900 mb-2 flex items-center dark:text-gray-100">
                      <FileText className="w-5 h-5 mr-2" />
                      Detailed Analysis
                    </h3>
                    <p className="text-gray-700 whitespace-pre-wrap dark:text-gray-300">{remediationSolution.solution.detailed_solution}</p>
                  </div>

                  {/* Remediation Steps */}
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 dark:text-gray-100">Remediation Steps</h3>
                    <div className="space-y-4">
                      {remediationSolution.solution.remediation_steps.map((step, index) => (
                        <div key={index} className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-shadow dark:bg-gray-700 dark:border-gray-600">
                          <div className="flex items-start space-x-4">
                            <div className="flex-shrink-0">
                              <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-full flex items-center justify-center font-semibold text-sm">
                                {step.step_id}
                              </div>
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-2">
                                <h4 className="font-medium text-gray-900 dark:text-gray-100">{step.action_type}</h4>
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${step.critical ? 'text-red-600 bg-red-100' : 'text-green-600 bg-green-100'
                                  }`}>
                                  {step.critical ? 'Critical' : 'Safe'}
                                </span>
                              </div>
                              <p className="text-gray-600 text-sm mb-3 dark:text-gray-300">{step.description}</p>
                                                           <div className="bg-gray-900 rounded-lg p-3 relative group dark:bg-gray-800">
                                <div className="pr-20"> {/* Add padding for buttons */}
                                  <pre className="text-green-400 text-sm font-mono whitespace-pre-wrap break-words overflow-x-auto max-w-full">
                                    {step.command}
                                  </pre>
                                </div>
                                <div className="absolute top-2 right-2 flex space-x-2">
                                  <button
                                    onClick={() => copyToClipboard(step.command, step.step_id)}
                                    className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 hover:text-white transition-colors border border-gray-600 dark:bg-gray-600 dark:hover:bg-gray-500 dark:border-gray-500"
                                  >
                                    {commandStatus[`${step.step_id}`] === 'copy' ? (
                                      <CheckCircle className="w-4 h-4 text-green-400" />
                                    ) : (
                                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                      </svg>
                                    )}
                                  </button>
                                  <button
                                    onClick={() => executeCommand(step.command, step.step_id)}
                                    className="p-1.5 bg-green-600 hover:bg-green-500 rounded text-white transition-colors border border-green-500 dark:bg-green-700 dark:hover:bg-green-600 dark:border-green-600"
                                  >
                                    {commandStatus[`${step.step_id}`] === 'execute' ? (
                                      <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                      <Terminal className="w-4 h-4" />
                                    )}
                                  </button>
                                </div>
                              </div>


                              {/* Command Output Section */}
                              {commandOutputs[`${step.step_id}`] && (
                                <div className="mt-3 bg-gray-50 rounded-lg p-3 dark:bg-gray-700">
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                      Command Output
                                    </span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${commandOutputs[`${step.step_id}`].success
                                      ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200'
                                      : 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-200'
                                      }`}>
                                      {commandOutputs[`${step.step_id}`].success ? 'Success' : 'Failed'}
                                    </span>
                                  </div>

                                  {/* Output */}
                                  {commandOutputs[`${step.step_id}`].output && (
                                    <div className="mb-2">
                                      <div className="text-xs text-gray-600 mb-1 dark:text-gray-400">Output:</div>
                                      <pre className="bg-gray-900 text-green-400 p-2 rounded text-xs overflow-x-auto max-h-32 dark:bg-gray-800">
                                        {commandOutputs[`${step.step_id}`].output}
                                      </pre>
                                    </div>
                                  )}

                                  {/* Error */}
                                  {commandOutputs[`${step.step_id}`].error && (
                                    <div className="mb-2">
                                      <div className="text-xs text-red-600 mb-1 dark:text-red-400">Error:</div>
                                      <pre className="bg-red-100 text-red-800 p-2 rounded text-xs overflow-x-auto max-h-32 dark:bg-red-900/30 dark:text-red-300">
                                        {commandOutputs[`${step.step_id}`].error}
                                      </pre>
                                    </div>
                                  )}

                                  <div className="text-xs text-gray-500 dark:text-gray-400">
                                    Executed at: {new Date(commandOutputs[`${step.step_id}`].executed_at).toLocaleString()}
                                  </div>
                                </div>
                              )}

                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>




                  {/* Additional Notes */}
                  {remediationSolution.solution.additional_notes && (
                    <div className="bg-yellow-50 p-4 rounded-xl border border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-700">
                      <h3 className="font-semibold text-yellow-900 mb-2 flex items-center dark:text-yellow-100">
                        <AlertTriangle className="w-5 h-5 mr-2" />
                        Important Notes
                      </h3>
                      <p className="text-yellow-800 dark:text-yellow-200">{remediationSolution.solution.additional_notes}</p>
                    </div>
                  )}
                  {/* Execution Results - ADD THIS SECTION */}
                  {remediationSolution.execution_results && (
                    <div className="bg-gray-50 p-4 rounded-xl dark:bg-gray-700">
                      <h3 className="font-semibold text-gray-900 mb-4 flex items-center dark:text-gray-100">
                        <Settings className="w-5 h-5 mr-2" />
                        Execution Results
                      </h3>
                      <div className="space-y-3">
                        {remediationSolution.execution_results.map((result: any, index: number) => (
                          <div key={index} className={`p-3 rounded-lg border-l-4 ${result.success
                            ? 'border-green-500 bg-green-50 dark:bg-green-900/20 dark:border-green-400'
                            : 'border-red-500 bg-red-50 dark:bg-red-900/20 dark:border-red-400'
                            }`}>
                            <div className="flex items-center space-x-2 mb-2">
                              {result.success ? (
                                <div className="w-5 h-5 bg-green-500 text-white rounded-full flex items-center justify-center text-xs font-medium dark:bg-green-400">
                                  ✓
                                </div>
                              ) : (
                                <div className="w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center text-xs font-medium dark:bg-red-400">
                                  ✗
                                </div>
                              )}
                              <span className="font-medium text-sm text-gray-900 dark:text-gray-100">
                                Step {index + 1}: {result.description || result.command}
                              </span>
                            </div>

                            {/* Command */}
                            <div className="mb-2">
                              <div className="text-xs text-gray-600 mb-1 dark:text-gray-400">Command:</div>
                              <div className="bg-gray-900 text-green-400 p-2 rounded font-mono text-xs overflow-x-auto dark:bg-gray-800">
                                {result.command}
                              </div>
                            </div>

                            {/* Output */}
                            {result.output && (
                              <div className="mb-2">
                                <div className="text-xs text-gray-600 mb-1 dark:text-gray-400">Output:</div>
                                <pre className="bg-gray-100 text-gray-800 p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap dark:bg-gray-600 dark:text-gray-200">
                                  {result.output}
                                </pre>
                              </div>
                            )}

                            {/* Error */}
                            {result.error && (
                              <div>
                                <div className="text-xs text-red-600 mb-1 dark:text-red-400">Error:</div>
                                <pre className="bg-red-100 text-red-800 p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap dark:bg-red-900/30 dark:text-red-300">
                                  {result.error}
                                </pre>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Modal Footer */}
              <div className="bg-gray-50 px-6 py-4 flex justify-between items-center dark:bg-gray-700">
                <button
                  onClick={() => setShowSolutionModal(false)} // CHANGE: Use setShowSolutionModal
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors dark:text-gray-400 dark:hover:text-gray-200"
                >
                  Close
                </button>
                <div className="flex space-x-3">
                  <button
                    onClick={() => executeRemediationSteps(remediationSolution.incident_id)}
                    disabled={executingRemediation}  // Remove hasExecuted condition
                    className="flex items-center space-x-2 px-6 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-lg hover:from-green-600 hover:to-emerald-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed dark:from-green-600 dark:to-emerald-600 dark:hover:from-green-700 dark:hover:to-emerald-700"
                  >
                    {executingRemediation ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    <span>Execute Automatically</span>  {/* Always show same text */}
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </motion.div>
  );
};
