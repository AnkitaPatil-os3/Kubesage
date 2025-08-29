import React, { useEffect, useState } from "react";
import { Icon } from "@iconify/react";
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Chip,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell
} from "@heroui/react";
import { useHistory } from "react-router-dom";

interface SecurityScannerProps {
  clusterName: string; // ✅ Accept cluster name
}

export const SecurityScanner: React.FC<SecurityScannerProps> = ({ clusterName }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const history = useHistory();

  useEffect(() => {
    if (!clusterName) return;

    setLoading(true);
    fetch(`/api/v2.0/security?cluster=${encodeURIComponent(clusterName)}`)
      .then((res) => res.json())
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load security data:", err);
        setData(null);
        setLoading(false);
      });
  }, [clusterName]);

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

  if (loading) return <p>Loading...</p>;
  if (!data || !data.vulnerabilities || !data.issues) return <p>No data available.</p>;

  const { vulnerabilities, issues } = data;
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
            base: "max-h-[300px] overflow-auto",
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

      
      </CardBody>
    </Card>
  );
};
