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
    X,
    Check,
    AlertTriangle,
    Info,
    Loader2,
    FileText,
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
}

interface PolicyApplication {
    id: number;
    cluster_name: string;
    policy_id: string;
    policy_name: string;
    status: 'PENDING' | 'APPLYING' | 'APPLIED' | 'FAILED';
    kubernetes_namespace: string;
    applied_at: string;
    error_message?: string;
    application_log?: string;
}

interface PoliciesProps {
    selectedCluster: string;
}

export const Policies: React.FC<PoliciesProps> = ({ selectedCluster }) => {
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
    const [clusterOverview, setClusterOverview] = useState<any>(null);

    // Modal states
    const [showPolicyModal, setShowPolicyModal] = useState(false);
    const [showYamlEditor, setShowYamlEditor] = useState(true);
    const [editedYaml, setEditedYaml] = useState('');
    const [showConfirmDialog, setShowConfirmDialog] = useState(false);
    const [showStatsModal, setShowStatsModal] = useState(false);

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

    // Add these new state variables at the top with other state declarations
    const [editableFields, setEditableFields] = useState<{ [key: string]: string }>({});
    const [originalYaml, setOriginalYaml] = useState('');

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


    // Make this function available globally for the modal
    window.handleRemovePolicyConfirmed = async (applicationId: number) => {
        try {
            const response = await fetch(`${POLICIES_API}/applications/${applicationId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                showToast('Policy removed successfully from cluster', 'success');
                // Refresh the applications list
                fetchApplications();
            } else {
                showToast(data.message || 'Failed to remove policy', 'error');
            }
        } catch (error) {
            console.error('Error removing policy:', error);
            showToast('Failed to remove policy from cluster', 'error');
        }
    };

    // Add this helper function to extract editable fields from YAML
    const extractEditableFields = (yamlContent: string) => {
        const lines = yamlContent.split('\n');
        const fields: { [key: string]: string } = {};

        lines.forEach((line, index) => {
            if (line.includes('##editable')) {
                // Extract the field name and value
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

    // Add this helper function to reconstruct YAML with edited values
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
                        // Preserve indentation
                        const indentation = line.match(/^\s*/)?.[0] || '';
                        const comment = line.match(/##editable.*$/)?.[0] || '';
                        lines[index] = `${indentation}${fieldName}: "${editedFields[fieldKey]}" ${comment}`;
                    }
                }
            }
        });

        return lines.join('\n');
    };


    const showRemoveConfirmModal = (applicationId: number, policyName: string) => {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div class="flex items-center mb-4">
                <div class="flex-shrink-0 w-10 h-10 mx-auto bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center">
                    <svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                    </svg>
                </div>
            </div>
            <div class="text-center">
                <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Remove Policy</h3>
                <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
                    Are you sure you want to remove the policy "<strong>${policyName}</strong>" from the cluster? This action cannot be undone.
                </p>
                <div class="flex space-x-3">
                    <button 
                        onclick="this.closest('.fixed').remove()" 
                        class="flex-1 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                        Cancel
                    </button>
                    <button 
                        onclick="handleRemovePolicyConfirmed(${applicationId}); this.closest('.fixed').remove()" 
                        class="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                    >
                        Remove
                    </button>
                </div>
            </div>
        </div>
    `;
        document.body.appendChild(modal);
    };




    const showYamlModal = (app: PolicyApplication & { yaml?: string }) => {
        // Create a modal to show YAML content
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';

        // Get YAML content - try different possible field names
        const yamlContent = app.applied_yaml || app.yaml || 'YAML content not available';

        modal.innerHTML = `
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-4xl max-h-[80vh] overflow-auto">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Applied YAML - ${app.policy?.name || app.policy_name}</h3>
                <button class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200" onclick="this.closest('.fixed').remove()">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <pre class="bg-gray-100 dark:bg-gray-900 p-4 rounded-lg overflow-auto text-sm font-mono whitespace-pre-wrap"><code>${yamlContent}</code></pre>
        </div>
    `;
        document.body.appendChild(modal);
    };


    // Fetch functions
    const fetchAvailablePoliciesForCluster = async (clusterName: string) => {
        if (!clusterName) return;

        try {
            const params = new URLSearchParams({
                page: '1',
                size: '50'
            });
            if (selectedCategory) {
                params.append('category', selectedCategory);
            }

            const response = await fetch(`${POLICIES_API}/clusters/${clusterName}/available-policies?${params}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.warn('Available policies service not available');
                return;
            }

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
        if (!clusterName) return;

        try {
            const params = new URLSearchParams({
                page: '1',
                size: '50'
            });
            if (statusFilter) {
                params.append('status', statusFilter);
            }

            const response = await fetch(`${POLICIES_API}/clusters/${clusterName}/applied-policies?${params}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.warn('Applied policies service not available');
                return;
            }

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

    const fetchPolicyApplicationDetails = async (applicationId: number) => {
        try {
            const response = await fetch(`${POLICIES_API}/applications/${applicationId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Policy application service not available');
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                return data.data;
            }
        } catch (error) {
            console.error('Error fetching policy application details:', error);
            throw error;
        }
    };

    const removePolicyFromCluster = async (applicationId: number) => {
        try {
            const response = await fetch(`${POLICIES_API}/applications/${applicationId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Policy removal service not available');
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success) {
                showToast('Policy removed successfully', 'success');
                fetchAppliedPoliciesForCluster(selectedClusterName);
                fetchAvailablePoliciesForCluster(selectedClusterName);
                return data.data;
            } else {
                throw new Error(data.message || 'Failed to remove policy');
            }
        } catch (error) {
            console.error('Error removing policy:', error);
            showToast('Failed to remove policy', 'error');
            throw error;
        }
    };

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

            // Check if response is HTML (404 page)
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
        try {
            const requestBody = {
                page: 1,
                size: 100
            };

            if (selectedClusterName) {
                requestBody.cluster_name = selectedClusterName;
            }
            if (statusFilter) {
                requestBody.status = statusFilter;
            }

            const response = await fetch(`${POLICIES_API}/applications/list`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            // Check if response is HTML (404 page)
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.warn('Policy applications service not available');
                return; // Don't show error for applications as it's optional
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.data) {
                setApplications(data.data.applications);
            }
        } catch (error) {
            console.error('Error fetching applications:', error);
            // Don't show toast for applications as it's not critical
        }
    };


    const fetchCategoryStats = async (categoryName: string) => {
        try {
            const response = await fetch(`${POLICIES_API}/categories/${categoryName}/stats`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                }
            });
            const data = await response.json();
            if (data.success && data.data) {
                setStats(data.data);
            }
        } catch (error) {
            console.error('Error fetching category stats:', error);
        }
    };

    const initializePolicies = async () => {
        try {
            const response = await fetch(`${POLICIES_API}/initialize`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    'Content-Type': 'application/json'
                }
            });

            // Check if response is HTML (404 page)
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Security service not available. Please ensure the backend is running on port 8005.');
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success) {
                showToast('Policy initialized successfully', 'success');
                fetchCategories();
            } else {
                throw new Error(data.message || 'Failed to initialize policies');
            }
        } catch (error) {
            console.error('Error initializing policies:', error);
            showToast('Failed to initialize policies. Please check if the security service is running.', 'error');
        }
    };

    // Helper function to check if policy is already applied
    const isPolicyApplied = (policyId: string) => {
        return appliedPoliciesForCluster.some(
            app => app.policy_id === policyId &&
                ['APPLIED', 'APPLYING', 'PENDING'].includes(app.status)
        );
    };

    const applyPolicy = async (policy: Policy) => {
        if (!selectedClusterName) {
            showToast('Please select a cluster first', 'error');
            return;
        }

        // Check if policy is already applied to this cluster
        const isAlreadyApplied = appliedPoliciesForCluster.some(
            app => app.policy_id === policy.policy_id &&
                ['APPLIED', 'APPLYING', 'PENDING'].includes(app.status)
        );

        if (isAlreadyApplied) {
            showToast(`Policy "${policy.name}" is already applied or being applied to this cluster`, 'error');
            return;
        }

        setApplyingPolicy(policy.policy_id);
        try {
            const response = await fetch(`${POLICIES_API}/apply`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                },
                body: JSON.stringify({
                    cluster_name: selectedClusterName,
                    policy_id: policy.policy_id,
                    kubernetes_namespace: 'cluster-wide'
                })
            });

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Policy application service not available');
            }

            const data = await response.json();
            if (data.success) {
                showToast(`Policy "${policy.name}" applied successfully!`, 'success');
                fetchApplications();
                fetchAppliedPoliciesForCluster(selectedClusterName);
                fetchAvailablePoliciesForCluster(selectedClusterName);
            } else {
                // Handle specific error cases
                if (data.message && data.message.includes('already applied')) {
                    showToast(`Policy "${policy.name}" is already applied to this cluster`, 'error');
                } else {
                    showToast(data.message || 'Failed to apply policy', 'error');
                }
            }
        } catch (error) {
            console.error('Error applying policy:', error);
            if (error.message.includes('already applied')) {
                showToast(`Policy "${policy.name}" is already applied to this cluster`, 'error');
            } else {
                showToast('Failed to apply policy. Please check if the cluster is accessible.', 'error');
            }
        } finally {
            setApplyingPolicy(null);
            setShowConfirmDialog(false);
        }
    };

    // Add this new function after line 733
    const applyPolicyToCluster = async (policy: Policy, editedYaml?: string) => {
        if (!selectedClusterName) {
            showToast('Please select a cluster first', 'error');
            return;
        }

        setApplyingPolicy(policy.policy_id);

        try {
            const requestBody = {
                cluster_name: selectedClusterName,
                policy_id: policy.policy_id,
                kubernetes_namespace: null,
                ...(editedYaml && { edited_yaml: editedYaml }) // Include edited YAML if provided
            };

            const response = await fetch('https://10.0.32.106:8005/api/v1/policies/apply', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error(`Failed to apply policy: ${response.statusText}`);
            }

            const result = await response.json();

            if (result.success) {
                showToast(`Policy "${policy.name}" applied successfully!`, 'success');
                fetchApplications(); // Refresh applications
                fetchAppliedPoliciesForCluster(selectedClusterName);
                fetchAvailablePoliciesForCluster(selectedClusterName);
            } else {
                throw new Error(result.message || 'Failed to apply policy');
            }
        } catch (error: any) {
            console.error('Error applying policy:', error);
            showToast(`Failed to apply policy: ${error.message}`, 'error');
        } finally {
            setApplyingPolicy(null);
            setShowConfirmDialog(false);
        }
    };


    // Utility functions
    const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
        // Simple toast implementation - you can replace with your preferred toast library
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg ${type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
                'bg-blue-500 text-white'
            }`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 3000);
    };

    const calculateStats = (policiesList: Policy[]) => {
        const total = policiesList.length;
        const applied = applications.filter(app => app.status === 'APPLIED').length;
        const failed = applications.filter(app => app.status === 'FAILED').length;
        const pending = applications.filter(app => app.status === 'PENDING').length;

        const severityBreakdown = policiesList.reduce((acc, policy) => {
            acc[policy.severity] = (acc[policy.severity] || 0) + 1;
            return acc;
        }, { critical: 0, high: 0, medium: 0, low: 0 });

        setStats({
            totalPolicies: total,
            appliedPolicies: applied,
            failedPolicies: failed,
            pendingPolicies: pending,
            severityBreakdown
        });
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'critical': return 'text-red-600 bg-red-100 border-red-200 dark:text-red-400 dark:bg-red-900/30 dark:border-red-700';
            case 'high': return 'text-orange-600 bg-orange-100 border-orange-200 dark:text-orange-400 dark:bg-orange-900/30 dark:border-orange-700';
            case 'medium': return 'text-yellow-600 bg-yellow-100 border-yellow-200 dark:text-yellow-400 dark:bg-yellow-900/30 dark:border-yellow-700';
            case 'low': return 'text-green-600 bg-green-100 border-green-200 dark:text-green-400 dark:bg-green-900/30 dark:border-green-700';
            default: return 'text-gray-600 bg-gray-100 border-gray-200 dark:text-gray-400 dark:bg-gray-900/30 dark:border-gray-700';
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'APPLIED': return 'text-green-600 bg-green-100 border-green-200 dark:text-green-400 dark:bg-green-900/30 dark:border-green-700';
            case 'APPLYING': return 'text-blue-600 bg-blue-100 border-blue-200 dark:text-blue-400 dark:bg-blue-900/30 dark:border-blue-700';
            case 'PENDING': return 'text-yellow-600 bg-yellow-100 border-yellow-200 dark:text-yellow-400 dark:bg-yellow-900/30 dark:border-yellow-700';
            case 'FAILED': return 'text-red-600 bg-red-100 border-red-200 dark:text-red-400 dark:bg-red-900/30 dark:border-red-700';
            default: return 'text-gray-600 bg-gray-100 border-gray-200 dark:text-gray-400 dark:bg-gray-900/30 dark:border-gray-700';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'APPLIED': return <CheckCircle className="w-4 h-4" />;
            case 'APPLYING': return <Loader2 className="w-4 h-4 animate-spin" />;
            case 'PENDING': return <Clock className="w-4 h-4" />;
            case 'FAILED': return <XCircle className="w-4 h-4" />;
            default: return <Info className="w-4 h-4" />;
        }
    };

    const getCategoryIcon = (iconName: string) => {
        const iconMap = {
            'shield-check': <Shield className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />,
            'edit': <Edit3 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />,
            'plus-circle': <Plus className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />,
            'trash': <Trash2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />,
            'verified': <CheckCircle className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />,
            'puzzle': <Layers className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
        };
        return iconMap[iconName] || <FileText className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />;
    };

    const filteredPolicies = policies.filter(policy => {
        const matchesSearch = policy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            policy.description?.toLowerCase().includes(searchTerm.toLowerCase());
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
                comparison = severityOrder[b.severity] - severityOrder[a.severity];
                break;
            case 'created_at':
                comparison = new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
                break;
        }
        return sortOrder === 'asc' ? comparison : -comparison;
    });

    const loadData = async () => {
        setLoading(true);
        await Promise.all([
            fetchClusters(),
            fetchCategories(),
            fetchApplications()
        ]);
        setLoading(false);
    };

    // Effects
    useEffect(() => {
        loadData();
        fetchClusterOverview();
    }, []);

    useEffect(() => {
        if (selectedCategory) {
            fetchPoliciesByCategory(selectedCategory);
            fetchCategoryStats(selectedCategory);
        }
    }, [selectedCategory, currentPage]);

    useEffect(() => {
        if (selectedClusterName) {
            fetchApplications();
            fetchAppliedPoliciesForCluster(selectedClusterName);
            fetchAvailablePoliciesForCluster(selectedClusterName);
        }
    }, [selectedClusterName, statusFilter, selectedCategory]);

    // Update the useEffect for selectedPolicy
    useEffect(() => {
        if (selectedPolicy) {
            setOriginalYaml(selectedPolicy.yaml_content);
            setEditedYaml(selectedPolicy.yaml_content);
            setEditableFields(extractEditableFields(selectedPolicy.yaml_content));
        }
    }, [selectedPolicy]);

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
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-blue-900/20 dark:to-indigo-900/20">
            <div className="container mx-auto px-6 py-8">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
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
                                className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-cyan-600 hover:from-blue-600 hover:to-cyan-700 text-white font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl"
                            >
                                <RefreshCw className="w-4 h-4" />
                                <span>Refresh</span>
                            </button>
                        </div>
                    </div>
                </motion.div>

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
                                onClick={() => setSelectedClusterName(cluster.cluster_name)}
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
                            {categories.map((category) => (
                                <motion.div
                                    key={category.id}
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    onClick={() => setSelectedCategory(category.name)}
                                    className={`p-6 rounded-xl border-2 cursor-pointer transition-all duration-200 ${selectedCategory === category.name
                                        ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/30 shadow-lg'
                                        : 'border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600 bg-gray-50 dark:bg-gray-700/50'
                                        }`}
                                >
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center space-x-3">
                                            {getCategoryIcon(category.icon)}
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
                            ))}
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
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ 
                delay: index * 0.1,
                duration: 0.4,
                layout: { duration: 0.3 }
            }}
            whileHover={{ 
                scale: 1.02,
                transition: { duration: 0.2 }
            }}
            className={`bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 rounded-xl shadow-lg border border-gray-200/50 dark:border-gray-700/50 hover:shadow-xl transition-all duration-300 ${
                viewMode === 'list' ? 'flex items-center p-4' : 'p-6'
            }`}
        >
            {viewMode === 'grid' ? (
                <div className="h-full flex flex-col">
                    {/* Grid View */}
                    <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center space-x-3 flex-1 min-w-0">
                            <motion.div 
                                whileHover={{ rotate: 360 }}
                                transition={{ duration: 0.5 }}
                                className="p-2 bg-gradient-to-r from-blue-500 to-cyan-600 rounded-lg flex-shrink-0"
                            >
                                <Shield className="w-4 h-4 text-white" />
                            </motion.div>
                            <div className="min-w-0 flex-1">
                                <h4 className="font-semibold text-gray-900 dark:text-white text-sm truncate">
                                    {policy.name}
                                </h4>
                                <motion.span 
                                    initial={{ scale: 0.8 }}
                                    animate={{ scale: 1 }}
                                    className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border mt-1 ${getSeverityColor(policy.severity)}`}
                                >
                                    {policy.severity.toUpperCase()}
                                </motion.span>
                            </div>
                        </div>
                        <motion.button
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            onClick={() => {
                                setSelectedPolicy(policy);
                                setShowPolicyModal(true);
                            }}
                            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex-shrink-0"
                        >
                            <Eye className="w-4 h-4" />
                        </motion.button>
                    </div>

                    <div className="flex-1 mb-4">
                        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
                            {policy.description || policy.purpose}
                        </p>
                    </div>

                    {policy.tags && policy.tags.length > 0 && (
                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.2 }}
                            className="flex flex-wrap gap-1 mb-4"
                        >
                            {policy.tags.slice(0, 3).map((tag, tagIndex) => (
                                <motion.span
                                    key={tagIndex}
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ delay: tagIndex * 0.1 }}
                                    className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                                >
                                    <Tag className="w-3 h-3 mr-1" />
                                    {tag}
                                </motion.span>
                            ))}
                            {policy.tags.length > 3 && (
                                <motion.span 
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ delay: 0.3 }}
                                    className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                                >
                                    +{policy.tags.length - 3}
                                </motion.span>
                            )}
                        </motion.div>
                    )}

                    <div className="flex items-center justify-between mt-auto">
                        <div className="flex items-center space-x-2">
                            <motion.button
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => {
                                    setSelectedPolicy(policy);
                                    setShowPolicyModal(true);
                                }}
                                className="flex items-center space-x-2 px-3 py-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                            >
                                <Eye className="w-4 h-4" />
                                <span className="text-sm">View</span>
                            </motion.button>
                            <motion.button
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => {
                                    navigator.clipboard.writeText(policy.yaml_content);
                                    showToast('YAML copied to clipboard', 'success');
                                }}
                                className="flex items-center space-x-2 px-3 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg transition-colors"
                            >
                                <Copy className="w-4 h-4" />
                                <span className="text-sm">Copy</span>
                            </motion.button>
                        </div>

                        <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => {
                                if (!selectedClusterName) {
                                    showToast('Please select a cluster first', 'error');
                                    return;
                                }
                                if (isApplied) {
                                    showToast(`Policy "${policy.name}" is already applied to this cluster`, 'error');
                                    return;
                                }
                                setSelectedPolicy(policy);
                                setShowConfirmDialog(true);
                            }}
                            disabled={!selectedClusterName || applyingPolicy === policy.policy_id || isApplied}
                            className={`flex items-center space-x-2 px-4 py-2 font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl ${
                                isApplied
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
                        </motion.button>
                    </div>
                </div>
            ) : (
                <>
                    {/* List View */}
                    <div className="flex items-center space-x-4 flex-1">
                        <motion.div 
                            whileHover={{ rotate: 360 }}
                            transition={{ duration: 0.5 }}
                            className="p-2 bg-gradient-to-r from-blue-500 to-cyan-600 rounded-lg flex-shrink-0"
                        >
                            <Shield className="w-4 h-4 text-white" />
                        </motion.div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-3 mb-1">
                                <h4 className="font-semibold text-gray-900 dark:text-white truncate">
                                    {policy.name}
                                </h4>
                                <motion.span 
                                    initial={{ scale: 0.8 }}
                                    animate={{ scale: 1 }}
                                    className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border flex-shrink-0 ${getSeverityColor(policy.severity)}`}
                                >
                                    {policy.severity.toUpperCase()}
                                </motion.span>
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                                {policy.description || policy.purpose}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center space-x-2 flex-shrink-0">
                        <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => {
                                setSelectedPolicy(policy);
                                setShowPolicyModal(true);
                            }}
                            className="flex items-center space-x-2 px-3 py-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                        >
                            <Eye className="w-4 h-4" />
                            <span className="text-sm">View</span>
                        </motion.button>
                        <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => {
                                navigator.clipboard.writeText(policy.yaml_content);
                                showToast('YAML copied to clipboard', 'success');
                            }}
                            className="flex items-center space-x-2 px-3 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg transition-colors"
                        >
                            <Copy className="w-4 h-4" />
                            <span className="text-sm">Copy</span>
                        </motion.button>
                        <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => {
                                if (!selectedClusterName) {
                                    showToast('Please select a cluster first', 'error');
                                    return;
                                }
                                if (isApplied) {
                                    showToast(`Policy "${policy.name}" is already applied to this cluster`, 'error');
                                    return;
                                }
                                setSelectedPolicy(policy);
                                setShowConfirmDialog(true);
                            }}
                            disabled={!selectedClusterName || applyingPolicy === policy.policy_id || isApplied}
                            className={`flex items-center space-x-2 px-4 py-2 font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl ${
                                isApplied
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
                        </motion.button>
                    </div>
                </>
            )}
        </motion.div>
    );
})}

                                </div>

                                {/* Pagination */}
                                {totalPages > 1 && (
                                    <div className="flex items-center justify-center space-x-2 mt-8">
                                        <button
                                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                                            disabled={currentPage === 1}
                                            className="px-3 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            <ChevronLeft className="w-4 h-4" />
                                        </button>

                                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                            const pageNum = Math.max(1, Math.min(currentPage - 2 + i, totalPages - 4 + i));
                                            return (
                                                <button
                                                    key={pageNum}
                                                    onClick={() => setCurrentPage(pageNum)}
                                                    className={`px-3 py-2 rounded-lg ${currentPage === pageNum
                                                        ? 'bg-blue-500 text-white'
                                                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                                        }`}
                                                >
                                                    {pageNum}
                                                </button>
                                            );
                                        })}

                                        <button
                                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                                            disabled={currentPage === totalPages}
                                            className="px-3 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            <ChevronRight className="w-4 h-4" />
                                        </button>
                                    </div>
                                )}
                            </>
                        )}
                    </motion.div>
                )}






                {/* Recent Applications */}
                {applications.filter(app => app.status !== 'REMOVED' && app.status !== 'removed').length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 p-6 mb-6"
                    >
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
                                <Activity className="w-5 h-5 mr-2 text-green-600 dark:text-green-400" />
                                Recent Applications
                            </h3>
                            <div className="flex items-center space-x-4">
                                <select
                                    value={statusFilter}
                                    onChange={(e) => setStatusFilter(e.target.value)}
                                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                >
                                    <option value="">All Status</option>
                                    <option value="APPLIED">Applied</option>
                                    <option value="APPLYING">Applying</option>
                                    <option value="PENDING">Pending</option>
                                    <option value="FAILED">Failed</option>
                                </select>
                                <span className="text-sm text-gray-500 dark:text-gray-400">
                                    {applications.filter(app => app.status !== 'REMOVED' && app.status !== 'removed').length} applications
                                </span>

                            </div>
                        </div>

                        <div className="space-y-3">
                            {applications
                                .filter(app => app.status !== 'REMOVED' && app.status !== 'removed') // Filter out removed policies (both cases)
                                .slice(0, 10)
                                .map((app, index) => {
                                    // Debug logging - remove this after testing
                                    console.log('App data:', app, 'Status:', app.status, 'Is APPLIED:', app.status === 'APPLIED');

                                    return (
                                        <motion.div
                                            key={app.id}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: index * 0.1 }}
                                            className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                        >
                                            <div className="flex items-center space-x-4">
                                                <div className={`p-2 rounded-lg ${getStatusColor(app.status)}`}>
                                                    {getStatusIcon(app.status)}
                                                </div>
                                                <div>
                                                    <h4 className="font-medium text-gray-900 dark:text-white">
                                                        {app.policy?.name || app.policy_name || app.policy_id}
                                                    </h4>
                                                    <p className="text-sm text-gray-600 dark:text-gray-400">
                                                        {app.cluster_name} • {app.kubernetes_namespace}
                                                    </p>
                                                    {app.status === 'FAILED' && app.error_message && (
                                                        <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                                                            <AlertTriangle className="w-3 h-3 inline mr-1" />
                                                            {app.error_message}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>

                                            <div className="flex items-center space-x-3">
                                                <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(app.status)}`}>
                                                    {app.status}
                                                </span>
                                                <span className="text-sm text-gray-500 dark:text-gray-400">
                                                    {new Date(app.applied_at).toLocaleDateString()}
                                                </span>

                                                {/* YAML View Icon */}
                                                <button
                                                    onClick={() => showYamlModal(app)}
                                                    className="p-1 text-blue-500 hover:text-blue-700 dark:hover:text-blue-400"
                                                    title="View Applied YAML"
                                                >
                                                    <FileText className="w-4 h-4" />
                                                </button>

                                                {/* Remove Policy Button - Show for APPLIED policies */}
                                                {(app.status === 'APPLIED' || app.status === 'applied') && (
                                                    <button
                                                        onClick={() => {
                                                            console.log('Remove button clicked for app:', app.id);
                                                            showRemoveConfirmModal(app.id, app.policy?.name || app.policy_name || app.policy_id);
                                                        }}
                                                        className="p-1 text-red-500 hover:text-red-700 dark:hover:text-red-400"
                                                        title="Remove Policy from Cluster"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                )}

                                                {/* Error Icon for Failed Policies */}
                                                {app.status === 'FAILED' && app.error_message && (
                                                    <button
                                                        onClick={() => showToast(app.error_message, 'error')}
                                                        className="p-1 text-red-500 hover:text-red-700 dark:hover:text-red-400"
                                                        title="View Error Details"
                                                    >
                                                        <AlertTriangle className="w-4 h-4" />
                                                    </button>
                                                )}
                                            </div>
                                        </motion.div>
                                    );
                                })}
                        </div>

                        {applications.filter(app => app.status !== 'REMOVED' && app.status !== 'removed').length > 10 && (
                            <div className="mt-4 text-center">
                                <button className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm font-medium">
                                    View All Applications
                                </button>
                            </div>
                        )}

                    </motion.div>
                )}




            </div>

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
                                                    if (isPolicyApplied(selectedPolicy.policy_id)) {
                                                        showToast(`Policy "${selectedPolicy.name}" is already applied to this cluster`, 'error');
                                                        return;
                                                    }
                                                    setShowConfirmDialog(true);
                                                    setShowPolicyModal(false);
                                                }}
                                                disabled={!selectedClusterName || applyingPolicy === selectedPolicy.policy_id || isPolicyApplied(selectedPolicy.policy_id)}
                                                className={`w-full flex items-center justify-center space-x-2 px-4 py-3 font-medium rounded-lg transition-all duration-200 ${isPolicyApplied(selectedPolicy.policy_id)
                                                    ? 'bg-gray-400 text-white cursor-not-allowed'
                                                    : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white disabled:opacity-50 disabled:cursor-not-allowed'
                                                    }`}
                                            >
                                                {applyingPolicy === selectedPolicy.policy_id ? (
                                                    <>
                                                        <Loader2 className="w-4 h-4 animate-spin" />
                                                        <span>Applying...</span>
                                                    </>
                                                ) : isPolicyApplied(selectedPolicy.policy_id) ? (
                                                    <>
                                                        <Check className="w-4 h-4" />
                                                        <span>Already Applied</span>
                                                    </>
                                                ) : (
                                                    <>
                                                        <Play className="w-4 h-4" />
                                                        <span>Apply to {selectedClusterName || 'Cluster'}</span>
                                                    </>
                                                )}
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

                                    <div className="flex-1 overflow-hidden">
                                        {showYamlEditor ? (
                                            <div className="h-full flex">
                                                {/* YAML Display (Read-only) */}
                                                <div className="flex-1">
                                                    <Editor
                                                        height="100%"
                                                        defaultLanguage="yaml"
                                                        value={reconstructYamlWithEdits(originalYaml, editableFields)}
                                                        theme="vs-dark"
                                                        options={{
                                                            readOnly: true,
                                                            minimap: { enabled: false },
                                                            scrollBeyondLastLine: false,
                                                            fontSize: 14,
                                                            lineNumbers: 'on',
                                                            wordWrap: 'on',
                                                            automaticLayout: true
                                                        }}
                                                    />
                                                </div>

                                                {/* Editable Fields Panel */}
                                                <div className="w-80 border-l border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 overflow-y-auto">
                                                    <div className="p-4">
                                                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                                                            <Edit3 className="w-4 h-4 mr-2" />
                                                            Editable Fields
                                                        </h4>

                                                        {Object.keys(editableFields).length === 0 ? (
                                                            <p className="text-sm text-gray-500 dark:text-gray-400">
                                                                No editable fields found in this policy.
                                                            </p>
                                                        ) : (
                                                            <div className="space-y-4">
                                                                {Object.entries(editableFields).map(([fieldKey, fieldValue]) => {
                                                                    // Extract readable field name
                                                                    const fieldName = fieldKey.replace(/^line_\d+_/, '').replace(/_/g, ' ');

                                                                    return (
                                                                        <div key={fieldKey} className="space-y-2">
                                                                            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 capitalize">
                                                                                {fieldName}
                                                                            </label>
                                                                            <input
                                                                                type="text"
                                                                                value={fieldValue}
                                                                                onChange={(e) => {
                                                                                    setEditableFields(prev => ({
                                                                                        ...prev,
                                                                                        [fieldKey]: e.target.value
                                                                                    }));
                                                                                }}
                                                                                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                                                placeholder="Enter value..."
                                                                            />
                                                                        </div>
                                                                    );
                                                                })}

                                                                <div className="pt-4 border-t border-gray-200 dark:border-gray-600">
                                                                    <button
                                                                        onClick={() => {
                                                                            setEditableFields(extractEditableFields(originalYaml));
                                                                            showToast('Fields reset to original values', 'success');
                                                                        }}
                                                                        className="w-full flex items-center justify-center space-x-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg transition-colors"
                                                                    >
                                                                        <RefreshCw className="w-4 h-4" />
                                                                        <span>Reset to Original</span>
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="h-full overflow-auto p-4 bg-gray-50 dark:bg-gray-900">
                                                <pre className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-mono">
                                                    {reconstructYamlWithEdits(originalYaml, editableFields)}
                                                </pre>
                                            </div>
                                        )}
                                    </div>
                                </div>

                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Confirmation Dialog */}
            <AnimatePresence>
                {showConfirmDialog && selectedPolicy && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                        onClick={() => setShowConfirmDialog(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full p-6"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center space-x-4 mb-6">
                                <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl">
                                    <Play className="w-6 h-6 text-white" />
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                                        Apply Policy
                                    </h3>
                                    <p className="text-gray-600 dark:text-gray-400">
                                        Confirm policy application
                                    </p>
                                </div>
                            </div>

                            <div className="space-y-4 mb-6">
                                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Policy:</span>
                                        <span className="text-sm font-semibold text-gray-900 dark:text-white">
                                            {selectedPolicy.name}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Cluster:</span>
                                        <span className="text-sm font-semibold text-gray-900 dark:text-white">
                                            {selectedClusterName}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Severity:</span>
                                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getSeverityColor(selectedPolicy.severity)}`}>
                                            {selectedPolicy.severity.toUpperCase()}
                                        </span>
                                    </div>
                                </div>

                                <div className="p-4 bg-blue-50 dark:bg-blue-900/30 rounded-xl border border-blue-200 dark:border-blue-700">
                                    <div className="flex items-start space-x-3">
                                        <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                                        <div>
                                            <p className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
                                                Policy Application
                                            </p>
                                            <p className="text-sm text-blue-700 dark:text-blue-300">
                                                This policy will be applied cluster-wide and will take effect immediately.
                                                Make sure you understand the policy's impact before proceeding.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center justify-end space-x-4">
                                <button
                                    onClick={() => setShowConfirmDialog(false)}
                                    className="px-6 py-3 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-colors font-medium"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={() => applyPolicy(selectedPolicy)}
                                    disabled={applyingPolicy === selectedPolicy.policy_id}
                                    className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {applyingPolicy === selectedPolicy.policy_id ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            <span>Applying...</span>
                                        </>
                                    ) : (
                                        <>
                                            <Play className="w-4 h-4" />
                                            <span>Apply Policy</span>
                                        </>
                                    )}
                                </button>
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
                                                {policies.length}
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
                                                    : applications.filter(app => app.status === 'applied').length
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
                                                    : applications.filter(app => app.status === 'failed').length
                                                }
                                            </span>
                                        </div>
                                        <h3 className="font-semibold text-red-900 dark:text-red-100">Failed Policies</h3>
                                        <p className="text-sm text-red-700 dark:text-red-300">Application failed</p>
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
                                                    : applications.filter(app => ['pending', 'applying'].includes(app.status)).length
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
                                                {selectedClusterName
                                                    ? applications.filter(app => app.cluster_name === selectedClusterName && app.policy?.severity === 'critical').length
                                                    : policies.filter(policy => policy.severity === 'critical').length
                                                }
                                            </div>
                                            <div className="text-sm text-red-700 dark:text-red-300 font-medium">Critical</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400 mb-1">
                                                {selectedClusterName
                                                    ? applications.filter(app => app.cluster_name === selectedClusterName && app.policy?.severity === 'high').length
                                                    : policies.filter(policy => policy.severity === 'high').length
                                                }
                                            </div>
                                            <div className="text-sm text-orange-700 dark:text-orange-300 font-medium">High</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400 mb-1">
                                                {selectedClusterName
                                                    ? applications.filter(app => app.cluster_name === selectedClusterName && app.policy?.severity === 'medium').length
                                                    : policies.filter(policy => policy.severity === 'medium').length
                                                }
                                            </div>
                                            <div className="text-sm text-yellow-700 dark:text-yellow-300 font-medium">Medium</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-green-600 dark:text-green-400 mb-1">
                                                {selectedClusterName
                                                    ? applications.filter(app => app.cluster_name === selectedClusterName && app.policy?.severity === 'low').length
                                                    : policies.filter(policy => policy.severity === 'low').length
                                                }
                                            </div>
                                            <div className="text-sm text-green-700 dark:text-green-300 font-medium">Low</div>
                                        </div>
                                    </div>
                                </div>

                                {/* Cluster Overview */}
                                {clusters.length > 0 && (
                                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-6">
                                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                                            {selectedClusterName ? `${selectedClusterName} Policy Overview` : 'Cluster Policy Overview'}
                                        </h3>
                                        <div className="space-y-4">
                                            {(selectedClusterName
                                                ? clusters.filter(cluster => cluster.cluster_name === selectedClusterName)
                                                : clusters
                                            ).map((cluster, index) => {
                                                const clusterApplications = applications.filter(app => app.cluster_name === cluster.cluster_name);
                                                const appliedCount = clusterApplications.filter(app => app.status === 'applied').length;
                                                const failedCount = clusterApplications.filter(app => app.status === 'failed').length;
                                                const pendingCount = clusterApplications.filter(app => ['pending', 'applying'].includes(app.status)).length;

                                                // Get unique categories applied to this cluster
                                                const categoriesApplied = [...new Set(
                                                    clusterApplications
                                                        .filter(app => app.policy && app.status === 'applied')
                                                        .map(app => app.policy.category?.name || 'Unknown')
                                                )];

                                                return (
                                                    <div key={index} className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
                                                        <div className="flex items-center justify-between mb-3">
                                                            <div className="flex items-center space-x-3">
                                                                <Server className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                                                                <div>
                                                                    <h4 className="font-semibold text-gray-900 dark:text-white">
                                                                        {cluster.cluster_name}
                                                                    </h4>
                                                                    <p className="text-sm text-gray-600 dark:text-gray-400">
                                                                        {cluster.provider_name || 'Unknown Provider'}
                                                                    </p>
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center space-x-4 text-sm">
                                                                <span className="text-green-600 dark:text-green-400 font-medium">
                                                                    {appliedCount} Applied
                                                                </span>
                                                                <span className="text-red-600 dark:text-red-400 font-medium">
                                                                    {failedCount} Failed
                                                                </span>
                                                                <span className="text-yellow-600 dark:text-yellow-400 font-medium">
                                                                    {pendingCount} Pending
                                                                </span>
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center justify-between">
                                                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                                                Total Applications: {clusterApplications.length}
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




        </div>
    );
};

export default Policies;




