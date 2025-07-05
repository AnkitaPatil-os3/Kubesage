// src/config/navConfig.ts

export const navCategories = [
    {
      id: "overview",
      name: "OVERVIEW",
      icon: "lucide:layout-dashboard",
      items: [
        { id: "dashboard", name: "Dashboard", icon: "lucide:layout-dashboard", path: "/dashboard/overview" },
        { id: "clusters", name: "Clusters", icon: "lucide:database", path: "/dashboard/upload" },
        { id: "applications", name: "Applications", icon: "lucide:box", path: "/dashboard/upload" },
        { id: "workloads", name: "Workloads", icon: "lucide:layers", path: "/dashboard/upload" },
        { id: "analyze", name: "Cluster Analysis", icon: "mdi:magnify-scan", path: "/dashboard/analyze" },
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
        { id: "carbon-emission", name: "GreenOps", icon: "mdi:leaf", path: "/dashboard/carbon-emission" },
        { id: "cost", name: "FinOps", icon: "mdi:currency-inr", path: "/dashboard/cost" },
        { id: "security", name: "SecOps", icon: "lucide:shield", path: "/dashboard/security-dashboard" },
        { id: "backup", name: "Backup & Restore", icon: "mdi:backup-restore", path: "/dashboard/backup" },
      ]
    },
    {
      id: "security",
      name: "SECURITY",
      icon: "lucide:shield",
      items: [
        { id: "security", name: "Security Scanner", icon: "lucide:shield", path: "/dashboard/security" },
        { id: "security-policies", name: "Security Policies", icon: "lucide:shield", path: "/dashboard/security-policies" },
        { id: "secrets", name: "Secrets", icon: "lucide:key", path: "/dashboard/secrets" },
        { id: "compliance", name: "Compliance", icon: "lucide:key", path: "/dashboard/compliance" },
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
  