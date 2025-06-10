import React from "react";
import { Switch, Route, Redirect } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { useTheme } from "@heroui/use-theme";
 
// Pages
import { LoginPage } from "./pages/login";
import { DashboardLayout } from "./layouts/dashboard-layout";
import { ClusterOnboarding } from "./pages/cluster-onboarding";
import { ClusterHealth } from "./pages/cluster-health";
import { ChatOps } from "./pages/chat-ops";
import { AdminDashboard } from "./pages/admin-dashboard";
import { UploadKubeconfig } from "./pages/upload-kubeconfig";
import remediationsPage from "./pages/remediations";
import { CostAnalysis } from "./components/cost-analysis";
import { ObservabilityDashboard } from "./components/observability-dashboard";
import { CarbonEmissionDashboard } from "./components/Carbon-emission";
import ClusterAnalyze from "./components/cluster-analyze";

 
export default function App() {
  const { theme, setTheme } = useTheme();
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);
  
  const handleLogin = (email: string, password: string) => {
    // In a real app, this would validate credentials with an API
    if (email && password) {
      setIsAuthenticated(true);
      return true;
    }
    return false;
  };
  
  const handleLogout = () => {
    setIsAuthenticated(false);
  };
  
  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };
 
  return (
    <div className={theme}>
      <AnimatePresence mode="wait">
        <Switch>
          <Route exact path="/login">
            {isAuthenticated ? (
              <Redirect to="/dashboard" />
            ) : (
              <LoginPage onLogin={handleLogin} />
            )}
          </Route>
          
          <Route path="/dashboard">
            {!isAuthenticated ? (
              <Redirect to="/login" />
            ) : (
              <DashboardLayout
                onLogout={handleLogout}
                toggleTheme={toggleTheme}
                currentTheme={theme}
              >
                <Switch>
                  <Route exact path="/dashboard" component={() => <Redirect to="/dashboard/overview" />} />
                  <Route path="/dashboard/overview" component={ClusterHealth} />
                  <Route path="/dashboard/onboarding" component={ClusterOnboarding} />
                  <Route path="/dashboard/chatops" component={ChatOps} />
                  <Route path="/dashboard/admin" component={AdminDashboard} />
                  <Route path="/dashboard/upload" component={UploadKubeconfig} />
                  <Route path="/dashboard/cost" component={CostAnalysis} />
                  <Route path="/dashboard/remediations" component={remediationsPage} />
                  <Route path="/dashboard/observability" component={ObservabilityDashboard} />
                  <Route path="/dashboard/carbon-emission" component={CarbonEmissionDashboard} />
                  <Route path="/dashboard/analyze" component={ClusterAnalyze} />
                </Switch>
              </DashboardLayout>
            )}
          </Route>
          
          <Route path="/">
            <Redirect to={isAuthenticated ? "/dashboard" : "/login"} />
          </Route>
        </Switch>
      </AnimatePresence>
    </div>
  );
}