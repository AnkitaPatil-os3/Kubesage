import React from "react";
import { Link, useHistory } from "react-router-dom";
import { Icon } from "@iconify/react";
import { Button, Tooltip, Switch, Divider } from "@heroui/react";
import { motion } from "framer-motion";

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
  const history = useHistory();
  const clusters = [
    { id: "production", name: "Production", icon: "lucide:server" },
    { id: "staging", name: "Staging", icon: "lucide:server" },
    { id: "development", name: "Development", icon: "lucide:server" },
  ];

  const navItems = [
    { id: "overview", name: "Overview", icon: "lucide:layout-dashboard", path: "/dashboard/overview" },
    { id: "onboarding", name: "Cluster Onboarding", icon: "lucide:plus-circle", path: "/dashboard/onboarding" },
    { id: "chatops", name: "ChatOps", icon: "lucide:message-square", path: "/dashboard/chatops" },
    { id: "observability", name: "Observability", icon: "lucide:activity", path: "/dashboard" },
    { id: "security", name: "Security", icon: "lucide:shield", path: "/dashboard" },
    { id: "compliance", name: "Compliance", icon: "lucide:check-circle", path: "/dashboard" },
    { id: "insights", name: "AI Insights", icon: "lucide:lightbulb", path: "/dashboard" },
    { id: "admin", name: "Admin", icon: "lucide:settings", path: "/dashboard/admin" },
  ];

  return (
    <motion.aside 
      className="hidden md:flex flex-col w-64 bg-content1 border-r border-divider"
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className="p-4 flex items-center gap-2">
        <motion.div 
          className="bg-primary rounded-md p-1"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Icon icon="lucide:layers" className="text-white text-xl" />
        </motion.div>
        <h1 className="text-xl font-semibold">KubeSage</h1>
      </div>
      
      <div className="p-4">
        <h2 className="text-sm font-medium text-foreground-500 mb-2">CLUSTERS</h2>
        <div className="space-y-1">
          {clusters.map((cluster) => (
            <Button
              key={cluster.id}
              variant={selectedCluster === cluster.id ? "flat" : "ghost"}
              color={selectedCluster === cluster.id ? "primary" : "default"}
              className="w-full justify-start"
              startContent={<Icon icon={cluster.icon} />}
              onPress={() => setSelectedCluster(cluster.id)}
            >
              {cluster.name}
            </Button>
          ))}
        </div>
      </div>
      
      <div className="p-4 flex-1">
        <h2 className="text-sm font-medium text-foreground-500 mb-2">NAVIGATION</h2>
        <div className="space-y-1">
          {navItems.map((item) => (
            <Button
              key={item.id}
              variant={currentPage === item.id ? "flat" : "ghost"}
              color={currentPage === item.id ? "primary" : "default"}
              className="w-full justify-start"
              startContent={<Icon icon={item.icon} />}
              onPress={() => history.push(item.path)}
            >
              {item.name}
            </Button>
          ))}
        </div>
      </div>
      
      <div className="p-4 border-t border-divider">
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
      </div>
    </motion.aside>
  );
};