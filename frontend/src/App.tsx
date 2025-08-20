import React from "react";
import { Switch, Route, Redirect } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { useTheme } from "@heroui/use-theme";
 
import { ProtectedRoute } from "./components/protected-route";
// import { rolePermissions } from "./config/permissions";
import { Remediations } from "./pages/remediations";
// Pages
import { LoginPage } from "./pages/login";
import { DashboardLayout } from "./layouts/dashboard-layout";
import { ClusterHealth } from "./pages/cluster-health";
import ChatOps from "./pages/chat-ops";
import UploadKubeconfig from "./pages/upload-kubeconfig";
import { CostAnalysis } from "./components/cost-analysis";
import { ObservabilityDashboard } from "./components/test";
import { CarbonEmissionDashboard } from "./components/Carbon-emission";
import ClusterAnalyze from "./components/cluster-analyze";
// import { SecurityPage } from "./components/security-page";
import { UsersAndRBAC } from "./components/UsersAndRBAC";
import { SecOpsDashboard } from "./components/SecOpsDashboard";
import  Policies  from "./pages/policies";
import WorkloadDashboard from "./pages/workload-dashboard";
import Applications from "./pages/applications";
 
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
    if (email && password) {
      setIsAuthenticated(true);
      localStorage.setItem('isAuthenticated', 'true');
      localStorage.setItem('userEmail', email);
      localStorage.setItem('username', email);
      return true;
    }
    return false;
  };
 
  const handleLogout = () => {
    setIsAuthenticated(false);
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('username');
    localStorage.removeItem('access_token');
  };
 
  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };
 
  // Define all dashboard routes with required permissions and components
  const dashboardRoutes = [
    { path: "/dashboard", exact: true, permission: "dashboard", component: () => <Redirect to="/dashboard/overview" /> },
    { path: "/dashboard/overview", permission: "dashboard", component: ClusterHealth },
    { path: "/dashboard/chatops", permission: "chatops", component: ChatOps },
    { path: "/dashboard/upload", permission: "dashboard", component: UploadKubeconfig },
    { path: "/dashboard/applications", permission: "applications", component: Applications },
    { path: "/dashboard/workloads", permission: "workloads", component: WorkloadDashboard },
    { path: "/dashboard/cost", permission: "cost", component: CostAnalysis },
    // { path: "/dashboard/security", permission: "security", component: SecurityPage },
    { path: "/dashboard/observability", permission: "observability", component: ObservabilityDashboard },
    { path: "/dashboard/analyze", permission: "analyze", component: ClusterAnalyze },
    // Special case for /dashboard/users route
    
    { path: "/dashboard/remediations", permission: "remediations", component: Remediations },
    { path: "/dashboard/users", permission: "users_only", component: UsersAndRBAC },
    { path: "/dashboard/security-dashboard", permission: "security", component: SecOpsDashboard },
    { path: "/dashboard/security-policies", permission: "security", component: Policies },
    { path: "/dashboard/carbon-emission", permission: "carbon-emission", component: CarbonEmissionDashboard },
    { path: "/dashboard/backup", permission: "backup", component: () => <div>Backup & Restore Page</div> },
    { path: "/dashboard/secrets", permission: "secrets", component: () => <div>Secrets Management Page</div> },
    { path: "/dashboard/compliance", permission: "compliance", component: () => <div>Compliance Page</div> },
    { path: "/dashboard/settings", permission: "settings", component: () => <div>Settings Page</div> },
    { path: "/dashboard/integrations", permission: "integrations", component: () => <div>Integrations Page</div> },
    { path: "/dashboard/help", permission: "help", component: () => <div>Help Page</div> },
  ];
 
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
              <DashboardLayout onLogout={handleLogout} toggleTheme={toggleTheme} currentTheme={theme}>
                <Switch>
                  {dashboardRoutes.map(({ path, exact, permission, component }) => (
                    <ProtectedRoute
                      key={path}
                      path={path}
                      exact={exact}
                      requiredPermission={permission}
                      component={component}
                    />
                  ))}
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
 