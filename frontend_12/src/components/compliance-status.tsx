import React from "react";
import { Icon } from "@iconify/react";
import { 
  Card, 
  CardBody, 
  CardHeader, 
  Progress, 
  Chip,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button
} from "@heroui/react";

interface ComplianceStatusProps {
  clusterId: string;
}

export const ComplianceStatus: React.FC<ComplianceStatusProps> = ({ clusterId }) => {
  // Sample data - in a real app, this would be fetched from an API
  const complianceData = {
    production: {
      score: 92,
      frameworks: [
        { id: "pci", name: "PCI DSS", score: 94 },
        { id: "hipaa", name: "HIPAA", score: 96 },
        { id: "gdpr", name: "GDPR", score: 88 },
        { id: "soc2", name: "SOC 2", score: 90 }
      ],
      issues: [
        { id: 1, rule: "Network Policy", status: "failed", description: "Default deny policy not configured" },
        { id: 2, rule: "Pod Security", status: "warning", description: "Privileged containers detected" },
        { id: 3, rule: "Secret Management", status: "warning", description: "Unencrypted secrets found" }
      ]
    },
    staging: {
      score: 84,
      frameworks: [
        { id: "pci", name: "PCI DSS", score: 82 },
        { id: "hipaa", name: "HIPAA", score: 86 },
        { id: "gdpr", name: "GDPR", score: 80 },
        { id: "soc2", name: "SOC 2", score: 88 }
      ],
      issues: [
        { id: 1, rule: "Network Policy", status: "failed", description: "Default deny policy not configured" },
        { id: 2, rule: "Pod Security", status: "failed", description: "Privileged containers detected" },
        { id: 3, rule: "Secret Management", status: "warning", description: "Unencrypted secrets found" },
        { id: 4, rule: "RBAC", status: "warning", description: "Over-permissive roles detected" }
      ]
    },
    development: {
      score: 76,
      frameworks: [
        { id: "pci", name: "PCI DSS", score: 74 },
        { id: "hipaa", name: "HIPAA", score: 78 },
        { id: "gdpr", name: "GDPR", score: 72 },
        { id: "soc2", name: "SOC 2", score: 80 }
      ],
      issues: [
        { id: 1, rule: "Network Policy", status: "failed", description: "Default deny policy not configured" },
        { id: 2, rule: "Pod Security", status: "failed", description: "Privileged containers detected" },
        { id: 3, rule: "Secret Management", status: "failed", description: "Unencrypted secrets found" },
        { id: 4, rule: "RBAC", status: "warning", description: "Over-permissive roles detected" },
        { id: 5, rule: "Resource Limits", status: "warning", description: "Missing resource limits" }
      ]
    }
  };

  // Default to production if the clusterId doesn't exist in complianceData
  const data = complianceData[clusterId as keyof typeof complianceData] || complianceData.production;
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case "passed": return "success";
      case "warning": return "warning";
      case "failed": return "danger";
      default: return "default";
    }
  };
  
  const getScoreColor = (score: number) => {
    if (score >= 90) return "success";
    if (score >= 80) return "primary";
    if (score >= 70) return "warning";
    return "danger";
  };

  return (
    <Card>
      <CardHeader className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <Icon icon="lucide:check-circle" className="text-primary" />
          <h3 className="text-lg font-semibold">Compliance Status</h3>
        </div>
      </CardHeader>
      <CardBody>
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-sm text-foreground-500">Overall Compliance Score</p>
            <p className="text-3xl font-semibold">{data.score}%</p>
          </div>
          <div className="w-16 h-16 rounded-full border-4 border-primary flex items-center justify-center">
            <Icon 
              icon={data.score >= 90 ? "lucide:check" : "lucide:alert-triangle"} 
              className={`text-2xl ${data.score >= 90 ? "text-success" : "text-warning"}`} 
            />
          </div>
        </div>
        
        <div className="space-y-3 mb-6">
          {data.frameworks.map((framework) => (
            <div key={framework.id}>
              <div className="flex justify-between mb-1">
                <span className="text-sm">{framework.name}</span>
                <span className="text-sm font-medium">{framework.score}%</span>
              </div>
              <Progress 
                value={framework.score} 
                color={getScoreColor(framework.score)}
                size="sm"
              />
            </div>
          ))}
        </div>
        
        <div>
          <h4 className="text-sm font-medium mb-2">Compliance Issues</h4>
          <Table 
            aria-label="Compliance issues" 
            removeWrapper
            classNames={{
              base: "max-h-[180px] overflow-auto",
            }}
          >
            <TableHeader>
              <TableColumn>RULE</TableColumn>
              <TableColumn>STATUS</TableColumn>
              <TableColumn>DESCRIPTION</TableColumn>
            </TableHeader>
            <TableBody>
              {data.issues.map((issue) => (
                <TableRow key={issue.id}>
                  <TableCell>{issue.rule}</TableCell>
                  <TableCell>
                    <Chip 
                      color={getStatusColor(issue.status)} 
                      variant="flat" 
                      size="sm"
                    >
                      {issue.status}
                    </Chip>
                  </TableCell>
                  <TableCell>{issue.description}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        
        <div className="flex justify-end mt-4">
          <Button 
            variant="flat" 
            color="primary" 
            endContent={<Icon icon="lucide:external-link" />}
          >
            View Full Report
          </Button>
        </div>
      </CardBody>
    </Card>
  );
};