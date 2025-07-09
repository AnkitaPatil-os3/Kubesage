import React from "react";
import { Card, CardBody, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";

export const SecOpsDashboard: React.FC = () => {
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);
    const [dashboardUrl, setDashboardUrl] = React.useState<string | null>(null);
    const [theme, setTheme] = React.useState<string>(() => localStorage.getItem("heroui-theme") || "dark");

    const buildDashboardUrl = (currentTheme: string): string => {
        const role = localStorage.getItem("roles") || "";
        const username = localStorage.getItem("username") || "k8s-usr";;

        const isSuperAdmin = role.toLowerCase().includes("super");

        const baseUrl = isSuperAdmin
            ? "https://10.0.34.151:3000/d/security_trivy_operator/trivy-operator-vulnerabilities"
            : "https://10.0.34.151:3000/d/security_trivy_operator-1/trivy-operator-vulnerabilities-replica";

        const params = new URLSearchParams({
            orgId: "1",
            from: "now-1h",
            to: "now",
            timezone: "browser",
            refresh: "30s",
            theme: currentTheme,
            kiosk: "true",
            "var-datasource": "eepx4n9ag9vk0c",
            "var-namespace": "$__all",
            "var-resolution": "30s"
        });

        if (!isSuperAdmin) {
            params.append("var-Username", username);
        }

        return `${baseUrl}?${params.toString()}`;
    };

    // Monitor theme changes
    React.useEffect(() => {
        const updateTheme = () => {
            const stored = localStorage.getItem("heroui-theme") || "dark";
            if (stored !== theme) {
                setTheme(stored);
                setDashboardUrl(buildDashboardUrl(stored));
                setIsLoading(true);
            }
        };

        const interval = setInterval(updateTheme, 1000);
        setDashboardUrl(buildDashboardUrl(theme));

        return () => clearInterval(interval);
    }, [theme]);

    const handleIframeLoad = () => {
        setIsLoading(false);
        setError(null);
    };

    const handleIframeError = () => {
        setIsLoading(false);
        setError("Failed to load the SecOps dashboard. Please check the server or network connection.");
    };

    return (
        <div className="p-4 space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-r from-rose-500 to-red-600 rounded-full flex items-center justify-center">
                    <Icon icon="mdi:shield-account" className="text-white text-2xl" />
                </div>
                <div>
                    <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
                        SecOps Dashboard
                    </h1>
                    <p className="text-sm text-foreground-500 mt-1">
                        Security vulnerabilities and container insights 
                    </p>
                </div>
            </div>

            {/* Dashboard */}
            <Card className="w-full shadow-lg">
                <CardBody className="p-0 relative">
                    <div className="relative w-full bg-content1 rounded-lg overflow-hidden" style={{ height: "calc(100vh - 200px)", minHeight: "600px" }}>
                        {isLoading && (
                            <div className="absolute inset-0 flex items-center justify-center bg-content1 z-10">
                                <div className="flex flex-col items-center gap-4">
                                    <Spinner size="lg" color="danger" />
                                    <p className="text-lg font-medium text-foreground">Loading SecOps Dashboard...</p>
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
                                id="secops-dashboard-iframe"
                                src={dashboardUrl}
                                className="w-full h-full border-0"
                                title="Grafana SecOps Dashboard"
                                onLoad={handleIframeLoad}
                                onError={handleIframeError}
                                sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
                                style={{
                                    background: "transparent",
                                    display: error ? "none" : "block"
                                }}
                            />
                        )}
                    </div>
                </CardBody>
            </Card>
        </div>
    );
};

export default SecOpsDashboard;
