import React, { useEffect, useState } from "react";
import { useHistory } from "react-router-dom";
import { Icon } from "@iconify/react";
import {
  Button,
  Tooltip,
  Switch,
  Divider
} from "@heroui/react";
import { motion, AnimatePresence } from "framer-motion";
import { navCategories } from "../config/navConfig";
import { rolePermissions, UserRole } from "../config/permissions";
 
const API_BASE_URL = (import.meta as any).env.VITE_USER_SERVICE;
 
interface SidebarProps {
  selectedCluster: string;
  setSelectedCluster: (cluster: string) => void;
  currentPage: string;
  onLogout: () => void;
  toggleTheme: () => void;
  currentTheme: string;
}
 
const roleMap: Record<string, UserRole> = {
  "Super Admin": "super_admin",
  "Platform Engineer": "platform_engineer",
  "DevOps": "devops",
  "Developer": "developer",
  "Security Engineer": "security_engineer"
};
 
export const Sidebar: React.FC<SidebarProps> = ({
  selectedCluster,
  setSelectedCluster,
  currentPage,
  onLogout,
  toggleTheme,
  currentTheme
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<{ [key: string]: boolean }>({
    clusters: true,
  });
  const [isAdmin, setIsAdmin] = useState(false);
  const history = useHistory();
 
  const userEmail = localStorage.getItem("userEmail") || "user@kubesage.io";
  const userName = userEmail.split("@")[0].charAt(0).toUpperCase() + userEmail.split("@")[0].slice(1);
  const userInitials = userName.slice(0, 2).toUpperCase();
 
  // Normalize role
  const rawRole = localStorage.getItem("roles") || "super_admin";
  const role: UserRole = roleMap[rawRole] || (rawRole.toLowerCase().replace(" ", "_") as UserRole);
  const userRole = role.replace(/^"(.*)"$/, '$1');
 
  // Determine permissions
  let permissions: string[] = rolePermissions[userRole] ?? [];
  if (permissions.includes("all")) {
    permissions = navCategories.flatMap(category => category.items.map(item => item.id));
  }
 

  
 
  const filteredCategories = navCategories
    .map((category) => {
      const filteredItems = category.items.filter((item) =>
        permissions.includes(item.id)
      );
      return { ...category, items: filteredItems };
    })
    .filter((category) => category.items.length > 0);
 
  useEffect(() => {
    const fetchAdminStatus = async () => {
      try {
        const accessToken = localStorage.getItem("access_token");
        if (!accessToken) return setIsAdmin(false);
 
        const response = await fetch(`${API_BASE_URL}/auth/check-admin`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });
 
        const data = await response.json();
        setIsAdmin(response.ok && data.is_admin);
      } catch (error) {
        console.error("Failed to fetch admin status:", error);
        setIsAdmin(false);
      }
    };
 
    fetchAdminStatus();
  }, []);
 
  const handleLogout = async () => {
    try {
      const accessToken = localStorage.getItem("access_token");
      if (accessToken) {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
        });
      }
    } catch (error) {
      console.error("Logout failed:", error);
    } finally {
      localStorage.clear();
      onLogout();
    }
  };
 
  const toggleCollapse = () => setIsCollapsed(!isCollapsed);
  const toggleCategory = (categoryId: string) =>
    setExpandedCategories(prev => ({ ...prev, [categoryId]: !prev[categoryId] }));
 
  return (
    <motion.aside
      className={`flex flex-col bg-content1 border-r border-divider transition-all duration-300 ${isCollapsed ? "w-16" : "w-64"}`}
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="p-4 flex items-center justify-between border-b border-divider">
        {!isCollapsed ? (
          <div className="flex items-center gap-2">
            <div className="bg-primary rounded-md p-1">
              <Icon icon="lucide:layers" className="text-white text-xl" />
            </div>
            <h1 className="text-xl font-semibold truncate">KubeSage</h1>
          </div>
        ) : (
          <div className="bg-primary rounded-md p-1 mx-auto">
            <Icon icon="lucide:layers" className="text-white text-xl" />
          </div>
        )}
        <Button isIconOnly variant="ghost" size="sm" onPress={toggleCollapse}>
          <Icon icon={isCollapsed ? "lucide:chevron-right" : "lucide:chevron-left"} />
        </Button>
      </div>
 
      {/* Navigation */}
      <div className="flex-1 overflow-y-auto scrollbar-hide py-2">
        {filteredCategories.map((category) => (
          <div key={category.id} className="mb-3">
            {!isCollapsed ? (
              <div
                className={`px-4 py-2 flex items-center justify-between cursor-pointer transition-colors ${
                  expandedCategories[category.id] ? "bg-content2" : "hover:bg-content2"
                }`}
                onClick={() => toggleCategory(category.id)}
              >
                <div className="flex items-center gap-2">
                  <Icon icon={category.icon} className={expandedCategories[category.id] ? "text-primary" : "text-foreground-500"} />
                  <span className={`text-xs font-medium ${expandedCategories[category.id] ? "text-primary font-semibold" : "text-foreground-500"}`}>
                    {category.name}
                  </span>
                </div>
                <Icon
                  icon={expandedCategories[category.id] ? "lucide:chevron-down" : "lucide:chevron-right"}
                  className="text-sm text-foreground-400"
                />
              </div>
            ) : (
              <Tooltip content={category.name} placement="right">
                <div className="flex justify-center">
                  <Button
                    isIconOnly
                    variant={expandedCategories[category.id] ? "flat" : "ghost"}
                    color={expandedCategories[category.id] ? "primary" : "default"}
                    onPress={() => toggleCategory(category.id)}
                    size="sm"
                  >
                    <Icon icon={category.icon} />
                  </Button>
                </div>
              </Tooltip>
            )}
 
            {/* Sub-menu */}
            <AnimatePresence>
              {expandedCategories[category.id] && !isCollapsed && (
                <motion.div
                  className="pl-4 pr-2 space-y-1 py-1"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
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
                </motion.div>
              )}
            </AnimatePresence>
 
            {/* Collapsed Icons */}
            {isCollapsed && (
              <div className="space-y-1 flex flex-col items-center mt-1">
                {expandedCategories[category.id] &&
                  category.items.map((item) => (
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
            )}
          </div>
        ))}
      </div>
 
      {/* Footer */}
      <div className={`p-4 border-t border-divider ${isCollapsed ? "flex flex-col items-center" : ""}`}>
        {!isCollapsed ? (
          <>
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm">Theme</span>
              <div className="flex items-center gap-2">
                <Icon
                  icon="lucide:sun"
                  className={`text-sm ${currentTheme === "light" ? "text-primary" : "text-foreground-400"}`}
                />
                <Switch
                  size="sm"
                  isSelected={currentTheme === "dark"}
                  onValueChange={toggleTheme}
                  color="primary"
                />
                <Icon
                  icon="lucide:moon"
                  className={`text-sm ${currentTheme === "dark" ? "text-primary" : "text-foreground-400"}`}
                />
              </div>
            </div>
            <Divider className="my-3" />
            <div
              className="flex items-center justify-between gap-3 rounded px-2 py-1 transition"
              onClick={() => isAdmin && history.push("/dashboard/admin")}
              title={isAdmin ? "Go to Admin Dashboard" : "Profile not clickable"}
              style={{ cursor: isAdmin ? "pointer" : "default" }}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white font-medium">
                  {userInitials}
                </div>
                <div>
                  <p className="text-sm font-medium">{userName}</p>
                  <p className="text-xs text-foreground-500">{userEmail}</p>
                </div>
              </div>
              <Tooltip content="Logout">
                <Button isIconOnly variant="ghost" color="danger" size="sm" onClick={(e) => { e.stopPropagation(); handleLogout(); }}>
                  <Icon icon="lucide:log-out" />
                </Button>
              </Tooltip>
            </div>
          </>
        ) : (
          <>
            <Tooltip content="Toggle Theme" placement="right">
              <Button isIconOnly variant="ghost" size="sm" onPress={toggleTheme} className="mb-3">
                <Icon icon={currentTheme === "light" ? "lucide:sun" : "lucide:moon"} />
              </Button>
            </Tooltip>
            <Divider className="my-3 w-full" />
            <Tooltip content={`${userName} (${userEmail})`} placement="right">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white font-medium mb-3">
                {userInitials}
              </div>
            </Tooltip>
            <Tooltip content="Logout" placement="right">
              <Button isIconOnly variant="ghost" color="danger" size="sm" onClick={handleLogout}>
                <Icon icon="lucide:log-out" />
              </Button>
            </Tooltip>
          </>
        )}
      </div>
    </motion.aside>
  );
};
 
 