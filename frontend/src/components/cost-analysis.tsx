import React from "react";
import { Card, CardBody, CardHeader, Button, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";
 
interface CostAnalysisProps {
  selectedCluster?: string;
}
 
export const CostAnalysis: React.FC<CostAnalysisProps> = ({ selectedCluster }) => {
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
 
  // Grafana URL with parameters to hide UI elements
  const grafanaUrl = React.useMemo(() => {
    const baseUrl = "https://10.0.32.103:3000/grafana-monitoring/d/opencost-mixin-kover-jkwq/finops-overview";
    const params = new URLSearchParams({
      orgId: "1",
      from: "now-1h",
      to: "now",
      theme: "dark",
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
    setError("Failed to load Grafana dashboard. Please check if Grafana is accessible.");
  };
 
  const refreshDashboard = () => {
    setIsLoading(true);
    setError(null);
    // Force iframe reload
    const iframe = document.getElementById('grafana-iframe') as HTMLIFrameElement;
    if (iframe) {
      iframe.src = iframe.src;
    }
  };
 
  return (
    <div className="space-y-6">
      <Card className="w-full">
        <CardBody className="p-0 relative">
          <div className="relative w-full" style={{ height: "calc(100vh - 120px)" }}>
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-content1 z-10">
                <div className="flex flex-col items-center gap-4">
                  <Spinner size="lg" color="primary" />
                  <p className="text-sm text-foreground-500">Loading cost dashboard...</p>
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
              id="grafana-iframe"
              src={grafanaUrl}
              className="w-full h-full border-0 rounded-lg"
              title="OpenCost Dashboard"
              onLoad={handleIframeLoad}
              onError={handleIframeError}
              sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
              style={{
                minHeight: "600px",
                background: "transparent"
              }}
            />
 
            {/* Overlay header to hide Grafana dashboard header */}
            <div className="absolute top-0 left-0 right-0 z-30 shadow-sm w-[1080px]" style={{ backgroundColor: 'rgb(26, 28, 35)' }}>
              <div className="justify-center py-[5px] px-6 border-b border-divider">
                <div className="flex gap-3">
                  <Icon icon="lucide:indian-rupee" className="text-primary text-2xl mt-1" />
                  <div>
                    <h3 className="text-xl font-semibold text-white">Cost Analysis</h3>
                  
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>
 
      
    </div>
  );
};
 
export default CostAnalysis;
