import React from "react";
import { Icon } from "@iconify/react";
import { Card, CardBody, Chip, Progress, Button } from "@heroui/react";

interface ClusterOverviewProps {
  clusterId: string;
}

export const ClusterOverview: React.FC<ClusterOverviewProps> = ({ clusterId }) => {
  // In a real app, this would be fetched from an API
  const clusterData = {
    production: {
      name: "Production Cluster",
      version: "v1.28.4",
      nodes: 12,
      pods: 156,
      deployments: 28,
      services: 32,
      status: "Healthy",
      healthScore: 94,
      region: "us-west-2",
      provider: "AWS EKS"
    },
    staging: {
      name: "Staging Cluster",
      version: "v1.28.3",
      nodes: 6,
      pods: 78,
      deployments: 18,
      services: 21,
      status: "Healthy",
      healthScore: 96,
      region: "us-east-1",
      provider: "AWS EKS"
    },
    development: {
      name: "Development Cluster",
      version: "v1.29.0",
      nodes: 3,
      pods: 42,
      deployments: 12,
      services: 14,
      status: "Warning",
      healthScore: 82,
      region: "us-east-2",
      provider: "AWS EKS"
    }
  };

  // Default to production if the clusterId doesn't exist in clusterData
  const cluster = clusterData[clusterId as keyof typeof clusterData] || clusterData.production;
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case "Healthy": return "success";
      case "Warning": return "warning";
      case "Critical": return "danger";
      default: return "default";
    }
  };

  return (
    <Card>
      <CardBody>
        <div className="flex flex-col md:flex-row justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <h2 className="text-xl font-semibold">{cluster.name}</h2>
              <Chip 
                color={getStatusColor(cluster.status)} 
                variant="flat" 
                size="sm"
              >
                {cluster.status}
              </Chip>
            </div>
            
            <div className="flex flex-wrap gap-6 mt-4">
              <div>
                <p className="text-sm text-foreground-500">Kubernetes Version</p>
                <p className="font-medium">{cluster.version}</p>
              </div>
              <div>
                <p className="text-sm text-foreground-500">Provider</p>
                <p className="font-medium">{cluster.provider}</p>
              </div>
              <div>
                <p className="text-sm text-foreground-500">Region</p>
                <p className="font-medium">{cluster.region}</p>
              </div>
            </div>
          </div>
          
          <div className="mt-4 md:mt-0 flex items-center">
            <div className="w-16 h-16 rounded-full border-4 border-primary flex items-center justify-center">
              <span className="text-xl font-bold">{cluster.healthScore}</span>
            </div>
            <div className="ml-4">
              <p className="text-sm text-foreground-500">Health Score</p>
              <Progress 
                value={cluster.healthScore} 
                color={cluster.healthScore > 90 ? "success" : cluster.healthScore > 70 ? "warning" : "danger"}
                className="w-32 mt-1"
              />
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          <div className="bg-content2 p-4 rounded-medium">
            <div className="flex items-center gap-2">
              <Icon icon="lucide:server" className="text-primary text-lg" />
              <p className="text-sm font-medium">Nodes</p>
            </div>
            <p className="text-2xl font-semibold mt-2">{cluster.nodes}</p>
          </div>
          
          <div className="bg-content2 p-4 rounded-medium">
            <div className="flex items-center gap-2">
              <Icon icon="lucide:circle-dot" className="text-primary text-lg" />
              <p className="text-sm font-medium">Pods</p>
            </div>
            <p className="text-2xl font-semibold mt-2">{cluster.pods}</p>
          </div>
          
          <div className="bg-content2 p-4 rounded-medium">
            <div className="flex items-center gap-2">
              <Icon icon="lucide:layers" className="text-primary text-lg" />
              <p className="text-sm font-medium">Deployments</p>
            </div>
            <p className="text-2xl font-semibold mt-2">{cluster.deployments}</p>
          </div>
          
          <div className="bg-content2 p-4 rounded-medium">
            <div className="flex items-center gap-2">
              <Icon icon="lucide:network" className="text-primary text-lg" />
              <p className="text-sm font-medium">Services</p>
            </div>
            <p className="text-2xl font-semibold mt-2">{cluster.services}</p>
          </div>
        </div>
        
        <div className="flex justify-end mt-4">
          <Button variant="flat" color="primary" endContent={<Icon icon="lucide:external-link" />}>
            View Details
          </Button>
        </div>
      </CardBody>
    </Card>
  );
};