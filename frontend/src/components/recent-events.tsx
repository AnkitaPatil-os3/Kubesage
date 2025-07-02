import React from "react";
import { Icon } from "@iconify/react";
import { 
  Card, 
  CardBody, 
  CardHeader, 
  Chip,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button,
  Pagination
} from "@heroui/react";

interface RecentEventsProps {
  clusterId: string;
}

export const RecentEvents: React.FC<RecentEventsProps> = ({ clusterId }) => {
  const [page, setPage] = React.useState(1);
  const rowsPerPage = 5;
  
  // Sample data - in a real app, this would be fetched from an API
  const eventsData = {
    production: [
      { id: 1, type: "Pod", name: "api-server-5d8c7b9f68-2xvqz", event: "Started", severity: "info", time: "2 minutes ago", namespace: "default" },
      { id: 2, type: "Deployment", name: "frontend", event: "Scaled", severity: "info", time: "15 minutes ago", namespace: "web" },
      { id: 3, type: "Node", name: "worker-node-3", event: "DiskPressure", severity: "warning", time: "32 minutes ago", namespace: "" },
      { id: 4, type: "Service", name: "api-gateway", event: "EndpointsUpdated", severity: "info", time: "45 minutes ago", namespace: "api" },
      { id: 5, type: "Pod", name: "redis-master-0", event: "OOMKilled", severity: "error", time: "1 hour ago", namespace: "database" },
      { id: 6, type: "StatefulSet", name: "postgres", event: "Scaled", severity: "info", time: "1.5 hours ago", namespace: "database" },
      { id: 7, type: "ConfigMap", name: "app-config", event: "Created", severity: "info", time: "2 hours ago", namespace: "default" },
      { id: 8, type: "Secret", name: "api-keys", event: "Updated", severity: "info", time: "2.5 hours ago", namespace: "api" },
      { id: 9, type: "PersistentVolume", name: "data-volume", event: "Bound", severity: "info", time: "3 hours ago", namespace: "" },
      { id: 10, type: "Ingress", name: "main-ingress", event: "Updated", severity: "info", time: "3.5 hours ago", namespace: "web" },
      { id: 11, type: "Pod", name: "monitoring-6f7d9c4b5-1qaz2", event: "Failed", severity: "error", time: "4 hours ago", namespace: "monitoring" },
      { id: 12, type: "HorizontalPodAutoscaler", name: "api-hpa", event: "ScalingReplicaSet", severity: "info", time: "4.5 hours ago", namespace: "api" }
    ],
    staging: [
      { id: 1, type: "Pod", name: "api-server-5d8c7b9f68-2xvqz", event: "Started", severity: "info", time: "5 minutes ago", namespace: "default" },
      { id: 2, type: "Deployment", name: "frontend", event: "Scaled", severity: "info", time: "20 minutes ago", namespace: "web" },
      { id: 3, type: "Pod", name: "cache-6f7d9c4b5-1qaz2", event: "Failed", severity: "error", time: "35 minutes ago", namespace: "cache" },
      { id: 4, type: "Service", name: "api-gateway", event: "EndpointsUpdated", severity: "info", time: "50 minutes ago", namespace: "api" },
      { id: 5, type: "Node", name: "worker-node-2", event: "Ready", severity: "info", time: "1.2 hours ago", namespace: "" },
      { id: 6, type: "StatefulSet", name: "postgres", event: "Scaled", severity: "info", time: "1.8 hours ago", namespace: "database" }
    ],
    development: [
      { id: 1, type: "Pod", name: "api-server-5d8c7b9f68-2xvqz", event: "Started", severity: "info", time: "10 minutes ago", namespace: "default" },
      { id: 2, type: "Deployment", name: "frontend", event: "Failed", severity: "error", time: "25 minutes ago", namespace: "web" },
      { id: 3, type: "Pod", name: "cache-6f7d9c4b5-1qaz2", event: "OOMKilled", severity: "error", time: "40 minutes ago", namespace: "cache" },
      { id: 4, type: "Service", name: "api-gateway", event: "EndpointsUpdated", severity: "info", time: "55 minutes ago", namespace: "api" }
    ]
  };

  // Default to production if the clusterId doesn't exist in eventsData
  const events = eventsData[clusterId as keyof typeof eventsData] || eventsData.production;
  const pages = Math.ceil(events.length / rowsPerPage);
  
  const items = React.useMemo(() => {
    const start = (page - 1) * rowsPerPage;
    const end = start + rowsPerPage;
    
    return events.slice(start, end);
  }, [page, events]);
  
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "info": return "primary";
      case "warning": return "warning";
      case "error": return "danger";
      default: return "default";
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon icon="lucide:list" className="text-primary" />
            <h3 className="text-lg font-semibold">Recent Events</h3>
          </div>
          <div className="flex gap-2">
            <Button 
              size="sm" 
              variant="flat" 
              color="default" 
              startContent={<Icon icon="lucide:filter" />}
            >
              Filter
            </Button>
            <Button 
              size="sm" 
              variant="flat" 
              color="primary" 
              startContent={<Icon icon="lucide:refresh-cw" />}
            >
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardBody>
        <Table 
          aria-label="Recent cluster events" 
          removeWrapper
        >
          <TableHeader>
            <TableColumn>TYPE</TableColumn>
            <TableColumn>NAME</TableColumn>
            <TableColumn>EVENT</TableColumn>
            <TableColumn>NAMESPACE</TableColumn>
            <TableColumn>SEVERITY</TableColumn>
            <TableColumn>TIME</TableColumn>
          </TableHeader>
          <TableBody>
            {items.map((event) => (
              <TableRow key={event.id}>
                <TableCell>{event.type}</TableCell>
                <TableCell>{event.name}</TableCell>
                <TableCell>{event.event}</TableCell>
                <TableCell>{event.namespace || "-"}</TableCell>
                <TableCell>
                  <Chip 
                    color={getSeverityColor(event.severity)} 
                    variant="flat" 
                    size="sm"
                  >
                    {event.severity}
                  </Chip>
                </TableCell>
                <TableCell>{event.time}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        
        <div className="flex justify-between items-center mt-4">
          <span className="text-sm text-foreground-500">
            Showing {Math.min(events.length, page * rowsPerPage) - ((page - 1) * rowsPerPage)} of {events.length} events
          </span>
          <Pagination 
            total={pages} 
            page={page} 
            onChange={setPage}
            showControls
            size="sm"
          />
        </div>
      </CardBody>
    </Card>
  );
};