import React from "react";
import { Card, CardBody, CardHeader, Button, Spinner, Select, SelectItem, Chip } from "@heroui/react";
import { Icon } from "@iconify/react";

interface CostAnalysisProps {
  selectedCluster?: string;
}

interface ClusterInfo {
  filename: string;
  cluster_name: string;
  active: boolean;
  provider?: string;
}

export const CostAnalysis: React.FC<CostAnalysisProps> = ({ selectedCluster }) => {
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [clusters, setClusters] = React.useState<ClusterInfo[]>([]);
  const [selectedClusterName, setSelectedClusterName] = React.useState<string>("");
  const [isLoadingClusters, setIsLoadingClusters] = React.useState(false);
  const [currentTheme, setCurrentTheme] = React.useState<string>('dark');

  const getAuthToken = () => {
    return localStorage.getItem('access_token') || '';
  };

  // Get theme from localStorage
  const getThemeFromStorage = () => {
    return localStorage.getItem('heroui-theme') || 'dark';
  };

  // Initialize theme from localStorage
  React.useEffect(() => {
    const storedTheme = getThemeFromStorage();
    setCurrentTheme(storedTheme);
  }, []);

  // Listen for theme changes in localStorage
  React.useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'heroui-theme' && e.newValue) {
        setCurrentTheme(e.newValue);
        setIsLoading(true); // Reload dashboard with new theme
      }
    };

    // Listen for custom theme change events
    const handleThemeChange = (e: CustomEvent) => {
      const newTheme = e.detail.theme;
      setCurrentTheme(newTheme);
      setIsLoading(true); // Reload dashboard with new theme
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('themeChanged' as any, handleThemeChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('themeChanged' as any, handleThemeChange);
    };
  }, []);

  // Fetch clusters from API
  const fetchClusters = async () => {
    setIsLoadingClusters(true);
    try {
      const response = await fetch("/kubeconfig/clusters", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch clusters: ${response.statusText}`);
      }

      const data = await response.json();
      if (data && Array.isArray(data.cluster_names)) {
        setClusters(data.cluster_names);
        // Set the first active cluster as default
        const activeCluster = data.cluster_names.find((cluster: ClusterInfo) => cluster.active);
        if (activeCluster) {
          setSelectedClusterName(activeCluster.cluster_name);
        } else if (data.cluster_names.length > 0) {
          setSelectedClusterName(data.cluster_names[0].cluster_name);
        }
      }
    } catch (err: any) {
      console.error("Error fetching clusters:", err);
      setError(err.message || 'Failed to fetch clusters');
    } finally {
      setIsLoadingClusters(false);
    }
  };

  React.useEffect(() => {
    fetchClusters();
  }, []);

  // Dashboard URL with correct format
  const dashboardUrl = React.useMemo(() => {
    if (!selectedClusterName) return "";
    
    const baseUrl = "https://10.0.32.108:3000/grafana-monitoring/d/opencost-mixin-kover-jkwq/finops-overview";
    
    const params = new URLSearchParams({
      orgId: "1",
      "var-DS": "fekxeesdvhgcgb1", // KubeSage metrics datasource ID
      "var-Cluster": selectedClusterName, // Selected cluster name
      "var-Node": "", // Empty - will show all nodes
      "var-Namespace": "", // Empty - will show all namespaces
      "var-Pod": "", // Empty - will show all pods
      "var-Container": "", // Empty - will show all containers
      "var-logs": "eemj7g7ndgzcwe", // Logs datasource ID
      from: "now-1h",
      to: "now",
      theme: currentTheme === 'dark' ? "dark" : "light",
      kiosk: "true", // Full kiosk mode for clean embedding
      refresh: "30s" // Auto-refresh every 30 seconds
    });

    return `${baseUrl}?${params.toString()}`;
  }, [selectedClusterName, currentTheme]);

  const handleIframeLoad = () => {
    setIsLoading(false);
    setError(null);
  };

  const handleIframeError = () => {
    setIsLoading(false);
    setError("Failed to load cost analysis dashboard. Please check if the dashboard is accessible.");
  };

  const refreshDashboard = () => {
    setIsLoading(true);
    setError(null);
    // Force iframe reload with new URL
    const iframe = document.getElementById('cost-analysis-iframe') as HTMLIFrameElement;
    if (iframe && dashboardUrl) {
      iframe.src = dashboardUrl;
    }
  };

  const handleClusterChange = (keys: any) => {
    const selected = Array.from(keys)[0] as string;
    if (selected && selected !== selectedClusterName) {
      setSelectedClusterName(selected);
      setIsLoading(true); // Show loading when switching clusters
    }
  };

  const toggleTheme = () => {
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setCurrentTheme(newTheme);
    localStorage.setItem('heroui-theme', newTheme);
    
    // Dispatch custom event to notify other components
    window.dispatchEvent(new CustomEvent('themeChanged', { 
      detail: { theme: newTheme } 
    }));
    
    setIsLoading(true); // Show loading when switching themes
  };

  // Auto-refresh dashboard when cluster changes or theme changes
  React.useEffect(() => {
    if (selectedClusterName && dashboardUrl) {
      refreshDashboard();
    }
  }, [selectedClusterName, dashboardUrl]);

  return (
    <div className="space-y-6 p-4">
      {/* Header Section */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center">
            <Icon icon="lucide:indian-rupee" className="text-white text-2xl" />
          </div>
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
              Cost Analysis Dashboard
            </h1>
            <p className="text-sm text-foreground-500 mt-1">
              Financial insights and cost optimization powered by KubeSage
            </p>
          </div>
        </div>

        {/* Controls Section */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          {/* Cluster Selector */}
          <div className="min-w-[280px]">
            <Select
              label="Select Cluster"
              placeholder="Choose a cluster to analyze"
              selectedKeys={selectedClusterName ? [selectedClusterName] : []}
              onSelectionChange={handleClusterChange}
              variant="bordered"
              size="lg"
              isLoading={isLoadingClusters}
              startContent={<Icon icon="mdi:kubernetes" className="text-primary" />}
              classNames={{
                trigger: "bg-content1 border-2 hover:border-primary",
                value: "font-medium",
                label: "font-semibold"
              }}
            >
              {clusters.map((cluster) => (
                <SelectItem 
                  key={cluster.cluster_name} 
                  value={cluster.cluster_name}
                  textValue={cluster.cluster_name}
                >
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-2">
                      <Icon icon="mdi:kubernetes" className="text-blue-500" />
                      <span className="font-medium">{cluster.cluster_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {cluster.provider && (
                        <Chip size="sm" variant="flat" color="secondary">
                          {cluster.provider}
                        </Chip>
                      )}
                      <Chip 
                        size="sm" 
                        variant="flat" 
                        color={cluster.active ? "success" : "default"}
                      >
                        {cluster.active ? "Active" : "Inactive"}
                      </Chip>
                    </div>
                  </div>
                </SelectItem>
              ))}
            </Select>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button
              color="primary"
              variant="flat"
              size="lg"
              onPress={refreshDashboard}
              isIconOnly
              className="min-w-12"
              isDisabled={!selectedClusterName}
            >
              <Icon icon="lucide:refresh-cw" className="text-lg" />
            </Button>
            <Button
              color="secondary"
              variant="flat"
              size="lg"
              onPress={toggleTheme}
              isIconOnly
              className="min-w-12"
            >
              <Icon icon={currentTheme === 'dark' ? "lucide:sun" : "lucide:moon"} className="text-lg" />
            </Button>
          </div>
        </div>
      </div>

      {/* Status Bar */}
      {selectedClusterName && (
        <Card className="bg-gradient-to-r from-success-50 to-primary-50 dark:from-success/10 dark:to-primary/10 border border-success/20">
          <CardBody className="py-3">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-success rounded-full animate-pulse"></div>
                <span className="font-medium text-foreground">
                  Analyzing: <span className="text-success font-bold">{selectedClusterName}</span>
                </span>
                <Chip size="sm" variant="flat" color="primary">
                  Theme: {currentTheme}
                </Chip>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

      {/* No Cluster Selected State */}
      {!selectedClusterName && !isLoadingClusters && (
        <Card className="bg-warning-50 dark:bg-warning/10 border border-warning/20">
          <CardBody className="text-center py-8">
            <div className="w-16 h-16 bg-warning/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Icon icon="lucide:alert-triangle" className="text-4xl text-warning" />
            </div>
            <h3 className="text-xl font-bold text-warning mb-2">No Cluster Selected</h3>
            <p className="text-foreground-500 mb-4">
              Please select a cluster from the dropdown above to view cost analysis.
            </p>
            <Button
              color="warning"
              variant="flat"
              onPress={fetchClusters}
              startContent={<Icon icon="lucide:refresh-cw" />}
            >
              Refresh Clusters
            </Button>
          </CardBody>
        </Card>
      )}

      {/* Main Dashboard Card */}
      {selectedClusterName && (
        <Card className="w-full shadow-lg">
          <CardBody className="p-0 relative">
            <div 
              className="relative w-full bg-content1 rounded-lg overflow-hidden" 
              style={{ height: "calc(100vh - 200px)", minHeight: "600px" }}
            >
              {/* Loading State */}
              {isLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-content1 z-10">
                  <div className="flex flex-col items-center gap-4">
                    <Spinner size="lg" color="primary" />
                    <div className="text-center">
                      <p className="text-lg font-medium text-foreground">Loading Dashboard</p>
                      <p className="text-sm text-foreground-500">
                        Initializing cost analysis for {selectedClusterName}...
                      </p>
                      <p className="text-xs text-foreground-400 mt-1">
                        Theme: {currentTheme}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Error State */}
              {error && (
                <div className="absolute inset-0 flex items-center justify-center bg-content1 z-10">
                  <div className="text-center space-y-4 max-w-md mx-auto p-6">
                    <div className="w-16 h-16 bg-danger/10 rounded-full flex items-center justify-center mx-auto">
                      <Icon icon="lucide:alert-circle" className="text-4xl text-danger" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-danger mb-2">Dashboard Unavailable</h3>
                      <p className="text-sm text-foreground-500 mb-2">{error}</p>
                      <div className="flex items-center justify-center gap-2 text-xs text-foreground-400">
                        <Icon icon="lucide:server" className="text-sm" />
                        <span>Cluster: {selectedClusterName}</span>
                      </div>
                    </div>
                    <div className="flex flex-col sm:flex-row gap-2 justify-center">
                      <Button
                        color="primary"
                        variant="flat"
                        onPress={refreshDashboard}
                        startContent={<Icon icon="lucide:refresh-cw" />}
                      >
                        Retry Connection
                      </Button>
                      <Button
                        color="secondary"
                        variant="light"
                        onPress={fetchClusters}
                        startContent={<Icon icon="lucide:settings" />}
                      >
                        Check Configuration
                      </Button>
                    </div>
                  </div>
                </div>
              )}

                            {/* Dashboard Iframe */}
                            {dashboardUrl && (
                <iframe
                  id="cost-analysis-iframe"
                  src={dashboardUrl}
                  className="w-full h-full border-0"
                  title={`Cost Analysis Dashboard - ${selectedClusterName}`}
                  onLoad={handleIframeLoad}
                  onError={handleIframeError}
                  sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
                  style={{
                    background: "transparent",
                    display: error ? 'none' : 'block'
                  }}
                />
              )}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Quick Stats Footer */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20">
          <CardBody className="flex flex-row items-center gap-3 py-4">
            <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center">
              <Icon icon="lucide:server" className="text-green-500" />
            </div>
            <div>
              <p className="text-sm text-foreground-500">Total Clusters</p>
              <p className="text-xl font-bold text-foreground">{clusters.length}</p>
            </div>
          </CardBody>
        </Card>

        <Card className="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border border-blue-500/20">
          <CardBody className="flex flex-row items-center gap-3 py-4">
            <div className="w-10 h-10 bg-blue-500/20 rounded-full flex items-center justify-center">
              <Icon icon="lucide:check-circle" className="text-blue-500" />
            </div>
            <div>
              <p className="text-sm text-foreground-500">Active Clusters</p>
              <p className="text-xl font-bold text-foreground">
                {clusters.filter(c => c.active).length}
              </p>
            </div>
          </CardBody>
        </Card>

        <Card className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20">
          <CardBody className="flex flex-row items-center gap-3 py-4">
            <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center">
              <Icon icon="lucide:indian-rupee" className="text-purple-500" />
            </div>
            <div>
              <p className="text-sm text-foreground-500">Current Cluster</p>
              <p className="text-sm font-bold text-foreground truncate max-w-[120px]" title={selectedClusterName}>
                {selectedClusterName || 'None'}
              </p>
            </div>
          </CardBody>
        </Card>

        <Card className="bg-gradient-to-r from-orange-500/10 to-red-500/10 border border-orange-500/20">
          <CardBody className="flex flex-row items-center gap-3 py-4">
            <div className="w-10 h-10 bg-orange-500/20 rounded-full flex items-center justify-center">
              <Icon icon="lucide:database" className="text-orange-500" />
            </div>
            <div>
              <p className="text-sm text-foreground-500">Data Sources</p>
              <p className="text-xs font-bold text-foreground">Metrics + Logs</p>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
};

export default CostAnalysis;
