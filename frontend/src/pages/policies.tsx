import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Shield,
    Server,
    Settings,
    Eye,
    Code,
    Play,
    RefreshCw,
    Search,
    Filter,
    ChevronDown,
    ChevronRight,
    ChevronLeft,
    X,
    Check,
    AlertTriangle,
    Info,
    Loader2,
    FileText,
    Edit,
    Edit3,
    Save,
    Copy,
    ExternalLink,
    Layers,
    Lock,
    Zap,
    Target,
    GitBranch,
    Database,
    Globe,
    CheckCircle,
    XCircle,
    Clock,
    Tag,
    Hash,
    Calendar,
    User,
    Activity,
    TrendingUp,
    BarChart3,
    PieChart,
    Lightbulb,
    Sparkles,
    Rocket,
    Crown,
    Star,
    Award,
    Gem,
    Plus,
    Download,
    Upload,
    Trash2,
    MoreVertical,
    ArrowLeft,
    ArrowRight,
    Filter as FilterIcon,
    SortAsc,
    SortDesc,
    Grid,
    List,
    Maximize2,
    Minimize2
} from 'lucide-react';
import Editor from '@monaco-editor/react';

// Types
interface Cluster {
    id: number;
    cluster_name: string;
    server_url: string;
    context_name: string;
    provider_name: string;
    tags: string;
    use_secure_tls: boolean;
    is_operator_installed: boolean;
    created_at: string;
    updated_at: string;
}

interface PolicyCategory {
    id: number;
    name: string;
    display_name: string;
    description: string;
    icon: string;
    policy_count: number;
    created_at: string;
    updated_at: string;
}

interface Policy {
    id: number;
    policy_id: string;
    name: string;
    description: string;
    purpose: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    yaml_content: string;
    policy_metadata: any;
    tags: string[];
    is_active: boolean;
    category_id: number;
    created_at: string;
    updated_at: string;
    category?: PolicyCategory;
}

interface PolicyApplication {
    id: number;
    user_id: number;
    cluster_id: number;
    cluster_name: string;
    policy_id: number;
    policy?: Policy;
    status: 'PENDING' | 'APPLYING' | 'APPLIED' | 'FAILED' | 'REMOVED' | 'pending' | 'applying' | 'applied' | 'failed' | 'removed';
    applied_yaml?: string;
    original_yaml?: string;
    is_edited?: boolean;
    application_log?: string;
    error_message?: string;
    kubernetes_name?: string;
    kubernetes_namespace: string;
    created_at: string;
    applied_at?: string;
    updated_at?: string;
    policy_name?: string;
    policy_severity?: string;
}

interface ClusterOverview {
    cluster: {
        id: number;
        cluster_name: string;
        server_url: string;
        provider_name?: string;
        is_accessible: boolean;
    };
    total_applications: number;
    applied_count: number;
    failed_count: number;
    pending_count: number;
    categories_applied: string[];
}

interface PoliciesProps {
    selectedCluster: string;
}

const Policies: React.FC<PoliciesProps> = ({ selectedCluster }) => {
    // State
    const [clusters, setClusters] = useState<Cluster[]>([]);
    const [categories, setCategories] = useState<PolicyCategory[]>([]);
    const [policies, setPolicies] = useState<Policy[]>([]);
    const [applications, setApplications] = useState<PolicyApplication[]>([]);
    const [selectedClusterName, setSelectedClusterName] = useState<string>('');
    const [selectedCategory, setSelectedCategory] = useState<string>('');
    const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
    const [loading, setLoading] = useState(true);
    const [categoriesLoading, setCategoriesLoading] = useState(false);
    const [policiesLoading, setPoliciesLoading] = useState(false);
    const [applyingPolicy, setApplyingPolicy] = useState<string | null>(null);
    const [availablePolicies, setAvailablePolicies] = useState<Policy[]>([]);
    const [appliedPoliciesForCluster, setAppliedPoliciesForCluster] = useState<PolicyApplication[]>([]);
    const [clusterOverview, setClusterOverview] = useState<ClusterOverview[]>([]);

    // Modal states
    const [showPolicyModal, setShowPolicyModal] = useState(false);
    const [showYamlEditor, setShowYamlEditor] = useState(true);
    const [editedYaml, setEditedYaml] = useState('');
    const [showConfirmDialog, setShowConfirmDialog] = useState(false);
    const [showStatsModal, setShowStatsModal] = useState(false);
    const [showYamlModal, setShowYamlModal] = useState(false);
    const [selectedYamlContent, setSelectedYamlContent] = useState<string>('');
    const [showRemoveModal, setShowRemoveModal] = useState(false);
    const [removeModalData, setRemoveModalData] = useState<{ applicationId: number, policyName: string } | null>(null);
    const [removingPolicy, setRemovingPolicy] = useState(false);
    const [showYamlComparisonModal, setShowYamlComparisonModal] = useState(false);
    const [selectedApplicationForComparison, setSelectedApplicationForComparison] = useState<PolicyApplication | null>(null);

    // Search and filters
    const [searchTerm, setSearchTerm] = useState('');
    const [severityFilter, setSeverityFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [sortBy, setSortBy] = useState<'name' | 'severity' | 'created_at'>('name');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

    // Pagination
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const pageSize = 12;

    // Editable fields state
    const [editableFields, setEditableFields] = useState<{ [key: string]: string }>({});
    const [originalYaml, setOriginalYaml] = useState('');


    const [applicationsLoading, setApplicationsLoading] = useState(false);
    const [filteredApplications, setFilteredApplications] = useState<PolicyApplication[]>([]);
    const [totalPolicies, setTotalPolicies] = useState(0);

    const [refreshing, setRefreshing] = useState(false);

    // Stats
    const [stats, setStats] = useState({
        totalPolicies: 0,
        appliedPolicies: 0,
        failedPolicies: 0,
        pendingPolicies: 0,
        severityBreakdown: { critical: 0, high: 0, medium: 0, low: 0 }
    });

    // API Base URLs
    const KUBECONFIG_API = '/kubeconfig';
    const POLICIES_API = 'https://10.0.32.106:8005/api/v1/policies';



    // Helper functions
    const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
        // Format error messages to be user-friendly
        let displayMessage = message;
        if (type === 'error') {
            if (message.includes('404') || message.includes('Not Found')) {
                displayMessage = 'Policy or resource not found. Please check if the policy exists.';
            } else if (message.includes('500') || message.includes('Internal Server Error')) {
                displayMessage = 'Server error occurred. Please try again later.';
            } else if (message.includes('403') || message.includes('Forbidden')) {
                displayMessage = 'Access denied. You do not have permission to perform this action.';
            } else if (message.includes('401') || message.includes('Unauthorized')) {
                displayMessage = 'Authentication failed. Please log in again.';
            } else if (message.includes('timeout') || message.includes('network')) {
                displayMessage = 'Network connection failed. Please check your connection.';
            } else if (message.includes('HTTP response headers') || message.includes('HTTPHeaderDict')) {
                displayMessage = 'Policy application failed. Please try again or contact support.';
            } else if (message.length > 100) {
                displayMessage = 'An error occurred while processing your request. Please try again.';
            }
        }

        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg ${type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
                'bg-blue-500 text-white'
            }`;
        toast.textContent = displayMessage;
        document.body.appendChild(toast);
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 3000);
    };


    const extractEditableFields = (yamlContent: string) => {
        const lines = yamlContent.split('\n');
        const fields: { [key: string]: string } = {};

        lines.forEach((line, index) => {
            if (line.includes('##editable')) {
                const cleanLine = line.replace(/##editable.*$/, '').trim();
                const colonIndex = cleanLine.lastIndexOf(':');
                if (colonIndex !== -1) {
                    const fieldName = cleanLine.substring(0, colonIndex).trim();
                    const fieldValue = cleanLine.substring(colonIndex + 1).trim().replace(/['"]/g, '');
                    const fieldKey = `line_${index}_${fieldName.replace(/\s+/g, '_')}`;
                    fields[fieldKey] = fieldValue;
                }
            }
        });

        return fields;
    };

    const reconstructYamlWithEdits = (originalYaml: string, editedFields: { [key: string]: string }) => {
        const lines = originalYaml.split('\n');

        lines.forEach((line, index) => {
            if (line.includes('##editable')) {
                const cleanLine = line.replace(/##editable.*$/, '').trim();
                const colonIndex = cleanLine.lastIndexOf(':');
                if (colonIndex !== -1) {
                    const fieldName = cleanLine.substring(0, colonIndex).trim();
                    const fieldKey = `line_${index}_${fieldName.replace(/\s+/g, '_')}`;

                    if (editedFields[fieldKey] !== undefined) {
                        const indentation = line.match(/^\s*/)?.[0] || '';
                        const comment = line.match(/##editable.*$/)?.[0] || '';
                        lines[index] = `${indentation}${fieldName}: "${editedFields[fieldKey]}" ${comment}`;
                    }
                }
            }
        });

        return lines.join('\n');
    };

    const showYamlModalHandler = (application: PolicyApplication) => {
        setSelectedYamlContent(application.applied_yaml || '');
        setShowYamlModal(true);
    };

    const showRemoveConfirmModal = (applicationId: number, policyName: string) => {
        setRemoveModalData({ applicationId, policyName });
        setShowRemoveModal(true);
    };

   

    const handleRemovePolicy = async () => {
        if (!removeModalData) return;

        setRemovingPolicy(true);
        try {
            const response = await fetch(`${POLICIES_API}/applications/${removeModalData.applicationId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            const data = await response.json();

            if (data.success) {
                showToast('Policy removed successfully from cluster', 'success');
                fetchApplications();
                if (selectedClusterName) {
                    fetchAvailablePoliciesForCluster(selectedClusterName);
                    fetchAppliedPoliciesForCluster(selectedClusterName);
                }
                setShowRemoveModal(false);
                setRemoveModalData(null);
            } else {
                showToast(data.message || 'Failed to remove policy', 'error');
            }
        } catch (error) {
            console.error('Error removing policy:', error);
            showToast('Failed to remove policy. Please try again.', 'error');
        } finally {
            setRemovingPolicy(false);
        }
    };

    // API Functions
    const fetchClusters = async () => {
        try {
            const response = await fetch(`${KUBECONFIG_API}/clusters`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });
            const data = await response.json();
            if (data.clusters) {
                setClusters(data.clusters);
                if (data.clusters.length > 0 && !selectedClusterName) {
                    setSelectedClusterName(data.clusters[0].cluster_name);
                }
            }
        } catch (error) {
            console.error('Error fetching clusters:', error);
            showToast('Failed to fetch clusters', 'error');
        }
    };

    const fetchCategories = async () => {
        setCategoriesLoading(true);
        try {
            const response = await fetch(`${POLICIES_API}/categories`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Security service not available. Please ensure the backend is running on port 8005.');
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                setCategories(data.data);
            } else {
                throw new Error(data.message || 'Failed to fetch categories');
            }
        } catch (error) {
            console.error('Error fetching categories:', error);
            showToast('Security service unavailable. Please start the backend service.', 'error');
        } finally {
            setCategoriesLoading(false);
        }
    };

    const fetchPoliciesByCategory = async (categoryName: string) => {
        setPoliciesLoading(true);
        try {
            const response = await fetch(`${POLICIES_API}/categories/${categoryName}?page=${currentPage}&size=${pageSize}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                setPolicies(data.data.policies);
                setTotalPages(data.data.total_pages);
                calculateStats(data.data.policies);
            }
        } catch (error) {
            console.error('Error fetching policies:', error);
            showToast('Failed to fetch policies', 'error');
        } finally {
            setPoliciesLoading(false);
        }
    };

    const fetchApplications = async () => {
        setApplicationsLoading(true);
        try {
            const requestBody = {
                page: 1,
                size: 100,
                cluster_name: selectedClusterName || undefined,
                status: statusFilter || undefined
            };

            const response = await fetch(`${POLICIES_API}/applications/list`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.warn('Policy applications service not available');
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                setApplications(data.data.applications);
                setFilteredApplications(data.data.applications);
            }
        } catch (error) {
            console.error('Error fetching applications:', error);
            showToast('Failed to load policy applications. Please refresh the page.', 'error');
        } finally {
            setApplicationsLoading(false);
        }
    };


    const fetchPolicyById = async (policyId: string) => {
        try {
            const response = await fetch(`${POLICIES_API}/${policyId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                return data.data;
            }
            return null;
        } catch (error) {
            console.error('Error fetching policy by ID:', error);
            return null;
        }
    };

    const fetchEditablePolicy = async (policyId: string) => {
        try {
            const response = await fetch(`${POLICIES_API}/${policyId}/editable`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                return data.data;
            }
            return null;
        } catch (error) {
            console.error('Error fetching editable policy:', error);
            return null;
        }
    };

    const fetchEditedApplications = async () => {
        try {
            const params = new URLSearchParams({
                page: '1',
                size: '50'
            });
            if (selectedClusterName) {
                params.append('cluster_name', selectedClusterName);
            }

            const response = await fetch(`${POLICIES_API}/applications/edited?${params}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                return data.data.applications;
            }
            return [];
        } catch (error) {
            console.error('Error fetching edited applications:', error);
            return [];
        }
    };

    const fetchYamlComparison = async (applicationId: number) => {
        try {
            const response = await fetch(`${POLICIES_API}/applications/${applicationId}/yaml-comparison`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                return data.data;
            }
            return null;
        } catch (error) {
            console.error('Error fetching YAML comparison:', error);
            return null;
        }
    };

    const fetchClusterOverview = async () => {
        try {
            const response = await fetch(`${POLICIES_API}/clusters/overview`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.warn('Cluster overview service not available');
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                setClusterOverview(data.data);
            }
        } catch (error) {
            console.error('Error fetching cluster overview:', error);
        }
    };

    const fetchCategoryStats = async (categoryName: string) => {
        try {
            const response = await fetch(`${POLICIES_API}/categories/${categoryName}/stats`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                setStats(data.data);
            }
        } catch (error) {
            console.error('Error fetching category stats:', error);
        }
    };

    const fetchAvailablePoliciesForCluster = async (clusterName: string) => {
        try {
            const response = await fetch(`${POLICIES_API}/clusters/${clusterName}/available-policies?page=1&size=100`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                setAvailablePolicies(data.data.policies);
            }
        } catch (error) {
            console.error('Error fetching available policies:', error);
        }
    };

    const fetchAppliedPoliciesForCluster = async (clusterName: string) => {
        try {
            const response = await fetch(`${POLICIES_API}/clusters/${clusterName}/applied-policies?page=1&size=100`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                setAppliedPoliciesForCluster(data.data.applications);
            }
        } catch (error) {
            console.error('Error fetching applied policies:', error);
        }
    };

    const fetchPolicyApplicationDetails = async (applicationId: number) => {
        try {
            const response = await fetch(`${POLICIES_API}/applications/${applicationId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                return data.data;
            }
            return null;
        } catch (error) {
            console.error('Error fetching policy application details:', error);
            return null;
        }
    };

    
    const applyPolicy = async (policy: Policy, editedYaml?: string) => {
        if (!selectedClusterName) {
            showToast('Please select a cluster first', 'error');
            return;
        }

        setApplyingPolicy(policy.policy_id);
        try {
            const requestBody = {
                cluster_name: selectedClusterName,
                policy_id: policy.policy_id,
                kubernetes_namespace: "cluster-wide",
                edited_yaml: editedYaml || undefined
            };

            const response = await fetch(`${POLICIES_API}/apply`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (data.success) {
                showToast(`Policy "${policy.name}" ${editedYaml ? '(edited)' : ''} applied successfully to ${selectedClusterName}`, 'success');
                fetchApplications();
                fetchAvailablePoliciesForCluster(selectedClusterName);
                fetchAppliedPoliciesForCluster(selectedClusterName);
            } else {
                // Only show "already applied" error if no edited YAML is provided
                if (data.message && data.message.includes('already applied') && !editedYaml) {
                    showToast(`Policy "${policy.name}" is already applied to this cluster`, 'error');
                } else {
                    showToast(data.message || 'Failed to apply policy', 'error');
                }
            }
        } catch (error) {
            console.error('Error applying policy:', error);
            showToast('Failed to apply policy. Please check your connection and try again.', 'error');
        } finally {
            setApplyingPolicy(null);
        }
    };

        

    // Utility functions
    const calculateStats = (policiesList: Policy[]) => {
        const severityBreakdown = { critical: 0, high: 0, medium: 0, low: 0 };
        policiesList.forEach(policy => {
            if (policy.severity in severityBreakdown) {
                severityBreakdown[policy.severity as keyof typeof severityBreakdown]++;
            }
        });

        setStats({
            totalPolicies: policiesList.length,
            appliedPolicies: applications.filter(app => app.status === 'applied' || app.status === 'APPLIED').length,
            failedPolicies: applications.filter(app => app.status === 'failed' || app.status === 'FAILED').length,
            pendingPolicies: applications.filter(app => app.status === 'pending' || app.status === 'PENDING').length,
            severityBreakdown
        });
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'critical': return 'text-red-600 bg-red-100 dark:bg-red-900/20';
            case 'high': return 'text-orange-600 bg-orange-100 dark:bg-orange-900/20';
            case 'medium': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20';
            case 'low': return 'text-green-600 bg-green-100 dark:bg-green-900/20';
            default: return 'text-gray-600 bg-gray-100 dark:bg-gray-900/20';
        }
    };

    const getStatusColor = (status: string) => {
        const normalizedStatus = status.toLowerCase();
        switch (normalizedStatus) {
            case 'applied': return 'text-green-600 bg-green-100 dark:bg-green-900/20';
            case 'failed': return 'text-red-600 bg-red-100 dark:bg-red-900/20';
            case 'pending': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20';
            case 'applying': return 'text-blue-600 bg-blue-100 dark:bg-blue-900/20';
            case 'removed': return 'text-gray-600 bg-gray-100 dark:bg-gray-900/20';
            default: return 'text-gray-600 bg-gray-100 dark:bg-gray-900/20';
        }
    };

    const getCategoryIcon = (categoryName: string) => {
        switch (categoryName) {
            case 'validation': return Shield;
            case 'mutation': return Edit3;
            case 'generation': return Plus;
            case 'cleanup': return Trash2;
            case 'image_verification': return Lock;
            case 'miscellaneous': return Settings;
            default: return Shield;
        }
    };

    const filteredPolicies = policies.filter(policy => {
        const matchesSearch = policy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            policy.description.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesSeverity = !severityFilter || policy.severity === severityFilter;
        return matchesSearch && matchesSeverity;
    });

    const sortedPolicies = [...filteredPolicies].sort((a, b) => {
        let comparison = 0;
        switch (sortBy) {
            case 'name':
                comparison = a.name.localeCompare(b.name);
                break;
            case 'severity':
                const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
                comparison = (severityOrder[a.severity as keyof typeof severityOrder] || 0) -
                    (severityOrder[b.severity as keyof typeof severityOrder] || 0);
                break;
            case 'created_at':
                comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
                break;
        }
        return sortOrder === 'asc' ? comparison : -comparison;
    });

    // Event handlers
    const handlePolicyClick = async (policy: Policy) => {
        setSelectedPolicy(policy);
        setOriginalYaml(policy.yaml_content);
        setEditedYaml(policy.yaml_content);

        // Extract editable fields
        const fields = extractEditableFields(policy.yaml_content);
        setEditableFields(fields);

        setShowPolicyModal(true);
    };

    const handleApplyPolicy = () => {
        if (!selectedPolicy) return;

        if (showYamlEditor && editedYaml !== originalYaml) {
            // Apply with edited YAML
            applyPolicyWithEdits(selectedPolicy, editedYaml);
        } else {
            // Apply original policy
            applyPolicy(selectedPolicy);
        }
        setShowPolicyModal(false);
    };
    const initializePolicies = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${POLICIES_API}/initialize`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                showToast('Policy initialized successfully!', 'success');
                // Refresh the categories and policies after initialization
                await fetchCategories();
                if (selectedCategory) {
                    await fetchPoliciesByCategory(selectedCategory);
                }
            } else {
                showToast(data.message || 'Failed to initialize policies', 'error');
            }
        } catch (error) {
            console.error('Error initializing policies:', error);
            showToast('Failed to initialize policy database', 'error');
        } finally {
            setLoading(false);
        }
    };


   // In the modal, update the field change handler:
const handleFieldChange = (fieldKey: string, value: string) => {
    setEditableFields(prev => ({
        ...prev,
        [fieldKey]: value
    }));

    // Update YAML with new field values
    const updatedYaml = reconstructYamlWithEdits(originalYaml, {
        ...editableFields,
        [fieldKey]: value
    });
    setEditedYaml(updatedYaml);
};


    const handleClusterChange = (clusterName: string) => {
        setSelectedClusterName(clusterName);
        fetchAvailablePoliciesForCluster(clusterName);
        fetchAppliedPoliciesForCluster(clusterName);
    };

    const handleCategorySelect = (categoryName: string) => {
        setSelectedCategory(categoryName);
        setCurrentPage(1);
        fetchPoliciesByCategory(categoryName);
        fetchCategoryStats(categoryName);
    };


    // Effects
    useEffect(() => {
        const initializeData = async () => {
            setLoading(true);
            try {
                await Promise.all([
                    fetchClusters(),
                    fetchCategories(),
                    fetchClusterOverview()
                ]);
            } catch (error) {
                console.error('Error initializing data:', error);
            } finally {
                setLoading(false);
            }
        };

        initializeData();
    }, []);

    const loadData = async () => {
        setRefreshing(true);
        try {
            await Promise.all([
                fetchClusters(),
                fetchCategories(),
                fetchApplications()
            ]);
        } finally {
            setRefreshing(false);
        }
    };

    // Effects
    useEffect(() => {
        loadData();
        fetchClusterOverview();
    }, []);

    useEffect(() => {
        if (statusFilter) {
            setFilteredApplications(applications.filter(app => app.status === statusFilter));
        } else {
            setFilteredApplications(applications);
        }
    }, [applications, statusFilter]);


    useEffect(() => {
        if (selectedCluster && selectedCluster !== selectedClusterName) {
            setSelectedClusterName(selectedCluster);
        }
    }, [selectedCluster]);

    useEffect(() => {
        if (selectedClusterName) {
            fetchApplications();
            fetchAvailablePoliciesForCluster(selectedClusterName);
            fetchAppliedPoliciesForCluster(selectedClusterName);
        }
    }, [selectedClusterName, statusFilter]);

    useEffect(() => {
        if (selectedCategory) {
            fetchPoliciesByCategory(selectedCategory);
        }
    }, [currentPage, selectedCategory]);

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-blue-900/20 dark:to-indigo-900/20 flex items-center justify-center">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center"
                >
                    <div className="relative">
                        <div className="w-20 h-20 border-4 border-blue-200 dark:border-blue-800 rounded-full animate-spin border-t-blue-600 dark:border-t-blue-400 mx-auto mb-4"></div>
                        <div className="absolute inset-0 w-20 h-20 border-4 border-transparent rounded-full animate-ping border-t-blue-400 mx-auto"></div>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Loading Policies</h3>
                    <p className="text-gray-600 dark:text-gray-400">Fetching security policies and configurations...</p>
                </motion.div>
            </div>
        );
    }


    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                    <div className="p-3 bg-gradient-to-r from-blue-500 to-cyan-600 rounded-2xl shadow-lg">
                        <Shield className="w-8 h-8 text-white" />
                    </div>
                    <div>
                        <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-300 bg-clip-text text-transparent">
                            Security Policies
                        </h1>
                        <p className="text-gray-600 dark:text-gray-400 mt-1">
                            Manage and apply Kubernetes security policies across your clusters
                        </p>
                    </div>
                </div>

                <div className="flex items-center space-x-4">
                    <button
                        onClick={() => setShowStatsModal(true)}
                        className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl"
                    >
                        <BarChart3 className="w-4 h-4" />
                        <span>Statistics</span>
                    </button>
                    <button
                        onClick={initializePolicies}
                        className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl"
                    >
                        <Database className="w-4 h-4" />
                        <span>Initialize Policies</span>
                    </button>
                    <button
                        onClick={loadData}
                        disabled={refreshing}
                        className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-cyan-600 hover:from-blue-600 hover:to-cyan-700 text-white font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50"
                    >
                        <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                        <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
                    </button>

                </div>
            </div>


            {/* Cluster Selection */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 p-6 mb-6"
            >
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
                        <Server className="w-5 h-5 mr-2 text-blue-600 dark:text-blue-400" />
                        Select Target Cluster
                    </h3>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                        {clusters.length} clusters available
                    </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {clusters.map((cluster) => (
                        <motion.div
                            key={cluster.id}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => handleClusterChange(cluster.cluster_name)}
                            className={`p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 ${selectedClusterName === cluster.cluster_name
                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 shadow-lg'
                                : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 bg-gray-50 dark:bg-gray-700/50'
                                }`}
                        >
                            <div className="flex items-center justify-between mb-2">
                                <h4 className="font-semibold text-gray-900 dark:text-white">
                                    {cluster.cluster_name}
                                </h4>
                                {cluster.is_operator_installed && (
                                    <CheckCircle className="w-4 h-4 text-green-500" />
                                )}
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                                {cluster.provider_name}
                            </p>
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-gray-500 dark:text-gray-400">
                                    {cluster.server_url}
                                </span>
                                {selectedClusterName === cluster.cluster_name && (
                                    <Check className="w-4 h-4 text-blue-500" />
                                )}
                            </div>
                        </motion.div>
                    ))}
                </div>
            </motion.div>


            {/* Policy Categories */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 p-6 mb-6"
            >
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
                        <Layers className="w-5 h-5 mr-2 text-purple-600 dark:text-purple-400" />
                        Policy Categories
                    </h3>
                    {categoriesLoading && (
                        <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                    )}
                </div>

                {categories.length === 0 ? (
                    <div className="text-center py-12">
                        <Shield className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
                        <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                            No Policy Categories Found
                        </h4>
                        <p className="text-gray-600 dark:text-gray-400 mb-4">
                            Initialize the policy database to load predefined security policies.
                        </p>
                        <button
                            onClick={initializePolicies}
                            className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-600 hover:from-blue-600 hover:to-cyan-700 text-white font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl mx-auto"
                        >
                            <Database className="w-4 h-4" />
                            <span>Initialize Policy Database</span>
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {categories.map((category) => {
                            const IconComponent = getCategoryIcon(category.name);
                            return (
                                <motion.div
                                    key={category.id}
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    onClick={() => handleCategorySelect(category.name)}
                                    className={`p-6 rounded-xl border-2 cursor-pointer transition-all duration-200 ${selectedCategory === category.name
                                        ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/30 shadow-lg'
                                        : 'border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600 bg-gray-50 dark:bg-gray-700/50'
                                        }`}
                                >
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center space-x-3">
                                            <IconComponent className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                                            <h4 className="font-semibold text-gray-900 dark:text-white">
                                                {category.display_name}
                                            </h4>
                                        </div>
                                        <span className="text-sm font-medium text-purple-600 dark:text-purple-400 bg-purple-100 dark:bg-purple-900/50 px-2 py-1 rounded-full">
                                            {category.policy_count}
                                        </span>
                                    </div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                                        {category.description}
                                    </p>
                                    {selectedCategory === category.name && (
                                        <div className="flex items-center text-purple-600 dark:text-purple-400">
                                            <Check className="w-4 h-4 mr-1" />
                                            <span className="text-sm font-medium">Selected</span>
                                        </div>
                                    )}
                                </motion.div>
                            );
                        })}
                    </div>
                )}
            </motion.div>


            {/* Policies Grid */}
            {selectedCategory && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 p-6 mb-6"
                >
                    {/* Search and Filters */}
                    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
                        <div className="flex items-center space-x-4">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                                <input
                                    type="text"
                                    placeholder="Search policies..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                            </div>

                            <select
                                value={severityFilter}
                                onChange={(e) => setSeverityFilter(e.target.value)}
                                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="">All Severities</option>
                                <option value="critical">Critical</option>
                                <option value="high">High</option>
                                <option value="medium">Medium</option>
                                <option value="low">Low</option>
                            </select>
                        </div>

                        <div className="flex items-center space-x-4">
                            <div className="flex items-center space-x-2">
                                <button
                                    onClick={() => setViewMode('grid')}
                                    className={`p-2 rounded-lg ${viewMode === 'grid' ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}
                                >
                                    <Grid className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => setViewMode('list')}
                                    className={`p-2 rounded-lg ${viewMode === 'list' ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}
                                >
                                    <List className="w-4 h-4" />
                                </button>
                            </div>

                            <select
                                value={`${sortBy}-${sortOrder}`}
                                onChange={(e) => {
                                    const [field, order] = e.target.value.split('-');
                                    setSortBy(field as 'name' | 'severity' | 'created_at');
                                    setSortOrder(order as 'asc' | 'desc');
                                }}
                                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="name-asc">Name A-Z</option>
                                <option value="name-desc">Name Z-A</option>
                                <option value="severity-desc">Severity High-Low</option>
                                <option value="severity-asc">Severity Low-High</option>
                                <option value="created_at-desc">Newest First</option>
                                <option value="created_at-asc">Oldest First</option>
                            </select>
                        </div>
                    </div>

                    {/* Policies Loading */}
                    {policiesLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="w-8 h-8 animate-spin text-blue-500 mr-3" />
                            <span className="text-gray-600 dark:text-gray-400">Loading policies...</span>
                        </div>
                    ) : sortedPolicies.length === 0 ? (
                        <div className="text-center py-12">
                            <FileText className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
                            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                                No Policies Found
                            </h4>
                            <p className="text-gray-600 dark:text-gray-400">
                                {searchTerm || severityFilter ? 'Try adjusting your search criteria.' : 'No policies available in this category.'}
                            </p>
                        </div>
                    ) : (
                        <>
                            {/* Policies Grid/List */}
                            <div className={viewMode === 'grid'
                                ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                                : "space-y-4"
                            }>
                                {sortedPolicies.map((policy, index) => {
                                    const isApplied = applications.some(app =>
                                        app.policy?.policy_id === policy.policy_id &&
                                        app.cluster_name === selectedClusterName &&
                                        app.status === 'applied'
                                    );

                                    return (
                                        <motion.div
                                            key={policy.id}
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: index * 0.1 }}
                                            className={`bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 rounded-xl shadow-lg border border-gray-200/50 dark:border-gray-700/50 hover:shadow-xl transition-all duration-300 ${viewMode === 'list' ? 'flex items-center p-4' : 'p-6'
                                                }`}
                                        >
                                            {viewMode === 'grid' ? (
                                                <>
                                                    {/* Grid View */}
                                                    <div className="flex items-start justify-between mb-4">
                                                        <div className="flex items-center space-x-3">
                                                            <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-600 rounded-lg">
                                                                <Shield className="w-4 h-4 text-white" />
                                                            </div>
                                                            <div>
                                                                <h4 className="font-semibold text-gray-900 dark:text-white text-sm">
                                                                    {policy.name}
                                                                </h4>
                                                                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getSeverityColor(policy.severity)}`}>
                                                                    {policy.severity.toUpperCase()}
                                                                </span>
                                                            </div>
                                                        </div>
                                                        <button
                                                            onClick={() => handlePolicyClick(policy)}
                                                            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                                        >
                                                            <Eye className="w-4 h-4" />
                                                        </button>
                                                    </div>

                                                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-3">
                                                        {policy.description}
                                                    </p>

                                                    {policy.tags && policy.tags.length > 0 && (
                                                        <div className="flex flex-wrap gap-1 mb-4">
                                                            {policy.tags.slice(0, 3).map((tag, tagIndex) => (
                                                                <span
                                                                    key={tagIndex}
                                                                    className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                                                                >
                                                                    <Tag className="w-3 h-3 mr-1" />
                                                                    {tag}
                                                                </span>
                                                            ))}
                                                            {policy.tags.length > 3 && (
                                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                                                                    +{policy.tags.length - 3}
                                                                </span>
                                                            )}
                                                        </div>
                                                    )}

                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center space-x-2">
                                                            <button
                                                                onClick={() => handlePolicyClick(policy)}
                                                                className="flex items-center space-x-2 px-3 py-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                                                            >
                                                                <Eye className="w-4 h-4" />
                                                                <span className="text-sm">View</span>
                                                            </button>
                                                            <button
                                                                onClick={() => {
                                                                    navigator.clipboard.writeText(policy.yaml_content);
                                                                    showToast('YAML copied to clipboard', 'success');
                                                                }}
                                                                className="flex items-center space-x-2 px-3 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg transition-colors"
                                                            >
                                                                <Copy className="w-4 h-4" />
                                                                <span className="text-sm">Copy</span>
                                                            </button>
                                                        </div>

                                                        <button
                                                            onClick={() => {
                                                                if (!selectedClusterName) {
                                                                    showToast('Please select a cluster first', 'error');
                                                                    return;
                                                                }
                                                                if (isApplied) {
                                                                    showToast(`Policy "${policy.name}" is already applied to this cluster`, 'error');
                                                                    return;
                                                                }
                                                                applyPolicy(policy);
                                                            }}
                                                            disabled={!selectedClusterName || applyingPolicy === policy.policy_id || isApplied}
                                                            className={`flex items-center space-x-2 px-4 py-2 font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl ${isApplied
                                                                ? 'bg-gray-400 text-white cursor-not-allowed'
                                                                : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white disabled:opacity-50 disabled:cursor-not-allowed'
                                                                }`}
                                                        >
                                                            {applyingPolicy === policy.policy_id ? (
                                                                <>
                                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                                    <span className="text-sm">Applying...</span>
                                                                </>
                                                            ) : isApplied ? (
                                                                <>
                                                                    <Check className="w-4 h-4" />
                                                                    <span className="text-sm">Applied</span>
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <Play className="w-4 h-4" />
                                                                    <span className="text-sm">Apply</span>
                                                                </>
                                                            )}
                                                        </button>
                                                    </div>
                                                </>
                                            ) : (
                                                <>
                                                    {/* List View */}
                                                    <div className="flex items-center space-x-4 flex-1">
                                                        <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-600 rounded-lg">
                                                            <Shield className="w-4 h-4 text-white" />
                                                        </div>
                                                        <div className="flex-1">
                                                            <div className="flex items-center space-x-3 mb-1">
                                                                <h4 className="font-semibold text-gray-900 dark:text-white">
                                                                    {policy.name}
                                                                </h4>
                                                                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getSeverityColor(policy.severity)}`}>
                                                                    {policy.severity.toUpperCase()}
                                                                </span>
                                                            </div>
                                                            <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                                                                {policy.description}
                                                            </p>
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center space-x-2">
                                                        <button
                                                            onClick={() => handlePolicyClick(policy)}
                                                            className="flex items-center space-x-2 px-3 py-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                                                        >
                                                            <Eye className="w-4 h-4" />
                                                            <span className="text-sm">View</span>
                                                        </button>

                                                        <button
                                                            onClick={() => {
                                                                if (!selectedClusterName) {
                                                                    showToast('Please select a cluster first', 'error');
                                                                    return;
                                                                }
                                                                if (isApplied) {
                                                                    showToast(`Policy "${policy.name}" is already applied to this cluster`, 'error');
                                                                    return;
                                                                }
                                                                applyPolicy(policy);
                                                            }}
                                                            disabled={!selectedClusterName || applyingPolicy === policy.policy_id || isApplied}
                                                            className={`flex items-center space-x-2 px-4 py-2 font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl ${isApplied
                                                                ? 'bg-gray-400 text-white cursor-not-allowed'
                                                                : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white disabled:opacity-50 disabled:cursor-not-allowed'
                                                                }`}
                                                        >
                                                            {applyingPolicy === policy.policy_id ? (
                                                                <>
                                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                                    <span className="text-sm">Applying...</span>
                                                                </>
                                                            ) : isApplied ? (
                                                                <>
                                                                    <Check className="w-4 h-4" />
                                                                    <span className="text-sm">Applied</span>
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <Play className="w-4 h-4" />
                                                                    <span className="text-sm">Apply</span>
                                                                </>
                                                            )}
                                                        </button>
                                                    </div>
                                                </>
                                            )}
                                        </motion.div>
                                    );
                                })}
                            </div>

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
                                    <div className="text-sm text-gray-600 dark:text-gray-400">
                                        Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalPolicies)} of {totalPolicies} policies
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <button
                                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                                            disabled={currentPage === 1}
                                            className="px-3 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                        >
                                            <ChevronLeft className="w-4 h-4" />
                                        </button>

                                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                            const pageNum = i + 1;
                                            return (
                                                <button
                                                    key={pageNum}
                                                    onClick={() => setCurrentPage(pageNum)}
                                                    className={`px-3 py-2 rounded-lg transition-colors ${currentPage === pageNum
                                                        ? 'bg-blue-600 text-white'
                                                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'
                                                        }`}
                                                >
                                                    {pageNum}
                                                </button>
                                            );
                                        })}

                                        <button
                                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                                            disabled={currentPage === totalPages}
                                            className="px-3 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                        >
                                            <ChevronRight className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </motion.div>
            )}

                       {/* Applied Policies Section */}
            {selectedClusterName && applications.filter(app => app.status !== 'removed').length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 p-6"
                >
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
                            <CheckCircle className="w-5 h-5 mr-2 text-green-600 dark:text-green-400" />
                            Applied Policies - {selectedClusterName}
                        </h3>
                        <div className="flex items-center space-x-4">
                            <select
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="">All Status</option>
                                <option value="applied">Applied</option>
                                <option value="failed">Failed</option>
                                <option value="pending">Pending</option>
                                <option value="applying">Applying</option>
                            </select>
                            {applicationsLoading && (
                                <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                            )}
                        </div>
                    </div>

                    {applicationsLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="w-8 h-8 animate-spin text-blue-500 mr-3" />
                            <span className="text-gray-600 dark:text-gray-400">Loading applied policies...</span>
                        </div>
                    ) : filteredApplications.filter(app => app.status !== 'removed').length === 0 ? (
                        <div className="text-center py-12">
                            <Shield className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
                            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                                No Applied Policies
                            </h4>
                            <p className="text-gray-600 dark:text-gray-400">
                                {statusFilter ? 'No policies match the selected status filter.' : `No policies have been applied to ${selectedClusterName} yet.`}
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {filteredApplications.filter(app => app.status !== 'removed').map((application, index) => (
                                <motion.div
                                    key={application.id}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.1 }}
                                    className="bg-gradient-to-r from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 rounded-xl p-6 border border-gray-200/50 dark:border-gray-700/50 shadow-lg hover:shadow-xl transition-all duration-300"
                                >
                                    {/* Rest of the application card content remains the same */}
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center space-x-4">
                                            <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg">
                                                <Shield className="w-5 h-5 text-white" />
                                            </div>
                                            <div>
                                                <h4 className="font-semibold text-gray-900 dark:text-white">
                                                    {application.policy?.name || 'Unknown Policy'}
                                                </h4>
                                                <div className="flex items-center space-x-3 mt-1">
                                                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(application.status)}`}>
                                                        {application.status.toUpperCase()}
                                                    </span>
                                                    {application.policy?.severity && (
                                                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getSeverityColor(application.policy.severity)}`}>
                                                            {application.policy.severity.toUpperCase()}
                                                        </span>
                                                    )}
                                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                                        Applied: {new Date(application.created_at).toLocaleDateString()}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center space-x-2">
                                            <button
                                                onClick={() => {
                                                    setSelectedYamlContent(application.applied_yaml || '');
                                                    setShowYamlModal(true);
                                                }}
                                                className="flex items-center space-x-2 px-3 py-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                                            >
                                                <FileText className="w-4 h-4" />
                                                <span className="text-sm">View YAML</span>
                                            </button>

                                            {application.status === 'applied' && (
                                                <button
                                                    onClick={() => {
                                                        setRemoveModalData({
                                                            applicationId: application.id,
                                                            policyName: application.policy?.name || 'Unknown Policy'
                                                        });
                                                        setShowRemoveModal(true);
                                                    }}
                                                    className="flex items-center space-x-2 px-3 py-2 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                    <span className="text-sm">Remove</span>
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    {application.error_message && (
                                        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                                            <p className="text-sm text-red-600 dark:text-red-400">
                                                <strong>Error:</strong> {(() => {
                                                    const errorMsg = application.error_message;
                                                    if (errorMsg.includes('404') || errorMsg.includes('Not Found')) {
                                                        return 'Policy or resource not found';
                                                    } else if (errorMsg.includes('500') || errorMsg.includes('Internal Server Error')) {
                                                        return 'Server error occurred during policy application';
                                                    } else if (errorMsg.includes('403') || errorMsg.includes('Forbidden')) {
                                                        return 'Access denied - insufficient permissions';
                                                    } else if (errorMsg.includes('401') || errorMsg.includes('Unauthorized')) {
                                                        return 'Authentication failed - please log in again';
                                                    } else if (errorMsg.includes('timeout') || errorMsg.includes('network')) {
                                                        return 'Network connection failed';
                                                    } else if (errorMsg.includes('HTTP response headers') || errorMsg.includes('HTTPHeaderDict') || errorMsg.includes('Audit-Id')) {
                                                        return 'Policy application failed - please try again';
                                                    } else if (errorMsg.includes('already exists') || errorMsg.includes('AlreadyExists')) {
                                                        return 'Policy already exists in the cluster';
                                                    } else if (errorMsg.includes('validation failed') || errorMsg.includes('invalid')) {
                                                        return 'Policy validation failed - check policy configuration';
                                                    } else if (errorMsg.length > 100) {
                                                        return 'Policy application failed - contact support if issue persists';
                                                    } else {
                                                        return errorMsg;
                                                    }
                                                })()}
                                            </p>
                                        </div>
                                    )}

                                    {application.application_log && !application.application_log.includes('HTTP response headers') && !application.application_log.includes('Audit-Id') && (
                                        <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg">
                                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                                <strong>Log:</strong> {(() => {
                                                    const logMsg = application.application_log;
                                                    if (logMsg.includes('404') || logMsg.includes('Not Found')) {
                                                        return 'Policy application failed - resource not found';
                                                    } else if (logMsg.includes('500') || logMsg.includes('Internal Server Error')) {
                                                        return 'Policy application failed - server error';
                                                    } else if (logMsg.includes('Failed to apply policy')) {
                                                        return 'Policy application failed - please check cluster connectivity';
                                                    } else if (logMsg.length > 200) {
                                                        return 'Policy application completed with warnings';
                                                    } else {
                                                        return logMsg;
                                                    }
                                                })()}
                                            </p>
                                        </div>
                                    )}
                                </motion.div>
                            ))}
                        </div>
                    )}
                </motion.div>
            )}





            {/* Policy Detail Modal */}
            <AnimatePresence>
                {showPolicyModal && selectedPolicy && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                        onClick={() => setShowPolicyModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden"
                            onClick={(e) => e.stopPropagation()}
                        >
                            {/* Modal Header */}
                            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
                                <div className="flex items-center space-x-4">
                                    <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-600 rounded-lg">
                                        <Shield className="w-6 h-6 text-white" />
                                    </div>
                                    <div>
                                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                                            {selectedPolicy.name}
                                        </h2>
                                        <div className="flex items-center space-x-3 mt-1">
                                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getSeverityColor(selectedPolicy.severity)}`}>
                                                {selectedPolicy.severity.toUpperCase()}
                                            </span>
                                            <span className="text-sm text-gray-500 dark:text-gray-400">
                                                ID: {selectedPolicy.policy_id}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setShowPolicyModal(false)}
                                    className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <X className="w-6 h-6" />
                                </button>
                            </div>

                            {/* Modal Content */}
                            <div className="flex h-[calc(90vh-120px)]">
                                {/* Left Panel - Policy Info */}
                                <div className="w-1/3 p-6 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
                                    <div className="space-y-6">
                                        {/* Description */}
                                        <div>
                                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                                                Description
                                            </h3>
                                            <p className="text-gray-600 dark:text-gray-400">
                                                {selectedPolicy.description || selectedPolicy.purpose || 'No description available.'}
                                            </p>
                                        </div>

                                        {/* Purpose */}
                                        {selectedPolicy.purpose && selectedPolicy.purpose !== selectedPolicy.description && (
                                            <div>
                                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                                                    Purpose
                                                </h3>
                                                <p className="text-gray-600 dark:text-gray-400">
                                                    {selectedPolicy.purpose}
                                                </p>
                                            </div>
                                        )}

                                        {/* Tags */}
                                        {selectedPolicy.tags && selectedPolicy.tags.length > 0 && (
                                            <div>
                                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                                                    Tags
                                                </h3>
                                                <div className="flex flex-wrap gap-2">
                                                    {selectedPolicy.tags.map((tag, index) => (
                                                        <span
                                                            key={index}
                                                            className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400"
                                                        >
                                                            <Tag className="w-3 h-3 mr-1" />
                                                            {tag}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Metadata */}
                                        {selectedPolicy.policy_metadata && (
                                            <div>
                                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                                                    Metadata
                                                </h3>
                                                <div className="space-y-2">
                                                    {Object.entries(selectedPolicy.policy_metadata).map(([key, value]) => (
                                                        <div key={key} className="flex justify-between">
                                                            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                                                                {key}:
                                                            </span>
                                                            <span className="text-sm text-gray-900 dark:text-white">
                                                                {Array.isArray(value) ? value.join(', ') : String(value)}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Actions */}
                                        <div className="space-y-3">
                                            <button
                                                onClick={() => {
                                                    const finalYaml = reconstructYamlWithEdits(originalYaml, editableFields);
                                                    navigator.clipboard.writeText(finalYaml);
                                                    showToast('YAML copied to clipboard', 'success');
                                                }}
                                                className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
                                            >
                                                <Copy className="w-4 h-4" />
                                                <span>Copy YAML</span>
                                            </button>

                                                                                       <button
                                                onClick={() => {
    if (!selectedClusterName) {
        showToast('Please select a cluster first', 'error');
        return;
    }
    
    // Check if any field has been edited
    const hasEditedFields = Object.keys(editableFields).some(fieldKey => {
        const lineIndex = parseInt(fieldKey.split('_')[1]);
        const yamlLines = originalYaml.split('\n');
        const originalLine = yamlLines[lineIndex] || '';
        const originalValue = originalLine.match(/:\s*"?([^"#\n]+)"?/)?.[1]?.trim();
        return editableFields[fieldKey] !== originalValue;
    });
    
    // Always apply if fields are edited, regardless of current status
    const finalYaml = hasEditedFields ? reconstructYamlWithEdits(originalYaml, editableFields) : undefined;
    applyPolicy(selectedPolicy, finalYaml);
    setShowPolicyModal(false);
}}

                                                disabled={!selectedClusterName || applyingPolicy === selectedPolicy.policy_id}
                                                className={`w-full flex items-center justify-center space-x-2 px-4 py-3 font-medium rounded-lg transition-all duration-200 ${
                                                    !selectedClusterName || applyingPolicy === selectedPolicy.policy_id
                                                        ? 'bg-gray-400 text-white cursor-not-allowed'
                                                        : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white'
                                                }`}
                                            >
                                                {applyingPolicy === selectedPolicy.policy_id ? (
                                                    <>
                                                        <Loader2 className="w-4 h-4 animate-spin" />
                                                        <span>Applying...</span>
                                                    </>
                                                ) : (() => {
                                                    const isApplied = applications.some(app =>
                                                        app.policy?.policy_id === selectedPolicy.policy_id &&
                                                        app.cluster_name === selectedClusterName &&
                                                        app.status === 'applied'
                                                    );
                                                    
                                                    const hasEditedFields = Object.keys(editableFields).some(fieldKey => {
                                                        const lineIndex = parseInt(fieldKey.split('_')[1]);
                                                        const yamlLines = originalYaml.split('\n');
                                                        const originalLine = yamlLines[lineIndex] || '';
                                                        const originalValue = originalLine.match(/:\s*"?([^"#\n]+)"?/)?.[1]?.trim();
                                                        return editableFields[fieldKey] !== originalValue;
                                                    });
                                                    
                                                    if (isApplied && hasEditedFields) {
                                                        return (
                                                            <>
                                                                <Play className="w-4 h-4" />
                                                                <span>Apply Edited Policy</span>
                                                            </>
                                                        );
                                                    } else if (isApplied && !hasEditedFields) {
                                                        return (
                                                            <>
                                                                <Check className="w-4 h-4" />
                                                                <span>Already Applied</span>
                                                            </>
                                                        );
                                                    } else {
                                                        return (
                                                            <>
                                                                <Play className="w-4 h-4" />
                                                                <span>Apply to {selectedClusterName || 'Cluster'}</span>
                                                            </>
                                                        );
                                                    }
                                                })()}
                                            </button>

                                        </div>
                                    </div>
                                </div>

                                {/* Right Panel - YAML Editor */}
                                <div className="flex-1 flex flex-col">
                                    <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                                        <div className="flex items-center space-x-4">
                                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                                Policy YAML
                                            </h3>
                                            <div className="flex items-center space-x-2">
                                                <button
                                                    onClick={() => setShowYamlEditor(!showYamlEditor)}
                                                    className={`p-2 rounded-lg transition-colors ${showYamlEditor
                                                        ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                                                        : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
                                                        }`}
                                                >
                                                    <Code className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => setShowYamlEditor(!showYamlEditor)}
                                                    className={`p-2 rounded-lg transition-colors ${!showYamlEditor
                                                        ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                                                        : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
                                                        }`}
                                                >
                                                    <Eye className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </div>
                                        <div className="flex items-center space-x-2">
                                            <button
                                                onClick={() => {
                                                    const finalYaml = reconstructYamlWithEdits(originalYaml, editableFields);
                                                    navigator.clipboard.writeText(finalYaml);
                                                    showToast('YAML copied to clipboard', 'success');
                                                }}
                                                className="flex items-center space-x-2 px-3 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                            >
                                                <Copy className="w-4 h-4" />
                                                <span className="text-sm">Copy</span>
                                            </button>
                                        </div>
                                    </div>

                                    <div className="flex-1 flex">
                                        {/* Editable Fields Panel */}
                                        {Object.keys(editableFields).length > 0 && (
                                            <div className="w-80 p-4 border-r border-gray-200 dark:border-gray-700 overflow-y-auto bg-gray-50 dark:bg-gray-900/50">
                                                <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                                                    <Edit className="w-4 h-4 mr-2" />
                                                    Editable Fields
                                                </h4>
                                                <div className="space-y-4">
                                                    {Object.entries(editableFields).map(([fieldKey, value]) => {
                                                        const lineIndex = parseInt(fieldKey.split('_')[1]);
                                                        const yamlLines = originalYaml.split('\n');
                                                        const contextLine = yamlLines[lineIndex] || '';
                                                        const fieldName = contextLine.split(':')[0]?.trim() || `Field ${lineIndex}`;

                                                        return (
                                                            <div key={fieldKey} className="space-y-2">
                                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                                                                    {fieldName}
                                                                </label>
                                                                <input
                                                                    type="text"
                                                                    value={editableFields[fieldKey]}
                                                                    onChange={(e) => {
                                                                        setEditableFields(prev => ({
                                                                            ...prev,
                                                                            [fieldKey]: e.target.value
                                                                        }));
                                                                    }}
                                                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                                                                    placeholder={value}
                                                                />
                                                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                                                    Line {lineIndex + 1}: {contextLine.trim()}
                                                                </p>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        )}

                                        {/* YAML Display */}
                                        <div className="flex-1">
                                            {showYamlEditor ? (
                                                <Editor
                                                    height="100%"
                                                    language="yaml"
                                                    value={reconstructYamlWithEdits(originalYaml, editableFields)}
                                                    options={{
                                                        readOnly: true,
                                                        minimap: { enabled: false },
                                                        scrollBeyondLastLine: false,
                                                        fontSize: 12,
                                                        lineNumbers: 'on',
                                                        wordWrap: 'on',
                                                        folding: true,
                                                        renderLineHighlight: 'none'
                                                    }}
                                                    theme="vs-dark"
                                                />
                                            ) : (
                                                <div className="h-full overflow-auto p-4 bg-gray-900 text-gray-100 font-mono text-sm">
                                                    <pre className="whitespace-pre-wrap">
                                                        {reconstructYamlWithEdits(originalYaml, editableFields)}
                                                    </pre>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Modal Footer */}
                            <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                                <div className="flex items-center space-x-4">
                                    <div className="text-sm text-gray-600 dark:text-gray-400">
                                        {Object.keys(editableFields).length > 0 ? (
                                            <span className="flex items-center">
                                                <Edit className="w-4 h-4 mr-1" />
                                                {Object.keys(editableFields).length} editable field(s) found
                                            </span>
                                        ) : (
                                            <span>No editable fields in this policy</span>
                                        )}
                                    </div>
                                    {selectedClusterName && (
                                        <div className="text-sm text-blue-600 dark:text-blue-400">
                                            Target: {selectedClusterName}
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center space-x-3">
                                    <button
                                        onClick={() => setShowPolicyModal(false)}
                                        className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg transition-colors"
                                    >
                                        Close
                                    </button>
                                    <button
                                        onClick={() => {
                                            if (!selectedClusterName) {
                                                showToast('Please select a cluster first', 'error');
                                                return;
                                            }
                                            const isApplied = applications.some(app =>
                                                app.policy?.policy_id === selectedPolicy.policy_id &&
                                                app.cluster_name === selectedClusterName &&
                                                app.status === 'applied'
                                            );
                                            if (isApplied) {
                                                showToast(`Policy "${selectedPolicy.name}" is already applied to this cluster`, 'error');
                                                return;
                                            }
                                            // Apply policy with edited YAML
                                            const finalYaml = reconstructYamlWithEdits(originalYaml, editableFields);
                                            applyPolicy(selectedPolicy, finalYaml);
                                            setShowPolicyModal(false);
                                        }}
                                        disabled={!selectedClusterName || applyingPolicy === selectedPolicy.policy_id}
                                        className={`px-6 py-2 font-medium rounded-lg transition-all duration-200 ${applications.some(app =>
                                            app.policy?.policy_id === selectedPolicy.policy_id &&
                                            app.cluster_name === selectedClusterName &&
                                            app.status === 'applied'
                                        )
                                            ? 'bg-gray-400 text-white cursor-not-allowed'
                                            : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white disabled:opacity-50 disabled:cursor-not-allowed'
                                            }`}
                                    >
                                        {applyingPolicy === selectedPolicy.policy_id ? (
                                            <span className="flex items-center space-x-2">
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                                <span>Applying...</span>
                                            </span>
                                        ) : applications.some(app =>
                                            app.policy?.policy_id === selectedPolicy.policy_id &&
                                            app.cluster_name === selectedClusterName &&
                                            app.status === 'applied'
                                        ) ? (
                                            <span className="flex items-center space-x-2">
                                                <Check className="w-4 h-4" />
                                                <span>Already Applied</span>
                                            </span>
                                        ) : (
                                            <span className="flex items-center space-x-2">
                                                <Play className="w-4 h-4" />
                                                <span>Apply Policy</span>
                                            </span>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>






            {/* Statistics Modal */}
            <AnimatePresence>
                {showStatsModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                        onClick={() => setShowStatsModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
                            onClick={(e) => e.stopPropagation()}
                        >
                            {/* Stats Modal Header */}
                            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
                                <div className="flex items-center space-x-4">
                                    <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-600 rounded-lg">
                                        <BarChart3 className="w-6 h-6 text-white" />
                                    </div>
                                    <div>
                                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                                            Policy Statistics
                                        </h2>
                                        <p className="text-gray-600 dark:text-gray-400">
                                            {selectedClusterName ? `Overview for ${selectedClusterName}` : 'Overview of all policy applications and status'}
                                        </p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setShowStatsModal(false)}
                                    className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <X className="w-6 h-6" />
                                </button>
                            </div>

                            {/* Stats Content */}
                            <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                                    {/* Total Policies */}
                                    <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 p-6 rounded-xl border border-blue-200 dark:border-blue-700">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="p-2 bg-blue-500 rounded-lg">
                                                <FileText className="w-5 h-5 text-white" />
                                            </div>
                                            <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                                                {stats.totalPolicies}
                                            </span>
                                        </div>
                                        <h3 className="font-semibold text-blue-900 dark:text-blue-100">Total Policies</h3>
                                        <p className="text-sm text-blue-700 dark:text-blue-300">Available policies</p>
                                    </div>

                                    {/* Applied Policies */}
                                    <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/30 p-6 rounded-xl border border-green-200 dark:border-green-700">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="p-2 bg-green-500 rounded-lg">
                                                <CheckCircle className="w-5 h-5 text-white" />
                                            </div>
                                            <span className="text-2xl font-bold text-green-600 dark:text-green-400">
                                                {selectedClusterName
                                                    ? applications.filter(app => app.cluster_name === selectedClusterName && app.status === 'applied').length
                                                    : stats.appliedPolicies
                                                }
                                            </span>
                                        </div>
                                        <h3 className="font-semibold text-green-900 dark:text-green-100">Applied Policies</h3>
                                        <p className="text-sm text-green-700 dark:text-green-300">Successfully applied</p>
                                    </div>

                                    {/* Failed Policies */}
                                    <div className="bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/30 dark:to-red-800/30 p-6 rounded-xl border border-red-200 dark:border-red-700">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="p-2 bg-red-500 rounded-lg">
                                                <XCircle className="w-5 h-5 text-white" />
                                            </div>
                                            <span className="text-2xl font-bold text-red-600 dark:text-red-400">
                                                {selectedClusterName
                                                    ? applications.filter(app => app.cluster_name === selectedClusterName && app.status === 'failed').length
                                                    : stats.failedPolicies
                                                }
                                            </span>
                                        </div>
                                        <h3 className="font-semibold text-red-900 dark:text-red-100">Failed Policies</h3>
                                        <p className="text-sm text-red-700 dark:text-red-300">Policy application failed due to configuration or cluster issues</p>
                                    </div>


                                    {/* Pending Policies */}
                                    <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-900/30 dark:to-yellow-800/30 p-6 rounded-xl border border-yellow-200 dark:border-yellow-700">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="p-2 bg-yellow-500 rounded-lg">
                                                <Clock className="w-5 h-5 text-white" />
                                            </div>
                                            <span className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                                                {selectedClusterName
                                                    ? applications.filter(app => app.cluster_name === selectedClusterName && ['pending', 'applying'].includes(app.status)).length
                                                    : stats.pendingPolicies
                                                }
                                            </span>
                                        </div>
                                        <h3 className="font-semibold text-yellow-900 dark:text-yellow-100">Pending Policies</h3>
                                        <p className="text-sm text-yellow-700 dark:text-yellow-300">Awaiting application</p>
                                    </div>
                                </div>

                                {/* Severity Breakdown */}
                                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-6 mb-6">
                                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                                        Severity Breakdown {selectedClusterName && `(${selectedClusterName})`}
                                    </h3>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-red-600 dark:text-red-400 mb-1">
                                                {stats.severityBreakdown?.critical || 0}
                                            </div>
                                            <div className="text-sm text-red-700 dark:text-red-300 font-medium">Critical</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400 mb-1">
                                                {stats.severityBreakdown?.high || 0}
                                            </div>
                                            <div className="text-sm text-orange-700 dark:text-orange-300 font-medium">High</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400 mb-1">
                                                {stats.severityBreakdown?.medium || 0}
                                            </div>
                                            <div className="text-sm text-yellow-700 dark:text-yellow-300 font-medium">Medium</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-green-600 dark:text-green-400 mb-1">
                                                {stats.severityBreakdown?.low || 0}
                                            </div>
                                            <div className="text-sm text-green-700 dark:text-green-300 font-medium">Low</div>
                                        </div>
                                    </div>
                                </div>

                                {/* Cluster Overview */}
                                {clusterOverview.length > 0 && (
                                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-6">
                                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                                            {selectedClusterName ? `${selectedClusterName} Policy Overview` : 'Cluster Policy Overview'}
                                        </h3>
                                        <div className="space-y-4">
                                            {(selectedClusterName
                                                ? clusterOverview.filter(cluster => cluster.cluster.cluster_name === selectedClusterName)
                                                : clusterOverview
                                            ).map((overview, index) => {
                                                // Get unique categories applied to this cluster
                                                const categoriesApplied = overview.categories_applied || [];

                                                return (
                                                    <div key={index} className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
                                                        <div className="flex items-center justify-between mb-3">
                                                            <div className="flex items-center space-x-3">
                                                                <Server className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                                                                <div>
                                                                    <h4 className="font-semibold text-gray-900 dark:text-white">
                                                                        {overview.cluster.cluster_name}
                                                                    </h4>
                                                                    <p className="text-sm text-gray-600 dark:text-gray-400">
                                                                        {overview.cluster.provider_name || 'Unknown Provider'}
                                                                    </p>
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center space-x-4 text-sm">
                                                                <span className="text-green-600 dark:text-green-400 font-medium">
                                                                    {overview.applied_count} Applied
                                                                </span>
                                                                <span className="text-red-600 dark:text-red-400 font-medium">
                                                                    {overview.failed_count} Failed
                                                                </span>
                                                                <span className="text-yellow-600 dark:text-yellow-400 font-medium">
                                                                    {overview.pending_count} Pending
                                                                </span>
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center justify-between">
                                                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                                                Total Applications: {overview.total_applications}
                                                            </div>
                                                            {categoriesApplied.length > 0 && (
                                                                <div className="flex items-center space-x-2">
                                                                    <span className="text-sm text-gray-600 dark:text-gray-400">Categories:</span>
                                                                    <div className="flex space-x-1">
                                                                        {categoriesApplied.slice(0, 3).map((category, catIndex) => (
                                                                            <span
                                                                                key={catIndex}
                                                                                className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400"
                                                                            >
                                                                                {category}
                                                                            </span>
                                                                        ))}
                                                                        {categoriesApplied.length > 3 && (
                                                                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                                                                                +{categoriesApplied.length - 3}
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>


            {/* YAML View Modal */}
            <AnimatePresence>
                {showYamlModal && selectedYamlContent && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
                        onClick={() => setShowYamlModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-white dark:bg-gray-800 rounded-lg p-4 max-w-4xl w-full max-h-[85vh] overflow-auto"
                            onClick={(e) => e.stopPropagation()}
                        >

                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-2">
                                    <FileText className="w-5 h-5 text-blue-600" />
                                    <h2 className="text-lg font-bold text-gray-900 dark:text-white">Applied YAML</h2>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => {
                                            navigator.clipboard.writeText(selectedYamlContent);
                                            showToast('YAML copied to clipboard', 'success');
                                        }}
                                        className="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center gap-1.5"
                                    >
                                        <Copy className="w-3.5 h-3.5" />
                                        Copy
                                    </button>
                                    <button
                                        onClick={() => setShowYamlModal(false)}
                                        className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>


                            <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                                <Editor
                                    height="40vh"
                                    language="yaml"
                                    width="100%"

                                    value={selectedYamlContent}
                                    options={{
                                        readOnly: true,
                                        minimap: { enabled: false },
                                        scrollBeyondLastLine: false,
                                        fontSize: 12,
                                        lineNumbers: 'on',
                                        wordWrap: 'on'
                                    }}
                                    theme="vs-dark"
                                />
                            </div>

                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

           

            {/* Remove Confirmation Modal */}
            <AnimatePresence>
                {showRemoveModal && removeModalData && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
                        onClick={() => setShowRemoveModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center gap-3 mb-4">
                                <div className="w-10 h-10 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center">
                                    <AlertTriangle className="w-5 h-5 text-red-600" />
                                </div>
                                <h2 className="text-lg font-bold text-gray-900 dark:text-white">Remove Policy</h2>
                            </div>

                            <p className="text-gray-600 dark:text-gray-400 mb-6">
                                Are you sure you want to remove the policy "{removeModalData.policyName}" from the cluster?
                                This action cannot be undone.
                            </p>

                            <div className="flex items-center justify-end gap-3">
                                <button
                                    onClick={() => setShowRemoveModal(false)}
                                    className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleRemovePolicy}
                                    disabled={removingPolicy}
                                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                                >
                                    {removingPolicy ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Trash2 className="w-4 h-4" />
                                    )}
                                    Remove Policy
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Confirm Apply Dialog */}
            <AnimatePresence>
                {showConfirmDialog && selectedPolicy && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
                        onClick={() => setShowConfirmDialog(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center gap-3 mb-4">
                                <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center">
                                    <Shield className="w-5 h-5 text-blue-600" />
                                </div>
                                <h2 className="text-lg font-bold text-gray-900 dark:text-white">Apply Policy</h2>
                            </div>

                            <p className="text-gray-600 dark:text-gray-400 mb-6">
                                Are you sure you want to apply the policy "{selectedPolicy.name}" to cluster "{selectedClusterName}"?
                            </p>

                            <div className="flex items-center justify-end gap-3">
                                <button
                                    onClick={() => setShowConfirmDialog(false)}
                                    className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={() => {
                                        if (selectedPolicy) {
                                            applyPolicy(selectedPolicy);
                                        }
                                    }}
                                    disabled={applyingPolicy === selectedPolicy.policy_id}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                                >
                                    {applyingPolicy === selectedPolicy.policy_id ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Play className="w-4 h-4" />
                                    )}
                                    Apply Policy
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default Policies;


