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

export const Dashboard: React.FC<DashboardProps> = ({ selectedCluster }) => {
  // Add dashboard summary data
  const dashboardSummary = {
    totalClusters: 8,
    healthyNodes: {
      total: 42,
      outOf: 45
    },
    activeAlerts: 12,
    securityIssues: 5
  };

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
                <span className="text-2xl font-bold">{dashboardSummary.totalClusters}</span>
              </div>
              <p className="text-sm font-medium mt-3">Total Clusters</p>
            </CardBody>
          </Card>
          {/* Healthy Nodes Card */}
          <Card className="bg-content1 border-none">
            <CardBody className="p-4">
              <div className="flex items-start justify-between">
                <div className="bg-green-100 dark:bg-green-900/30 p-2 rounded-lg">
                  <Icon icon="lucide:server" className="text-green-600 dark:text-green-400 text-xl" />
                </div>
                <span className="text-2xl font-bold">{dashboardSummary.healthyNodes.total} / {dashboardSummary.healthyNodes.outOf}</span>
              </div>
              <p className="text-sm font-medium mt-3">Healthy Nodes</p>
            </CardBody>
          </Card>
          {/* Active Alerts Card */}
          <Card className="bg-content1 border-none">
            <CardBody className="p-4">
              <div className="flex items-start justify-between">
                <div className="bg-amber-100 dark:bg-amber-900/30 p-2 rounded-lg">
                  <Icon icon="lucide:bell" className="text-amber-600 dark:text-amber-400 text-xl" />
                </div>
                <span className="text-2xl font-bold">{dashboardSummary.activeAlerts}</span>
              </div>
              <p className="text-sm font-medium mt-3">Active Alerts</p>
            </CardBody>
          </Card>
          {/* Security Issues Card */}
          <Card className="bg-content1 border-none">
            <CardBody className="p-4">
              <div className="flex items-start justify-between">
                <div className="bg-red-100 dark:bg-red-900/30 p-2 rounded-lg">
                  <Icon icon="lucide:shield-alert" className="text-red-600 dark:text-red-400 text-xl" />
                </div>
                <span className="text-2xl font-bold">{dashboardSummary.securityIssues}</span>
              </div>
              <p className="text-sm font-medium mt-3">Security Issues</p>
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
      {/* <ClusterOverview clusterId={selectedCluster} /> */}
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