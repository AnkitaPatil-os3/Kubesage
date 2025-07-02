import React from "react";
import { Icon } from "@iconify/react";
import { 
  Card, 
  CardBody, 
  CardHeader, 
  Button, 
  Progress, 
  Chip,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell
} from "@heroui/react";

interface SecurityScannerProps {
  clusterId: string;
}

export const SecurityScanner: React.FC<SecurityScannerProps> = ({ clusterId }) => {
  // Sample data - in a real app, this would be fetched from an API
  const securityData = {
    production: {
      lastScan: "2 hours ago",
      vulnerabilities: {
        critical: 0,
        high: 2,
        medium: 8,
        low: 15
      },
      issues: [
        { id: 1, severity: "high", name: "CVE-2023-5678", component: "nginx:1.21.0", description: "Buffer overflow vulnerability" },
        { id: 2, severity: "high", name: "CVE-2023-4321", component: "redis:6.2.5", description: "Authentication bypass vulnerability" },
        { id: 3, severity: "medium", name: "CVE-2023-9876", component: "postgres:13.4", description: "Information disclosure vulnerability" }
      ]
    },
    staging: {
      lastScan: "6 hours ago",
      vulnerabilities: {
        critical: 1,
        high: 3,
        medium: 12,
        low: 18
      },
      issues: [
        { id: 1, severity: "critical", name: "CVE-2023-1234", component: "node:16.13.0", description: "Remote code execution vulnerability" },
        { id: 2, severity: "high", name: "CVE-2023-5678", component: "nginx:1.21.0", description: "Buffer overflow vulnerability" },
        { id: 3, severity: "high", name: "CVE-2023-4321", component: "redis:6.2.5", description: "Authentication bypass vulnerability" }
      ]
    },
    development: {
      lastScan: "1 day ago",
      vulnerabilities: {
        critical: 2,
        high: 5,
        medium: 14,
        low: 22
      },
      issues: [
        { id: 1, severity: "critical", name: "CVE-2023-1234", component: "node:16.13.0", description: "Remote code execution vulnerability" },
        { id: 2, severity: "critical", name: "CVE-2023-2345", component: "python:3.9.6", description: "Arbitrary code execution vulnerability" },
        { id: 3, severity: "high", name: "CVE-2023-5678", component: "nginx:1.21.0", description: "Buffer overflow vulnerability" }
      ]
    }
  };

  // Default to production if the clusterId doesn't exist in securityData
  const data = securityData[clusterId as keyof typeof securityData] || securityData.production;
  
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical": return "danger";
      case "high": return "warning";
      case "medium": return "primary";
      case "low": return "default";
      default: return "default";
    }
  };
  
  const totalIssues = 
    data.vulnerabilities.critical + 
    data.vulnerabilities.high + 
    data.vulnerabilities.medium + 
    data.vulnerabilities.low;

  return (
    <Card>
      <CardHeader className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon icon="lucide:shield" className="text-primary" />
            <h3 className="text-lg font-semibold">Security Scanner</h3>
          </div>
          <Button 
            size="sm" 
            color="primary" 
            variant="flat" 
            startContent={<Icon icon="lucide:refresh-cw" />}
          >
            Scan Now
          </Button>
        </div>
        <p className="text-sm text-foreground-500">Last scan: {data.lastScan}</p>
      </CardHeader>
      <CardBody>
        <div className="grid grid-cols-4 gap-2 mb-6">
          <div className="flex flex-col items-center p-2 rounded-medium bg-content2">
            <span className="text-xs text-foreground-500">Critical</span>
            <span className="text-xl font-semibold text-danger">{data.vulnerabilities.critical}</span>
          </div>
          <div className="flex flex-col items-center p-2 rounded-medium bg-content2">
            <span className="text-xs text-foreground-500">High</span>
            <span className="text-xl font-semibold text-warning">{data.vulnerabilities.high}</span>
          </div>
          <div className="flex flex-col items-center p-2 rounded-medium bg-content2">
            <span className="text-xs text-foreground-500">Medium</span>
            <span className="text-xl font-semibold text-primary">{data.vulnerabilities.medium}</span>
          </div>
          <div className="flex flex-col items-center p-2 rounded-medium bg-content2">
            <span className="text-xs text-foreground-500">Low</span>
            <span className="text-xl font-semibold">{data.vulnerabilities.low}</span>
          </div>
        </div>
        
        <div className="mb-6">
          <div className="flex justify-between mb-2">
            <span className="text-sm">Security Score</span>
            <span className="text-sm font-medium">
              {Math.max(0, 100 - (data.vulnerabilities.critical * 15 + data.vulnerabilities.high * 5))}%
            </span>
          </div>
          <Progress 
            value={Math.max(0, 100 - (data.vulnerabilities.critical * 15 + data.vulnerabilities.high * 5))}
            color={data.vulnerabilities.critical > 0 ? "danger" : data.vulnerabilities.high > 0 ? "warning" : "success"}
          />
        </div>
        
        <Table 
          aria-label="Security vulnerabilities" 
          removeWrapper
          classNames={{
            base: "max-h-[240px] overflow-auto",
          }}
        >
          <TableHeader>
            <TableColumn>SEVERITY</TableColumn>
            <TableColumn>VULNERABILITY</TableColumn>
            <TableColumn>COMPONENT</TableColumn>
          </TableHeader>
          <TableBody>
            {data.issues.map((issue) => (
              <TableRow key={issue.id}>
                <TableCell>
                  <Chip 
                    color={getSeverityColor(issue.severity)} 
                    variant="flat" 
                    size="sm"
                  >
                    {issue.severity}
                  </Chip>
                </TableCell>
                <TableCell>
                  <div>
                    <p className="font-medium">{issue.name}</p>
                    <p className="text-xs text-foreground-500">{issue.description}</p>
                  </div>
                </TableCell>
                <TableCell>{issue.component}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        
        <div className="flex justify-end mt-4">
          <Button 
            variant="flat" 
            color="primary" 
            endContent={<Icon icon="lucide:external-link" />}
          >
            View All ({totalIssues})
          </Button>
        </div>
      </CardBody>
    </Card>
  );
};