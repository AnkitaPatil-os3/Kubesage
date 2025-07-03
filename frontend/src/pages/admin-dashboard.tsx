import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Icon } from "@iconify/react";
import { jwtDecode } from "jwt-decode";
const API_BASE_URL = (import.meta as any).env.VITE_USER_SERVICE;
const KUBECONFIG_BASE_URL = (import.meta as any).env.VITE_KUBECONFIG_SERVICE;

import { 
  Card, 
  CardBody, 
  CardHeader, 
  Button, 
  Tabs, 
  Tab,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  Avatar,
  Progress,
  Pagination,
  Tooltip,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Input,
  Select,
  SelectItem,
  Switch,
  Checkbox
} from "@heroui/react";
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
  BarChart,
  Bar
} from "recharts";

interface AdminDashboardProps {
  selectedCluster?: string;
}
// new 
interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_admin: boolean;
  roles: string[];
  created_at?: string;
  confirmed?: boolean;
}

interface NewUser {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  roles: string[];
}

interface EditUser {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  roles: string[];
  password?: string; // Optional for edit
}
// new
interface NewCluster {
  name: string;
  provider: string;
  region: string;
  version: string;
  nodeCount: number;
  instanceType: string;
  description: string;
}

interface Cluster {
  id: number;
  name: string;
  provider: string;
  region: string;
  version: string;
  nodes: number;
  status: string;
}

// Check if token is valid
const isTokenValid = (token: string | null): boolean => {
  if (!token) return false;
  
  try {
    // Check if token has 3 parts (header.payload.signature)
    const parts = token.split('.');
    if (parts.length !== 3) {
      console.error('Token does not have 3 parts');
      return false;
    }
    
    // Decode and check expiration
    const decoded: any = jwtDecode(token); // Updated function call
    const currentTime = Date.now() / 1000;
    
    if (decoded.exp && decoded.exp < currentTime) {
      console.error('Token is expired');
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('Token validation error:', error);
    return false;
  }
};

// Get valid token or handle error
const getValidToken = (): string | null => {
  const token = localStorage.getItem("access_token");
  
  if (!isTokenValid(token)) {
    console.error("Invalid or expired token");
    // Clear invalid token
    localStorage.removeItem("access_token");
    return null;
  }
  
  return token;
};

// Check current user's admin status first
const checkAdminStatus = async () => {
  try {
    const token = getValidToken();
    if (!token) return false;
    
    const res = await fetch(`${API_BASE_URL}/auth/check-admin`, {
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    });
    
    if (res.ok) {
      const data = await res.json();
      return data.is_admin;
    }
    return false;
  } catch (error) {
    console.error("Error checking admin status:", error);
    return false;
  }
};

export const AdminDashboard: React.FC<AdminDashboardProps> = () => {
  const [activeTab, setActiveTab] = React.useState("overview");
  const [page, setPage] = React.useState(1);
  const rowsPerPage = 5;

  // User Management State
  const [showAddUser, setShowAddUser] = useState(false);
  const [showEditUser, setShowEditUser] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [newUser, setNewUser] = useState<NewUser>({
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    is_active: true,
    roles: [],
  });
  const [editUser, setEditUser] = useState<EditUser>({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    is_active: true,
    roles: [],
    password: "",
  });

  // Cluster Management State
  const [showAddCluster, setShowAddCluster] = useState(false);
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [newCluster, setNewCluster] = useState<NewCluster>({
    name: "",
    provider: "AWS EKS",
    region: "",
    version: "",
    nodeCount: 3,
    instanceType: "t3.medium",
    description: ""
  });

  // Current user admin status
  const [currentUserIsAdmin, setCurrentUserIsAdmin] = useState(false);
  const [checkingAdmin, setCheckingAdmin] = useState(true);

  // Fetch users from backend
  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = getValidToken();
      if (!token) {
        setError("Please login again. Token is invalid or expired.");
        setLoading(false);
        return;
      }

      // Check if user is admin first
      const isAdmin = await checkAdminStatus();
      if (!isAdmin) {
        setError("Access denied. Admin privileges required.");
        setLoading(false);
        return;
      }

      console.log('Using token:', token.substring(0, 50) + '...');

      const res = await fetch(`${API_BASE_URL}/users/?skip=0&limit=100`, {
        method: 'GET',
        headers: {
          "accept": "application/json",
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
      });

      console.log('Response status:', res.status);

      if (res.ok) {
        const data = await res.json();
        console.log('Users data:', data);
        setUsers(Array.isArray(data) ? data : []);
      } else {
        const errorText = await res.text();
        console.error('API Error:', res.status, errorText);

        if (res.status === 401) {
          localStorage.removeItem("access_token");
          setError("Session expired. Please login again.");
        } else if (res.status === 403) {
          setError("Access denied. Admin privileges required.");
        } else {
          setError(`Failed to fetch users: ${res.status}`);
        }
      }
    } catch (error) {
      console.error("Error fetching users:", error);
      setError("Network error. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  // Fetch clusters from backend
  const fetchClusters = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = getValidToken();
      if (!token) {
        setError("Please login again. Token is invalid or expired.");
        setLoading(false);
        return;
      }

      // Check if user is admin first
      const isAdmin = await checkAdminStatus();
      if (!isAdmin) {
        setError("Access denied. Admin privileges required.");
        setLoading(false);
        return;
      }

      console.log('Using token:', token.substring(0, 50) + '...');

      // Updated API endpoint to fetch cluster names from kubeconfig service on port 8002
     const res = await fetch(`${KUBECONFIG_BASE_URL}/kubeconfig/clusters`, {
  method: 'GET',
  headers: {
    "accept": "application/json",
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  },
});

      console.log('Response status:', res.status);

      if (res.ok) {
        const data = await res.json();
        console.log('Clusters data:', data);

        // Extract cluster names from kubeconfigs list response
        if (data.kubeconfigs && Array.isArray(data.kubeconfigs)) {
          const clusterList = data.kubeconfigs.map((k: any) => ({
            id: k.id,
            name: k.cluster_name || "Unknown",
            provider: "Unknown",
            region: "Unknown",
            version: "Unknown",
            nodes: 0,
            status: "Unknown"
          }));
          setClusters(clusterList);
        } else {
          setClusters([]);
        }
      } else {
        const errorText = await res.text();
        console.error('API Error:', res.status, errorText);

        if (res.status === 401) {
          localStorage.removeItem("access_token");
          setError("Session expired. Please login again.");
        } else if (res.status === 403) {
          setError("Access denied. Admin privileges required.");
        } else {
          setError(`Failed to fetch clusters: ${res.status}`);
        }
      }
    } catch (error) {
      console.error("Error fetching clusters:", error);
      setError("Network error. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const checkAdmin = async () => {
      const isAdmin = await checkAdminStatus();
      setCurrentUserIsAdmin(isAdmin);
      setCheckingAdmin(false);
    };
    checkAdmin();
    fetchUsers();
    fetchClusters();
  }, []);

  // Add user API call
  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const token = getValidToken();
      if (!token) {
        setError("Please login again. Token is invalid or expired.");
        setLoading(false);
        return;
      }

      console.log('Adding user:', newUser);

      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: {
          "accept": "application/json",
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        // NEW
        body: JSON.stringify({
          ...newUser,
          roles: newUser.roles,
        }),

      });
      // new
      if (res.ok) {
        const responseData = await res.json();
        console.log('User created:', responseData);

        setShowAddUser(false);
        setNewUser({
          username: "",
          email: "",
          password: "",
          first_name: "",
          last_name: "",
          is_active: true,
          roles: [],
        });

        await fetchUsers();
        setSuccessMessage("User added successfully! Confirmation email sent. Waiting for user to confirm.");
        setShowSuccessModal(true);
      } else {
        const errorData = await res.text();
        console.error('Add user error:', res.status, errorData);

        if (res.status === 401) {
          setError("Session expired. Please login again.");
        } else if (res.status === 422) {
          setError(`Validation error: ${errorData}`);
        } else {
          setError(`User add failed: ${res.status}`);
        }
      }
    } catch (error) {
      console.error("Error adding user:", error);
      setError("User add failed: Network error");
    } finally {
      setLoading(false);
    }
  };

  // Edit user API call
  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;

    try {
      setLoading(true);
      const token = getValidToken();
      if (!token) {
        alert("Please login again. Token is invalid or expired.");
        setLoading(false);
        return;
      }

      console.log('Editing user:', selectedUser.id, editUser);

      // Prepare update data - only include password if it's provided
      const updateData: any = {
        username: editUser.username,
        email: editUser.email,
        first_name: editUser.first_name,
        last_name: editUser.last_name,
        is_active: editUser.is_active,
        roles: editUser.roles,
      };

      // Only include password if it's provided
      if (editUser.password && editUser.password.trim() !== "") {
        updateData.password = editUser.password;
      }

      const res = await fetch(`${API_BASE_URL}/users/${selectedUser.id}`, {
        method: "PUT",
        headers: {
          "accept": "application/json",
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(updateData),
      });
      
      if (res.ok) {
        const responseData = await res.json();
        console.log('User updated:', responseData);
        
        setShowEditUser(false);
        setSelectedUser(null);
        setEditUser({
          username: "",
          email: "",
          first_name: "",
          last_name: "",
          is_active: true,
          roles: [],
          password: "",
        });
        
        await fetchUsers();
        setSuccessMessage("User updated successfully!");
        setShowSuccessModal(true);
      } else {
        const errorData = await res.text();
        console.error('Edit user error:', res.status, errorData);

        if (res.status === 401) {
          setError("Session expired. Please login again.");
        } else if (res.status === 422) {
          setError(`Validation error: ${errorData}`);
        } else if (res.status === 404) {
          setError("User not found.");
        } else if (res.status === 403) {
          setError("Only admin users can update users.");
          setSuccessMessage("Only admin users can update users.");
          setShowSuccessModal(true);
          return;
        } else {
          setError(`User update failed: ${res.status}`);
        }
      }
    } catch (error) {
      console.error("Error updating user:", error);
      setError("User update failed: Network error");
    } finally {
      setLoading(false);
    }
  };

  // Delete user API call
  const handleDeleteUser = async () => {
    if (!selectedUser) return;

    try {
      setLoading(true);
      const token = getValidToken();
      if (!token) {
        alert("Please login again. Token is invalid or expired.");
        setLoading(false);
        return;
      }

      console.log('Deleting user:', selectedUser.id);

      const res = await fetch(`${API_BASE_URL}/users/${selectedUser.id}`, {
        method: "DELETE",
        headers: {
          "accept": "application/json",
          "Authorization": `Bearer ${token}`,
        },
      });
      
      if (res.ok) {
        console.log('User deleted successfully');
        
        setShowDeleteConfirm(false);
        setSelectedUser(null);
        
        await fetchUsers();
        setSuccessMessage("User deleted successfully!");
        setShowSuccessModal(true);
      } else {
        const errorData = await res.text();
        console.error('Delete user error:', res.status, errorData);

        if (res.status === 401) {
          setError("Session expired. Please login again.");
        } else if (res.status === 404) {
          setError("User not found.");
        } else if (res.status === 403) {
          setError("Access denied. Cannot delete this user.");
        } else {
          setError(`User deletion failed: ${res.status}`);
        }
      }
    } catch (error) {
      console.error("Error deleting user:", error);
      setError("User deletion failed: Network error");
    } finally {
      setLoading(false);
    }
  };

  // Open edit modal with user data
  const openEditModal = (user: User) => {
    setSelectedUser(user);
    setEditUser({
      username: user.username,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      is_active: user.is_active,
      roles: user.roles,
      password: "", // Keep empty for security
    });
    setShowEditUser(true);
  };

  // Open delete confirmation modal
  const openDeleteModal = (user: User) => {
    setSelectedUser(user);
    setShowDeleteConfirm(true);
  };

  // Handle add cluster
  const handleAddCluster = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Adding cluster:", newCluster);
    setShowAddCluster(false);
    setNewCluster({
      name: "",
      provider: "AWS EKS",
      region: "",
      version: "",
      nodeCount: 3,
      instanceType: "t3.medium",
      description: ""
    });
    alert("Cluster configuration saved! (Implementation pending)");
  };

  // Sample data for charts
  const clusterUsageData = [
    { name: "Jan", cpu: 65, memory: 55, storage: 40 },
    { name: "Feb", cpu: 68, memory: 59, storage: 43 },
    { name: "Mar", cpu: 75, memory: 65, storage: 45 },
    { name: "Apr", cpu: 85, memory: 70, storage: 48 },
    { name: "May", cpu: 78, memory: 72, storage: 52 },
    { name: "Jun", cpu: 82, memory: 75, storage: 55 },
    { name: "Jul", cpu: 88, memory: 80, storage: 58 },
  ];
  
  const costData = [
    { name: "Jan", cost: 4200 },
    { name: "Feb", cost: 4500 },
    { name: "Mar", cost: 4800 },
    { name: "Apr", cost: 5200 },
    { name: "May", cost: 5500 },
    { name: "Jun", cost: 5800 },
    { name: "Jul", cost: 6200 },
  ];
  
  const resourceDistributionData = [
    { name: "Production", value: 55 },
    { name: "Staging", value: 25 },

    { name: "Development", value: 20 },
  ];
  
  const COLORS = ["#0ea5e9", "#7828c8", "#17c964", "#f5a524"];
  
  // Remove the hardcoded clusters array to avoid redeclaration error
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case "Active": return "success";
      case "Inactive": return "warning";
      case "Healthy": return "success";
      case "Warning": return "warning";
      case "Critical": return "danger";
      default: return "default";
    }
  };
  
  const getInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase();
  };
  
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };
  
  const renderUserTable = () => {
    if (loading) {
      return (
        <div className="flex justify-center items-center h-32">
          <div className="text-center">
            <Icon icon="lucide:loader-2" className="animate-spin text-2xl mb-2" />
            <p>Loading users...</p>
          </div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex justify-center items-center h-32">
          <div className="text-center">
            <Icon icon="lucide:alert-circle" className="text-danger text-2xl mb-2" />
            <p className="text-danger">{error}</p>
            <Button 
              size="sm" 
              color="primary" 
              variant="flat" 
              className="mt-2"
              onClick={fetchUsers}
            >
              Retry
            </Button>
          </div>
        </div>
      );
    }

    if (users.length === 0) {
      return (
        <div className="flex justify-center items-center h-32">
          <div className="text-center">
            <Icon icon="lucide:users" className="text-foreground-400 text-2xl mb-2" />
            <p>No users found</p>
          </div>
        </div>
      );
    }

    const startIndex = (page - 1) * rowsPerPage;
    const endIndex = startIndex + rowsPerPage;
    const displayedUsers = users.slice(startIndex, endIndex);
    const pages = Math.ceil(users.length / rowsPerPage);
    
    return (
      <>
        <Table 
          aria-label="Users table" 
          removeWrapper
        >
        
          <TableHeader>
            <TableColumn>USER</TableColumn>
            {/* TableColumn for ROLE removed */}
            <TableColumn>STATUS</TableColumn>
            <TableColumn>CREATED</TableColumn>
            {/* new */}
            <TableColumn>ROLES</TableColumn>  
            <TableColumn>CONFIRMATION</TableColumn>
            {/* new */}
            <TableColumn>ACTIONS</TableColumn>
          </TableHeader>
                <TableBody>
            {displayedUsers.map((user) => {
              const canEditOrDelete = user.is_admin || user.id === user.id;
              return (
                <TableRow key={user.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar
                        name={getInitials(`${user.first_name} ${user.last_name}`)}
                        size="sm"
                      />
                      <div>
                        <p className="font-medium">{user.first_name} {user.last_name}</p>
                        <p className="text-xs text-foreground-500">{user.email}</p>
                        <p className="text-xs text-foreground-400">@{user.username}</p>
                      </div>
                    </div>
                  </TableCell>
                  {/* 
                  <TableCell>
                    <Chip 
                      color={user.is_admin ? "primary" : "default"} 
                      variant="flat" 
                      size="sm"
                    >
                      {user.is_admin ? "Admin" : "User"}
                    </Chip>
                  </TableCell>
                  */}
                  <TableCell>
                    <Chip 
                      color={getStatusColor(user.is_active ? "Active" : "Inactive")} 
                      variant="flat" 
                      size="sm"
                    >
                      {user.is_active ? "Active" : "Inactive"}
                    </Chip>
                  </TableCell>
                  <TableCell>
                    {user.created_at ? new Date(user.created_at).toLocaleDateString() : "N/A"}
                  </TableCell>
                  {/* new */}
                  <TableCell>
                    <div className="flex gap-1 flex-wrap">
                      {user.roles && user.roles.length > 0 ? (
                        user.roles.map((role) => (
                          <Chip key={role} color="primary" variant="flat" size="sm">{role}</Chip>
                        ))
                      ) : (
                        <Chip color="default" variant="flat" size="sm">No Role</Chip>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {user.confirmed ? (
                      <Chip color="success" variant="flat" size="sm">Confirmed</Chip>
                    ) : (
                      <Chip color="warning" variant="flat" size="sm">Pending</Chip>
                    )}
                  </TableCell>
                  {/* new */}
                  <TableCell>
                    <div className="flex gap-2">
                      <Tooltip content={currentUserIsAdmin ? "Edit User" : "Admin only"}>
                        <Button
                          isIconOnly
                          size="sm"
                          variant="light"
                          onPress={() => {
                            if (currentUserIsAdmin) {
                              openEditModal(user);
                            } else {
                              setSuccessMessage("Only admin users can update users.");
                              setShowSuccessModal(true);
                            }
                          }}
                          isDisabled={loading}
                          disabled={!currentUserIsAdmin}
                        >
                          <Icon icon="lucide:edit-2" width={16} height={16} />
                        </Button>
                      </Tooltip>
                      <Tooltip content={currentUserIsAdmin ? "Delete User" : "Admin only"}>
                        <Button
                          isIconOnly
                          size="sm"
                          variant="light"
                          color="danger"
                          onPress={() => {
                            if (currentUserIsAdmin) {
                              openDeleteModal(user);
                            } else {
                              setSuccessMessage("Only admin users can delete users.");
                              setShowSuccessModal(true);
                            }
                          }}
                          isDisabled={loading}
                          disabled={!currentUserIsAdmin}
                        >
                          <Icon icon="lucide:trash-2" width={16} height={16} />
                        </Button>
                      </Tooltip>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        
        <div className="flex justify-between items-center mt-4">
          <span className="text-sm text-foreground-500">
            Showing {startIndex + 1} to {Math.min(endIndex, users.length)} of {users.length} users
          </span>
          <Pagination 
            total={pages} 
            page={page} 
            onChange={setPage}
            showControls
            size="sm"
          />
        </div>
      </>
    );
  };
  
  const renderClusterTable = () => {
    return (
      <Table 
        aria-label="Clusters table" 
        removeWrapper
      >
        <TableHeader>
          <TableColumn>CLUSTER</TableColumn>
          <TableColumn>PROVIDER</TableColumn>
          <TableColumn>VERSION</TableColumn>
          <TableColumn>NODES</TableColumn>
          <TableColumn>STATUS</TableColumn>
          <TableColumn>ACTIONS</TableColumn>
        </TableHeader>
        <TableBody>
          {clusters.map((cluster) => (
            <TableRow key={cluster.id}>
              <TableCell>
                <div>
                  <p className="font-medium">{cluster.name}</p>
                  <p className="text-xs text-foreground-500">{cluster.region}</p>
                </div>
              </TableCell>
              <TableCell>{cluster.provider}</TableCell>
              <TableCell>{cluster.version}</TableCell>
              <TableCell>{cluster.nodes}</TableCell>
              <TableCell>
                <Chip 
                  color={getStatusColor(cluster.status)} 
                  variant="flat" 
                  size="sm"
                >
                  {cluster.status}
                </Chip>
              </TableCell>
              <TableCell>
                <div className="flex gap-2">
                  <Tooltip content="View Details">
                    <Button isIconOnly size="sm" variant="light">
                      <Icon icon="lucide:eye" width={16} height={16} />
                    </Button>
                  </Tooltip>
                  <Tooltip content="Edit Cluster">
                    <Button isIconOnly size="sm" variant="light">
                      <Icon icon="lucide:settings" width={16} height={16} />
                    </Button>
                  </Tooltip>
                  <Tooltip content="Delete Cluster">
                    <Button isIconOnly size="sm" variant="light" color="danger">
                      <Icon icon="lucide:trash-2" width={16} height={16} />
                    </Button>
                  </Tooltip>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    );
  };
  
  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };
  
  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.4 } }
  };

  const resendConfirmation = async (userId: number) => {
  // Call your backend API to resend confirmation email
  const token = getValidToken();
  const res = await fetch(`${API_BASE_URL}/auth/resend-confirm/${userId}`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "accept": "application/json"
    }
  });
  if (res.ok) {
    setSuccessMessage("Confirmation email resent.");
    setShowSuccessModal(true);
  } else {
    setError("Failed to resend confirmation.");
  }
};

const manuallyConfirmUser = async (userId: number) => {
  // Call your backend API to manually confirm the user
  const token = getValidToken();
  const res = await fetch(`${API_BASE_URL}/auth/confirm/${userId}/accept`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "accept": "application/json"
    }
  });
  if (res.ok) {
    setSuccessMessage("User confirmed successfully.");
    setShowSuccessModal(true);
    await fetchUsers();
  } else {
    setError("Failed to confirm user.");
  }
};

  if (checkingAdmin) {
    return (
      <div className="flex justify-center items-center h-64">
        <Icon icon="lucide:loader-2" className="animate-spin text-2xl mr-2" />
        <span>Checking admin access...</span>
      </div>
    );
  }

  if (!currentUserIsAdmin) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <Icon icon="lucide:alert-triangle" className="text-danger text-4xl mb-2" />
        <p className="text-lg text-danger font-semibold">Access Denied</p>
        <p className="text-foreground-500">You do not have admin privileges to view this page.</p>
      </div>
    );
  }
//new
 const ROLE_OPTIONS = [
  "Super Admin",
  "Platform/System Engineer",
  "DevOps/SRE",
  "Developer",
  "Security Engineer"
];
//new 
  return (
    <>
      <motion.div 
        className="space-y-6"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        <Card>
          <CardHeader className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Icon icon="lucide:settings" className="text-primary" />
              <h2 className="text-xl font-semibold">Admin Dashboard</h2>
            </div>
            <p className="text-sm text-foreground-500">Manage users, clusters, and system settings</p>
          </CardHeader>
          <CardBody>
            <Tabs 
              aria-label="Admin options" 
              selectedKey={activeTab} 
              onSelectionChange={setActiveTab as any}
              variant="underlined"
              color="primary"
            >
              <Tab 
                key="overview" 
                title={
                  <div className="flex items-center gap-2">
                    <Icon icon="lucide:layout-dashboard" />
                    <span>Overview</span>
                  </div>
                }
              >
                <motion.div 
                  className="mt-4 space-y-6"
                  variants={containerVariants}
                  initial="hidden"
                  animate="show"
                >
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <motion.div variants={itemVariants}>
                      <Card className="bg-content2">
                        <CardBody className="p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm text-foreground-500">Total Clusters</p>
                              <p className="text-2xl font-semibold">{clusters.length}</p>
                            </div>
                            <div className="p-3 rounded-full bg-primary/10">
                              <Icon icon="lucide:server" className="text-primary text-xl" />
                            </div>
                          </div>
                        </CardBody>
                      </Card>
                    </motion.div>
                    
                    <motion.div variants={itemVariants}>
                      <Card className="bg-content2">
                        <CardBody className="p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm text-foreground-500">Total Users</p>
                              <p className="text-2xl font-semibold">{users.length}</p>
                            </div>
                            <div className="p-3 rounded-full bg-secondary/10">
                              <Icon icon="lucide:users" className="text-secondary text-xl" />
                            </div>
                          </div>
                        </CardBody>
                      </Card>
                    </motion.div>
                    
                    <motion.div variants={itemVariants}>
                      <Card className="bg-content2">
                        <CardBody className="p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm text-foreground-500">Total Nodes</p>
                              <p className="text-2xl font-semibold">{clusters.reduce((acc, cluster) => acc + cluster.nodes, 0)}</p>
                            </div>
                            <div className="p-3 rounded-full bg-success/10">
                              <Icon icon="lucide:cpu" className="text-success text-xl" />
                            </div>
                          </div>
                        </CardBody>
                      </Card>
                    </motion.div>
                    
                    <motion.div variants={itemVariants}>
                      <Card className="bg-content2">
                        <CardBody className="p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm text-foreground-500">Monthly Cost</p>
                              <p className="text-2xl font-semibold">{formatCurrency(costData[costData.length - 1].cost)}</p>
                            </div>
                            <div className="p-3 rounded-full bg-warning/10">
                              <Icon icon="lucide:dollar-sign" className="text-warning text-xl" />
                            </div>
                          </div>
                        </CardBody>
                      </Card>
                    </motion.div>
                  </div>
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <motion.div variants={itemVariants}>
                      <Card>
                        <CardHeader className="flex flex-col gap-1">
                          <h3 className="text-lg font-semibold">Resource Usage Trends</h3>
                        </CardHeader>
                        <CardBody>
                          <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                              <AreaChart
                                data={clusterUsageData}
                                margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
                              >
                                <defs>
                                  <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="hsl(var(--heroui-primary))" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="hsl(var(--heroui-primary))" stopOpacity={0} />
                                  </linearGradient>
                                  <linearGradient id="colorMemory" x1="0" y1="0" x2="0" y2="1">


                                    <stop offset="5%" stopColor="hsl(var(--heroui-secondary))" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="hsl(var(--heroui-secondary))" stopOpacity={0} />
                                  </linearGradient>
                                  <linearGradient id="colorStorage" x1="0" y1="0" x2="0" y2="1">


                                    <stop offset="5%" stopColor="hsl(var(--heroui-success))" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="hsl(var(--heroui-success))" stopOpacity={0} />
                                  </linearGradient>
                                </defs>




                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--heroui-divider))" />
                                <XAxis 
                                  dataKey="name" 
                                  axisLine={false}
                                  tickLine={false}
                                />
                                <YAxis 
                                  domain={[0, 100]}
                                  axisLine={false}
                                  tickLine={false}
                                  tickFormatter={(value) => `${value}%`}
                                />
                                <RechartsTooltip 
                                  contentStyle={{ 
                                    backgroundColor: 'hsl(var(--heroui-content1))', 
                                    borderColor: 'hsl(var(--heroui-divider))'
                                  }}
                                />
                                <Area 
                                  type="monotone" 
                                  dataKey="cpu" 


                                  name="CPU"
                                  stroke="hsl(var(--heroui-primary))" 
                                  fillOpacity={1}
                                  fill="url(#colorCpu)" 
                                />
                                <Area 
                                  type="monotone" 
                                  dataKey="memory" 


                                  name="Memory"
                                  stroke="hsl(var(--heroui-secondary))" 
                                  fillOpacity={1}
                                  fill="url(#colorMemory)" 
                                />
                                <Area 
                                  type="monotone" 
                                  dataKey="storage" 


                                  name="Storage"
                                  stroke="hsl(var(--heroui-success))" 
                                  fillOpacity={1}
                                  fill="url(#colorStorage)" 
                                />
                                <Legend />
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>
                        </CardBody>
                      </Card>
                    </motion.div>
                    
                    <motion.div variants={itemVariants}>
                      <Card>
                        <CardHeader className="flex flex-col gap-1">

                          <h3 className="text-lg font-semibold">Cost Analysis</h3>
                        </CardHeader>
                        <CardBody>
                          <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">

















                              <BarChart
                                data={costData}
                                margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
                              >
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--heroui-divider))" />
                                <XAxis 
                                  dataKey="name" 
                                  axisLine={false}
                                  tickLine={false}
                                />
                                <YAxis 
                                  axisLine={false}
                                  tickLine={false}
                                  tickFormatter={(value) => `${value}`}
                                />
                                <RechartsTooltip 
                                  formatter={(value: number) => [`${value}`, 'Cost']}
                                  contentStyle={{ 
                                    backgroundColor: 'hsl(var(--heroui-content1))', 
                                    borderColor: 'hsl(var(--heroui-divider))'
                                  }}
                                />
                                <Bar 
                                  dataKey="cost" 
                                  fill="hsl(var(--heroui-warning))" 
                                  radius={[4, 4, 0, 0]}
                                  name="Monthly Cost"
                                />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </CardBody>
                      </Card>
                    </motion.div>
                  </div>
                  
                  <motion.div variants={itemVariants}>
                    <Card>
                      <CardHeader className="flex flex-col gap-1">
                        <h3 className="text-lg font-semibold">Resource Distribution</h3>
                      </CardHeader>
                      <CardBody>
                        <div className="h-64 flex items-center justify-center">
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={resourceDistributionData}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                outerRadius={80}
                                fill="#8884d8"
                                dataKey="value"
                                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                              >
                                {resourceDistributionData.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                              </Pie>
                              <Legend />
                              <RechartsTooltip 
                                formatter={(value: number) => [`${value}%`, 'Usage']}
                                contentStyle={{ 
                                  backgroundColor: 'hsl(var(--heroui-content1))', 
                                  borderColor: 'hsl(var(--heroui-divider))'
                                }}
                              />
                            </PieChart>
                          </ResponsiveContainer>
                        </div>
                      </CardBody>
                    </Card>
                  </motion.div>
                </motion.div>
              </Tab>
              
              <Tab 
                key="users" 
                title={
                  <div className="flex items-center gap-2">
                    <Icon icon="lucide:users" />
                    <span>Users</span>
                  </div>
                }
              >
                <div className="mt-4">
                  <div className="flex justify-between mb-4">
                    <h3 className="text-lg font-semibold">User Management</h3>
                    <Button 
                      color="primary" 
                      startContent={<Icon icon="lucide:user-plus" />} 
                      onClick={() => setShowAddUser(true)}
                      isDisabled={loading}
                    >
                      Add User
                    </Button>
                  </div>
                  {renderUserTable()}
                </div>
              </Tab>
              
              <Tab 
                key="clusters" 
                title={
                  <div className="flex items-center gap-2">
                    <Icon icon="lucide:server" />
                    <span>Clusters</span>
                  </div>
                }
              >
                <div className="mt-4">
                  <div className="flex justify-between mb-4">
                    <h3 className="text-lg font-semibold">Cluster Management</h3>
                    {/* <Button 
                      color="primary" 
                      startContent={<Icon icon="lucide:plus" />}
                      onClick={() => setShowAddCluster(true)}
                    >
                      Add Cluster
                    </Button> */}
                  </div>
                  {renderClusterTable()}
                </div>
              </Tab>
              
              <Tab 
                key="settings" 
                title={
                  <div className="flex items-center gap-2">
                    <Icon icon="lucide:settings" />
                    <span>Settings</span>
                  </div>
                }
              >
                <div className="mt-4 space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold mb-4">System Settings</h3>
                    <Card>
                      <CardBody className="p-4">
                        <div className="space-y-4">
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-medium">Automatic Updates</p>
                              <p className="text-sm text-foreground-500">Enable automatic updates for system components</p>
                            </div>
                            <Button color="primary" variant="flat">Configure</Button>
                          </div>
                          
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-medium">Backup Schedule</p>
                              <p className="text-sm text-foreground-500">Configure automated backup schedule</p>
                            </div>
                            <Button color="primary" variant="flat">Configure</Button>
                          </div>
                          
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-medium">Authentication</p>
                              <p className="text-sm text-foreground-500">Configure SSO and authentication providers</p>
                            </div>
                            <Button color="primary" variant="flat">Configure</Button>
                          </div>
                          
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-medium">Notifications</p>
                              <p className="text-sm text-foreground-500">Configure email and Slack notifications</p>
                            </div>
                            <Button color="primary" variant="flat">Configure</Button>
                          </div>
                          
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-medium">API Access</p>
                              <p className="text-sm text-foreground-500">Manage API keys and access tokens</p>
                            </div>
                            <Button color="primary" variant="flat">Configure</Button>
                          </div>
                        </div>
                      </CardBody>
                    </Card>
                  </div>
                  
                  <div>
                    <h3 className="text-lg font-semibold mb-4">License Information</h3>
                    <Card>
                      <CardBody className="p-4">
                        <div className="space-y-4">
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-medium">License Type</p>
                              <p className="text-sm">Enterprise</p>
                            </div>
                            <Chip color="success" variant="flat">Active</Chip>
                          </div>
                          
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-medium">Expiration Date</p>
                              <p className="text-sm">December 31, 2024</p>
                            </div>
                            <Button color="primary" variant="flat">Renew</Button>
                          </div>
                          
                          <div>
                            <p className="font-medium">Features</p>
                            <div className="mt-2 space-y-2">
                              <div className="flex items-center gap-2">
                                <Icon icon="lucide:check" className="text-success" />
                                <p className="text-sm">Multi-cluster Management</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Icon icon="lucide:check" className="text-success" />
                                <p className="text-sm">AI-powered Insights</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Icon icon="lucide:check" className="text-success" />
                                <p className="text-sm">Advanced Security Scanning</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Icon icon="lucide:check" className="text-success" />
                                <p className="text-sm">Compliance Management</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Icon icon="lucide:check" className="text-success" />
                                <p className="text-sm">24/7 Premium Support</p>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardBody>
                    </Card>
                  </div>
                </div>
              </Tab>
            </Tabs>
          </CardBody>
        </Card>
      </motion.div>




      {/* Add User Modal */}
      <Modal 
        isOpen={showAddUser} 
        onOpenChange={setShowAddUser}
        placement="top-center"
        size="2xl"
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:user-plus" className="text-primary text-2xl" />
                  <span className="text-xl font-bold">Add New User</span>
                </div>
                <p className="text-sm text-foreground-500 font-normal">
                  Fill in the details to create a new user account
                </p>
              </ModalHeader>
              <form onSubmit={handleAddUser}>
                <ModalBody className="p-6">
                  <div className="space-y-6">
                    {/* Section: Basic Info */}
                    <Card className="bg-content2 border border-divider">
                      <CardHeader>
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                          <Icon icon="lucide:user" className="text-secondary" />
                          Basic Information
                        </h3>
                      </CardHeader>
                      <CardBody className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Input
                          autoFocus
                          label="Username"
                          placeholder="Enter username"
                          variant="bordered"
                          value={newUser.username}
                          onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                          startContent={<Icon icon="lucide:at-sign" className="text-foreground-400" />}
                          isRequired
                        />
                        <Input
                          label="Email"
                          placeholder="Enter email"
                          type="email"
                          variant="bordered"
                          value={newUser.email}
                          onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                          startContent={<Icon icon="lucide:mail" className="text-foreground-400" />}
                          isRequired
                        />
                        <Input
                          label="First Name"
                          placeholder="Enter first name"
                          variant="bordered"
                          value={newUser.first_name}
                          onChange={(e) => setNewUser({...newUser, first_name: e.target.value})}
                          startContent={<Icon icon="lucide:user" className="text-foreground-400" />}
                          isRequired
                        />
                        <Input
                          label="Last Name"
                          placeholder="Enter last name"
                          variant="bordered"
                          value={newUser.last_name}
                          onChange={(e) => setNewUser({...newUser, last_name: e.target.value})}
                          startContent={<Icon icon="lucide:user" className="text-foreground-400" />}
                          isRequired
                        />
                      </CardBody>
                    </Card>

                    {/* Section: Security */}
                    <Card className="bg-content2 border border-divider">
                      <CardHeader>
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                          <Icon icon="lucide:lock" className="text-warning" />
                          Security & Access
                        </h3>
                      </CardHeader>
                      <CardBody className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Input
                          label="Password"
                          placeholder="Enter password"
                          type="password"
                          variant="bordered"
                          value={newUser.password}
                          onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                          startContent={<Icon icon="lucide:key" className="text-foreground-400" />}
                          isRequired
                        />
                        {/* new */}
                        <Select
                          label="Roles"
                          placeholder="Select roles"
                          variant="bordered"
                          selectionMode="multiple"
                          selectedKeys={newUser.roles}
                          onSelectionChange={(keys) => setNewUser({ ...newUser, roles: Array.from(keys) as string[] })}
                          startContent={<Icon icon="lucide:shield" className="text-primary" />}
                          isRequired
                        >
                          {ROLE_OPTIONS.map((role) => (
                            <SelectItem key={role}>{role}</SelectItem>
                          ))}
                        </Select>
                        {/* new */}
                        <div className="flex items-center gap-2 mt-2 md:col-span-2">
                          <Checkbox
                            isSelected={newUser.is_active}
                            onValueChange={(checked) => setNewUser({ ...newUser, is_active: checked })}
                            color="success"
                          >
                            <span className="font-medium">Active User</span>
                          </Checkbox>
                        </div>
                      </CardBody>
                    </Card>
                  </div>
                </ModalBody>
                <ModalFooter>
                  <Button color="danger" variant="flat" onPress={onClose}>
                    Cancel
                  </Button>
                  <Button 
                    color="primary" 
                    type="submit"
                    isLoading={loading}
                    endContent={<Icon icon="lucide:user-plus" />}
                  >
                    Add User
                  </Button>
                </ModalFooter>
              </form>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Edit User Modal */}
      <Modal 
        isOpen={showEditUser} 
        onOpenChange={setShowEditUser}
        placement="top-center"
        size="2xl"
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:edit-2" className="text-primary" />
                  <span>Edit User</span>
                </div>
                {selectedUser && (
                  <p className="text-sm text-foreground-500">
                    Editing: {selectedUser.first_name} {selectedUser.last_name} (@{selectedUser.username})
                  </p>
                )}
              </ModalHeader>
              <form onSubmit={handleEditUser}>
                <ModalBody className="p-6">
                  <div className="space-y-6">
                    {/* Section: Basic Info */}
                    <Card className="bg-content2 border border-divider">
                      <CardHeader>
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                          <Icon icon="lucide:user" className="text-secondary" />
                          Basic Information
                        </h3>
                      </CardHeader>
                      <CardBody className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Input
                          autoFocus
                          label="Username"
                          placeholder="Enter username"
                          variant="bordered"
                          value={editUser.username}
                          onChange={(e) => setEditUser({...editUser, username: e.target.value})}
                          isRequired
                        />
                        <Input
                          label="Email"
                          placeholder="Enter email"
                          type="email"
                          variant="bordered"
                          value={editUser.email}
                          onChange={(e) => setEditUser({...editUser, email: e.target.value})}
                          isRequired
                        />
                        <Input
                          label="First Name"
                          placeholder="Enter first name"
                          variant="bordered"
                          value={editUser.first_name}
                          onChange={(e) => setEditUser({...editUser, first_name: e.target.value})}
                          isRequired
                        />
                        <Input
                          label="Last Name"
                          placeholder="Enter last name"
                          variant="bordered"
                          value={editUser.last_name}
                          onChange={(e) => setEditUser({...editUser, last_name: e.target.value})}
                          isRequired
                        />
                      </CardBody>
                    </Card>

                    {/* Section: Security */}
                    <Card className="bg-content2 border border-divider">
                      <CardHeader>
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                          <Icon icon="lucide:lock" className="text-warning" />
                          Security & Access
                        </h3>
                      </CardHeader>
                      <CardBody className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Input
                          label="New Password"
                          placeholder="Leave empty to keep current password"
                          type="password"
                          variant="bordered"
                          value={editUser.password || ""}
                          onChange={(e) => setEditUser({...editUser, password: e.target.value})}
                          description="Leave empty to keep current password"
                        />
                        <Select
                          label="Roles"
                          placeholder="Select roles"
                          variant="bordered"
                          selectionMode="multiple"
                          selectedKeys={editUser.roles}
                          onSelectionChange={(keys) => setEditUser({ ...editUser, roles: Array.from(keys) as string[] })}
                          isRequired
                        >
                          {ROLE_OPTIONS.map((role) => (
                            <SelectItem key={role}>{role}</SelectItem>
                          ))}
                        </Select>
                        <div className="flex items-center gap-2 mt-2 md:col-span-2">
                          <Checkbox
                            isSelected={editUser.is_active}
                            onValueChange={(checked) => setEditUser({ ...editUser, is_active: checked })}
                            color="success"
                          >
                            <span className="font-medium">Active User</span>
                          </Checkbox>
                        </div>
                      </CardBody>
                    </Card>
                  </div>
                </ModalBody>
                <ModalFooter>
                  <Button 
                    color="danger" 
                    variant="flat" 
                    onPress={() => {
                      onClose();
                      setSelectedUser(null);
                      setEditUser({
                        username: "",
                        email: "",
                        first_name: "",
                        last_name: "",
                        is_active: true,
                        roles: [],
                        password: "",
                      });
                    }}
                  >
                    Cancel
                  </Button>
                  <Button 
                    color="primary" 
                    type="submit"
                    isLoading={loading}
                  >
                    Update User
                  </Button>
                </ModalFooter>
              </form>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Delete User Confirmation Modal */}
      <Modal 
        isOpen={showDeleteConfirm} 
        onOpenChange={setShowDeleteConfirm}
        placement="top-center"
        size="md"
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:alert-triangle" className="text-danger" />
                  <span>Confirm Delete</span>
                </div>
              </ModalHeader>
              <ModalBody>
                {selectedUser && (
                  <div className="space-y-4">
                    <p className="text-foreground">
                      Are you sure you want to delete this user? This action cannot be undone.
                    </p>
                    
                    <Card className="bg-danger/10 border border-danger/20">
                      <CardBody className="p-4">
                        <div className="flex items-center gap-3">
                          <Avatar
                            name={getInitials(`${selectedUser.first_name} ${selectedUser.last_name}`)}
                            size="sm"
                          />
                          <div>
                            <p className="font-medium text-foreground">
                              {selectedUser.first_name} {selectedUser.last_name}
                            </p>
                            <p className="text-xs text-foreground-500">{selectedUser.email}</p>
                            <p className="text-xs text-foreground-400">@{selectedUser.username}</p>
                          </div>
                        </div>
                      </CardBody>
                    </Card>
                    
                    <div className="bg-warning/10 border border-warning/20 rounded-lg p-3">
                      <div className="flex items-start gap-2">
                        <Icon icon="lucide:alert-triangle" className="text-warning flex-shrink-0 mt-0.5" />
                        <div className="text-sm">
                          <p className="font-medium text-warning">Warning</p>
                          <p className="text-foreground-600">
                            Deleting this user will remove all their data, sessions, and access permissions permanently.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </ModalBody>
              <ModalFooter>
                <Button 
                  color="default" 
                  variant="flat" 
                  onPress={() => {
                    onClose();
                    setSelectedUser(null);
                  }}
                >
                  Cancel
                </Button>
                <Button 
                  color="danger" 
                  onPress={handleDeleteUser}
                  isLoading={loading}
                  startContent={<Icon icon="lucide:trash-2" />}
                >
                  Delete User
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Add Cluster Modal */}
      <Modal 
        isOpen={showAddCluster} 
        onOpenChange={setShowAddCluster}
        placement="top-center"
        size="2xl"
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:server" className="text-primary" />
                  <span>Add New Cluster</span>
                </div>
              </ModalHeader>
              <form onSubmit={handleAddCluster}>
                <ModalBody>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                      autoFocus
                      label="Cluster Name"
                      placeholder="Enter cluster name"
                      variant="bordered"
                      value={newCluster.name}
                      onChange={(e) => setNewCluster({...newCluster, name: e.target.value})}
                      isRequired
                    />
                    <Select
                      label="Provider"
                      placeholder="Select provider"
                      variant="bordered"
                      selectedKeys={[newCluster.provider]}
                      onSelectionChange={(keys) => {
                        const selectedProvider = Array.from(keys)[0] as string;
                        setNewCluster({...newCluster, provider: selectedProvider});
                      }}
                      isRequired
                    >
                      <SelectItem key="AWS EKS">AWS EKS</SelectItem>
                      <SelectItem key="GCP GKE">GCP GKE</SelectItem>
                      <SelectItem key="Azure AKS">Azure AKS</SelectItem>
                      <SelectItem key="On-Premise">On-Premise</SelectItem>
                    </Select>
                    <Input
                      label="Region"
                      placeholder="Enter region (e.g., us-west-2)"
                      variant="bordered"
                      value={newCluster.region}
                      onChange={(e) => setNewCluster({...newCluster, region: e.target.value})}
                      isRequired
                    />
                    <Input
                      label="Kubernetes Version"
                      placeholder="Enter version (e.g., 1.28.4)"
                      variant="bordered"
                      value={newCluster.version}
                      onChange={(e) => setNewCluster({...newCluster, version: e.target.value})}
                      isRequired
                    />
                    <Input
                      label="Node Count"
                      placeholder="Enter number of nodes"
                      type="number"
                      variant="bordered"
                      value={newCluster.nodeCount.toString()}
                      onChange={(e) => setNewCluster({...newCluster, nodeCount: parseInt(e.target.value) || 1})}
                      min="1"
                      max="100"
                      isRequired
                    />
                    <Select
                      label="Instance Type"
                      placeholder="Select instance type"
                      variant="bordered"
                      selectedKeys={[newCluster.instanceType]}
                      onSelectionChange={(keys) => {
                        const selectedType = Array.from(keys)[0] as string;
                        setNewCluster({...newCluster, instanceType: selectedType});
                      }}
                      isRequired
                    >
                      <SelectItem key="t3.small">t3.small</SelectItem>
                      <SelectItem key="t3.medium">t3.medium</SelectItem>
                      <SelectItem key="t3.large">t3.large</SelectItem>
                      <SelectItem key="m5.large">m5.large</SelectItem>
                      <SelectItem key="m5.xlarge">m5.xlarge</SelectItem>
                      <SelectItem key="c5.large">c5.large</SelectItem>
                      <SelectItem key="c5.xlarge">c5.xlarge</SelectItem>
                    </Select>
                  </div>
                  <Input
                    label="Description"
                    placeholder="Enter cluster description (optional)"
                    variant="bordered"
                    value={newCluster.description}
                    onChange={(e) => setNewCluster({...newCluster, description: e.target.value})}
                  />
                </ModalBody>
                <ModalFooter>
                  <Button color="danger" variant="flat" onPress={onClose}>
                    Cancel
                  </Button>
                  <Button color="primary" type="submit">
                    Create Cluster
                  </Button>
                </ModalFooter>
              </form>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Success Modal */}
      <Modal
        isOpen={showSuccessModal}
        onOpenChange={setShowSuccessModal}
        placement="top-center"
        size="md"
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:check-circle" className="text-success" />
                  <span>Success</span>
                </div>
              </ModalHeader>
              <ModalBody>
                <p className="text-foreground">{successMessage}</p>
              </ModalBody>
              <ModalFooter>
                <Button
                  color="primary"
                  onPress={() => {
                    onClose();
                    setShowSuccessModal(false);
                    setSuccessMessage("");
                  }}
                >
                  OK
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </>
  );
};
