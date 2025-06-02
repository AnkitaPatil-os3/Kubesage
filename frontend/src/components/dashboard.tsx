import React from "react";
import { ClusterOverview } from "./cluster-overview";
import { ResourceUsage } from "./resource-usage";
import { SecurityScanner } from "./security-scanner";
import { ComplianceStatus } from "./compliance-status";
import { AiInsights } from "./ai-insights";
import { RecentEvents } from "./recent-events";

interface DashboardProps {
  selectedCluster: string;
}

export const Dashboard: React.FC<DashboardProps> = ({ selectedCluster }) => {
  return (
    <div className="space-y-6">
      <ClusterOverview clusterId={selectedCluster} />
      
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