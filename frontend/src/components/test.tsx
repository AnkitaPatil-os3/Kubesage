import React from "react";
import { Card, CardBody, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";

export const ObservabilityDashboard: React.FC = () => {
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);
    const [dashboardUrl, setDashboardUrl] = React.useState<string | null>(null);
    const [theme, setTheme] = React.useState<string>(() => localStorage.getItem("heroui-theme") || "light");

    // Helper to generate dashboard URL
    const getDashboardUrl = (currentTheme: string) => {
        const role = localStorage.getItem("roles") || "";
        const username = localStorage.getItem("username") || "";

        const isSuperAdmin = role.toLowerCase().includes("super");

        const baseParams = new URLSearchParams({
            orgId: "1",
            from: "now-5m",
            to: "now",
            timezone: "browser",
            theme: currentTheme,
            kiosk: "true",
            "var-DS": "eepx4n9ag9vk0c",
            "var-Cluster": "rod-lgtm-stck-mumbai-south",
            "var-Node": "prod-lgtm-stck-mumbai-south",
            "var-Namespace": "alloy",
            "var-Pod": "alloy-tc5vp",
            "var-Container": "alloy",
            "var-logs": "aepxfvdv7708wf",
        });

        if (!isSuperAdmin) {
            baseParams.append("var-Username", username);
        }

        const baseUrl = isSuperAdmin
            ? "https://10.0.34.151:3000/d/ddonjajttscn4e/kub-cluster-details"
            : "https://10.0.34.151:3000/d/ddonjajttscn4/kub-cluster-details-replica";

        return `${baseUrl}?${baseParams.toString()}`;
    };

    // Watch for theme changes in real-time
    React.useEffect(() => {
        const checkThemeChange = () => {
            const current = localStorage.getItem("heroui-theme") || "light";
            if (current !== theme) {
                setTheme(current);
                setDashboardUrl(getDashboardUrl(current));
                setIsLoading(true);
            }
        };

        // Run every 1 second (can reduce to 500ms if needed)
        const interval = setInterval(checkThemeChange, 1000);

        // Initial load
        setDashboardUrl(getDashboardUrl(theme));

        return () => clearInterval(interval);
    }, [theme]);

    const handleIframeLoad = () => {
        setIsLoading(false);
        setError(null);
    };

    const handleIframeError = () => {
        setIsLoading(false);
        setError("Failed to load monitoring dashboard. Please check if the dashboard is accessible.");
    };

    return (
        <div className="p-4 space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                    <Icon icon="lucide:activity" className="text-white text-2xl" />
                </div>
                <div>
                    <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
                        Monitoring Dashboard
                    </h1>
                    <p className="text-sm text-foreground-500 mt-1">
                        Real-time insights and performance metrics powered by KubeSage
                    </p>
                </div>
            </div>

            {/* Dashboard */}
            <Card className="w-full shadow-lg">
                <CardBody className="p-0 relative">
                    <div
                        className="relative w-full bg-content1 rounded-lg overflow-hidden"
                        style={{ height: "calc(100vh - 200px)", minHeight: "600px" }}
                    >
                        {isLoading && (
                            <div className="absolute inset-0 flex items-center justify-center bg-content1 z-10">
                                <div className="flex flex-col items-center gap-4">
                                    <Spinner size="lg" color="primary" />
                                    <p className="text-lg font-medium text-foreground">Loading Dashboard...</p>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="absolute inset-0 flex items-center justify-center bg-content1 z-10">
                                <div className="text-center space-y-4 max-w-md mx-auto p-6">
                                    <div className="w-16 h-16 bg-danger/10 rounded-full flex items-center justify-center mx-auto">
                                        <Icon icon="lucide:alert-circle" className="text-4xl text-danger" />
                                    </div>
                                    <h3 className="text-xl font-bold text-danger mb-2">Dashboard Unavailable</h3>
                                    <p className="text-sm text-foreground-500 mb-2">{error}</p>
                                </div>
                            </div>
                        )}

                        {dashboardUrl && !error && (
                            <iframe
                                id="observability-iframe"
                                src={dashboardUrl}
                                className="w-full h-full border-0"
                                title="Grafana Monitoring Dashboard"
                                onLoad={handleIframeLoad}
                                onError={handleIframeError}
                                sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
                                style={{
                                    background: "transparent",
                                    display: error ? "none" : "block",
                                }}
                            />
                        )}
                    </div>
                </CardBody>
            </Card>
        </div>
    );
};

export default ObservabilityDashboard;
