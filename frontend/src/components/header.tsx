import React from "react";
import { useLocation } from "react-router-dom";
import { Icon } from "@iconify/react";
import {
  Button,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  Input,
  Avatar
} from "@heroui/react";
import { motion } from "framer-motion";

interface HeaderProps {
  toggleChat: () => void;
  onLogout?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ toggleChat, onLogout }) => {
  const location = useLocation();
  const [isSearchFocused, setIsSearchFocused] = React.useState(false);
  
  // Get user details from localStorage
  const userEmail = localStorage.getItem('userEmail') || 'user@kubesage.io';
  const userName = userEmail.split('@')[0].charAt(0).toUpperCase() + userEmail.split('@')[0].slice(1);
  const userInitials = userName.slice(0, 2).toUpperCase();
  
  // Get page title from path
  const getPageTitle = () => {
    const path = location.pathname.split('/').pop() || 'overview';
    switch(path) {
      case 'overview': return 'Dashboard';
      case 'upload': return 'Cluster Overview';
      case 'onboarding': return 'Cluster Onboarding';
      case 'chatops': return 'ChatOps Console';
      case 'admin': return 'Admin Dashboard';
      case 'cost': return 'Cost Analysis';
      case 'remediations': return 'Remediations';
      case 'observability': return 'Observability';
      case 'carbon-emission': return 'Carbon Emission';
      case 'backup': return 'Backup & Restore';
      default: return 'Dashboard';
    }
  };

  const handleLogout = async () => {
    try {
      const accessToken = localStorage.getItem('access_token');
      console.log('Logout request with token:', accessToken);
      
      // Call backend logout endpoint
      if (accessToken) {
        await fetch('/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
          }
        });
      }
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      // Clear all authentication data
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('isAuthenticated');
      localStorage.removeItem('userEmail');
      
      // Call the parent logout handler if provided
      if (onLogout) {
        onLogout();
      } else {
        // Fallback to direct redirect if no handler provided
        window.location.href = '/login';
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
      
      <div className="hidden md:flex flex-1 max-w-md mx-6">
        <Input
          placeholder="Search resources..."
          startContent={<Icon icon="lucide:search" className="text-foreground-400" />}
          size="sm"
          className={`transition-all duration-300 ${isSearchFocused ? 'shadow-md' : ''}`}
          onFocus={() => setIsSearchFocused(true)}
          onBlur={() => setIsSearchFocused(false)}
        />
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
