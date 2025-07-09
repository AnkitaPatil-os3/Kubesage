import React, { useState, useRef, useEffect } from 'react';
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Input,
  Textarea,
  ScrollShadow,
  Chip,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  useDisclosure,
  Switch,
  Kbd,
  Spinner,
  Code,
  Divider,
  Avatar,
  Tooltip
} from '@heroui/react';
import { Icon } from '@iconify/react';
import { motion, AnimatePresence } from 'framer-motion';
import { addToast } from '../components/toast-manager';
import { UserRole, rolePermissions } from '../config/permissions';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';
import '../styles/chat-ops.css';

// Initialize markdown parser
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,
});

const defaultFence = md.renderer.rules.fence || function (tokens, idx, options, env, self) {
  return self.renderToken(tokens, idx, options);
};

// Enhanced markdown fence renderer for proper code block alignment
md.renderer.rules.fence = function (tokens, idx, options, env, self) {
  const token = tokens[idx];
  const lines = token.content.split('\n');
  let headerLine = '';
  let commandLines = lines;

  if (lines.length > 0 && lines[0].trim().startsWith('#')) {
    headerLine = lines[0].trim().substring(1).trim();
    commandLines = lines.slice(1);
  }

  const escapedHeader = md.utils.escapeHtml(headerLine);
  const commandContent = commandLines.join('\n');
  const commands = commandContent.split('\n\n')
    .map(cmd => cmd.trim())
    .filter(cmd => cmd.length > 0);

  if (commands.length === 0 && commandContent.trim()) {
    commands.push(commandContent.trim());
  }

  const commandBlocks = commands.map(cmd => {
    const normalizedCmd = cmd
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0)
      .join('\n');

    const escapedCmd = md.utils.escapeHtml(normalizedCmd);

    return `
      <div class="mb-4">
        <div class="relative rounded-lg border border-divider bg-content2 overflow-hidden">
          <div class="flex items-center justify-between bg-content3 px-3 py-2 border-b border-divider">
            <span class="text-xs font-medium text-default-600">bash</span>
            <button class="text-xs text-default-500 hover:text-default-700 cursor-pointer transition-colors" onclick="navigator.clipboard.writeText('${escapedCmd.replace(/'/g, "\\'")}')">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
              </svg>
            </button>
          </div>
          <pre class="p-4 m-0 bg-transparent overflow-x-auto font-mono text-sm leading-relaxed text-foreground">
            <code class="text-foreground block">${escapedCmd}</code>
          </pre>
        </div>
      </div>
    `;
  }).join('\n');

  return `
    <div class="mb-4">
      ${headerLine ? `<div class="mb-3 font-semibold text-foreground">${escapedHeader}</div>` : ''}
      ${commandBlocks}
    </div>
  `;
};

// Enhanced message content renderer with better formatting
const RenderMessageContent: React.FC<{ content: string }> = ({ content }) => {
  const parts = React.useMemo(() => {
    const bashCodeBlockRegex = /```bash\n([\s\S]*?)```/g;
    const result = [];
    let lastIndex = 0;
    let match;

    while ((match = bashCodeBlockRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        const textContent = content.substring(lastIndex, match.index);
        if (textContent.trim()) {
          result.push({ type: 'text', content: textContent });
        }
      }

      const codeContent = match[1];
      result.push({ type: 'code', content: codeContent });
      lastIndex = bashCodeBlockRegex.lastIndex;
    }

    if (lastIndex < content.length) {
      const remainingContent = content.substring(lastIndex);
      if (remainingContent.trim()) {
        result.push({ type: 'text', content: remainingContent });
      }
    }

    if (result.length === 0) {
      result.push({ type: 'text', content: content });
    }

    return result;
  }, [content]);

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      {parts.map((part, idx) => {
        if (part.type === 'text') {
          const htmlContent = md.render(part.content);
          return (
            <div
              key={idx}
              className="mb-2"
              dangerouslySetInnerHTML={{ __html: htmlContent }}
              style={{
                '--tw-prose-body': 'rgb(var(--nextui-foreground))',
                '--tw-prose-headings': 'rgb(var(--nextui-foreground))',
                '--tw-prose-links': 'rgb(var(--nextui-primary))',
                '--tw-prose-bold': 'rgb(var(--nextui-foreground))',
                '--tw-prose-code': 'rgb(var(--nextui-foreground))',
                '--tw-prose-pre-bg': 'rgb(var(--nextui-content2))',
                '--tw-prose-pre-code': 'rgb(var(--nextui-foreground))',
                '--tw-prose-th-borders': 'rgb(var(--nextui-divider))',
                '--tw-prose-td-borders': 'rgb(var(--nextui-divider))',
              } as React.CSSProperties}
            />
          );
        } else if (part.type === 'code') {
          const commands = part.content
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0);

          return (
            <div key={idx} className="mb-4">
              <div className="mb-2 font-semibold text-foreground">Commands</div>
              <div className="relative rounded-lg border border-divider bg-content2 overflow-hidden">
                <div className="flex items-center justify-between bg-content3 px-3 py-2 border-b border-divider">
                  <span className="text-xs font-medium text-default-600">bash</span>
                  <Button
                    size="sm"
                    variant="light"
                    isIconOnly
                    className="h-6 w-6 min-w-6"
                    onPress={() => navigator.clipboard.writeText(commands.join('\n'))}
                  >
                    <Icon icon="solar:copy-bold" width={12} />
                  </Button>
                </div>
                <div className="p-4 bg-transparent overflow-x-auto">
                  {commands.map((command, cmdIdx) => (
                    <div key={cmdIdx} className="mb-1 last:mb-0">
                      <code className="font-mono text-sm text-foreground block">
                        {command}
                      </code>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        }
        return null;
      })}
    </div>
  );
};

// Types
interface Message {
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
}

interface Session {
  id: number;
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

interface ToolInfo {
  name: string;
  args: string;
}

interface ToolResponse {
  name: string;
  response: string;
}

interface ChatResponse {
  session_id: string;
  response: string;
  tools_info?: ToolInfo[];
  tool_response?: ToolResponse[];
}

// API Configuration
const API_BASE_URL = 'https://10.0.32.103:8003';

class ChatAPI {
  private getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }

  async sendMessage(message: string, sessionId?: string, enableToolResponse: boolean = false): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        message,
        session_id: sessionId,
        enable_tool_response: enableToolResponse
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async getSessions(): Promise<{ sessions: Session[] }> {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async createSession(title: string): Promise<Session> {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ title })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async deleteSession(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  }

  async getSessionHistory(sessionId: string): Promise<{ id: string; created_at: string; messages: Message[] }> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async getHealthStatus() {
    const response = await fetch(`${API_BASE_URL}/health`, {
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }
}

const chatAPI = new ChatAPI();

// Export Sessions Function
const exportSessions = async (sessions: Session[], messages: Message[]) => {
  try {
    const exportData = {
      exportDate: new Date().toISOString(),
      version: "1.0",
      sessions: sessions,
      currentSessionMessages: messages,
      metadata: {
        totalSessions: sessions.length,
        totalMessages: messages.length
      }
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `kubesage-sessions-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    addToast({
      title: 'Success',
      description: 'Sessions exported successfully',
      color: 'success'
    });
  } catch (error) {
    console.error('Failed to export sessions:', error);
    addToast({
      title: 'Error',
      description: 'Failed to export sessions',
      color: 'danger'
    });
  }
};

// Role-specific Quick Commands
const getRoleSpecificCommands = (userRole: UserRole) => {
  const baseCommands = {
    super_admin: [
      {
        category: "Cluster Management",
        icon: "solar:server-bold",
        commands: [
          { label: "Full cluster overview", command: "Give me a comprehensive cluster overview with all namespaces and resources" },
          { label: "All node status", command: "Show me detailed status of all nodes in the cluster" },
          { label: "System resource usage", command: "Show system-wide resource usage across all namespaces" },
          { label: "Critical alerts", command: "Show me all critical alerts and system issues" }
        ]
      },
      {
        category: "Security & Compliance",
        icon: "solar:shield-check-bold",
        commands: [
          { label: "Security audit", command: "Perform a comprehensive security audit of the cluster" },
          { label: "RBAC analysis", command: "Analyze RBAC permissions and potential security issues" },
          { label: "Compliance check", command: "Check cluster compliance with security standards" },
          { label: "Vulnerability scan", command: "Show me security vulnerabilities in the cluster" }
        ]
      },
      {
        category: "Advanced Operations",
        icon: "solar:settings-bold",
        commands: [
          { label: "Backup status", command: "Show me backup status and schedules" },
          { label: "Cost analysis", command: "Provide detailed cost analysis and optimization suggestions" },
          { label: "Performance tuning", command: "Analyze cluster performance and suggest optimizations" },
          { label: "Carbon footprint", command: "Show carbon emission metrics and sustainability insights" }
        ]
      },
    ],
    platform_engineer: [
      {
        category: "Infrastructure",
        icon: "solar:server-bold",
        commands: [
          { label: "Cluster health", command: "Show me overall cluster health and infrastructure status" },
          { label: "Node management", command: "Help me manage and troubleshoot cluster nodes" },
          { label: "Resource allocation", command: "Show resource allocation and capacity planning insights" },
          { label: "Network policies", command: "Help me review and optimize network policies" }
        ]
      },
      {
        category: "Applications",
        icon: "solar:widget-bold",
        commands: [
          { label: "Application overview", command: "Show me all applications and their health status" },
          { label: "Deployment strategies", command: "Help me with deployment strategies and best practices" },
          { label: "Service mesh", command: "Show service mesh configuration and traffic patterns" },
          { label: "Ingress management", command: "Help me manage ingress controllers and routing" }
        ]
      },
      {
        category: "Observability",
        icon: "solar:eye-bold",
        commands: [
          { label: "Monitoring setup", command: "Help me set up comprehensive monitoring and alerting" },
          { label: "Log aggregation", command: "Show log aggregation patterns and troubleshooting" },
          { label: "Metrics analysis", command: "Analyze key performance metrics and trends" },
          { label: "Tracing insights", command: "Show distributed tracing and performance insights" }
        ]
      }
    ],
    devops: [
      {
        category: "Deployments",
        icon: "solar:rocket-bold",
        commands: [
          { label: "Deployment status", command: "Show me current deployment status and health" },
          { label: "Rollback help", command: "Help me rollback a problematic deployment" },
          { label: "CI/CD pipeline", command: "Show CI/CD pipeline status and integration issues" },
          { label: "Blue-green deployment", command: "Help me implement blue-green deployment strategy" }
        ]
      },
      {
        category: "Troubleshooting",
        icon: "solar:bug-bold",
        commands: [
          { label: "Application issues", command: "Help me troubleshoot application performance issues" },
          { label: "Pod failures", command: "Diagnose and fix pod failures and crashes" },
          { label: "Service connectivity", command: "Troubleshoot service connectivity and networking issues" },
          { label: "Resource constraints", command: "Identify and resolve resource constraint issues" }
        ]
      },
      {
        category: "Automation",
        icon: "solar:settings-bold",
        commands: [
          { label: "Automation scripts", command: "Help me create automation scripts for common tasks" },
          { label: "Backup procedures", command: "Show backup and disaster recovery procedures" },
          { label: "Scaling strategies", command: "Help me implement auto-scaling strategies" },
          { label: "Cost optimization", command: "Suggest cost optimization strategies for resources" }
        ]
      }
    ],
    developer: [
      {
        category: "Application Development",
        icon: "solar:code-bold",
        commands: [
          { label: "My applications", command: "Show me the status of my applications and services" },
          { label: "Pod logs", command: "Help me get logs from my application pods" },
          { label: "Debug issues", command: "Help me debug application issues and errors" },
          { label: "Resource usage", command: "Show resource usage for my applications" }
        ]
      },
      {
        category: "Development Workflow",
        icon: "solar:widget-bold",
        commands: [
          { label: "Development environment", command: "Help me set up development environment in Kubernetes" },
          { label: "Testing strategies", command: "Show me testing strategies for Kubernetes applications" },
          { label: "Local development", command: "Help me with local development and testing workflows" },
          { label: "Configuration management", command: "Help me manage application configurations and secrets" }
        ]
      },
      {
        category: "Best Practices",
        icon: "solar:book-bold",
        commands: [
          { label: "Kubernetes best practices", command: "Show me Kubernetes development best practices" },
          { label: "Container optimization", command: "Help me optimize my container images and resources" },
          { label: "Health checks", command: "Help me implement proper health checks and monitoring" },
          { label: "Security practices", command: "Show me security best practices for application development" }
        ]
      }
    ],
    security_engineer: [
      {
        category: "Security Assessment",
        icon: "solar:shield-check-bold",
        commands: [
          { label: "Security scan", command: "Perform a comprehensive security scan of the cluster" },
          { label: "Vulnerability assessment", command: "Show me current vulnerabilities and security risks" },
          { label: "Compliance audit", command: "Check compliance with security standards and policies" },
          { label: "Threat detection", command: "Show me potential security threats and anomalies" }
        ]
      },
      {
        category: "Access Control",
        icon: "solar:key-bold",
        commands: [
          { label: "RBAC analysis", command: "Analyze RBAC permissions and access patterns" },
          { label: "Service accounts", command: "Review service account permissions and security" },
          { label: "Network policies", command: "Help me implement and review network security policies" },
          { label: "Secret management", command: "Show me secret management and encryption status" }
        ]
      },
      {
        category: "Incident Response",
        icon: "solar:danger-bold",
        commands: [
          { label: "Security incidents", command: "Show me recent security incidents and alerts" },
          { label: "Anomaly detection", command: "Help me identify security anomalies and unusual patterns" },
          { label: "Forensic analysis", command: "Help me perform forensic analysis of security events" },
          { label: "Remediation steps", command: "Show me security remediation steps and procedures" }
        ]
      }
    ]
  };

  return baseCommands[userRole] || baseCommands.developer;
};

// Get user role from localStorage
const getUserRole = (): UserRole => {
  const roles = localStorage.getItem("roles") || "";
  const username = localStorage.getItem("username") || "";

  // Check for super admin
  if (roles.toLowerCase().includes("super")) {
    return 'super_admin';
  }

  // Check for specific roles
  if (roles.toLowerCase().includes("platform")) {
    return 'platform_engineer';
  }

  if (roles.toLowerCase().includes("devops")) {
    return 'devops';
  }

  if (roles.toLowerCase().includes("security")) {
    return 'security_engineer';
  }

  // Default to developer
  return 'developer';
};

export default function ChatOpsPage() {
  // State management
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [enableToolResponse, setEnableToolResponse] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [userRole, setUserRole] = useState<UserRole>('developer');

  // Refs for auto-scrolling
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Modal states
  const { isOpen: isSessionModalOpen, onOpen: onSessionModalOpen, onClose: onSessionModalClose } = useDisclosure();
  const { isOpen: isExportModalOpen, onOpen: onExportModalOpen, onClose: onExportModalClose } = useDisclosure();

  // Get role-specific commands
  const QUICK_COMMANDS = getRoleSpecificCommands(userRole);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load sessions and user role on component mount
  useEffect(() => {
    loadSessions();
    checkHealthStatus();
    setUserRole(getUserRole());
  }, []);

  const loadSessions = async () => {
    try {
      setIsLoadingSessions(true);
      const response = await chatAPI.getSessions();
      setSessions(response.sessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      addToast({
        title: 'Error',
        description: 'Failed to load chat sessions',
        color: 'danger'
      });
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const checkHealthStatus = async () => {
    try {
      const status = await chatAPI.getHealthStatus();
      setHealthStatus(status);
    } catch (error) {
      console.error('Failed to check health status:', error);
    }
  };

  const loadSessionHistory = async (sessionId: string) => {
    try {
      const history = await chatAPI.getSessionHistory(sessionId);
      setMessages(history.messages);
      setCurrentSessionId(sessionId);
    } catch (error) {
      console.error('Failed to load session history:', error);
      addToast({
        title: 'Error',
        description: 'Failed to load session history',
        color: 'danger'
      });
    }
  };

  const createNewSession = async (title?: string) => {
    try {
      const newSession = await chatAPI.createSession(title || 'New Chat');
      setSessions(prev => [newSession, ...prev]);
      setCurrentSessionId(newSession.session_id);
      setMessages([]);
      addToast({
        title: 'Success',
        description: 'New chat session created',
        color: 'success'
      });
    } catch (error) {
      console.error('Failed to create session:', error);
      addToast({
        title: 'Error',
        description: 'Failed to create new session',
        color: 'danger'
      });
    }
  };

  const deleteSession = async (sessionId: string) => {
    try {
      await chatAPI.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
      addToast({
        title: 'Success',
        description: 'Session deleted successfully',
        color: 'success'
      });
    } catch (error) {
      console.error('Failed to delete session:', error);
      addToast({
        title: 'Error',
        description: 'Failed to delete session',
        color: 'danger'
      });
    }
  };

  const sendMessage = async (message: string) => {
    if (!message.trim()) return;

    const userMessage: Message = {
      role: 'user',
      content: message,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await chatAPI.sendMessage(message, currentSessionId || undefined, enableToolResponse);

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);

      if (!currentSessionId) {
        setCurrentSessionId(response.session_id);
        await loadSessions();
      }

      if (enableToolResponse && (response.tools_info?.length || response.tool_response?.length)) {
        let toolInfo = '';
        if (response.tools_info?.length) {
          toolInfo += '**Tools Used:**\n';
          response.tools_info.forEach(tool => {
            toolInfo += `- ${tool.name}: ${tool.args}\n`;
          });
        }
        if (response.tool_response?.length) {
          toolInfo += '\n**Tool Responses:**\n';
          response.tool_response.forEach(tool => {
            toolInfo += `- ${tool.name}: ${tool.response.substring(0, 200)}...\n`;
          });
        }

        const toolMessage: Message = {
          role: 'assistant',
          content: toolInfo,
          created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, toolMessage]);
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      
      const errorMessage: Message = {
        role: 'assistant',
        content: `❌ **Error:** Failed to process your request: ${error instanceof Error ? error.message : 'Unknown error'}\n\n💡 **Please try again** or contact support if the issue persists.`,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);

      addToast({
        title: 'Error',
        description: 'Failed to send message',
        color: 'danger'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputMessage);
    }
  };

  const handleQuickCommand = (command: string) => {
    setInputMessage(command);
  };

  const getRoleDisplayName = (role: UserRole): string => {
    const roleNames = {
      super_admin: 'Super Admin',
      platform_engineer: 'Platform Engineer',
      devops: 'DevOps Engineer',
      developer: 'Developer',
      security_engineer: 'Security Engineer'
    };
    return roleNames[role] || 'User';
  };

  const getRoleColor = (role: UserRole): "default" | "primary" | "secondary" | "success" | "warning" | "danger" => {
    const roleColors = {
      super_admin: 'danger' as const,
      platform_engineer: 'primary' as const,
      devops: 'secondary' as const,
      developer: 'success' as const,
      security_engineer: 'warning' as const
    };
    return roleColors[role] || 'default';
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Fixed Left Sidebar - No scrolling */}
      <div className="w-80 border-r border-divider bg-content1 flex flex-col h-full">
        {/* Fixed Sidebar Header */}
        <div className="p-4 border-b border-divider flex-shrink-0 bg-content1">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
              <Icon icon="solar:chat-round-dots-bold" width={24} className="text-primary" />
              Chat Sessions
            </h2>
            <div className="flex gap-1">
              <Tooltip content="Export Sessions">
                <Button
                  isIconOnly
                  size="sm"
                  variant="light"
                  onPress={onExportModalOpen}
                  className="text-default-500 hover:text-default-700"
                >
                  <Icon icon="solar:download-bold" width={16} />
                </Button>
              </Tooltip>
              <Tooltip content="Refresh Sessions">
                <Button
                  isIconOnly
                  size="sm"
                  variant="light"
                                    onPress={loadSessions}
                  isLoading={isLoadingSessions}
                  className="text-default-500 hover:text-default-700"
                >
                  <Icon icon="solar:refresh-bold" width={16} />
                </Button>
              </Tooltip>
            </div>
          </div>

          <Button
            color="primary"
            onPress={() => createNewSession()}
            className="w-full mb-3"
            startContent={<Icon icon="solar:add-circle-bold" width={18} />}
          >
            New Chat
          </Button>

          {/* User Role Display */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-default-500">Role:</span>
            <Chip
              size="sm"
              color={getRoleColor(userRole)}
              variant="flat"
              className="text-xs"
            >
              {getRoleDisplayName(userRole)}
            </Chip>
          </div>
        </div>

        {/* Fixed Health Status */}
        {healthStatus && (
          <div className="p-4 border-b border-divider flex-shrink-0 bg-content1">
            <div className="flex items-center gap-2 mb-3">
              <Icon icon="solar:heart-pulse-bold" width={16} className="text-success" />
              <span className="text-sm font-semibold text-foreground">System Status</span>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-default-600">Overall</span>
                <Chip
                  size="sm"
                  color={healthStatus.status === 'healthy' ? 'success' : 'warning'}
                  variant="flat"
                  className="text-xs"
                >
                  {healthStatus.status}
                </Chip>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-default-600">LLM</span>
                <Chip
                  size="sm"
                  color={healthStatus.llm === 'healthy' ? 'success' : 'danger'}
                  variant="flat"
                  className="text-xs"
                >
                  {healthStatus.llm}
                </Chip>
              </div>
            </div>
          </div>
        )}

        {/* Scrollable Sessions List - Only this part scrolls */}
        <div className="flex-1 overflow-hidden bg-content1">
          <ScrollShadow className="h-full">
            <div className="p-4">
              <div className="space-y-2">
                {sessions.length === 0 ? (
                  <div className="text-center py-8">
                    <Icon icon="solar:chat-round-line-bold" width={32} className="text-default-300 mx-auto mb-2" />
                    <p className="text-sm text-default-500">No chat sessions yet</p>
                  </div>
                ) : (
                  sessions.map((session) => (
                    <Card
                      key={session.session_id}
                      isPressable
                      isHoverable
                      className={`cursor-pointer transition-all duration-200 ${currentSessionId === session.session_id
                          ? 'bg-primary-50 border-primary-200 dark:bg-primary-950 dark:border-primary-800 shadow-md'
                          : 'hover:bg-content2 hover:shadow-sm'
                        }`}
                      onPress={() => loadSessionHistory(session.session_id)}
                    >
                      <CardBody className="p-3">
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm truncate text-foreground mb-1">
                              {session.title}
                            </p>
                            <div className="flex items-center gap-2">
                              <p className="text-xs text-default-500">
                                {new Date(session.created_at).toLocaleDateString()}
                              </p>
                              {session.is_active && (
                                <Chip size="sm" color="success" variant="dot" className="text-xs">
                                  Active
                                </Chip>
                              )}
                            </div>
                          </div>
                          <Dropdown>
                            <DropdownTrigger>
                              <Button
                                isIconOnly
                                size="sm"
                                variant="light"
                                className="text-default-400 hover:text-default-600"
                              >
                                <Icon icon="solar:menu-dots-bold" width={16} />
                              </Button>
                            </DropdownTrigger>
                            <DropdownMenu>
                              <DropdownItem
                                key="delete"
                                color="danger"
                                onPress={() => deleteSession(session.session_id)}
                                startContent={<Icon icon="solar:trash-bin-bold" width={16} />}
                              >
                                Delete Session
                              </DropdownItem>
                            </DropdownMenu>
                          </Dropdown>
                        </div>
                      </CardBody>
                    </Card>
                  ))
                )}
              </div>
            </div>
          </ScrollShadow>
        </div>
      </div>

      {/* Main Chat Area - Fixed Layout */}
      <div className="flex-1 flex flex-col h-full">
        {/* Fixed Chat Header */}
        <div className="p-4 border-b border-divider bg-content1 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Avatar
                icon={<Icon icon="solar:cpu-bolt-bold" width={20} />}
                className="bg-primary-100 text-primary"
                size="sm"
              />
              <div>
                <h1 className="text-xl font-bold text-foreground">KubeSage Assistant</h1>
                <p className="text-sm text-default-500">
                  {currentSessionId ? 'Active Session' : `Ready to help ${getRoleDisplayName(userRole)}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Switch
                size="sm"
                isSelected={enableToolResponse}
                onValueChange={setEnableToolResponse}
                classNames={{
                  base: "inline-flex flex-row-reverse w-full max-w-md bg-content1 hover:bg-content2 items-center justify-between cursor-pointer rounded-lg gap-2 p-2 border-2 border-transparent data-[selected=true]:border-primary",
                  wrapper: "p-0 h-4 overflow-visible",
                  thumb: "w-6 h-6 border-2 shadow-lg group-data-[hover=true]:border-primary group-data-[selected=true]:ml-6 group-data-[pressed=true]:w-7 group-data-[selected]:group-data-[pressed]:ml-4",
                }}
              >
                {/* <div className="flex flex-col gap-1">
                  <p className="text-sm text-foreground">Show Tools</p>
                  <p className="text-xs text-default-400">Display tool usage details</p>
                </div> */}
              </Switch>
              <Tooltip content="Chat Settings">
                <Button
                  isIconOnly
                  size="sm"
                  variant="light"
                  onPress={onSessionModalOpen}
                  className="text-default-500 hover:text-default-700"
                >
                  <Icon icon="solar:settings-bold" width={18} />
                </Button>
              </Tooltip>
            </div>
          </div>
        </div>

        {/* Scrollable Messages Area - Only this scrolls */}
        <div className="flex-1 overflow-hidden">
          <ScrollShadow
            ref={chatContainerRef}
            className="h-full"
          >
            <div className="p-4">
              {messages.length === 0 && !isLoading ? (
                <div className="flex flex-col items-center justify-center h-full min-h-[60vh] text-center">
                  <div className="mb-8">
                    <h3 className="text-2xl font-bold text-foreground mb-2">
                      Welcome to KubeSage
                    </h3>
                    <p className="text-default-500 mb-2 max-w-md">
                      Your intelligent Kubernetes assistant for {getRoleDisplayName(userRole)}s.
                    </p>
                    <p className="text-sm text-default-400 mb-6 max-w-md">
                      Ask questions, get diagnostics, or request help with troubleshooting your cluster.
                    </p>
                  </div>

                  {/* Role-Specific Quick Commands */}
                  <div className="w-full max-w-6xl">
                    <div className="flex items-center gap-2 mb-4">
                      <h4 className="text-lg font-semibold text-foreground">Quick Commands for {getRoleDisplayName(userRole)}</h4>
                      <Chip
                        size="sm"
                        color={getRoleColor(userRole)}
                        variant="flat"
                      >
                        {userRole.replace('_', ' ').toUpperCase()}
                      </Chip>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {QUICK_COMMANDS.map((category) => (
                        <Card key={category.category} className="p-4 hover:shadow-md transition-shadow">
                          <CardHeader className="pb-3">
                            <div className="flex items-center gap-2">
                              <Icon icon={category.icon} width={20} className="text-primary" />
                              <h5 className="text-sm font-semibold text-foreground">{category.category}</h5>
                            </div>
                          </CardHeader>
                          <CardBody className="pt-0">
                            <div className="space-y-2">
                              {category.commands.map((cmd, idx) => (
                                <Button
                                  key={idx}
                                  size="sm"
                                  variant="light"
                                  className="w-full justify-start text-left h-auto p-2 hover:bg-primary-50 hover:text-primary"
                                  onPress={() => handleQuickCommand(cmd.command)}
                                >
                                  <span className="text-xs text-default-600 truncate">
                                    {cmd.label}
                                  </span>
                                </Button>
                              ))}
                            </div>
                          </CardBody>
                        </Card>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6 max-w-4xl mx-auto w-full">
                  <AnimatePresence>
                    {messages.map((message, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.3 }}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[85%] rounded-2xl p-4 ${message.role === 'user'
                              ? 'bg-primary text-primary-foreground ml-12'
                              : 'bg-content2 text-foreground mr-12'
                            }`}
                        >
                          <div className="flex items-start gap-3">
                            <Avatar
                              icon={
                                <Icon
                                  icon={message.role === 'user' ? 'solar:user-bold' : 'solar:cpu-bolt-bold'}
                                  width={16}
                                />
                              }
                              size="sm"
                              className={`flex-shrink-0 ${message.role === 'user'
                                  ? 'bg-primary-foreground/20 text-primary-foreground'
                                  : 'bg-primary-100 text-primary'
                                }`}
                            />
                            <div className="flex-1 min-w-0">
                              {message.role === 'user' ? (
                                <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                                  {message.content}
                                </div>
                              ) : (
                                <RenderMessageContent content={message.content} />
                              )}
                              {message.created_at && (
                                <div className="text-xs opacity-70 mt-3 flex items-center gap-1">
                                  <Icon icon="solar:clock-circle-bold" width={12} />
                                  {new Date(message.created_at).toLocaleTimeString()}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>

                  {/* Loading Message */}
                  {isLoading && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex justify-start"
                    >
                      <div className="max-w-[85%] rounded-2xl p-4 bg-content2 text-foreground mr-12">
                        <div className="flex items-center gap-3">
                          <Avatar
                            icon={<Spinner size="sm" />}
                            size="sm"
                            className="flex-shrink-0 bg-primary-100"
                          />
                          <span className="text-sm text-default-500">Processing your request...</span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollShadow>
        </div>

        {/* Fixed Input Area */}
        <div className="p-4 border-t border-divider bg-content1 flex-shrink-0">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <Textarea
                  placeholder={`Ask about your Kubernetes cluster as ${getRoleDisplayName(userRole)}...`}
                  value={inputMessage}
                  onValueChange={setInputMessage}
                  onKeyDown={handleKeyPress}
                  minRows={1}
                  maxRows={4}
                  className="w-full"
                  disabled={isLoading}
                  classNames={{
                    input: "text-sm",
                    inputWrapper: "bg-content2 border-2 border-divider hover:border-primary focus-within:border-primary transition-colors"
                  }}
                />
              </div>
              <Button
                color="primary"
                isIconOnly
                onPress={() => sendMessage(inputMessage)}
                                isDisabled={!inputMessage.trim() || isLoading}
                isLoading={isLoading}
                className="h-14 w-14 min-w-14"
                radius="lg"
              >
                <Icon icon="solar:arrow-up-bold" width={20} />
              </Button>
            </div>
            <div className="flex items-center justify-between mt-3 text-xs text-default-500">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1">
                  <Kbd keys={['enter']}>Enter</Kbd>
                  <span>to send</span>
                </div>
                <div className="flex items-center gap-1">
                  <Kbd keys={['shift', 'enter']}>Shift + Enter</Kbd>
                  <span>for new line</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Chip
                  size="sm"
                  color={getRoleColor(userRole)}
                  variant="flat"
                  className="text-xs"
                >
                  {getRoleDisplayName(userRole)}
                </Chip>
                {currentSessionId && (
                  <Chip size="sm" variant="flat" color="primary" className="text-xs">
                    <Icon icon="solar:check-circle-bold" width={12} className="mr-1" />
                    Session Active
                  </Chip>
                )}
                {isLoading && (
                  <Chip size="sm" variant="flat" color="warning" className="text-xs">
                    <Spinner size="sm" className="mr-1" />
                    Processing
                  </Chip>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Session Settings Modal */}
      <Modal isOpen={isSessionModalOpen} onClose={onSessionModalClose} size="md">
        <ModalContent>
          <ModalHeader>
            <div className="flex items-center gap-2">
              <Icon icon="solar:settings-bold" width={20} />
              Chat Settings
            </div>
          </ModalHeader>
          <ModalBody>
            <div className="space-y-6">
              {/* User Role Information */}
              <div>
                <h4 className="text-sm font-semibold mb-3">User Information</h4>
                <div className="bg-content2 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-default-600">Current Role:</span>
                    <Chip
                      size="sm"
                      color={getRoleColor(userRole)}
                      variant="flat"
                    >
                      {getRoleDisplayName(userRole)}
                    </Chip>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-default-600">Username:</span>
                    <span className="text-sm font-medium text-foreground">
                      {localStorage.getItem('username') || 'Unknown'}
                    </span>
                  </div>
                </div>
              </div>

              <Divider />

              {/* Tool Response Settings */}
              <div>
                <h4 className="text-sm font-semibold mb-3">Tool Response</h4>
                <Switch
                  isSelected={enableToolResponse}
                  onValueChange={setEnableToolResponse}
                  classNames={{
                    base: "inline-flex flex-row-reverse w-full max-w-md bg-content1 hover:bg-content2 items-center justify-between cursor-pointer rounded-lg gap-2 p-4 border-2 border-transparent data-[selected=true]:border-primary",
                  }}
                >
                  <div className="flex flex-col gap-1">
                    <p className="text-medium">Enable Tool Response Details</p>
                    <p className="text-tiny text-default-400">
                      Show detailed information about tools used by the assistant
                    </p>
                  </div>
                </Switch>
              </div>

              <Divider />

              {/* Session Management */}
              <div>
                <h4 className="text-sm font-semibold mb-3">Session Management</h4>
                <div className="space-y-3">
                  <Button
                    variant="flat"
                    onPress={() => {
                      createNewSession();
                      onSessionModalClose();
                    }}
                    className="w-full justify-start"
                    startContent={<Icon icon="solar:add-circle-bold" width={16} />}
                  >
                    Create New Session
                  </Button>
                  <Button
                    variant="flat"
                    color="warning"
                    onPress={() => {
                      setCurrentSessionId(null);
                      setMessages([]);
                      onSessionModalClose();
                    }}
                    className="w-full justify-start"
                    startContent={<Icon icon="solar:refresh-bold" width={16} />}
                  >
                    Clear Current Chat
                  </Button>
                </div>
              </div>

              <Divider />

              {/* Statistics */}
              <div>
                <h4 className="text-sm font-semibold mb-3">Statistics</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-content2 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-primary">{sessions.length}</div>
                    <div className="text-xs text-default-500">Total Sessions</div>
                  </div>
                  <div className="bg-content2 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-success">{messages.length}</div>
                    <div className="text-xs text-default-500">Current Messages</div>
                  </div>
                </div>
              </div>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button variant="light" onPress={onSessionModalClose}>
              Close
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Export Modal */}
      <Modal isOpen={isExportModalOpen} onClose={onExportModalClose} size="md">
        <ModalContent>
          <ModalHeader>
            <div className="flex items-center gap-2">
              <Icon icon="solar:download-bold" width={20} />
              Export Chat Data
            </div>
          </ModalHeader>
          <ModalBody>
            <div className="space-y-4">
              <p className="text-sm text-default-600">
                Export your chat sessions and messages as a JSON file for backup or analysis.
              </p>

              <div className="bg-content2 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary">{sessions.length}</div>
                    <div className="text-xs text-default-500">Total Sessions</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-success">{messages.length}</div>
                    <div className="text-xs text-default-500">Current Messages</div>
                  </div>
                </div>
              </div>

              <div className="bg-warning-50 border border-warning-200 rounded-lg p-3 dark:bg-warning-950 dark:border-warning-800">
                <div className="flex items-start gap-2">
                  <Icon icon="solar:info-circle-bold" width={16} className="text-warning mt-0.5" />
                  <div className="text-xs text-warning-700 dark:text-warning-300">
                    <p className="font-medium mb-1">Export Information</p>
                    <p>This will export all your chat sessions and the current session messages.
                      The exported file can be used for backup or imported into other instances.</p>
                  </div>
                </div>
              </div>

              {/* Role-specific export note */}
              <div className="bg-primary-50 border border-primary-200 rounded-lg p-3 dark:bg-primary-950 dark:border-primary-800">
                <div className="flex items-start gap-2">
                  <Icon icon="solar:user-bold" width={16} className="text-primary mt-0.5" />
                  <div className="text-xs text-primary-700 dark:text-primary-300">
                    <p className="font-medium mb-1">Role-Specific Data</p>
                    <p>Exporting as {getRoleDisplayName(userRole)}. The exported data will include role-specific interactions and permissions.</p>
                  </div>
                </div>
              </div>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button variant="light" onPress={onExportModalClose}>
              Cancel
            </Button>
            <Button
              color="primary"
              onPress={() => {
                exportSessions(sessions, messages);
                onExportModalClose();
              }}
              startContent={<Icon icon="solar:download-bold" width={16} />}
            >
              Export Data
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </div>
  );
}


