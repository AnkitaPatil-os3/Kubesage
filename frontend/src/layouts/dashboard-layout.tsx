import React from "react";
import { useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Icon } from "@iconify/react";
import { Button, Switch, Tooltip } from "@heroui/react";
import { Sidebar } from "../components/sidebar";
import { Header } from "../components/header";
import { AIChatPanel } from "../components/ai-chat-panel";

interface DashboardLayoutProps {
  children: React.ReactNode;
  onLogout: () => void;
  toggleTheme: () => void;
  currentTheme: string;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ 
  children, 
  onLogout,
  toggleTheme,
  currentTheme
}) => {
  const [isChatOpen, setIsChatOpen] = React.useState(false);
  const [selectedCluster, setSelectedCluster] = React.useState("production");
  const location = useLocation();
  
  const toggleChat = () => {
    setIsChatOpen(!isChatOpen);
  };

  // Extract the current page from the URL
  const currentPage = location.pathname.split('/').pop() || 'overview';

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar 
        selectedCluster={selectedCluster} 
        setSelectedCluster={setSelectedCluster}
        currentPage={currentPage}
        onLogout={onLogout}
        toggleTheme={toggleTheme}
        currentTheme={currentTheme}
      />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header toggleChat={toggleChat} />
        <motion.main 
          className="flex-1 overflow-auto p-4 md:p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          {React.cloneElement(children as React.ReactElement, { selectedCluster })}
        </motion.main>
      </div>
      <AIChatPanel isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
  );
};