import React from "react";
import { Link, useHistory } from "react-router-dom";
import { Icon } from "@iconify/react";
import { Button, Tooltip, Switch, Divider } from "@heroui/react";
import { motion, AnimatePresence } from "framer-motion";
 
interface SidebarProps {
  selectedCluster: string;
  setSelectedCluster: (cluster: string) => void;
  currentPage: string;
  onLogout: () => void;
  toggleTheme: () => void;
  currentTheme: string;
}
 
export const Sidebar: React.FC<SidebarProps> = ({
  selectedCluster,
  setSelectedCluster,
  currentPage,
  onLogout,
  toggleTheme,
  currentTheme
}) => {
  const [isCollapsed, setIsCollapsed] = React.useState(false);
  const [expandedCategory, setExpandedCategory] = React.useState<string | null>("clusters");
  const history = useHistory();
  
  const clusters = [
    { id: "production", name: "Production", icon: "lucide:server" },
    { id: "staging", name: "Staging", icon: "lucide:server" },
    { id: "development", name: "Development", icon: "lucide:server" },
  ];
 
  const navCategories = [
    {
      id: "overview",
      name: "OVERVIEW",
      icon: "lucide:layout-dashboard",
      items: [
        { id: "dashboard", name: "Dashboard", icon: "lucide:layout-dashboard", path: "/dashboard/overview" },
        { id: "clusters", name: "Clusters", icon: "lucide:database", path: "/dashboard/upload" },
        { id: "applications", name: "Applications", icon: "lucide:box", path: "/dashboard/upload" },
        { id: "workloads", name: "Workloads", icon: "lucide:layers", path: "/dashboard/upload" },
      ]
    },
   
    {
      id: "ai_features",
      name: "AI FEATURES",
      icon: "lucide:cpu",
      items: [
        { id: "insights", name: "AI Insights", icon: "lucide:lightbulb", path: "/dashboard/insights" },
        { id: "chatops", name: "ChatOps", icon: "lucide:message-square", path: "/dashboard/chatops" },
        { id: "remediations", name: "Remediations", icon: "lucide:trending-up", path: "/dashboard/remediations" },
        { id: "anomalies", name: "Anomalies", icon: "lucide:alert-triangle", path: "/dashboard/anomalies" },
      ]
    },
    {
      id: "management",
      name: "MANAGEMENT",
      icon: "lucide:settings-2",
      items: [
        { id: "observability", name: "Observability", icon: "lucide:activity", path: "/dashboard/observability" },
        { id: "carbon-emission", name: "GreenOps", icon: "lucide:activity", path: "/dashboard/carbon-emission" },
        { id: "security", name: "Security", icon: "lucide:shield", path: "/dashboard/security" },
        { id: "cost", name: "FinOps", icon: "lucide:dollar-sign", path: "/dashboard/cost" },
        { id: "compliance", name: "Compliance", icon: "lucide:check-circle", path: "/dashboard/compliance" },
      ]
    },
    {
      id: "security",
      name: "SECURITY",
      icon: "lucide:shield",
      items: [
        { id: "security", name: "Security Scanner", icon: "lucide:shield", path: "/dashboard/security" },
        { id: "compliance", name: "Compliance", icon: "lucide:check-circle", path: "/dashboard/compliance" },
        { id: "secrets", name: "Secrets", icon: "lucide:key", path: "/dashboard/secrets" },
      ]
    },
    {
      id: "settings",
      name: "SETTINGS",
      icon: "lucide:settings",
      items: [
        { id: "settings", name: "Settings", icon: "lucide:settings", path: "/dashboard/settings" },
        { id: "users", name: "Users & RBAC", icon: "lucide:users", path: "/dashboard/users" },
        { id: "integrations", name: "Integrations", icon: "lucide:plug", path: "/dashboard/integrations" },
        { id: "help", name: "Help", icon: "lucide:help-circle", path: "/dashboard/help" },
      ]
    },
  ];
 
  const toggleCategory = (categoryId: string) => {
    setExpandedCategory(categoryId);
  };
 
  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };
 
  return (
    <motion.aside
      className={`flex flex-col bg-content1 border-r border-divider transition-all duration-300 ${
        isCollapsed ? "w-16" : "w-64"
      }`}
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className="p-4 flex items-center justify-between border-b border-divider">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <motion.div
              className="bg-primary rounded-md p-1 flex-shrink-0"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Icon icon="lucide:layers" className="text-white text-xl" />
            </motion.div>
            <h1 className="text-xl font-semibold truncate">KubeSage</h1>
          </div>
        )}
        
        {isCollapsed && (
          <motion.div
            className="bg-primary rounded-md p-1 mx-auto"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Icon icon="lucide:layers" className="text-white text-xl" />
          </motion.div>
        )}
        
        <Button
          isIconOnly
          variant="ghost"
          size="sm"
          onPress={toggleCollapse}
        >
          <Icon icon={isCollapsed ? "lucide:chevron-right" : "lucide:chevron-left"} />
        </Button>
      </div>
      
      <div className="flex-1 overflow-y-auto scrollbar-hide py-2">
        {navCategories.map((category) => (
          <div key={category.id} className="mb-3">
            {!isCollapsed ? (
              <>
                <div
                  className={`px-4 py-2 flex items-center justify-between cursor-pointer transition-colors ${
                    expandedCategory === category.id ? "bg-content2" : "hover:bg-content2"
                  }`}
                  onClick={() => toggleCategory(category.id)}
                >
                  <div className="flex items-center gap-2">
                    <Icon
                      icon={category.icon}
                      className={expandedCategory === category.id ? "text-primary" : "text-foreground-500"}
                    />
                    <span className={`text-xs font-medium ${
                      expandedCategory === category.id ? "text-primary font-semibold" : "text-foreground-500"
                    }`}>
                      {category.name}
                    </span>
                  </div>
                </div>
                
                <div className="pl-4 pr-2 space-y-1 py-1">
                  {category.items.map((item) => (
                    <Button
                      key={item.id}
                      variant={currentPage === item.id ? "flat" : "ghost"}
                      color={currentPage === item.id ? "primary" : "default"}
                      className="w-full justify-start"
                      startContent={<Icon icon={item.icon} />}
                      onPress={() => history.push(item.path)}
                      size="sm"
                    >
                      {item.name}
                    </Button>
                  ))}
                </div>
              </>
            ) : (
              <div className="py-1">
                <Tooltip content={category.name} placement="right">
                  <div className="flex justify-center mb-1">
                    <Button
                      isIconOnly
                      variant={expandedCategory === category.id ? "flat" : "ghost"}
                      color={expandedCategory === category.id ? "primary" : "default"}
                      onPress={() => toggleCategory(category.id)}
                      size="sm"
                    >
                      <Icon icon={category.icon} />
                    </Button>
                  </div>
                </Tooltip>
                
                <div className="space-y-1 flex flex-col items-center">
                  {category.items.map((item) => (
                    <Tooltip key={item.id} content={item.name} placement="right">
                      <Button
                        isIconOnly
                        variant={currentPage === item.id ? "flat" : "ghost"}
                        color={currentPage === item.id ? "primary" : "default"}
                        size="sm"
                        onPress={() => history.push(item.path)}
                      >
                        <Icon icon={item.icon} />
                      </Button>
                    </Tooltip>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className={`p-4 border-t border-divider ${isCollapsed ? "flex flex-col items-center" : ""}`}>
        {!isCollapsed ? (
          <>
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm">Theme</span>
              <div className="flex items-center gap-2">
                <Icon icon="lucide:sun" className={`text-sm ${currentTheme === 'light' ? 'text-primary' : 'text-foreground-400'}`} />
                <Switch
                  size="sm"
                  isSelected={currentTheme === 'dark'}
                  onValueChange={toggleTheme}
                  color="primary"
                />
                <Icon icon="lucide:moon" className={`text-sm ${currentTheme === 'dark' ? 'text-primary' : 'text-foreground-400'}`} />
              </div>
            </div>
            
            <Divider className="my-3" />
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white font-medium">
                  AS
                </div>
                <div>
                  <p className="text-sm font-medium">Admin User</p>
                  <p className="text-xs text-foreground-500">admin@kubesage.io</p>
                </div>
              </div>
              <Tooltip content="Logout">
                <Button
                  isIconOnly
                  variant="ghost"
                  color="danger"
                  size="sm"
                  onPress={onLogout}
                >
                  <Icon icon="lucide:log-out" />
                </Button>
              </Tooltip>
            </div>
          </>
        ) : (
          <>
            <Tooltip content="Toggle Theme" placement="right">
              <Button
                isIconOnly
                variant="ghost"
                size="sm"
                onPress={toggleTheme}
                className="mb-3"
              >
                <Icon icon={currentTheme === 'light' ? "lucide:sun" : "lucide:moon"} />
              </Button>
            </Tooltip>
            
            <Divider className="my-3 w-full" />
            
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white font-medium mb-3">
              AS
            </div>
            
            <Tooltip content="Logout" placement="right">
              <Button
                isIconOnly
                variant="ghost"
                color="danger"
                size="sm"
                onPress={onLogout}
              >
                <Icon icon="lucide:log-out" />
              </Button>
            </Tooltip>
          </>
        )}
      </div>
    </motion.aside>
  );
};
 