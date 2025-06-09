import React from "react";
import { Card, CardBody, CardHeader, Button, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";
 
interface ObservabilityDashboardProps {
    selectedCluster?: string;
}
 
export const ObservabilityDashboard: React.FC<ObservabilityDashboardProps> = ({ selectedCluster }) => {
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);
 
    // Dashboard URL with parameters to hide UI elements
    const dashboardUrl = React.useMemo(() => {
        const baseUrl = "https://10.0.32.103:3000/grafana-monitoring/d/ddonjajttscn4e/kub-cluster-details";
        const params = new URLSearchParams({
            orgId: "1",
            "var-DS": "delfjenv5n30ga",
            "var-Cluster": selectedCluster || "OMEGA-Agent",
            "var-Node": "ashish-master",
            "var-Namespace": "calico-system",
            "var-Pod": "calico-node-s56zs",
            "var-Container": "calico-node",
            "var-logs": "eemj7g7ndgzcwe",
            from: "1749426869920",
            to: "1749448469920",
            theme: "light",
            // Hide UI elements for embedded view
            kiosk: "tv",
        });
 
        return `${baseUrl}?${params.toString()}`;
    }, [selectedCluster]);
 
    const handleIframeLoad = () => {
        setIsLoading(false);
        setError(null);
    };
 
    const handleIframeError = () => {
        setIsLoading(false);
        setError("Failed to load observability dashboard. Please check if the dashboard is accessible.");
    };
 
    const refreshDashboard = () => {
        setIsLoading(true);
        setError(null);
        // Force iframe reload
        const iframe = document.getElementById('observability-iframe') as HTMLIFrameElement;
        if (iframe) {
            iframe.src = iframe.src;
        }
    };
 
    return (
        <div className="space-y-6">
            <Card className="w-full">
                <CardHeader className="flex flex-row items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Icon icon="lucide:activity" className="text-primary" />
                        <div>
                            <h2 className="text-xl font-semibold">Cluster Overview</h2>
                            <p className="text-sm text-foreground-500">
                                Real-time cluster metrics, performance analytics and resource monitoring
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="flat"
                            size="sm"
                            onPress={refreshDashboard}
                            startContent={<Icon icon="lucide:refresh-cw" />}
                        >
                            Refresh
                        </Button>
                    </div>
                </CardHeader>
                <CardBody className="p-0">
                    <div className="relative w-full" style={{ height: "calc(100vh - 200px)" }}>
                        {isLoading && (
                            <div className="absolute inset-0 flex items-center justify-center bg-content1 z-10">
                                <div className="flex flex-col items-center gap-3">
                                    <Spinner size="lg" color="primary" />
                                    <p className="text-sm text-foreground-500">Loading cluster dashboard...</p>
                                </div>
                            </div>
                        )}
 
                        {error && (
                            <div className="absolute inset-0 flex items-center justify-center bg-content1 z-10">
                                <div className="text-center space-y-3">
                                    <Icon icon="lucide:alert-circle" className="text-4xl text-danger mx-auto" />
                                    <div>
                                        <p className="text-danger font-medium">Dashboard Load Error</p>
                                        <p className="text-sm text-foreground-500 mt-1">{error}</p>
                                    </div>
                                    <Button
                                        color="primary"
                                        variant="flat"
                                        size="sm"
                                        onPress={refreshDashboard}
                                        startContent={<Icon icon="lucide:refresh-cw" />}
                                    >
                                        Try Again
                                    </Button>
                                </div>
                            </div>
                        )}
 
                        <iframe
                            id="observability-iframe"
                            src={dashboardUrl}
                            className="w-full h-full border-0 rounded-lg"
                            title="Cluster Overview Dashboard"
                            onLoad={handleIframeLoad}
                            onError={handleIframeError}
                            sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
                            style={{
                                minHeight: "600px",
                                background: "transparent"
                            }}
                        />
                    </div>
                </CardBody>
            </Card>
 
            {/* Additional Observability Insights Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                    <CardBody className="text-center">
                        <div className="flex flex-col items-center gap-2">
                            <Icon icon="lucide:cpu" className="text-2xl text-success" />
                            <div>
                                <p className="text-sm text-foreground-500">Resource Usage</p>
                                <p className="text-lg font-semibold">CPU & Memory</p>
                            </div>
                        </div>
                    </CardBody>
                </Card>
 
                <Card>
                    <CardBody className="text-center">
                        <div className="flex flex-col items-center gap-2">
                            <Icon icon="lucide:network" className="text-2xl text-primary" />
                            <div>
                                <p className="text-sm text-foreground-500">Network Traffic</p>
                                <p className="text-lg font-semibold">I/O Metrics</p>
                            </div>
                        </div>
                    </CardBody>
                </Card>
 
                <Card>
                    <CardBody className="text-center">
                        <div className="flex flex-col items-center gap-2">
                            <Icon icon="lucide:gauge" className="text-2xl text-warning" />
                            <div>
                                <p className="text-sm text-foreground-500">Performance</p>
                                <p className="text-lg font-semibold">Health Status</p>
                            </div>
                        </div>
                    </CardBody>
                </Card>
            </div>
        </div>
    );
};
 
export default ObservabilityDashboard;
 
 