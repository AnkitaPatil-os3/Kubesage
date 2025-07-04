import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Chip,
  Progress,
  Select,
  SelectItem,
  Input,
  Tabs,
  Tab,
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
  Badge,
  Tooltip,
  Switch,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  Accordion,
  AccordionItem,
  Code,
  Divider,
} from '@heroui/react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Area,
  AreaChart,
  Legend,
} from 'recharts';
import {
  Shield,
  AlertTriangle,
  AlertCircle,
  Info,
  Search,
  Filter,
  Download,
  RefreshCw,
  Eye,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Clock,
  Server,
  Package,
  Bug,
  CheckCircle,
  XCircle,
  Activity,
  BarChart3,
  PieChart as PieChartIcon,
  List,
  Grid,
  Settings,
  Terminal,
  Copy,
  CheckCheck,
} from 'lucide-react';
import axios from 'axios';

// Types
interface VulnerabilityInfo {
  report_name: string;
  namespace: string;
  vulnerability_id: string;
  title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  score?: number;
  resource: string;
  installed_version: string;
  fixed_version: string;
  primary_link?: string;
}

interface VulnerabilitySummary {
  report_name: string;
  namespace: string;
  container_name?: string;
  image_repository: string;
  image_tag: string;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  total_vulnerabilities: number;
}

interface SecurityMetrics {
  total_reports: number;
  total_vulnerabilities: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  fixable_count: number;
  affected_namespaces: number;
  last_updated: string;
}

interface APIResponse<T> {
  success: boolean;
  message: string;
  data: T;
  timestamp: string;
}

interface FilterOptions {
  severity: string;
  namespace: string;
  fixable_only: boolean;
  search: string;
}

interface HealthStatus {
  status: string;
  kubernetes: string;
  trivy_operator: string;
  service: string;
  version: string;
  timestamp: string;
}

interface InstallationGuide {
  trivy_operator_installation: {
    description: string;
    installation_methods: Array<{
      method: string;
      commands: string[];
    }>;
    verification: string[];
    post_installation: string[];
  };
}

// Constants
const SEVERITY_COLORS = {
  CRITICAL: '#dc2626',
  HIGH: '#ea580c',
  MEDIUM: '#d97706',
  LOW: '#65a30d',
};

const SEVERITY_BG_COLORS = {
  CRITICAL: '#fef2f2',
  HIGH: '#fff7ed',
  MEDIUM: '#fffbeb',
  LOW: '#f7fee7',
};

const API_BASE_URL = 'https://10.0.32.103:8005/api/v1/security';

// Authentication utilities
const getAuthToken = (): string | null => {
  return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
};

const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Create axios instance with authentication
const createAuthenticatedAxios = () => {
  const axiosInstance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
  });

  // Add request interceptor to include auth token
  axiosInstance.interceptors.request.use(
    (config) => {
      const token = getAuthToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Add response interceptor to handle auth errors
  axiosInstance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        // Clear tokens and redirect to login
        localStorage.removeItem('access_token');
        sessionStorage.removeItem('access_token');
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );

  return axiosInstance;
};

export const SecOps: React.FC = () => {
  // State
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [metrics, setMetrics] = useState<SecurityMetrics | null>(null);
  const [vulnerabilities, setVulnerabilities] = useState<VulnerabilityInfo[]>([]);
  const [summaries, setSummaries] = useState<VulnerabilitySummary[]>([]);
  const [namespaces, setNamespaces] = useState<string[]>([]);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [installationGuide, setInstallationGuide] = useState<InstallationGuide | null>(null);
  const [selectedTab, setSelectedTab] = useState('overview');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedCommand, setCopiedCommand] = useState<string | null>(null);

  // Filters
  const [filters, setFilters] = useState<FilterOptions>({
    severity: '',
    namespace: '',
    fixable_only: false,
    search: '',
  });

  // Modals
  const { isOpen: isVulnModalOpen, onOpen: onVulnModalOpen, onClose: onVulnModalClose } = useDisclosure();
  const { isOpen: isSettingsModalOpen, onOpen: onSettingsModalOpen, onClose: onSettingsModalClose } = useDisclosure();
  const { isOpen: isInstallModalOpen, onOpen: onInstallModalOpen, onClose: onInstallModalClose } = useDisclosure();
  const [selectedVulnerability, setSelectedVulnerability] = useState<VulnerabilityInfo | null>(null);

  // Create authenticated axios instance
  const apiClient = useMemo(() => createAuthenticatedAxios(), []);

  // Auto-refresh effect
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchData(true);
      }, 30000); // Refresh every 30 seconds
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  // Initial data fetch
  useEffect(() => {
    // Check if user is authenticated
    const token = getAuthToken();
    if (!token) {
      setError('Authentication required. Please log in.');
      setLoading(false);
      return;
    }
    
    fetchData();
  }, []);

  // Fetch all data
  const fetchData = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      // First check health status
      const healthRes = await apiClient.get('/health');
      setHealthStatus(healthRes.data);

      // If Trivy Operator is not installed, get installation guide
      if (healthRes.data.trivy_operator === 'not_installed') {
        const guideRes = await apiClient.get('/installation-guide');
        setInstallationGuide(guideRes.data.data);
        setError('Operator is not installed. Please install it to view security data.');
        return;
      }

      const [metricsRes, namespacesRes] = await Promise.all([
        apiClient.get('/metrics'),
        apiClient.get('/namespaces'),
      ]);

      setMetrics(metricsRes.data.data);
      setNamespaces(namespacesRes.data.data);

      // Fetch vulnerabilities and summaries based on current filters
      await fetchFilteredData();
    } catch (err: any) {
      console.error('Error fetching data:', err);
      if (err.response?.status === 401) {
        setError('Authentication failed. Please log in again.');
      } else if (err.response?.status === 503) {
        setError('Security service is unavailable. Please try again later.');
      } else {
        setError(err.response?.data?.message || 'Failed to fetch security data');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Fetch filtered data
  const fetchFilteredData = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.severity) params.append('severity', filters.severity);
      if (filters.namespace) params.append('namespace', filters.namespace);
      if (filters.fixable_only) params.append('fixable_only', 'true');

      const [vulnRes, summaryRes] = await Promise.all([
        apiClient.get(`/vulnerabilities?${params}`),
        apiClient.get(`/summary?${params}`),
      ]);

      setVulnerabilities(vulnRes.data.data);
      setSummaries(summaryRes.data.data);
    } catch (err: any) {
      console.error('Error fetching filtered data:', err);
      // Don't set error here as it's a secondary fetch
    }
  };

  // Filter vulnerabilities by search
  const filteredVulnerabilities = useMemo(() => {
    if (!filters.search) return vulnerabilities;
    const searchLower = filters.search.toLowerCase();
    return vulnerabilities.filter(
      (vuln) =>
        vuln.title.toLowerCase().includes(searchLower) ||
        vuln.vulnerability_id.toLowerCase().includes(searchLower) ||
        vuln.resource.toLowerCase().includes(searchLower)
    );
  }, [vulnerabilities, filters.search]);

  // Chart data
  const severityChartData = useMemo(() => {
    if (!metrics) return [];
    return [
      { name: 'Critical', value: metrics.critical_count, color: SEVERITY_COLORS.CRITICAL },
      { name: 'High', value: metrics.high_count, color: SEVERITY_COLORS.HIGH },
      { name: 'Medium', value: metrics.medium_count, color: SEVERITY_COLORS.MEDIUM },
      { name: 'Low', value: metrics.low_count, color: SEVERITY_COLORS.LOW },
    ];
  }, [metrics]);

  const namespaceChartData = useMemo(() => {
    const namespaceStats = summaries.reduce((acc, summary) => {
      if (!acc[summary.namespace]) {
        acc[summary.namespace] = { namespace: summary.namespace, total: 0, critical: 0, high: 0 };
      }
      acc[summary.namespace].total += summary.total_vulnerabilities;
      acc[summary.namespace].critical += summary.critical_count;
      acc[summary.namespace].high += summary.high_count;
      return acc;
    }, {} as Record<string, any>);

    return Object.values(namespaceStats).slice(0, 10); // Top 10 namespaces
  }, [summaries]);

  // Handle filter changes
  const handleFilterChange = (key: keyof FilterOptions, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  // Apply filters
  useEffect(() => {
    if (!loading && metrics) {
      fetchFilteredData();
    }
  }, [filters.severity, filters.namespace, filters.fixable_only]);

  // View vulnerability details
  const viewVulnerabilityDetails = (vulnerability: VulnerabilityInfo) => {
    setSelectedVulnerability(vulnerability);
    onVulnModalOpen();
  };

  // Export data
  const exportData = () => {
    const dataStr = JSON.stringify({ metrics, vulnerabilities, summaries }, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `security-report-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Copy command to clipboard
  const copyCommand = async (command: string) => {
    try {
      await navigator.clipboard.writeText(command);
      setCopiedCommand(command);
      setTimeout(() => setCopiedCommand(null), 2000);
    } catch (err) {
      console.error('Failed to copy command:', err);
    }
  };

  // Render installation guide
  const renderInstallationGuide = () => {
    if (!installationGuide) return null;

    const guide = installationGuide.trivy_operator_installation;

    return (
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center gap-3">
            <Terminal className="w-6 h-6 text-orange-500" />
            <div>
              <h3 className="text-lg font-semibold">Operator Installation Required</h3>
              <p className="text-sm text-gray-600">{guide.description}</p>
            </div>
          </div>
        </CardHeader>
        <CardBody>
          <Accordion variant="splitted">
            {guide.installation_methods.map((method, index) => (
              <AccordionItem
              key={index}
              aria-label={method.method}
              title={`Install using ${method.method}`}
            >
              <div className="space-y-3">
                {method.commands.map((command, cmdIndex) => (
                  <div key={cmdIndex} className="relative">
                    <Code className="block w-full p-3 bg-gray-900 text-green-400 rounded-lg font-mono text-sm">
                      {command}
                    </Code>
                    <Button
                      size="sm"
                      variant="flat"
                      className="absolute top-2 right-2"
                      onPress={() => copyCommand(command)}
                    >
                      {copiedCommand === command ? (
                        <CheckCheck className="w-4 h-4 text-green-500" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            </AccordionItem>
          ))}
          
          <AccordionItem aria-label="Verification" title="Verification Steps">
            <div className="space-y-3">
              {guide.verification.map((command, index) => (
                <div key={index} className="relative">
                  <Code className="block w-full p-3 bg-gray-900 text-green-400 rounded-lg font-mono text-sm">
                    {command}
                  </Code>
                  <Button
                    size="sm"
                    variant="flat"
                    className="absolute top-2 right-2"
                    onPress={() => copyCommand(command)}
                  >
                    {copiedCommand === command ? (
                      <CheckCheck className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </AccordionItem>

          <AccordionItem aria-label="Post Installation" title="Post Installation">
            <div className="space-y-2">
              {guide.post_installation.map((step, index) => (
                <div key={index} className="flex items-start gap-2">
                  <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-bold mt-0.5">
                    {index + 1}
                  </div>
                  <p className="text-sm">{step}</p>
                </div>
              ))}
            </div>
          </AccordionItem>
        </Accordion>

        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-blue-900">After Installation</h4>
              <p className="text-sm text-blue-700 mt-1">
                Once Operator is installed and running, refresh this page to view security data.
                The operator will automatically scan your workloads and generate vulnerability reports.
              </p>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

if (loading) {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <Spinner size="lg" />
        <p className="mt-4 text-gray-600">Loading security dashboard...</p>
      </div>
    </div>
  );
}

if (error && !metrics) {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-600" />
            Security Operations
          </h1>
          <p className="text-gray-600 mt-1">
            Monitor and manage Kubernetes security vulnerabilities
          </p>
        </div>
        <Button
          color="primary"
          startContent={<RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />}
          onPress={() => fetchData(true)}
          isLoading={refreshing}
        >
          Retry
        </Button>
      </div>

      {/* Error State */}
      <Card className="mb-6">
        <CardBody className="text-center py-12">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">Unable to Load Security Data</h3>
          <p className="text-gray-600 mb-6">{error}</p>
          
          {healthStatus?.trivy_operator === 'not_installed' && (
            <Button
              color="primary"
              onPress={onInstallModalOpen}
              startContent={<Terminal className="w-4 h-4" />}
            >
              View Installation Guide
            </Button>
          )}
        </CardBody>
      </Card>

      {/* Installation Guide */}
      {installationGuide && renderInstallationGuide()}
    </div>
  );
}

return (
  <div className="p-6 max-w-7xl mx-auto space-y-6">
    {/* Header */}
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Shield className="w-8 h-8 text-blue-600" />
          Security Operations
        </h1>
        <p className="text-gray-600 mt-1">
          Monitor and manage Kubernetes security vulnerabilities
        </p>
        {healthStatus && (
          <div className="flex items-center gap-2 mt-2">
            <div className={`w-2 h-2 rounded-full ${
              healthStatus.trivy_operator === 'available' ? 'bg-green-500' : 
              healthStatus.trivy_operator === 'not_installed' ? 'bg-red-500' : 'bg-yellow-500'
            }`}></div>
            <span className="text-sm text-gray-600">
              Operator: {healthStatus.trivy_operator === 'available' ? 'Available' : 
              healthStatus.trivy_operator === 'not_installed' ? 'Not Installed' : 'Unknown'}
            </span>
          </div>
        )}
      </div>
      <div className="flex items-center gap-3">
        <Switch
          isSelected={autoRefresh}
          onValueChange={setAutoRefresh}
          size="sm"
        >
          Auto-refresh
        </Switch>
        <Button
          variant="flat"
          startContent={<Settings className="w-4 h-4" />}
          onPress={onSettingsModalOpen}
        >
          Settings
        </Button>
        <Button
          variant="flat"
          startContent={<Download className="w-4 h-4" />}
          onPress={exportData}
        >
          Export
        </Button>
        <Button
          color="primary"
          startContent={<RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />}
          onPress={() => fetchData(true)}
          isLoading={refreshing}
        >
          Refresh
        </Button>
      </div>
    </div>

    {/* Show installation guide if Trivy Operator is not available */}
    {healthStatus?.trivy_operator === 'not_installed' && installationGuide && renderInstallationGuide()}

    {/* Metrics Cards */}
    {metrics && (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="border-l-4 border-l-red-500">
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Critical Vulnerabilities</p>
                <p className="text-2xl font-bold text-red-600">{metrics.critical_count}</p>
              </div>
              <AlertCircle className="w-8 h-8 text-red-500" />
            </div>
            <div className="mt-2">
              <Progress
                value={metrics.total_vulnerabilities > 0 ? (metrics.critical_count / metrics.total_vulnerabilities) * 100 : 0}
                color="danger"
                size="sm"
              />
            </div>
          </CardBody>
        </Card>

        <Card className="border-l-4 border-l-orange-500">
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">High Vulnerabilities</p>
                <p className="text-2xl font-bold text-orange-600">{metrics.high_count}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-orange-500" />
            </div>
            <div className="mt-2">
              <Progress
                value={metrics.total_vulnerabilities > 0 ? (metrics.high_count / metrics.total_vulnerabilities) * 100 : 0}
                color="warning"
                size="sm"
              />
            </div>
          </CardBody>
        </Card>

        <Card className="border-l-4 border-l-blue-500">
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Vulnerabilities</p>
                <p className="text-2xl font-bold text-blue-600">{metrics.total_vulnerabilities}</p>
              </div>
              <Bug className="w-8 h-8 text-blue-500" />
            </div>
            <div className="mt-2">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-green-600">
                  {metrics.fixable_count} fixable
                </span>
                <span className="text-gray-400">•</span>
                <span className="text-gray-600">
                  {metrics.affected_namespaces} namespaces
                </span>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card className="border-l-4 border-l-green-500">
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Security Score</p>
                <p className="text-2xl font-bold text-green-600">
                  {metrics.total_vulnerabilities > 0 ? 
                    Math.round(((metrics.total_vulnerabilities - metrics.critical_count - metrics.high_count) / metrics.total_vulnerabilities) * 100) : 100}%
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-500" />
            </div>
            <div className="mt-2">
              <Progress
                value={metrics.total_vulnerabilities > 0 ? 
                  ((metrics.total_vulnerabilities - metrics.critical_count - metrics.high_count) / metrics.total_vulnerabilities) * 100 : 100}
                color="success"
                size="sm"
              />
            </div>
          </CardBody>
        </Card>
      </div>
    )}

    {/* Filters */}
    <Card>
      <CardBody>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium">Filters:</span>
          </div>
          
          <Select
            placeholder="All Severities"
            className="w-40"
            size="sm"
            selectedKeys={filters.severity ? [filters.severity] : []}
            onSelectionChange={(keys) => handleFilterChange('severity', Array.from(keys)[0] || '')}
          >
            <SelectItem key="CRITICAL" value="CRITICAL">Critical</SelectItem>
            <SelectItem key="HIGH" value="HIGH">High</SelectItem>
            <SelectItem key="MEDIUM" value="MEDIUM">Medium</SelectItem>
            <SelectItem key="LOW" value="LOW">Low</SelectItem>
          </Select>

          <Select
            placeholder="All Namespaces"
            className="w-48"
            size="sm"
            selectedKeys={filters.namespace ? [filters.namespace] : []}
            onSelectionChange={(keys) => handleFilterChange('namespace', Array.from(keys)[0] || '')}
          >
            {namespaces.map((ns) => (
              <SelectItem key={ns} value={ns}>{ns}</SelectItem>
            ))}
          </Select>

          <Switch
            size="sm"
            isSelected={filters.fixable_only}
            onValueChange={(checked) => handleFilterChange('fixable_only', checked)}
          >
            Fixable only
          </Switch>

          <Input
            placeholder="Search vulnerabilities..."
            startContent={<Search className="w-4 h-4 text-gray-400" />}
            className="w-64"
            size="sm"
            value={filters.search}
            onValueChange={(value) => handleFilterChange('search', value)}
          />

          <div className="flex items-center gap-2 ml-auto">
            <Button
              variant={viewMode === 'grid' ? 'solid' : 'flat'}
              size="sm"
              isIconOnly
              onPress={() => setViewMode('grid')}
            >
              <Grid className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'solid' : 'flat'}
              size="sm"
              isIconOnly
              onPress={() => setViewMode('list')}
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardBody>
    </Card>

    {/* Main Content Tabs */}
    <Tabs
      selectedKey={selectedTab}
      onSelectionChange={(key) => setSelectedTab(key as string)}
      className="w-full"
    >
      <Tab key="overview" title={
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4" />
          Overview
        </div>
      }>
        <div className="space-y-6">
          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Severity Distribution */}
            <Card>
              <CardHeader>
              <h3 className="text-lg font-semibold">Vulnerability Distribution</h3>
                </CardHeader>
                <CardBody>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={severityChartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={120}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {severityChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <RechartsTooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </CardBody>
              </Card>

              {/* Namespace Vulnerabilities */}
              <Card>
                <CardHeader>
                  <h3 className="text-lg font-semibold">Top Vulnerable Namespaces</h3>
                </CardHeader>
                <CardBody>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={namespaceChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="namespace" />
                      <YAxis />
                      <RechartsTooltip />
                      <Bar dataKey="critical" stackId="a" fill={SEVERITY_COLORS.CRITICAL} />
                      <Bar dataKey="high" stackId="a" fill={SEVERITY_COLORS.HIGH} />
                      <Bar dataKey="total" fill="#e5e7eb" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardBody>
              </Card>
            </div>

            {/* Summary Cards */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Container Security Summary</h3>
                  <Badge color="primary" variant="flat">
                    {summaries.length} containers
                  </Badge>
                </div>
              </CardHeader>
              <CardBody>
                <div className={`grid gap-4 ${viewMode === 'grid' ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1'}`}>
                  {summaries.slice(0, 12).map((summary, index) => (
                    <Card key={index} className="border">
                      <CardBody className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium truncate">
                              {summary.image_repository}:{summary.image_tag}
                            </h4>
                            <p className="text-sm text-gray-600 truncate">
                              {summary.namespace} • {summary.container_name}
                            </p>
                          </div>
                          <Package className="w-5 h-5 text-gray-400 flex-shrink-0 ml-2" />
                        </div>
                        
                        <div className="grid grid-cols-4 gap-2 mb-3">
                          <div className="text-center">
                            <div className="text-xs text-gray-500">Critical</div>
                            <div className="font-semibold text-red-600">{summary.critical_count}</div>
                          </div>
                          <div className="text-center">
                            <div className="text-xs text-gray-500">High</div>
                            <div className="font-semibold text-orange-600">{summary.high_count}</div>
                          </div>
                          <div className="text-center">
                            <div className="text-xs text-gray-500">Medium</div>
                            <div className="font-semibold text-yellow-600">{summary.medium_count}</div>
                          </div>
                          <div className="text-center">
                            <div className="text-xs text-gray-500">Low</div>
                            <div className="font-semibold text-green-600">{summary.low_count}</div>
                          </div>
                        </div>

                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">
                            Total: {summary.total_vulnerabilities}
                          </span>
                          <Chip
                            size="sm"
                            color={summary.critical_count > 0 ? 'danger' : summary.high_count > 0 ? 'warning' : 'success'}
                            variant="flat"
                          >
                            {summary.critical_count > 0 ? 'Critical' : summary.high_count > 0 ? 'High Risk' : 'Low Risk'}
                          </Chip>
                        </div>
                      </CardBody>
                    </Card>
                  ))}
                </div>
              </CardBody>
            </Card>
          </div>
        </Tab>

        <Tab key="vulnerabilities" title={
          <div className="flex items-center gap-2">
            <Bug className="w-4 h-4" />
            Vulnerabilities
            <Badge size="sm" color="danger" variant="flat">
              {filteredVulnerabilities.length}
            </Badge>
          </div>
        }>
          <Card>
            <CardBody>
              <Table aria-label="Vulnerabilities table">
                <TableHeader>
                  <TableColumn>VULNERABILITY</TableColumn>
                  <TableColumn>SEVERITY</TableColumn>
                  <TableColumn>RESOURCE</TableColumn>
                  <TableColumn>VERSION</TableColumn>
                  <TableColumn>NAMESPACE</TableColumn>
                  <TableColumn>ACTIONS</TableColumn>
                </TableHeader>
                <TableBody>
                  {filteredVulnerabilities.slice(0, 50).map((vuln, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{vuln.vulnerability_id}</div>
                          <div className="text-sm text-gray-600 truncate max-w-xs">
                            {vuln.title}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="sm"
                          style={{
                            backgroundColor: SEVERITY_BG_COLORS[vuln.severity],
                            color: SEVERITY_COLORS[vuln.severity],
                          }}
                        >
                          {vuln.severity}
                          {vuln.score && ` (${vuln.score})`}
                        </Chip>
                      </TableCell>
                      <TableCell>
                        <div className="font-mono text-sm">{vuln.resource}</div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="text-sm">
                            <span className="text-red-600">{vuln.installed_version}</span>
                          </div>
                          {vuln.fixed_version && (
                            <div className="text-xs text-green-600">
                              → {vuln.fixed_version}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Chip size="sm" variant="flat">
                          {vuln.namespace}
                        </Chip>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Tooltip content="View Details">
                            <Button
                              size="sm"
                              variant="flat"
                              isIconOnly
                              onPress={() => viewVulnerabilityDetails(vuln)}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                          </Tooltip>
                          {vuln.primary_link && (
                            <Tooltip content="External Link">
                              <Button
                                size="sm"
                                variant="flat"
                                isIconOnly
                                onPress={() => window.open(vuln.primary_link, '_blank')}
                              >
                                <ExternalLink className="w-4 h-4" />
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
        </Tab>

        <Tab key="reports" title={
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            Reports
          </div>
        }>
          <div className="space-y-6">
            {/* Trend Chart */}
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold">Security Trends</h3>
              </CardHeader>
              <CardBody>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={namespaceChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="namespace" />
                    <YAxis />
                    <RechartsTooltip />
                    <Area
                      type="monotone"
                      dataKey="critical"
                      stackId="1"
                      stroke={SEVERITY_COLORS.CRITICAL}
                      fill={SEVERITY_COLORS.CRITICAL}
                    />
                    <Area
                      type="monotone"
                      dataKey="high"
                      stackId="1"
                      stroke={SEVERITY_COLORS.HIGH}
                      fill={SEVERITY_COLORS.HIGH}
                    />
                    <Legend />
                  </AreaChart>
                </ResponsiveContainer>
              </CardBody>
            </Card>

            {/* Detailed Reports */}
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold">Vulnerability Reports by Namespace</h3>
              </CardHeader>
              <CardBody>
                <Accordion variant="splitted">
                  {namespaces.map((namespace) => {
                    const namespaceSummaries = summaries.filter(s => s.namespace === namespace);
                    const totalVulns = namespaceSummaries.reduce((sum, s) => sum + s.total_vulnerabilities, 0);
                    const criticalVulns = namespaceSummaries.reduce((sum, s) => sum + s.critical_count, 0);
                    const highVulns = namespaceSummaries.reduce((sum, s) => sum + s.high_count, 0);

                    return (
                      <AccordionItem
                        key={namespace}
                        aria-label={namespace}
                        title={
                          <div className="flex items-center justify-between w-full">
                            <div className="flex items-center gap-3">
                              <Server className="w-5 h-5 text-blue-500" />
                              <span className="font-medium">{namespace}</span>
                            </div>
                            <div className="flex items-center gap-4">
                              <div className="flex items-center gap-2">
                                <Chip size="sm" color="danger" variant="flat">
                                  {criticalVulns} Critical
                                </Chip>
                                <Chip size="sm" color="warning" variant="flat">
                                  {highVulns} High
                                </Chip>
                                <Chip size="sm" variant="flat">
                                  {totalVulns} Total
                                </Chip>
                              </div>
                            </div>
                          </div>
                        }
                      >
                        <div className="space-y-4">
                          {namespaceSummaries.map((summary, idx) => (
                            <Card key={idx} className="border">
                              <CardBody className="p-4">
                                <div className="flex items-start justify-between mb-4">
                                  <div>
                                    <h4 className="font-medium text-lg">
                                      {summary.image_repository}:{summary.image_tag}
                                    </h4>
                                    <p className="text-sm text-gray-600">
                                      Container: {summary.container_name || 'N/A'}
                                    </p>
                                    <p className="text-xs text-gray-500">
                                      Report: {summary.report_name}
                                    </p>
                                  </div>
                                  <div className="text-right">
                                    <div className="text-2xl font-bold text-gray-800">
                                      {summary.total_vulnerabilities}
                                    </div>
                                    <div className="text-sm text-gray-500">vulnerabilities</div>
                                  </div>
                                </div>

                                <div className="grid grid-cols-4 gap-4">
                                  <div className="text-center p-3 rounded-lg" style={{ backgroundColor: SEVERITY_BG_COLORS.CRITICAL }}>
                                    <div className="text-2xl font-bold" style={{ color: SEVERITY_COLORS.CRITICAL }}>
                                      {summary.critical_count}
                                    </div>
                                    <div className="text-sm font-medium">Critical</div>
                                  </div>
                                  <div className="text-center p-3 rounded-lg" style={{ backgroundColor: SEVERITY_BG_COLORS.HIGH }}>
                                    <div className="text-2xl font-bold" style={{ color: SEVERITY_COLORS.HIGH }}>
                                      {summary.high_count}
                                    </div>
                                    <div className="text-sm font-medium">High</div>
                                  </div>
                                  <div className="text-center p-3 rounded-lg" style={{ backgroundColor: SEVERITY_BG_COLORS.MEDIUM }}>
                                    <div className="text-2xl font-bold" style={{ color: SEVERITY_COLORS.MEDIUM }}>
                                      {summary.medium_count}
                                    </div>
                                    <div className="text-sm font-medium">Medium</div>
                                  </div>
                                  <div className="text-center p-3 rounded-lg" style={{ backgroundColor: SEVERITY_BG_COLORS.LOW }}>
                                    <div className="text-2xl font-bold" style={{ color: SEVERITY_COLORS.LOW }}>
                                      {summary.low_count}
                                    </div>
                                    <div className="text-sm font-medium">Low</div>
                                  </div>
                                </div>

                                <div className="mt-4">
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium">Risk Level</span>
                                    <span className="text-sm text-gray-600">
                                      {summary.total_vulnerabilities > 0 ? 
                                        Math.round(((summary.critical_count + summary.high_count) / summary.total_vulnerabilities) * 100) : 0}% High Risk
                                    </span>
                                  </div>
                                  <Progress
                                                                        value={summary.total_vulnerabilities > 0 ? 
                                                                            ((summary.critical_count + summary.high_count) / summary.total_vulnerabilities) * 100 : 0}
                                                                          color={summary.critical_count > 0 ? 'danger' : summary.high_count > 0 ? 'warning' : 'success'}
                                                                          size="sm"
                                                                        />
                                                                      </div>
                                                                    </CardBody>
                                                                  </Card>
                                                                ))}
                                                              </div>
                                                            </AccordionItem>
                                                          );
                                                        })}
                                                      </Accordion>
                                                    </CardBody>
                                                  </Card>
                                                </div>
                                              </Tab>
                                      
                                              <Tab key="analytics" title={
                                                <div className="flex items-center gap-2">
                                                  <PieChartIcon className="w-4 h-4" />
                                                  Analytics
                                                </div>
                                              }>
                                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                                  {/* Security Score Trend */}
                                                  <Card>
                                                    <CardHeader>
                                                      <h3 className="text-lg font-semibold">Security Score by Namespace</h3>
                                                    </CardHeader>
                                                    <CardBody>
                                                      <ResponsiveContainer width="100%" height={300}>
                                                        <BarChart data={namespaceChartData}>
                                                          <CartesianGrid strokeDasharray="3 3" />
                                                          <XAxis dataKey="namespace" />
                                                          <YAxis />
                                                          <RechartsTooltip />
                                                          <Bar
                                                            dataKey="total"
                                                            fill="#e5e7eb"
                                                            name="Total Vulnerabilities"
                                                          />
                                                        </BarChart>
                                                      </ResponsiveContainer>
                                                    </CardBody>
                                                  </Card>
                                      
                                                  {/* Fixable vs Non-fixable */}
                                                  <Card>
                                                    <CardHeader>
                                                      <h3 className="text-lg font-semibold">Remediation Status</h3>
                                                    </CardHeader>
                                                    <CardBody>
                                                      <ResponsiveContainer width="100%" height={300}>
                                                        <PieChart>
                                                          <Pie
                                                            data={[
                                                              { name: 'Fixable', value: metrics?.fixable_count || 0, color: '#10b981' },
                                                              { name: 'Not Fixable', value: (metrics?.total_vulnerabilities || 0) - (metrics?.fixable_count || 0), color: '#ef4444' },
                                                            ]}
                                                            cx="50%"
                                                            cy="50%"
                                                            innerRadius={60}
                                                            outerRadius={120}
                                                            paddingAngle={5}
                                                            dataKey="value"
                                                          >
                                                            <Cell fill="#10b981" />
                                                            <Cell fill="#ef4444" />
                                                          </Pie>
                                                          <RechartsTooltip />
                                                          <Legend />
                                                        </PieChart>
                                                      </ResponsiveContainer>
                                                    </CardBody>
                                                  </Card>
                                      
                                                  {/* Top Vulnerable Images */}
                                                  <Card className="lg:col-span-2">
                                                    <CardHeader>
                                                      <h3 className="text-lg font-semibold">Most Vulnerable Container Images</h3>
                                                    </CardHeader>
                                                    <CardBody>
                                                      <div className="space-y-4">
                                                        {summaries
                                                          .sort((a, b) => b.total_vulnerabilities - a.total_vulnerabilities)
                                                          .slice(0, 10)
                                                          .map((summary, index) => (
                                                            <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                                                              <div className="flex items-center gap-4">
                                                                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                                                                  <Package className="w-4 h-4 text-blue-600" />
                                                                </div>
                                                                <div>
                                                                  <div className="font-medium">
                                                                    {summary.image_repository}:{summary.image_tag}
                                                                  </div>
                                                                  <div className="text-sm text-gray-600">
                                                                    {summary.namespace} • {summary.container_name}
                                                                  </div>
                                                                </div>
                                                              </div>
                                                              <div className="flex items-center gap-4">
                                                                <div className="flex items-center gap-2">
                                                                  <Chip size="sm" color="danger" variant="flat">
                                                                    {summary.critical_count}
                                                                  </Chip>
                                                                  <Chip size="sm" color="warning" variant="flat">
                                                                    {summary.high_count}
                                                                  </Chip>
                                                                </div>
                                                                <div className="text-right">
                                                                  <div className="font-bold text-lg">{summary.total_vulnerabilities}</div>
                                                                  <div className="text-xs text-gray-500">total</div>
                                                                </div>
                                                              </div>
                                                            </div>
                                                          ))}
                                                      </div>
                                                    </CardBody>
                                                  </Card>
                                                </div>
                                              </Tab>
                                            </Tabs>
                                      
                                            {/* Vulnerability Details Modal */}
                                            <Modal
                                              isOpen={isVulnModalOpen}
                                              onClose={onVulnModalClose}
                                              size="2xl"
                                              scrollBehavior="inside"
                                            >
                                              <ModalContent>
                                                {(onClose) => (
                                                  <>
                                                    <ModalHeader className="flex flex-col gap-1">
                                                      <div className="flex items-center gap-3">
                                                        <Bug className="w-6 h-6 text-red-500" />
                                                        <div>
                                                          <h3 className="text-xl font-bold">
                                                            {selectedVulnerability?.vulnerability_id}
                                                          </h3>
                                                          <p className="text-sm text-gray-600 font-normal">
                                                            {selectedVulnerability?.title}
                                                          </p>
                                                        </div>
                                                      </div>
                                                    </ModalHeader>
                                                    <ModalBody>
                                                      {selectedVulnerability && (
                                                        <div className="space-y-6">
                                                          {/* Severity and Score */}
                                                          <div className="flex items-center gap-4">
                                                            <Chip
                                                              size="lg"
                                                              style={{
                                                                backgroundColor: SEVERITY_BG_COLORS[selectedVulnerability.severity],
                                                                color: SEVERITY_COLORS[selectedVulnerability.severity],
                                                              }}
                                                            >
                                                              {selectedVulnerability.severity}
                                                              {selectedVulnerability.score && ` (${selectedVulnerability.score})`}
                                                            </Chip>
                                                            {selectedVulnerability.fixed_version && (
                                                              <Chip color="success" variant="flat">
                                                                Fixable
                                                              </Chip>
                                                            )}
                                                          </div>
                                      
                                                          {/* Details Grid */}
                                                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                            <div>
                                                              <h4 className="font-semibold mb-3">Resource Information</h4>
                                                              <div className="space-y-3">
                                                                <div>
                                                                  <label className="text-sm font-medium text-gray-600">Namespace</label>
                                                                  <div className="mt-1">
                                                                    <Chip size="sm" variant="flat">
                                                                      {selectedVulnerability.namespace}
                                                                    </Chip>
                                                                  </div>
                                                                </div>
                                                                <div>
                                                                  <label className="text-sm font-medium text-gray-600">Resource</label>
                                                                  <div className="mt-1 font-mono text-sm bg-gray-100 p-2 rounded">
                                                                    {selectedVulnerability.resource}
                                                                  </div>
                                                                </div>
                                                                <div>
                                                                  <label className="text-sm font-medium text-gray-600">Report</label>
                                                                  <div className="mt-1 text-sm text-gray-800">
                                                                    {selectedVulnerability.report_name}
                                                                  </div>
                                                                </div>
                                                              </div>
                                                            </div>
                                      
                                                            <div>
                                                              <h4 className="font-semibold mb-3">Version Information</h4>
                                                              <div className="space-y-3">
                                                                <div>
                                                                  <label className="text-sm font-medium text-gray-600">Installed Version</label>
                                                                  <div className="mt-1 font-mono text-sm bg-red-50 text-red-800 p-2 rounded">
                                                                    {selectedVulnerability.installed_version}
                                                                  </div>
                                                                </div>
                                                                {selectedVulnerability.fixed_version && (
                                                                  <div>
                                                                    <label className="text-sm font-medium text-gray-600">Fixed Version</label>
                                                                    <div className="mt-1 font-mono text-sm bg-green-50 text-green-800 p-2 rounded">
                                                                      {selectedVulnerability.fixed_version}
                                                                    </div>
                                                                  </div>
                                                                )}
                                                              </div>
                                                            </div>
                                                          </div>
                                      
                                                          {/* Remediation Steps */}
                                                          {selectedVulnerability.fixed_version && (
                                                            <div>
                                                              <h4 className="font-semibold mb-3">Remediation Steps</h4>
                                                              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                                                <div className="space-y-3">
                                                                  <div className="flex items-start gap-3">
                                                                    <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                                                                      1
                                                                    </div>
                                                                    <div>
                                                                      <p className="font-medium">Update Package Version</p>
                                                                      <p className="text-sm text-gray-600 mt-1">
                                                                        Upgrade {selectedVulnerability.resource} from version{' '}
                                                                        <code className="bg-red-100 text-red-800 px-1 rounded">
                                                                          {selectedVulnerability.installed_version}
                                                                        </code>{' '}
                                                                        to{' '}
                                                                        <code className="bg-green-100 text-green-800 px-1 rounded">
                                                                          {selectedVulnerability.fixed_version}
                                                                        </code>
                                                                      </p>
                                                                    </div>
                                                                  </div>
                                                                  <div className="flex items-start gap-3">
                                                                    <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                                                                      2
                                                                    </div>
                                                                    <div>
                                                                      <p className="font-medium">Rebuild Container Image</p>
                                                                      <p className="text-sm text-gray-600 mt-1">
                                                                        Update your Dockerfile and rebuild the container image with the fixed version.
                                                                      </p>
                                                                    </div>
                                                                  </div>
                                                                  <div className="flex items-start gap-3">
                                                                    <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                                                                      3
                                                                    </div>
                                                                    <div>
                                                                      <p className="font-medium">Deploy Updated Image</p>
                                                                      <p className="text-sm text-gray-600 mt-1">
                                                                        Deploy the updated container image to your Kubernetes cluster.
                                                                      </p>
                                                                    </div>
                                                                  </div>
                                                                </div>
                                                              </div>
                                                            </div>
                                                          )}
                                                        </div>
                                                      )}
                                                    </ModalBody>
                                                    <ModalFooter>
                                                      <Button variant="flat" onPress={onClose}>
                                                        Close
                                                      </Button>
                                                      {selectedVulnerability?.primary_link && (
                                                        <Button
                                                          color="primary"
                                                          startContent={<ExternalLink className="w-4 h-4" />}
                                                          onPress={() => window.open(selectedVulnerability.primary_link, '_blank')}
                                                        >
                                                          View Details
                                                        </Button>
                                                      )}
                                                    </ModalFooter>
                                                  </>
                                                )}
                                              </ModalContent>
                                            </Modal>
                                      
                                            {/* Settings Modal */}
                                            <Modal isOpen={isSettingsModalOpen} onClose={onSettingsModalClose}>
                                              <ModalContent>
                                                {(onClose) => (
                                                  <>
                                                    <ModalHeader>
                                                      <div className="flex items-center gap-2">
                                                        <Settings className="w-5 h-5" />
                                                        Dashboard Settings
                                                      </div>
                                                    </ModalHeader>
                                                    <ModalBody>
                                                      <div className="space-y-6">
                                                        <div>
                                                          <h4 className="font-semibold mb-3">Refresh Settings</h4>
                                                          <div className="space-y-3">
                                                            <div className="flex items-center justify-between">
                                                              <div>
                                                                <p className="font-medium">Auto-refresh</p>
                                                                <p className="text-sm text-gray-600">
                                                                  Automatically refresh data every 30 seconds
                                                                </p>
                                                              </div>
                                                              <Switch
                                                                isSelected={autoRefresh}
                                                                onValueChange={setAutoRefresh}
                                                              />
                                                            </div>
                                                          </div>
                                                        </div>
                                      
                                                        <div>
                                                          <h4 className="font-semibold mb-3">Display Settings</h4>
                                                          <div className="space-y-3">
                                                            <div className="flex items-center justify-between">
                                                              <div>
                                                                <p className="font-medium">Default View Mode</p>
                                                                <p className="text-sm text-gray-600">
                                                                  Choose how to display vulnerability summaries
                                                                </p>
                                                              </div>
                                                              <Select
                                                                selectedKeys={[viewMode]}
                                                                onSelectionChange={(keys) => setViewMode(Array.from(keys)[0] as 'grid' | 'list')}
                                                                className="w-32"
                                                                size="sm"
                                                              >
                                                                <SelectItem key="grid" value="grid">Grid</SelectItem>
                                                                <SelectItem key="list" value="list">List</SelectItem>
                                                              </Select>
                                                            </div>
                                                          </div>
                                                        </div>
                                      
                                                        <div>
                                                          <h4 className="font-semibold mb-3">API Configuration</h4>
                                                          <div className="space-y-3">
                                                            <div>
                                                              <label className="text-sm font-medium text-gray-600">API Base URL</label>
                                                              <Input
                                                                value={API_BASE_URL}
                                                                readOnly
                                                                className="mt-1"
                                                                size="sm"
                                                              />
                                                            </div>
                                                            <div className="flex items-center gap-2">
                                                              <div className={`w-2 h-2 rounded-full ${
                                                                healthStatus?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                                                              }`}></div>
                                                              <span className={`text-sm ${
                                                                healthStatus?.status === 'healthy' ? 'text-green-600' : 'text-red-600'
                                                              }`}>
                                                                                          {healthStatus?.status === 'healthy' ? 'Connected' : 'Disconnected'}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500">
                        Authentication: {getAuthToken() ? 'Active' : 'Missing'}
                      </div>
                    </div>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="flat" onPress={onClose}>
                  Close
                </Button>
                <Button color="primary" onPress={onClose}>
                  Save Settings
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Installation Guide Modal */}
      <Modal 
        isOpen={isInstallModalOpen} 
        onClose={onInstallModalClose}
        size="3xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>
                <div className="flex items-center gap-2">
                  <Terminal className="w-5 h-5 text-orange-500" />
                  Operator Installation Guide
                </div>
              </ModalHeader>
              <ModalBody>
                {installationGuide && (
                  <div className="space-y-6">
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-orange-600 mt-0.5" />
                        <div>
                          <h4 className="font-medium text-orange-900">Installation Required</h4>
                          <p className="text-sm text-orange-700 mt-1">
                            {installationGuide.trivy_operator_installation.description}
                          </p>
                        </div>
                      </div>
                    </div>

                    <Accordion variant="splitted">
                      {installationGuide.trivy_operator_installation.installation_methods.map((method, index) => (
                        <AccordionItem
                          key={index}
                          aria-label={method.method}
                          title={`Install using ${method.method}`}
                        >
                          <div className="space-y-3">
                            {method.commands.map((command, cmdIndex) => (
                              <div key={cmdIndex} className="relative">
                                <Code className="block w-full p-3 bg-gray-900 text-green-400 rounded-lg font-mono text-sm overflow-x-auto">
                                  {command}
                                </Code>
                                <Button
                                  size="sm"
                                  variant="flat"
                                  className="absolute top-2 right-2"
                                  onPress={() => copyCommand(command)}
                                >
                                  {copiedCommand === command ? (
                                    <CheckCheck className="w-4 h-4 text-green-500" />
                                  ) : (
                                    <Copy className="w-4 h-4" />
                                  )}
                                </Button>
                              </div>
                            ))}
                          </div>
                        </AccordionItem>
                      ))}
                      
                      <AccordionItem aria-label="Verification" title="Verification Steps">
                        <div className="space-y-3">
                          {installationGuide.trivy_operator_installation.verification.map((command, index) => (
                            <div key={index} className="relative">
                              <Code className="block w-full p-3 bg-gray-900 text-green-400 rounded-lg font-mono text-sm overflow-x-auto">
                                {command}
                              </Code>
                              <Button
                                size="sm"
                                variant="flat"
                                className="absolute top-2 right-2"
                                onPress={() => copyCommand(command)}
                              >
                                {copiedCommand === command ? (
                                  <CheckCheck className="w-4 h-4 text-green-500" />
                                ) : (
                                  <Copy className="w-4 h-4" />
                                )}
                              </Button>
                            </div>
                          ))}
                        </div>
                      </AccordionItem>

                      <AccordionItem aria-label="Post Installation" title="Post Installation">
                        <div className="space-y-2">
                          {installationGuide.trivy_operator_installation.post_installation.map((step, index) => (
                            <div key={index} className="flex items-start gap-2">
                              <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-bold mt-0.5">
                                {index + 1}
                              </div>
                              <p className="text-sm">{step}</p>
                            </div>
                          ))}
                        </div>
                      </AccordionItem>
                    </Accordion>

                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <Info className="w-5 h-5 text-blue-600 mt-0.5" />
                        <div>
                          <h4 className="font-medium text-blue-900">After Installation</h4>
                          <p className="text-sm text-blue-700 mt-1">
                            Once Operator is installed and running, refresh this page to view security data.
                            The operator will automatically scan your workloads and generate vulnerability reports.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </ModalBody>
              <ModalFooter>
                <Button variant="flat" onPress={onClose}>
                  Close
                </Button>
                <Button 
                  color="primary" 
                  onPress={() => {
                    onClose();
                    fetchData(true);
                  }}
                  startContent={<RefreshCw className="w-4 h-4" />}
                >
                  Check Installation
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Status Bar */}
      <div className="fixed bottom-4 right-4 z-50">
        <Card className="shadow-lg">
          <CardBody className="p-3">
            <div className="flex items-center gap-3 text-sm">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  healthStatus?.status === 'healthy' ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`}></div>
                <span>{healthStatus?.status === 'healthy' ? 'Live' : 'Offline'}</span>
              </div>
              {metrics && (
                <>
                  <div className="w-px h-4 bg-gray-300"></div>
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-gray-500" />
                    <span className="text-gray-600">
                      Updated {new Date(metrics.last_updated).toLocaleTimeString()}
                    </span>
                  </div>
                </>
              )}
              {autoRefresh && (
                <>
                  <div className="w-px h-4 bg-gray-300"></div>
                  <div className="flex items-center gap-1">
                    <RefreshCw className="w-3 h-3 text-blue-500 animate-spin" />
                    <span className="text-blue-600">Auto-refresh</span>
                  </div>
                </>
              )}
              <div className="w-px h-4 bg-gray-300"></div>
              <div className="flex items-center gap-1">
                <Shield className="w-3 h-3 text-gray-500" />
                <span className="text-gray-600">
                  {getAuthToken() ? 'Authenticated' : 'Not Authenticated'}
                </span>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
};

export default SecOps;                            