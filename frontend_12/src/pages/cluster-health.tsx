import React from "react";
import { motion } from "framer-motion";
import { Dashboard } from "../components/dashboard";

interface ClusterHealthProps {
  selectedCluster: string;
}

export const ClusterHealth: React.FC<ClusterHealthProps> = ({ selectedCluster }) => {
  // Animation variants for staggered children
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };
  
  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.4 } }
  };

  return (
    <motion.div 
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      <Dashboard selectedCluster={selectedCluster} />
    </motion.div>
  );
};