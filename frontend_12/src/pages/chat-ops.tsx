import React from 'react';
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
  Divider
} from '@heroui/react';
import { Icon } from '@iconify/react';
import { motion, AnimatePresence } from 'framer-motion';
import { addToast } from '../components/toast-manager';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

// Initialize markdown parser
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code class="hljs language-${lang}">${hljs.highlight(str, { language: lang }).value}</code></pre>`;
      } catch (__) {}
    }
    return `<pre class="hljs"><code class="hljs">${md.utils.escapeHtml(str)}</code></pre>`;
  }
});

// Update the renderMessageContent function
const renderMessageContent = (content: string) => {
  const htmlContent = md.render(content);
  return (
    <div 
      className="prose prose-sm dark:prose-invert max-w-none prose-pre:bg-content3 prose-pre:border prose-pre:border-divider prose-code:bg-content2 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-sm"
      dangerouslySetInnerHTML={{ __html: htmlContent }}
      style={{
        '--tw-prose-body': 'var(--nextui-colors-foreground)',
        '--tw-prose-headings': 'var(--nextui-colors-foreground)',
        '--tw-prose-lead': 'var(--nextui-colors-foreground-600)',
        '--tw-prose-links': 'var(--nextui-colors-primary)',
        '--tw-prose-bold': 'var(--nextui-colors-foreground)',
        '--tw-prose-counters': 'var(--nextui-colors-foreground-500)',
        '--tw-prose-bullets': 'var(--nextui-colors-foreground-400)',
        '--tw-prose-hr': 'var(--nextui-colors-divider)',
        '--tw-prose-quotes': 'var(--nextui-colors-foreground)',
        '--tw-prose-quote-borders': 'var(--nextui-colors-divider)',
        '--tw-prose-captions': 'var(--nextui-colors-foreground-500)',
        '--tw-prose-code': 'var(--nextui-colors-foreground)',
        '--tw-prose-pre-code': 'var(--nextui-colors-foreground)',
        '--tw-prose-pre-bg': 'var(--nextui-colors-content3)',
        '--tw-prose-th-borders': 'var(--nextui-colors-divider)',
        '--tw-prose-td-borders': 'var(--nextui-colors-divider)',
      } as React.CSSProperties}
    />
  );
};


// Types
interface Message {
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

interface Session {
  id: number;
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

interface ExecuteResult {
  status: 'success' | 'failed' | 'running';
  command: string;
  output?: string;
  error?: string;
  execution_time?: number;
  timestamp: string;
}

// API Configuration
const API_BASE_URL = 'https://10.0.32.103:8004/api/v1';

class ChatAPI {
  private getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }

  async sendMessage(message: string, sessionId?: string, stream: boolean = true) {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        message,
        session_id: sessionId,
        stream
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response;
  }

  async executeCommand(command: string): Promise<ExecuteResult> {
    const response = await fetch(`${API_BASE_URL}/execute`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ command })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async getSessions(): Promise<Session[]> {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.sessions;
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

  async updateSession(sessionId: string, title: string): Promise<Session> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: 'PUT',
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

  async getSessionHistory(sessionId: string): Promise<Message[]> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/history`, {
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.messages;
  }

  async clearSession(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  }

  async generateTitle(sessionId: string): Promise<string> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/title`, {
      method: 'POST',
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.title;
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

// Quick Commands
const QUICK_COMMANDS = [
  {
    category: "Pods",
    commands: [
      { label: "List all pods", command: "get pods --all-namespaces" },
      { label: "Get pod details", command: "describe pod <pod-name> -n <namespace>" },
      { label: "Get pod logs", command: "logs <pod-name> -n <namespace>" },
      { label: "Execute in pod", command: "exec -it <pod-name> -n <namespace> -- /bin/bash" }
    ]
  },
  {
    category: "Deployments",
    commands: [
      { label: "List deployments", command: "get deployments --all-namespaces" },
      { label: "Scale deployment", command: "scale deployment <deployment-name> --replicas=<count> -n <namespace>" },
      { label: "Restart deployment", command: "rollout restart deployment <deployment-name> -n <namespace>" },
      { label: "Check rollout status", command: "rollout status deployment <deployment-name> -n <namespace>" }
    ]
  },
  {
    category: "Services",
    commands: [
      { label: "List services", command: "get services --all-namespaces" },
      { label: "Describe service", command: "describe service <service-name> -n <namespace>" },
      { label: "Get endpoints", command: "get endpoints <service-name> -n <namespace>" }
    ]
  },
  {
    category: "Cluster",
    commands: [
      { label: "Get nodes", command: "get nodes" },
      { label: "Cluster info", command: "cluster-info" },
      { label: "Get events", command: "get events --sort-by=.metadata.creationTimestamp" },
      { label: "Top nodes", command: "top nodes" },
      { label: "Top pods", command: "top pods --all-namespaces" }
    ]
  },
  {
    category: "Troubleshooting",
    commands: [
      { label: "Check pod status", command: "get pods --field-selector=status.phase!=Running --all-namespaces" },
      { label: "Get failed pods", command: "get pods --field-selector=status.phase=Failed --all-namespaces" },
      { label: "Check resource usage", command: "describe node <node-name>" },
      { label: "Get all resources", command: "get all --all-namespaces" }
    ]
  }
];

// Main Component
export const ChatOps: React.FC = () => {
  // State
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [inputMessage, setInputMessage] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [isStreaming, setIsStreaming] = React.useState(false);
  const [sessions, setSessions] = React.useState<Session[]>([]);
  const [currentSession, setCurrentSession] = React.useState<Session | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = React.useState(false);
  const [streamingEnabled, setStreamingEnabled] = React.useState(true);
  const [executeResults, setExecuteResults] = React.useState<ExecuteResult[]>([]);
  const [commandInput, setCommandInput] = React.useState('');
  const [isExecuting, setIsExecuting] = React.useState(false);
  const [healthStatus, setHealthStatus] = React.useState<any>(null);

  // UI State
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);
  const [showQuickCommands, setShowQuickCommands] = React.useState(false);
  const [selectedQuickCommand, setSelectedQuickCommand] = React.useState('');

  // Modals
  const { isOpen: isNewSessionOpen, onOpen: onNewSessionOpen, onClose: onNewSessionClose } = useDisclosure();
  const { isOpen: isSettingsOpen, onOpen: onSettingsOpen, onClose: onSettingsClose } = useDisclosure();
  const { isOpen: isHealthOpen, onOpen: onHealthOpen, onClose: onHealthClose } = useDisclosure();

  // Refs
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = React.useRef<AbortController | null>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load sessions on mount
  React.useEffect(() => {
    loadSessions();
    loadHealthStatus();
  }, []);

  // Load sessions
  const loadSessions = async () => {
    try {
      setIsLoadingSessions(true);
      const sessionsData = await chatAPI.getSessions();
      setSessions(sessionsData);
      
      // Set current session to the most recent one if none selected
      if (!currentSession && sessionsData.length > 0) {
        const mostRecent = sessionsData.sort((a, b) => 
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        )[0];
        setCurrentSession(mostRecent);
        await loadSessionHistory(mostRecent.session_id);
      }
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

  // Load session history
  const loadSessionHistory = async (sessionId: string) => {
    try {
      const history = await chatAPI.getSessionHistory(sessionId);
      setMessages(history);
    } catch (error) {
      console.error('Failed to load session history:', error);
      addToast({
        title: 'Error',
        description: 'Failed to load session history',
        color: 'danger'
      });
    }
  };

  // Load health status
  const loadHealthStatus = async () => {
    try {
      const status = await chatAPI.getHealthStatus();
      setHealthStatus(status);
    } catch (error) {
      console.error('Failed to load health status:', error);
    }
  };

  // Create new session
  const createNewSession = async (title: string) => {
    try {
      const newSession = await chatAPI.createSession(title);
      setSessions(prev => [newSession, ...prev]);
      setCurrentSession(newSession);
      setMessages([]);
      onNewSessionClose();
      
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

  // Switch session
  const switchSession = async (session: Session) => {
    if (currentSession?.session_id === session.session_id) return;
    
    setCurrentSession(session);
    await loadSessionHistory(session.session_id);
  };

  // Delete session
  const deleteSession = async (sessionId: string) => {
    try {
      await chatAPI.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      
      if (currentSession?.session_id === sessionId) {
        const remainingSessions = sessions.filter(s => s.session_id !== sessionId);
        if (remainingSessions.length > 0) {
          const nextSession = remainingSessions[0];
          setCurrentSession(nextSession);
          await loadSessionHistory(nextSession.session_id);
        } else {
          setCurrentSession(null);
          setMessages([]);
        }
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

  // Clear session
  const clearSession = async () => {
    if (!currentSession) return;
    
    try {
      await chatAPI.clearSession(currentSession.session_id);
      setMessages([]);
      
      addToast({
        title: 'Success',
        description: 'Session cleared successfully',
        color: 'success'
      });
    } catch (error) {
      console.error('Failed to clear session:', error);
      addToast({
        title: 'Error',
        description: 'Failed to clear session',
        color: 'danger'
      });
    }
  };

  // Send message
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);
    setIsStreaming(streamingEnabled);

    // Add user message immediately
    const newUserMessage: Message = {
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, newUserMessage]);

    try {
      // Create session if none exists
      let sessionId = currentSession?.session_id;
      if (!sessionId) {
        const newSession = await chatAPI.createSession('New Chat');
        setCurrentSession(newSession);
        setSessions(prev => [newSession, ...prev]);
        sessionId = newSession.session_id;
      }

      if (streamingEnabled) {
        // Streaming response
        abortControllerRef.current = new AbortController();
        const response = await chatAPI.sendMessage(userMessage, sessionId, true);
        
        if (!response.body) {
          throw new Error('No response body');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // Add assistant message placeholder
        const assistantMessage: Message = {
          role: 'assistant',
          content: '',
          created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, assistantMessage]);

        let assistantContent = '';
        
        try {
          while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));
                  
                  if (data.token && !data.done) {
                    assistantContent += data.token;
                    setMessages(prev => {
                      const newMessages = [...prev];
                      newMessages[newMessages.length - 1] = {
                        ...newMessages[newMessages.length - 1],
                        content: assistantContent
                      };
                      return newMessages;
                    });
                  } else if (data.done) {
                    setIsStreaming(false);
                    break;
                  }
                } catch (e) {
                  // Ignore JSON parse errors for incomplete chunks
                }
              }
            }
          }
        } finally {
          reader.releaseLock();
        }
      } else {
        // Non-streaming response
        const response = await chatAPI.sendMessage(userMessage, sessionId, false);
        const data = await response.json();
        
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.content,
          created_at: data.created_at
        };
        setMessages(prev => [...prev, assistantMessage]);
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      
      const errorMessage: Message = {
        role: 'assistant',
        content: `❌ **Error:** Failed to send message. ${error instanceof Error ? error.message : 'Unknown error'}`,
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
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  // Execute kubectl command directly
  const executeCommand = async () => {
    if (!commandInput.trim() || isExecuting) return;

    const command = commandInput.trim();
    setIsExecuting(true);

    try {
      const result = await chatAPI.executeCommand(command);
      setExecuteResults(prev => [result, ...prev]);
      setCommandInput('');
      
      if (result.status === 'success') {
        addToast({
          title: 'Command Executed',
          description: 'Command executed successfully',
          color: 'success'
        });
      } else {
        addToast({
          title: 'Command Failed',
          description: result.error || 'Command execution failed',
          color: 'danger'
        });
      }
    } catch (error) {
      console.error('Failed to execute command:', error);
      addToast({
        title: 'Error',
        description: 'Failed to execute command',
        color: 'danger'
      });
    } finally {
      setIsExecuting(false);
    }
  };

   // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleCommandKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      executeCommand();
    }
  };

  // Stop streaming
  const stopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      setIsLoading(false);
    }
  };

  // Insert quick command
  const insertQuickCommand = (command: string) => {
    setInputMessage(prev => prev + (prev ? '\n' : '') + `kubectl ${command}`);
    setShowQuickCommands(false);
    inputRef.current?.focus();
  };

  // Render message content with markdown
  const renderMessageContent = (content: string) => {
    const htmlContent = md.render(content);
    return (
      <div 
        className="prose prose-sm dark:prose-invert max-w-none prose-pre:bg-content3 prose-pre:border prose-pre-border-divider prose-code:bg-content2 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-sm"
        dangerouslySetInnerHTML={{ __html: htmlContent }}
        style={{
          '--tw-prose-body': 'var(--nextui-colors-foreground)',
          '--tw-prose-headings': 'var(--nextui-colors-foreground)',
          '--tw-prose-lead': 'var(--nextui-colors-foreground-600)',
          '--tw-prose-links': 'var(--nextui-colors-primary)',
          '--tw-prose-bold': 'var(--nextui-colors-foreground)',
          '--tw-prose-counters': 'var(--nextui-colors-foreground-500)',
          '--tw-prose-bullets': 'var(--nextui-colors-foreground-400)',
          '--tw-prose-hr': 'var(--nextui-colors-divider)',
          '--tw-prose-quotes': 'var(--nextui-colors-foreground)',
          '--tw-prose-quote-borders': 'var(--nextui-colors-divider)',
          '--tw-prose-captions': 'var(--nextui-colors-foreground-500)',
          '--tw-prose-code': 'var(--nextui-colors-foreground)',
          '--tw-prose-pre-code': 'var(--nextui-colors-foreground)',
          '--tw-prose-pre-bg': 'var(--nextui-colors-content3)',
          '--tw-prose-th-borders': 'var(--nextui-colors-divider)',
          '--tw-prose-td-borders': 'var(--nextui-colors-divider)',
        } as React.CSSProperties}
      />
    );
  };

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'success';
      case 'degraded': return 'warning';
      case 'unhealthy': return 'danger';
      default: return 'default';
    }
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <motion.div
        initial={false}
        animate={{ width: sidebarCollapsed ? 60 : 320 }}
        className="border-r border-divider bg-content1 flex flex-col"
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-divider">
          <div className="flex items-center justify-between">
            {!sidebarCollapsed && (
              <div className="flex items-center gap-2">
                <Icon icon="lucide:message-square" className="text-primary text-xl" />
                <h2 className="font-semibold">ChatOps</h2>
              </div>
            )}
            <Button
              isIconOnly
              variant="ghost"
              size="sm"
              onPress={() => setSidebarCollapsed(!sidebarCollapsed)}
            >
              <Icon icon={sidebarCollapsed ? "lucide:chevron-right" : "lucide:chevron-left"} />
            </Button>
          </div>
        </div>

        {/* Session Actions */}
        {!sidebarCollapsed && (
          <div className="p-4 border-b border-divider">
            <div className="flex gap-2">
              <Button
                color="primary"
                variant="flat"
                size="sm"
                startContent={<Icon icon="lucide:plus" />}
                onPress={onNewSessionOpen}
                className="flex-1"
              >
                New Chat
              </Button>
              <Button
                variant="flat"
                size="sm"
                isIconOnly
                onPress={onSettingsOpen}
              >
                <Icon icon="lucide:settings" />
              </Button>
              <Button
                variant="flat"
                size="sm"
                isIconOnly
                onPress={onHealthOpen}
              >
                <Icon 
                  icon="lucide:activity" 
                  className={healthStatus?.status === 'healthy' ? 'text-success' : 'text-warning'}
                />
              </Button>
            </div>
          </div>
        )}

        {/* Sessions List */}
        {!sidebarCollapsed && (
          <ScrollShadow className="flex-1 p-2">
            {isLoadingSessions ? (
              <div className="flex justify-center p-4">
                <Spinner size="sm" />
              </div>
            ) : (
              <div className="space-y-1">
                {sessions.map((session) => (
                  <motion.div
                    key={session.session_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`p-3 rounded-lg cursor-pointer transition-colors group ${
                      currentSession?.session_id === session.session_id
                        ? 'bg-primary/10 border border-primary/20'
                        : 'hover:bg-content2'
                    }`}
                    onClick={() => switchSession(session)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {session.title}
                        </p>
                        <p className="text-xs text-foreground-500 mt-1">
                          {new Date(session.updated_at).toLocaleDateString()}
                        </p>
                      </div>
                      <Dropdown>
                        <DropdownTrigger>
                          <Button
                            isIconOnly
                            size="sm"
                            variant="light"
                            className="opacity-0 group-hover:opacity-100"
                          >
                            <Icon icon="lucide:more-vertical" className="text-sm" />
                          </Button>
                        </DropdownTrigger>
                        <DropdownMenu>
                          <DropdownItem
                            key="clear"
                            startContent={<Icon icon="lucide:trash-2" />}
                            onPress={() => clearSession()}
                          >
                            Clear Messages
                          </DropdownItem>
                          <DropdownItem
                            key="delete"
                            className="text-danger"
                            color="danger"
                            startContent={<Icon icon="lucide:trash" />}
                            onPress={() => deleteSession(session.session_id)}
                          >
                            Delete Session
                          </DropdownItem>
                        </DropdownMenu>
                      </Dropdown>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </ScrollShadow>
        )}

        {/* Collapsed Sidebar Icons */}
        {sidebarCollapsed && (
          <div className="flex flex-col items-center gap-2 p-2">
            <Button
              isIconOnly
              color="primary"
              variant="flat"
              size="sm"
              onPress={onNewSessionOpen}
            >
              <Icon icon="lucide:plus" />
            </Button>
            <Button
              isIconOnly
              variant="flat"
              size="sm"
              onPress={onSettingsOpen}
            >
              <Icon icon="lucide:settings" />
            </Button>
            <Button
              isIconOnly
              variant="flat"
              size="sm"
              onPress={onHealthOpen}
            >
              <Icon 
                icon="lucide:activity" 
                className={healthStatus?.status === 'healthy' ? 'text-success' : 'text-warning'}
              />
            </Button>
          </div>
        )}
      </motion.div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        <div className="p-4 border-b border-divider bg-content1">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Icon icon="lucide:terminal" className="text-primary text-xl" />
                <div>
                  <h1 className="font-semibold">
                    {currentSession?.title || 'KubeSage ChatOps'}
                  </h1>
                  <p className="text-xs text-foreground-500">
                    AI-powered Kubernetes operations assistant
                  </p>
                </div>
              </div>
              {healthStatus && (
                <Chip
                  size="sm"
                  color={getStatusColor(healthStatus.status)}
                  variant="flat"
                  startContent={<Icon icon="lucide:activity" className="text-xs" />}
                >
                  {healthStatus.status}
                </Chip>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant="flat"
                size="sm"
                startContent={<Icon icon="lucide:zap" />}
                onPress={() => setShowQuickCommands(!showQuickCommands)}
              >
                Quick Commands
              </Button>
              <Switch
                size="sm"
                isSelected={streamingEnabled}
                onValueChange={setStreamingEnabled}
                startContent={<Icon icon="lucide:zap" />}
                endContent={<Icon icon="lucide:message-circle" />}
              >
                Stream
              </Switch>
            </div>
          </div>
        </div>

        {/* Quick Commands Panel */}
        <AnimatePresence>
          {showQuickCommands && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="border-b border-divider bg-content2"
            >
              <ScrollShadow orientation="horizontal" className="p-4">
                <div className="flex gap-4">
                  {QUICK_COMMANDS.map((category) => (
                    <Card key={category.category} className="min-w-64">
                      <CardHeader className="pb-2">
                        <h4 className="text-sm font-semibold">{category.category}</h4>
                      </CardHeader>
                      <CardBody className="pt-0">
                        <div className="space-y-1">
                          {category.commands.map((cmd, index) => (
                            <Button
                              key={index}
                              variant="light"
                              size="sm"
                              className="justify-start h-auto p-2"
                              onPress={() => insertQuickCommand(cmd.command)}
                            >
                              <div className="text-left">
                                <p className="text-xs font-medium">{cmd.label}</p>
                                <Code className="text-xs mt-1">{cmd.command}</Code>
                              </div>
                            </Button>
                          ))}
                        </div>
                      </CardBody>
                    </Card>
                  ))}
                </div>
              </ScrollShadow>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Messages Area */}
        <ScrollShadow className="flex-1 p-4">
          <div className="max-w-4xl mx-auto space-y-4">
            <AnimatePresence>
              {messages.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-12"
                >
                  <Icon icon="lucide:message-square" className="text-6xl text-foreground-300 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold mb-2">Welcome to KubeSage ChatOps</h3>
                  <p className="text-foreground-500 mb-6">
                    Your AI-powered Kubernetes operations assistant. Ask questions, run commands, and manage your cluster.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                    <Card className="p-4">
                      <div className="flex items-center gap-3">
                        <Icon icon="lucide:search" className="text-primary text-xl" />
                        <div className="text-left">
                          <p className="font-medium">Ask Questions</p>
                          <p className="text-sm text-foreground-500">
                            "Show me all failing pods"
                          </p>
                        </div>
                      </div>
                    </Card>
                    <Card className="p-4">
                      <div className="flex items-center gap-3">
                        <Icon icon="lucide:terminal" className="text-primary text-xl" />
                        <div className="text-left">
                          <p className="font-medium">Run Commands</p>
                          <p className="text-sm text-foreground-500">
                            "kubectl get pods -n production"
                          </p>
                        </div>
                      </div>
                    </Card>
                    <Card className="p-4">
                      <div className="flex items-center gap-3">
                        <Icon icon="lucide:wrench" className="text-primary text-xl" />
                        <div className="text-left">
                          <p className="font-medium">Troubleshoot</p>
                          <p className="text-sm text-foreground-500">
                            "Why is my deployment failing?"
                          </p>
                        </div>
                      </div>
                    </Card>
                    <Card className="p-4">
                      <div className="flex items-center gap-3">
                        <Icon icon="lucide:scale" className="text-primary text-xl" />
                        <div className="text-left">
                          <p className="font-medium">Scale Resources</p>
                          <p className="text-sm text-foreground-500">
                            "Scale my-app to 5 replicas"
                          </p>
                        </div>
                      </div>
                    </Card>
                  </div>
                </motion.div>
              ) : (
                messages.map((message, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[80%] ${message.role === 'user' ? 'order-2' : 'order-1'}`}>
                      <Card className={`${
                        message.role === 'user' 
                          ? 'bg-primary text-primary-foreground' 
                          : 'bg-content2'
                      }`}>
                        <CardBody className="p-4">
                          <div className="flex items-start gap-3">
                            <div className={`p-2 rounded-full ${
                              message.role === 'user' 
                                ? 'bg-primary-foreground/20' 
                                : 'bg-primary/20'
                            }`}>
                              <Icon 
                                icon={message.role === 'user' ? 'lucide:user' : 'lucide:bot'} 
                                className={`text-sm ${
                                  message.role === 'user' 
                                    ? 'text-primary-foreground' 
                                    : 'text-primary'
                                }`}
                              />
                                        </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-sm font-medium">
                                  {message.role === 'user' ? 'You' : 'KubeSage'}
                                </span>
                                <span className="text-xs opacity-70">
                                  {new Date(message.created_at).toLocaleTimeString()}
                                </span>
                              </div>
                              <div className={`${
                                message.role === 'user' 
                                  ? 'text-primary-foreground' 
                                  : 'text-foreground'
                              }`}>
                                {message.role === 'user' ? (
                                  <p className="whitespace-pre-wrap">{message.content}</p>
                                ) : (
                                  renderMessageContent(message.content)
                                )}
                              </div>
                            </div>
                          </div>
                        </CardBody>
                      </Card>
                    </div>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
            
            {/* Streaming indicator */}
            {isStreaming && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <Card className="bg-content2">
                  <CardBody className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-full bg-primary/20">
                        <Icon icon="lucide:bot" className="text-sm text-primary" />
                      </div>
                      <div className="flex items-center gap-2">
                        <Spinner size="sm" />
                        <span className="text-sm">KubeSage is thinking...</span>
                        <Button
                          size="sm"
                          variant="flat"
                          color="danger"
                          onPress={stopStreaming}
                        >
                          Stop
                        </Button>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              </motion.div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollShadow>

        {/* Input Area */}
        <div className="p-4 border-t border-divider bg-content1">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3">
              <div className="flex-1">
                <Textarea
                  ref={inputRef}
                  placeholder="Ask KubeSage about your Kubernetes cluster... (e.g., 'Show me all pods in production namespace')"
                  value={inputMessage}
                  onValueChange={setInputMessage}
                  onKeyDown={handleKeyDown}
                  minRows={1}
                  maxRows={6}
                  variant="bordered"
                  classNames={{
                    input: "resize-none",
                    inputWrapper: "bg-content2"
                  }}
                  endContent={
                    <div className="flex items-center gap-1">
                      <Kbd keys={["enter"]}>Send</Kbd>
                      <Kbd keys={["shift", "enter"]}>New line</Kbd>
                    </div>
                  }
                />
              </div>
              <div className="flex flex-col gap-2">
                <Button
                  color="primary"
                  isDisabled={!inputMessage.trim() || isLoading}
                  isLoading={isLoading}
                  onPress={sendMessage}
                  className="h-14"
                >
                  <Icon icon="lucide:send" />
                </Button>
                <Button
                  variant="flat"
                  size="sm"
                  isIconOnly
                  onPress={() => setShowQuickCommands(!showQuickCommands)}
                >
                  <Icon icon="lucide:zap" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Direct Command Execution Panel */}
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: 400 }}
        className="border-l border-divider bg-content1 flex flex-col"
      >
        <div className="p-4 border-b border-divider">
          <div className="flex items-center gap-2">
            <Icon icon="lucide:terminal" className="text-primary" />
            <h3 className="font-semibold">Direct Commands</h3>
          </div>
          <p className="text-xs text-foreground-500 mt-1">
            Execute kubectl commands directly
          </p>
        </div>

        <div className="p-4 border-b border-divider">
          <div className="flex gap-2">
            <Input
              placeholder="kubectl command..."
              value={commandInput}
              onValueChange={setCommandInput}
              onKeyDown={handleCommandKeyDown}
              variant="bordered"
              size="sm"
              startContent={<span className="text-xs text-foreground-500">kubectl</span>}
            />
            <Button
              color="primary"
              size="sm"
              isDisabled={!commandInput.trim() || isExecuting}
              isLoading={isExecuting}
              onPress={executeCommand}
            >
              Run
            </Button>
          </div>
        </div>

        <ScrollShadow className="flex-1 p-4">
          <div className="space-y-3">
            {executeResults.length === 0 ? (
              <div className="text-center py-8">
                <Icon icon="lucide:terminal" className="text-4xl text-foreground-300 mx-auto mb-2" />
                <p className="text-sm text-foreground-500">
                  No commands executed yet
                </p>
              </div>
            ) : (
              executeResults.map((result, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <Card className="bg-content2">
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between w-full">
                        <div className="flex items-center gap-2">
                          <Chip
                            size="sm"
                            color={result.status === 'success' ? 'success' : 'danger'}
                            variant="flat"
                          >
                            {result.status}
                          </Chip>
                          <span className="text-xs text-foreground-500">
                            {new Date(result.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        {result.execution_time && (
                          <span className="text-xs text-foreground-500">
                            {result.execution_time}ms
                          </span>
                        )}
                      </div>
                    </CardHeader>
                    <CardBody className="pt-0">
                      <Code className="text-xs mb-2 block">
                        {result.command}
                      </Code>
                      {result.output && (
                        <pre className="text-xs bg-content3 p-2 rounded overflow-x-auto">
                          {result.output}
                        </pre>
                      )}
                      {result.error && (
                        <pre className="text-xs bg-danger/10 text-danger p-2 rounded overflow-x-auto">
                          {result.error}
                        </pre>
                      )}
                    </CardBody>
                  </Card>
                </motion.div>
              ))
            )}
          </div>
        </ScrollShadow>
      </motion.div>

      {/* New Session Modal */}
      <Modal isOpen={isNewSessionOpen} onClose={onNewSessionClose}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>Create New Chat Session</ModalHeader>
              <ModalBody>
                <Input
                  label="Session Title"
                  placeholder="e.g., Production Troubleshooting"
                  variant="bordered"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const title = (e.target as HTMLInputElement).value;
                      if (title.trim()) {
                        createNewSession(title.trim());
                      }
                    }
                  }}
                />
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>
                  Cancel
                </Button>
                <Button
                  color="primary"
                  onPress={() => {
                    const input = document.querySelector('input[placeholder*="Production"]') as HTMLInputElement;
                    const title = input?.value.trim() || 'New Chat';
                    createNewSession(title);
                  }}
                >
                  Create
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Settings Modal */}
      <Modal isOpen={isSettingsOpen} onClose={onSettingsClose}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>ChatOps Settings</ModalHeader>
              <ModalBody>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Streaming Responses</p>
                      <p className="text-sm text-foreground-500">
                        Enable real-time response streaming
                      </p>
                    </div>
                    <Switch
                      isSelected={streamingEnabled}
                      onValueChange={setStreamingEnabled}
                    />
                  </div>
                  
                  <Divider />
                  
                  <div>
                    <p className="font-medium mb-2">Quick Commands</p>
                    <p className="text-sm text-foreground-500 mb-3">
                      Manage your frequently used kubectl commands
                    </p>
                    <Button variant="flat" size="sm">
                      Customize Commands
                    </Button>
                  </div>
                  
                  <Divider />
                  
                  <div>
                    <p className="font-medium mb-2">Export/Import</p>
                    <p className="text-sm text-foreground-500 mb-3">
                      Backup your chat sessions and settings
                    </p>
                    <div className="flex gap-2">
                      <Button variant="flat" size="sm">
                        Export Sessions
                      </Button>
                      <Button variant="flat" size="sm">
                        Import Sessions
                      </Button>
                    </div>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button color="primary" onPress={onClose}>
                  Done
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Health Status Modal */}
      <Modal isOpen={isHealthOpen} onClose={onHealthClose}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>System Health Status</ModalHeader>
              <ModalBody>
                {healthStatus ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Overall Status</span>
                      <Chip
                        color={getStatusColor(healthStatus.status)}
                        variant="flat"
                      >
                        {healthStatus.status}
                      </Chip>
                    </div>
                    
                    <Divider />
                    
                    <div className="space-y-3">
                      <h4 className="font-medium">Components</h4>
                      
                      {healthStatus.components && (
                        <>
                          <div className="flex items-center justify-between">
                            <span className="text-sm">Database</span>
                            <Chip
                              size="sm"
                              color={healthStatus.components.database === 'connected' ? 'success' : 'danger'}
                              variant="flat"
                            >
                              {healthStatus.components.database}
                            </Chip>
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <span className="text-sm">LLM Service</span>
                            <Chip
                              size="sm"
                              color={healthStatus.components.llm === 'connected' ? 'success' : 'danger'}
                              variant="flat"
                            >
                              {healthStatus.components.llm}
                            </Chip>
                          </div>
                          
                          {healthStatus.components.kubernetes && (
                            <>
                              <div className="flex items-center justify-between">
                                <span className="text-sm">Kubernetes Client</span>
                                <Chip
                                  size="sm"
                                  color={healthStatus.components.kubernetes.client_available ? 'success' : 'danger'}
                                  variant="flat"
                                >
                                  {healthStatus.components.kubernetes.client_available ? 'Available' : 'Unavailable'}
                                </Chip>
                              </div>
                              
                              <div className="flex items-center justify-between">
                                <span className="text-sm">Cluster Access</span>
                                <Chip
                                  size="sm"
                                  color={healthStatus.components.kubernetes.cluster_accessible ? 'success' : 'danger'}
                                  variant="flat"
                                >
                                  {healthStatus.components.kubernetes.cluster_accessible ? 'Accessible' : 'Inaccessible'}
                                </Chip>
                              </div>
                              
                              {healthStatus.components.kubernetes.cluster_version && (
                                <div className="flex items-center justify-between">
                                  <span className="text-sm">Cluster Version</span>
                                  <Code size="sm">{healthStatus.components.kubernetes.cluster_version}</Code>
                                </div>
                              )}
                              
                              <div className="flex items-center justify-between">
                                <span className="text-sm">Nodes</span>
                                <span className="text-sm">{healthStatus.components.kubernetes.node_count}</span>
                              </div>
                              
                              <div className="flex items-center justify-between">
                                <span className="text-sm">Namespaces</span>
                                <span className="text-sm">{healthStatus.components.kubernetes.namespace_count}</span>
                              </div>
                            </>
                          )}
                        </>
                      )}
                    </div>
                    
                    {healthStatus.capabilities && (
                      <>
                        <Divider />
                        <div>
                          <h4 className="font-medium mb-2">Capabilities</h4>
                          <div className="flex flex-wrap gap-1">
                            {healthStatus.capabilities.map((capability: string, index: number) => (
                              <Chip key={index} size="sm" variant="flat">
                                {capability.replace(/_/g, ' ')}
                              </Chip>
                            ))}
                                      </div>
                        </div>
                      </>
                    )}
                    
                    {healthStatus.errors && healthStatus.errors.length > 0 && (
                      <>
                        <Divider />
                        <div>
                          <h4 className="font-medium mb-2 text-danger">Errors</h4>
                          <div className="space-y-2">
                            {healthStatus.errors.map((error: string, index: number) => (
                              <div key={index} className="p-2 bg-danger/10 rounded text-sm text-danger">
                                {error}
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                    
                    <Divider />
                    
                    <div className="text-xs text-foreground-500">
                      <p>Service Version: {healthStatus.version}</p>
                      <p>Last Updated: {new Date(healthStatus.timestamp).toLocaleString()}</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-center p-4">
                    <Spinner />
                  </div>
                )}
              </ModalBody>
              <ModalFooter>
                <Button variant="flat" onPress={loadHealthStatus}>
                  Refresh
                </Button>
                <Button color="primary" onPress={onClose}>
                  Close
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
};

export default ChatOps;       
