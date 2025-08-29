import React from "react";
import { ClusterOverview } from "./cluster-overview";
import { ResourceUsage } from "./resource-usage";
import { SecurityScanner } from "./security-scanner";
import { ComplianceStatus } from "./compliance-status";
import { AiInsights } from "./ai-insights";
import { RecentEvents } from "./recent-events";
import { Card, CardBody } from "@heroui/react";
import { Icon } from "@iconify/react";
import { Select, SelectItem } from "@heroui/react";

interface ClusterInfo {
  filename: string;
  cluster_name: string;
  active: boolean;
  provider?: string;
}

interface NodeStatusTotals {
  ready: number;
  not_ready: number;
  total: number;
}

interface DashboardSummary {
  totalClusters: number;
  activeClusters: number;
  healthyNodes: { total: number; outOf: number };
  activeAlerts: number;
  securityIssues: number;
}

// Helper to map provider names to icons (update as needed)
const getProviderIcon = (providerName: string) => {
  switch (providerName?.toLowerCase()) {
    case "aws":
      return "logos:aws";
    case "gcp":
      return "logos:google-cloud";
    case "azure":
      return "logos:microsoft-azure";
    default:
      return "lucide:database";
  }
};

export const Dashboard: React.FC = () => {
  const [clusters, setClusters] = React.useState<ClusterInfo[]>([]);
  const [selectedCluster, setSelectedCluster] = React.useState<string>("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [nodeStatusTotals, setNodeStatusTotals] = React.useState<NodeStatusTotals | null>(null);
  const [securityIssues, setSecurityIssues] = React.useState<number>(0);

  const getAuthToken = () => localStorage.getItem("access_token") || "";

  const fetchClusters = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v2.0/clusters", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAuthToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch clusters: ${response.statusText}`);
      }

      const data = await response.json();
      if (data && Array.isArray(data.clusters)) {
        setClusters(data.clusters);
        if (data.clusters.length > 0) {
          setSelectedCluster(data.clusters[0].cluster_name); // default select first cluster
        }
      } else {
        setClusters([]);
      }
    } catch (err: any) {
      console.error("Error fetching clusters:", err);
      setError(err.message || "Failed to fetch clusters");
      setClusters([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchNodeStatus = async (clusterName: string) => {
    try {
      const res = await fetch(
        `/api/v2.0/nodes/status/cluster?cluster=${clusterName}`,
        {
          headers: {
            Authorization: `Bearer ${getAuthToken()}`,
          },
        }
      );
      if (!res.ok) throw new Error(res.statusText);
      const json: NodeStatusTotals = await res.json();
      setNodeStatusTotals(json);
    } catch (err) {
      console.error("Failed to fetch node status:", err);
    }
  };

  const fetchSecurityData = async (clusterName: string) => {
    try {
      const res = await fetch(`/api/v2.0/security?cluster=${encodeURIComponent(clusterName)}`, {
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
        },
      });
      const data = await res.json();
      if (data?.vulnerabilities) {
        const { critical, high, medium, low } = data.vulnerabilities;
        const total = critical + high + medium + low;
        setSecurityIssues(total);
      } else {
        setSecurityIssues(0);
      }
    } catch (err) {
      console.error("Failed to fetch security data:", err);
      setSecurityIssues(0);
    }
  };

  React.useEffect(() => {
    fetchClusters();
  }, []);

  React.useEffect(() => {
    if (selectedCluster) {
      fetchNodeStatus(selectedCluster);
      fetchSecurityData(selectedCluster);
    }
  }, [selectedCluster]);

  const dashboardSummary: DashboardSummary = React.useMemo(() => {
    const totalClusters = clusters.length;
    const activeClusters = clusters.filter((cluster) => cluster.active).length;

    const healthyNodes = nodeStatusTotals
      ? { total: nodeStatusTotals.ready, outOf: nodeStatusTotals.total }
      : { total: 0, outOf: 0 };

    const activeAlerts = 0;

    return {
      totalClusters,
      activeClusters,
      healthyNodes,
      activeAlerts,
      securityIssues,
    };
  }, [clusters, nodeStatusTotals, securityIssues]);

  return (
    <div className="space-y-6 p-6 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-6">
          {/* Left title + description */}
          <div>
            <h1 className="text-3xl font-semibold">Dashboard</h1>
            <p className="text-base text-gray-600 dark:text-gray-400">
              AI-powered overview of your Kubernetes infrastructure
            </p>
          </div>

          {/* Cluster Selector with label and border */}
          <div className="flex items-center space-x-3 border border-gray-300 dark:border-gray-700 rounded-md px-4 py-2 bg-gray-50 dark:bg-gray-800 shadow-sm w-full max-w-2xl">
            <label
              htmlFor="cluster-select"
              className="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap"
            >
              Select Cluster:
            </label>
            <Select
              id="cluster-select"
              aria-label="Select cluster"
              className="flex-1"
              selectedKeys={selectedCluster ? [selectedCluster] : []}
              onSelectionChange={(keys) => {
                const selected = Array.from(keys)[0]; // ensure it's a single string
                setSelectedCluster(selected);
              }}
              startContent={
                selectedCluster ? (
                  <div className="flex items-center gap-2">
                    <Icon
                      icon={getProviderIcon(clusters.find((c) => c.cluster_name === selectedCluster)?.provider || "")}
                      className="text-lg flex-shrink-0"
                    />
                    <span className="whitespace-nowrap">{selectedCluster}</span>
                  </div>
                ) : (
                  <Icon icon="lucide:database" />
                )
              }
            // Remove any max width or truncation here to show full name
            >
              {clusters.map((cluster) => (
                <SelectItem key={cluster.cluster_name} value={cluster.cluster_name}>
                  <div className="flex items-center gap-2">
                    <Icon icon={getProviderIcon(cluster.provider || "")} className="text-lg flex-shrink-0" />
                    <span>{cluster.cluster_name}</span>
                  </div>
                </SelectItem>
              ))}
            </Select>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
          {/* Total Clusters */}
          <Card className="bg-content1 border-none">
            <CardBody className="p-4">
              <div className="flex items-start justify-between">
                <div className="bg-blue-100 dark:bg-blue-900/30 p-2 rounded-lg">
                  <Icon icon="lucide:database" className="text-blue-600 dark:text-blue-400 text-xl" />
                </div>
                <div className="text-right">
                  <span className="text-2xl font-bold">{dashboardSummary.totalClusters}</span>
                  {loading && (
                    <div className="w-4 h-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent ml-2 inline-block"></div>
                  )}
                </div>
              </div>
              <p className="text-sm font-medium mt-3">Total Clusters</p>
              {error && <p className="text-xs text-danger mt-1">Failed to load</p>}
            </CardBody>
          </Card>

          {/* Healthy Nodes */}
          <Card className="bg-content1 border-none">
            <CardBody className="p-4">
              <div className="flex items-start justify-between">
                <div className="bg-purple-100 dark:bg-purple-900/30 p-2 rounded-lg">
                  <Icon icon="lucide:cpu" className="text-purple-600 dark:text-purple-400 text-xl" />
                </div>
                <div className="text-right">
                  <span className="text-2xl font-bold">
                    {dashboardSummary.healthyNodes.total} / {dashboardSummary.healthyNodes.outOf}
                  </span>
                  {loading && (
                    <div className="w-4 h-4 animate-spin rounded-full border-2 border-purple-500 border-t-transparent ml-2 inline-block"></div>
                  )}
                </div>
              </div>
              <p className="text-sm font-medium mt-3">Healthy Nodes</p>
              <p className="text-xs text-foreground-500 mt-1">
                {dashboardSummary.healthyNodes.outOf > 0
                  ? `${Math.round(
                    (dashboardSummary.healthyNodes.total / dashboardSummary.healthyNodes.outOf) * 100
                  )}% healthy`
                  : "No nodes"}
              </p>
            </CardBody>
          </Card>

          {/* Active Alerts */}
          <Card className="bg-content1 border-none">
            <CardBody className="p-4">
              <div className="flex items-start justify-between">
                <div className="bg-amber-100 dark:bg-amber-900/30 p-2 rounded-lg">
                  <Icon icon="lucide:bell" className="text-amber-600 dark:text-amber-400 text-xl" />
                </div>
                <div className="text-right">
                  <span className="text-2xl font-bold">{dashboardSummary.activeAlerts}</span>
                  {loading && (
                    <div className="w-4 h-4 animate-spin rounded-full border-2 border-amber-500 border-t-transparent ml-2 inline-block"></div>
                  )}
                </div>
              </div>
              <p className="text-sm font-medium mt-3">Active Alerts</p>
              <p className="text-xs text-foreground-500 mt-1">
                {dashboardSummary.activeAlerts === 0 ? "All clear" : "Needs attention"}
              </p>
            </CardBody>
          </Card>

          {/* Security Issues */}
          <Card className="bg-content1 border-none">
            <CardBody className="p-4">
              <div className="flex items-start justify-between">
                <div className="bg-red-100 dark:bg-red-900/30 p-2 rounded-lg">
                  <Icon icon="lucide:shield-alert" className="text-red-600 dark:text-red-400 text-xl" />
                </div>
                <div className="text-right">
                  <span className="text-2xl font-bold">{dashboardSummary.securityIssues}</span>
                  {loading && (
                    <div className="w-4 h-4 animate-spin rounded-full border-2 border-red-500 border-t-transparent ml-2 inline-block"></div>
                  )}
                </div>
              </div>
              <p className="text-sm font-medium mt-3">Security Issues</p>
              <p className="text-xs text-foreground-500 mt-1">
                {dashboardSummary.securityIssues === 0 ? "Secure" : "Review required"}
              </p>
            </CardBody>
          </Card>
        </div>
      </div>

      {/* Rest of your dashboard */}
      {/* Cluster Insights */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Cluster Overview</h2>
          <div className="flex items-center text-sm text-primary">
            <Icon icon="lucide:chevron-right" className="ml-1" />
          </div>
        </div>
      </div>

      {/* Resource + Security */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ResourceUsage clusterId={selectedCluster} />
        <SecurityScanner clusterName={selectedCluster} />
      </div>
    </div>
  );
};
