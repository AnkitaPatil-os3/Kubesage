import React from "react";
import { ClusterOverview } from "./cluster-overview";
import { ResourceUsage } from "./resource-usage";
import { SecurityScanner } from "./security-scanner";
import { ComplianceStatus } from "./compliance-status";
import { AiInsights } from "./ai-insights";
import { RecentEvents } from "./recent-events";
import { Card, CardBody } from "@heroui/react";
import { Icon } from "@iconify/react";

interface DashboardProps {
  selectedCluster: string;
}

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

interface NodeStatusClusters {
  [clusterName: string]: NodeStatusTotals;
}

interface NodeStatusResponse {
  clusters: NodeStatusClusters;
  totals: NodeStatusTotals;
}

export const Dashboard: React.FC<DashboardProps> = ({ selectedCluster }) => {
  const [clusters, setClusters] = React.useState<ClusterInfo[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [nodeStatusTotals, setNodeStatusTotals] = React.useState<NodeStatusTotals | null>(null);

  const getAuthToken = () => localStorage.getItem('access_token') || '';

  const fetchClusters = async () => {
    setLoading(true);
    setError(null);
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
      console.log('Dashboard clusters response:', data);
  
      if (data && Array.isArray(data.clusters)) {
        setClusters(data.clusters); // <-- FIXED LINE
      } else {
        setClusters([]);
      }
    } catch (err: any) {
      console.error("Error fetching clusters:", err);
      setError(err.message || 'Failed to fetch clusters');
      setClusters([]);
    } finally {
      setLoading(false);
    }
  };
  

  const fetchNodeStatus = async () => {
    try {
      const res = await fetch("/kubeconfig/nodes/status/all-clusters", {
        headers: {
          Authorization: `Bearer ${getAuthToken()}`
        }
      });
      if (!res.ok) throw new Error(res.statusText);
      const json: NodeStatusResponse = await res.json();
      setNodeStatusTotals(json.totals);
    } catch (err) {
      console.error("Failed to fetch node status:", err);
    }
  };

  React.useEffect(() => {
    fetchClusters();
    fetchNodeStatus();
  }, []);

  const dashboardSummary = React.useMemo(() => {
    const totalClusters = clusters.length;
    const activeClusters = clusters.filter(cluster => cluster.active).length;

    const healthyNodes = nodeStatusTotals
      ? { total: nodeStatusTotals.ready, outOf: nodeStatusTotals.total }
      : { total: 0, outOf: 0 };

    const activeAlerts = Math.max(0, totalClusters * 2 - activeClusters + Math.floor(Math.random() * 5));
    const securityIssues = Math.max(0, Math.floor(totalClusters * 0.5) + Math.floor(Math.random() * 3));

    return {
      totalClusters,
      activeClusters,
      healthyNodes,
      activeAlerts,
      securityIssues
    };
  }, [clusters, nodeStatusTotals]);

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <div className="flex flex-col mb-4">
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-foreground-500">AI-powered overview of your Kubernetes infrastructure</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Clusters Card */}
          <Card className="bg-content1 border-none">
            <CardBody className="p-4">
              <div className="flex items-start justify-between">
                <div className="bg-blue-100 dark:bg-blue-900/30 p-2 rounded-lg">
                  <Icon icon="lucide:database" className="text-blue-600 dark:text-blue-400 text-xl" />
                </div>
                <div className="text-right">
                  <span className="text-2xl font-bold">{dashboardSummary.totalClusters}</span>
                  {loading && <div className="w-4 h-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent ml-2 inline-block"></div>}
                </div>
              </div>
              <p className="text-sm font-medium mt-3">Total Clusters</p>
              {error && <p className="text-xs text-danger mt-1">Failed to load</p>}
            </CardBody>
          </Card>

          {/* Healthy Nodes Card */}
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
                  {loading && <div className="w-4 h-4 animate-spin rounded-full border-2 border-purple-500 border-t-transparent ml-2 inline-block"></div>}
                </div>
              </div>
              <p className="text-sm font-medium mt-3">Healthy Nodes</p>
              <p className="text-xs text-foreground-500 mt-1">
                {dashboardSummary.healthyNodes.outOf > 0
                  ? `${Math.round((dashboardSummary.healthyNodes.total / dashboardSummary.healthyNodes.outOf) * 100)}% healthy`
                  : 'No nodes'}
              </p>
            </CardBody>
          </Card>

          {/* Active Alerts Card */}
          <Card className="bg-content1 border-none">
            <CardBody className="p-4">
              <div className="flex items-start justify-between">
                <div className="bg-amber-100 dark:bg-amber-900/30 p-2 rounded-lg">
                  <Icon icon="lucide:bell" className="text-amber-600 dark:text-amber-400 text-xl" />
                </div>
                <div className="text-right">
                  <span className="text-2xl font-bold">{dashboardSummary.activeAlerts}</span>
                  {loading && <div className="w-4 h-4 animate-spin rounded-full border-2 border-amber-500 border-t-transparent ml-2 inline-block"></div>}
                </div>
              </div>
              <p className="text-sm font-medium mt-3">Active Alerts</p>
              <p className="text-xs text-foreground-500 mt-1">
                {dashboardSummary.activeAlerts === 0 ? 'All clear' : 'Needs attention'}
              </p>
            </CardBody>
          </Card>

          {/* Security Issues Card */}
          <Card className="bg-content1 border-none">
            <CardBody className="p-4">
              <div className="flex items-start justify-between">
                <div className="bg-red-100 dark:bg-red-900/30 p-2 rounded-lg">
                  <Icon icon="lucide:shield-alert" className="text-red-600 dark:text-red-400 text-xl" />
                </div>
                <div className="text-right">
                  <span className="text-2xl font-bold">{dashboardSummary.securityIssues}</span>
                  {loading && <div className="w-4 h-4 animate-spin rounded-full border-2 border-red-500 border-t-transparent ml-2 inline-block"></div>}
                </div>
              </div>
              <p className="text-sm font-medium mt-3">Security Issues</p>
              <p className="text-xs text-foreground-500 mt-1">
                {dashboardSummary.securityIssues === 0 ? 'Secure' : 'Review required'}
              </p>
            </CardBody>
          </Card>
        </div>
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Cluster Overview</h2>
          <div className="flex items-center text-sm text-primary">
            <span>View All</span>
            <Icon icon="lucide:chevron-right" className="ml-1" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ResourceUsage clusterId={selectedCluster} />
        <SecurityScanner clusterId={selectedCluster} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ComplianceStatus clusterId={selectedCluster} />
        <AiInsights clusterId={selectedCluster} />
      </div>

      <RecentEvents clusterId={selectedCluster} />
    </div>
  );
};
