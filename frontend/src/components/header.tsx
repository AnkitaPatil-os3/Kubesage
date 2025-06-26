import React from "react";
import { useLocation, useHistory } from "react-router-dom";
import { Icon } from "@iconify/react";
import {
  Button,
  Input,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  Avatar
} from "@heroui/react";
import { motion } from "framer-motion";
import { navCategories } from "../config/navConfig"; // Shared sidebar config

interface HeaderProps {
  toggleChat: () => void;
  onLogout?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ toggleChat, onLogout }) => {
  const location = useLocation();
  const history = useHistory();

  const [searchQuery, setSearchQuery] = React.useState("");
  const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);

  // User info
  const userEmail = localStorage.getItem("userEmail") || "user@kubesage.io";
  const userName =
    userEmail.split("@")[0].charAt(0).toUpperCase() +
    userEmail.split("@")[0].slice(1);
  const userInitials = userName.slice(0, 2).toUpperCase();

  // Searchable sidebar items
  const sidebarItems = navCategories.flatMap((cat) =>
    cat.items.map((item) => ({
      ...item,
      category: cat.name,
    }))
  );

  const filteredItems = searchQuery.trim()
    ? sidebarItems.filter((item) =>
        item.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  const handleItemSelect = (path: string) => {
    setSearchQuery("");
    setIsDropdownOpen(false);
    history.push(path);
  };

  // Page title logic
  const getPageTitle = () => {
    const path = location.pathname.split("/").pop() || "overview";
    switch (path) {
      case "overview":
        return "Dashboard";
      case "upload":
        return "Cluster Overview";
      case "onboarding":
        return "Cluster Onboarding";
      case "chatops":
        return "ChatOps Console";
      case "admin":
        return "Admin Dashboard";
      case "cost":
        return "Cost Analysis";
      case "remediations":
        return "Remediations";
      case "observability":
        return "Observability";
      case "carbon-emission":
        return "Carbon Emission";
      case "backup":
        return "Backup & Restore";
      default:
        return "Dashboard";
    }
  };

  const handleLogout = async () => {
    try {
      const accessToken = localStorage.getItem("access_token");
      if (accessToken) {
        await fetch("/auth/logout", {
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
      if (onLogout) {
        onLogout();
      } else {
        window.location.href = "/login";
      }
    }
  };

  return (
    <motion.header
      className="h-16 border-b border-divider bg-content1 backdrop-blur-md bg-opacity-80 flex items-center justify-between px-4 md:px-6"
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className="md:hidden">
        <Button isIconOnly variant="ghost" aria-label="Menu">
          <Icon icon="lucide:menu" className="text-xl" />
        </Button>
      </div>

      <div className="hidden md:block">
        <motion.h1
          className="text-xl font-semibold"
          key={location.pathname}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {getPageTitle()}
        </motion.h1>
      </div>

      <div className="flex flex-1 max-w-md mx-6 relative">
  <Input
    placeholder="Search resources..."
    size="sm"
    value={searchQuery}
    onChange={(e) => {
      setSearchQuery(e.target.value);
      setIsDropdownOpen(true);
    }}
    onFocus={() => setIsDropdownOpen(true)}
    onBlur={() => setTimeout(() => setIsDropdownOpen(false), 200)}
    className="transition-all duration-300"
    startContent={<Icon icon="lucide:search" className="text-foreground-400" />}
  />

  {/* Custom Dropdown */}
  {isDropdownOpen && filteredItems.length > 0 && (
    <div className="absolute top-full left-0 mt-1 w-full bg-white dark:bg-content2 border border-divider rounded-md shadow-md z-50">
      {filteredItems.map(item => (
        <div
          key={item.id}
          className="flex items-start gap-2 px-3 py-2 hover:bg-content3 cursor-pointer"
          onMouseDown={() => handleItemSelect(item.path)} // use onMouseDown to avoid blur
        >
          <Icon icon={item.icon} className="text-primary mt-1" />
          <div>
            <div className="text-sm font-medium">{item.name}</div>
            <div className="text-xs text-default-500">{item.category}</div>
          </div>
        </div>
      ))}
    </div>
  )}
</div>



      <div className="flex items-center gap-2">
        <Button
          color="primary"
          variant="flat"
          startContent={<Icon icon="lucide:message-square" />}
          onPress={toggleChat}
          className="hidden md:flex"
        >
          AI Assistant
        </Button>

        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
          <Button isIconOnly variant="ghost" aria-label="Notifications">
            <Icon icon="lucide:bell" className="text-xl" />
          </Button>
        </motion.div>

        <Dropdown>
          <DropdownTrigger>
            <Avatar
              name={userInitials}
              size="sm"
              className="cursor-pointer bg-primary text-white"
            />
          </DropdownTrigger>
          <DropdownMenu aria-label="User Actions">
            <DropdownItem key="user-info" className="h-14 gap-2" textValue="User Info">
              <div className="flex items-center gap-2">
                <Avatar
                  name={userInitials}
                  size="sm"
                  className="bg-primary text-white"
                />
                <div className="flex flex-col">
                  <span className="text-small font-semibold">{userName}</span>
                  <span className="text-tiny text-default-400">{userEmail}</span>
                </div>
              </div>
            </DropdownItem>
            <DropdownItem key="profile" startContent={<Icon icon="lucide:user" />}>
              Profile
            </DropdownItem>
            <DropdownItem key="settings" startContent={<Icon icon="lucide:settings" />}>
              Settings
            </DropdownItem>
            <DropdownItem key="help" startContent={<Icon icon="lucide:help-circle" />}>
              Help & Documentation
            </DropdownItem>
            <DropdownItem key="feedback" startContent={<Icon icon="lucide:message-square" />}>
              Send Feedback
            </DropdownItem>
            <DropdownItem
              key="logout"
              className="text-danger"
              color="danger"
              startContent={<Icon icon="lucide:log-out" />}
              onClick={handleLogout}
            >
              Log Out
            </DropdownItem>
          </DropdownMenu>
        </Dropdown>
      </div>
    </motion.header>
  );
};
