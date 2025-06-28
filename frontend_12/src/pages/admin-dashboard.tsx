import React from "react";
import { motion } from "framer-motion";
import { Icon } from "@iconify/react";
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
  Tooltip
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

export const AdminDashboard: React.FC<AdminDashboardProps> = () => {
  const [activeTab, setActiveTab] = React.useState("overview");
  const [page, setPage] = React.useState(1);
  const rowsPerPage = 5;
  
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
  
  const users = [
    { id: 1, name: "John Doe", email: "john@example.com", role: "Admin", status: "Active", lastActive: "2 hours ago" },
    { id: 2, name: "Jane Smith", email: "jane@example.com", role: "Developer", status: "Active", lastActive: "5 minutes ago" },
    { id: 3, name: "Mike Johnson", email: "mike@example.com", role: "DevOps", status: "Inactive", lastActive: "2 days ago" },
    { id: 4, name: "Sarah Williams", email: "sarah@example.com", role: "Admin", status: "Active", lastActive: "1 hour ago" },
    { id: 5, name: "Alex Brown", email: "alex@example.com", role: "Developer", status: "Active", lastActive: "30 minutes ago" },
    { id: 6, name: "Lisa Davis", email: "lisa@example.com", role: "DevOps", status: "Active", lastActive: "15 minutes ago" },
    { id: 7, name: "David Miller", email: "david@example.com", role: "Developer", status: "Inactive", lastActive: "1 week ago" },
    { id: 8, name: "Emily Wilson", email: "emily@example.com", role: "Admin", status: "Active", lastActive: "3 hours ago" },
  ];
  
  const clusters = [
    { id: 1, name: "Production", provider: "AWS EKS", region: "us-west-2", version: "1.28.4", nodes: 12, status: "Healthy" },
    { id: 2, name: "Staging", provider: "AWS EKS", region: "us-east-1", version: "1.28.3", nodes: 6, status: "Healthy" },
    { id: 3, name: "Development", provider: "AWS EKS", region: "us-east-2", version: "1.29.0", nodes: 3, status: "Warning" },
    { id: 4, name: "QA", provider: "GCP GKE", region: "us-central1", version: "1.28.2", nodes: 4, status: "Healthy" },
    { id: 5, name: "EU Production", provider: "Azure AKS", region: "europe-west1", version: "1.28.1", nodes: 8, status: "Critical" },
  ];
  
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
            <TableColumn>ROLE</TableColumn>
            <TableColumn>STATUS</TableColumn>
            <TableColumn>LAST ACTIVE</TableColumn>
            <TableColumn>ACTIONS</TableColumn>
          </TableHeader>
          <TableBody>
            {displayedUsers.map((user) => (
              <TableRow key={user.id}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <Avatar
                      name={getInitials(user.name)}
                      size="sm"
                    />
                    <div>
                      <p className="font-medium">{user.name}</p>
                      <p className="text-xs text-foreground-500">{user.email}</p>
                    </div>
                  </div>
                </TableCell>
                <TableCell>{user.role}</TableCell>
                <TableCell>
                  <Chip 
                    color={getStatusColor(user.status)} 
                    variant="flat" 
                    size="sm"
                  >
                    {user.status}
                  </Chip>
                </TableCell>
                <TableCell>{user.lastActive}</TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Tooltip content="Edit User">
                      <Button isIconOnly size="sm" variant="light">
                        <Icon icon="lucide:edit-2" size={16} />
                      </Button>
                    </Tooltip>
                    <Tooltip content="Delete User">
                      <Button isIconOnly size="sm" variant="light" color="danger">
                        <Icon icon="lucide:trash-2" size={16} />
                      </Button>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            ))}
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
                      <Icon icon="lucide:eye" size={16} />
                    </Button>
                  </Tooltip>
                  <Tooltip content="Edit Cluster">
                    <Button isIconOnly size="sm" variant="light">
                      <Icon icon="lucide:settings" size={16} />
                    </Button>
                  </Tooltip>
                  <Tooltip content="Delete Cluster">
                    <Button isIconOnly size="sm" variant="light" color="danger">
                      <Icon icon="lucide:trash-2" size={16} />
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

  return (
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
                                tickFormatter={(value) => `$${value}`}
                              />
                              <RechartsTooltip 
                                formatter={(value: number) => [`$${value}`, 'Cost']}
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
                  <Button color="primary" startContent={<Icon icon="lucide:user-plus" />}>
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
                  <Button color="primary" startContent={<Icon icon="lucide:plus" />}>
                    Add Cluster
                  </Button>
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
  );
};