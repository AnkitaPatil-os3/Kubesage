import React from "react";
import { Icon } from "@iconify/react";
import { 
  Card, 
  CardBody, 
  CardHeader, 
  Button,
  Chip
} from "@heroui/react";

interface AiInsightsProps {
  clusterId: string;
}

export const AiInsights: React.FC<AiInsightsProps> = ({ clusterId }) => {
  // Sample data - in a real app, this would be fetched from an API
  const insightsData = {
    production: [
      { 
        id: 1, 
        type: "optimization", 
        title: "Resource Optimization Opportunity", 
        description: "Several deployments are consistently using less than 30% of requested resources. Consider right-sizing to save costs.",
        impact: "high"
      },
      { 
        id: 2, 
        type: "security", 
        title: "Security Best Practice", 
        description: "Network policies are not enforcing traffic segmentation between namespaces. Implement namespace isolation.",
        impact: "medium"
      },
      { 
        id: 3, 
        type: "reliability", 
        title: "Reliability Improvement", 
        description: "API service lacks proper horizontal scaling configuration. Add HPA to improve resilience.",
        impact: "high"
      }
    ],
    staging: [
      { 
        id: 1, 
        type: "optimization", 
        title: "Resource Optimization Opportunity", 
        description: "Several deployments are consistently using less than 40% of requested resources. Consider right-sizing to save costs.",
        impact: "medium"
      },
      { 
        id: 2, 
        type: "security", 
        title: "Security Best Practice", 
        description: "Network policies are not enforcing traffic segmentation between namespaces. Implement namespace isolation.",
        impact: "medium"
      },
      { 
        id: 3, 
        type: "reliability", 
        title: "Reliability Improvement", 
        description: "Multiple services lack readiness probes. Add probes to improve service reliability.",
        impact: "medium"
      }
    ],
    development: [
      { 
        id: 1, 
        type: "optimization", 
        title: "Resource Optimization Opportunity", 
        description: "Several deployments are consistently using less than 50% of requested resources. Consider right-sizing to save costs.",
        impact: "low"
      },
      { 
        id: 2, 
        type: "security", 
        title: "Security Best Practice", 
        description: "Network policies are not enforcing traffic segmentation between namespaces. Implement namespace isolation.",
        impact: "low"
      },
      { 
        id: 3, 
        type: "reliability", 
        title: "Reliability Improvement", 
        description: "Multiple services lack readiness probes. Add probes to improve service reliability.",
        impact: "medium"
      },
      { 
        id: 4, 
        type: "security", 
        title: "Security Vulnerability", 
        description: "Container images are running as root. Implement non-root user execution.",
        impact: "high"
      }
    ]
  };

  // Default to production if the clusterId doesn't exist in insightsData
  const insights = insightsData[clusterId as keyof typeof insightsData] || insightsData.production;
  
  const getTypeIcon = (type: string) => {
    switch (type) {
      case "optimization": return "lucide:zap";
      case "security": return "lucide:shield";
      case "reliability": return "lucide:heart-pulse";
      default: return "lucide:info";
    }
  };
  
  const getTypeColor = (type: string) => {
    switch (type) {
      case "optimization": return "primary";
      case "security": return "danger";
      case "reliability": return "success";
      default: return "default";
    }
  };
  
  const getImpactColor = (impact: string) => {
    switch (impact) {
      case "high": return "danger";
      case "medium": return "warning";
      case "low": return "primary";
      default: return "default";
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon icon="lucide:lightbulb" className="text-primary" />
            <h3 className="text-lg font-semibold">AI Insights</h3>
          </div>
          <Button 
            size="sm" 
            color="primary" 
            variant="flat" 
            startContent={<Icon icon="lucide:refresh-cw" />}
          >
            Refresh
          </Button>
        </div>
        <p className="text-sm text-foreground-500">AI-powered recommendations for your cluster</p>
      </CardHeader>
      <CardBody>
        <div className="space-y-4">
          {insights.map((insight) => (
            <div key={insight.id} className="p-3 border border-divider rounded-medium">
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-full bg-${getTypeColor(insight.type)}-100`}>
                  <Icon 
                    icon={getTypeIcon(insight.type)} 
                    className={`text-${getTypeColor(insight.type)}`} 
                  />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-medium">{insight.title}</h4>
                    <Chip 
                      color={getImpactColor(insight.impact)} 
                      variant="flat" 
                      size="sm"
                    >
                      {insight.impact} impact
                    </Chip>
                  </div>
                  <p className="text-sm text-foreground-500">{insight.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        <div className="flex justify-end mt-4">
          <Button 
            variant="flat" 
            color="primary" 
            endContent={<Icon icon="lucide:external-link" />}
          >
            View All Insights
          </Button>
        </div>
      </CardBody>
    </Card>
  );
};