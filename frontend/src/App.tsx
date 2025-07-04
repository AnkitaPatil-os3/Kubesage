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
import UploadKubeconfig from "./pages/upload-kubeconfig";
import { Remediations as remediationsPage } from "./pages/remediations";
import { CostAnalysis } from "./components/cost-analysis";
import { ObservabilityDashboard } from "./components/observability-dashboard";
import { CarbonEmissionDashboard } from "./components/Carbon-emission";
import ClusterAnalyze from "./components/cluster-analyze";
import Policies from './pages/policies';   
import SecOps from "./pages/sec-ops";

 
 
export default function App() {
  const { theme, setTheme } = useTheme();
  
  // Initialize authentication state from localStorage
  const [isAuthenticated, setIsAuthenticated] = React.useState(() => {
    const savedAuth = localStorage.getItem('isAuthenticated');
    return savedAuth === 'true';
  });
  
  // Update localStorage whenever authentication state changes
  React.useEffect(() => {
    localStorage.setItem('isAuthenticated', isAuthenticated.toString());
  }, [isAuthenticated]);
  
  const handleLogin = (email: string, password: string) => {
    // In a real app, this would validate credentials with an API
    if (email && password) {
      setIsAuthenticated(true);
      // Store authentication state in localStorage
      localStorage.setItem('isAuthenticated', 'true');
      // If you have user data, store it as well
      localStorage.setItem('userEmail', email);
      localStorage.setItem('username', email);
      return true;
    }
    return false;
  };
  
  const handleLogout = () => {
    setIsAuthenticated(false);
    // Clear authentication data from localStorage
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('username');
    localStorage.removeItem('access_token'); // Clear any existing tokens
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
                  <Route path="/dashboard/policies" component={() => <Policies selectedCluster="" />} />
                  <Route path="/dashboard/security" component={SecOps} />
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
 
 
 