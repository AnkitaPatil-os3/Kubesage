import React, { useEffect, useState } from "react";
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
import { useHistory } from "react-router-dom";
 
export const SecurityScanner: React.FC = () => {
  const username = "k8s-usr";
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const history = useHistory();
 
  useEffect(() => {
    fetch(`/kubeconfig/security?username=${username}`)
      .then((res) => res.json())
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load security data:", err);
        setLoading(false);
      });
  }, [username]);
 
  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return "danger";
      case "high":
        return "warning";
      case "medium":
        return "primary";
      case "low":
        return "default";
      default:
        return "default";
    }
  };
 
  const handleViewAll = () => {
    history.push("/dashboard/security-dashboard");
  };
 
  if (loading || !data) return <p>Loading...</p>;
 
  const { vulnerabilities, issues, lastScan } = data;
  const totalIssues =
    vulnerabilities.critical +
    vulnerabilities.high +
    vulnerabilities.medium +
    vulnerabilities.low;
 
  return (
    <Card>
      <CardHeader className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon icon="lucide:shield" className="text-primary" />
            <h3 className="text-lg font-semibold">Security Scanner</h3>
          </div>
        </div>
      </CardHeader>
 
      <CardBody>
        <div className="grid grid-cols-4 gap-2 mb-6">
          <div className="flex flex-col items-center p-2 rounded-medium bg-content2">
            <span className="text-xs text-foreground-500">Critical</span>
            <span className="text-xl font-semibold text-danger">
              {vulnerabilities.critical}
            </span>
          </div>
          <div className="flex flex-col items-center p-2 rounded-medium bg-content2">
            <span className="text-xs text-foreground-500">High</span>
            <span className="text-xl font-semibold text-warning">
              {vulnerabilities.high}
            </span>
          </div>
          <div className="flex flex-col items-center p-2 rounded-medium bg-content2">
            <span className="text-xs text-foreground-500">Medium</span>
            <span className="text-xl font-semibold text-primary">
              {vulnerabilities.medium}
            </span>
          </div>
          <div className="flex flex-col items-center p-2 rounded-medium bg-content2">
            <span className="text-xs text-foreground-500">Low</span>
            <span className="text-xl font-semibold">
              {vulnerabilities.low}
            </span>
          </div>
        </div>
 
        <Table
          aria-label="Top security vulnerabilities"
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
            {issues.map((issue: any) => (
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
                    <p className="text-xs text-foreground-500">
                      {issue.description}
                    </p>
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
            onClick={handleViewAll}
            endContent={<Icon icon="lucide:external-link" />}
          >
            View All ({totalIssues})
          </Button>
        </div>
      </CardBody>
    </Card>
  );
};
 
 