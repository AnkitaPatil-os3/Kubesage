import React from "react";
import { Card, CardBody, CardHeader, Button, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";
 
interface CarbonEmissionDashboardProps {
    selectedCluster?: string;
}
 
export const CarbonEmissionDashboard: React.FC<CarbonEmissionDashboardProps> = ({ selectedCluster }) => {
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);
 
    // Dashboard URL with parameters to hide UI elements
    const dashboardUrl = React.useMemo(() => {
        const baseUrl = "https://10.0.32105:3000/grafana-monitoring/d/NhnADUW4zIB/greenops-overview";
        const params = new URLSearchParams({
            orgId: "1",
            from: "now-5m",
            to: "now",
            theme: "light",
            hideControls: 'true', // Hide controls including share button
            toolbar: 'false' // Hide toolbar
            // Hide UI elements for embedded view
            // kiosk: "tv",
        });
 
        return `${baseUrl}?${params.toString()}`;
    }, [selectedCluster]);
 
    const handleIframeLoad = () => {
        setIsLoading(false);
        setError(null);
    };
 
    const handleIframeError = () => {
        setIsLoading(false);
        setError("Failed to load carbon emission dashboard. Please check if the dashboard is accessible.");
    };
 
    const refreshDashboard = () => {
        setIsLoading(true);
        setError(null);
        // Force iframe reload
        const iframe = document.getElementById('carbon-emission-iframe') as HTMLIFrameElement;
        if (iframe) {
            iframe.src = iframe.src;
        }
    };
 
    return (
        <div className="space-y-6">
            <Card className="w-full">
                
                <CardBody className="p-0 relative">
                    <div className="relative w-full" style={{ height: "calc(100vh - 200px)" }}>
                        {isLoading && (
                            <div className="absolute inset-0 flex items-center justify-center bg-content1 z-10">
                                <div className="flex flex-col items-center gap-4">
                                    <Spinner size="lg" color="success" />
                                    <p className="text-sm text-foreground-500">Loading carbon emission dashboard...</p>
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
                            id="carbon-emission-iframe"
                            src={dashboardUrl}
                            className="w-full h-full border-0 rounded-lg"
                            title="Carbon Emission Dashboard"
                            onLoad={handleIframeLoad}
                            onError={handleIframeError}
                            sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
                            style={{
                                minHeight: "600px",
                                background: "transparent"
                            }}
                        />
 
                        {/* Overlay header to hide Grafana dashboard header */}
                        <div className="absolute top-0 left-0 right-0 z-30 bg-content1 shadow-sm">
                            <div className="justify-center py-4 px-6 border-b border-divider">
                                <div className="flex gap-3">
                                    <Icon icon="lucide:cpu" className="text-success text-4xl mt-1" />
                                    <div>
                                    <h3 className="text-xl font-semibold text-foreground">Sustainable Computing</h3>
                                    <p className="text-sm text-foreground-500 ">
                                Real-time carbon footprint monitoring and energy consumption analytics
                            </p>
                                    </div>
                                </div>
                                
                            </div>
                        </div>
                    </div>
                </CardBody>
            </Card>
 
            {/* Carbon Emission Insights Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                    <CardBody className="text-center">
                        <div className="flex flex-col items-center gap-2">
                            <Icon icon="lucide:zap" className="text-2xl text-warning" />
                            <div>
                                <p className="text-sm text-foreground-500">Energy Consumption</p>
                                <p className="text-lg font-semibold">Power Usage</p>
                            </div>
                        </div>
                    </CardBody>
                </Card>
 
                <Card>
                    <CardBody className="text-center">
                        <div className="flex flex-col items-center gap-2">
                            <Icon icon="lucide:cloud" className="text-2xl text-primary" />
                            <div>
                                <p className="text-sm text-foreground-500">CO2 Emissions</p>
                                <p className="text-lg font-semibold">Carbon Footprint</p>
                            </div>
                        </div>
                    </CardBody>
                </Card>
 
                <Card>
                    <CardBody className="text-center">
                        <div className="flex flex-col items-center gap-2">
                            <Icon icon="lucide:trending-down" className="text-2xl text-success" />
                            <div>
                                <p className="text-sm text-foreground-500">Efficiency</p>
                                <p className="text-lg font-semibold">Green Metrics</p>
                            </div>
                        </div>
                    </CardBody>
                </Card>
            </div>
        </div>
    );
};
 
export default CarbonEmissionDashboard;
 
 