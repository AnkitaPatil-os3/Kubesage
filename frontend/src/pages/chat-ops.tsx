import React, { useState } from 'react';
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
import '../styles/chat-ops.css';

// Initialize markdown parser
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,
});

const defaultFence = md.renderer.rules.fence || function(tokens, idx, options, env, self) {
  return self.renderToken(tokens, idx, options);
};

// Fixed markdown fence renderer for proper code block alignment
md.renderer.rules.fence = function(tokens, idx, options, env, self) {
  const token = tokens[idx];

  // Extract first comment line starting with # as header, rest as commands
  const lines = token.content.split('\n');
  let headerLine = '';
  let commandLines = lines;
  
  if (lines.length > 0 && lines[0].trim().startsWith('#')) {
    headerLine = lines[0].trim().substring(1).trim(); // remove # and trim
    commandLines = lines.slice(1);
  }
  
  const escapedHeader = md.utils.escapeHtml(headerLine);

  // Join all command lines and split by double newlines to separate command blocks
  const commandContent = commandLines.join('\n');
  
  // Split by double newlines and filter out empty commands
  const commands = commandContent.split('\n\n')
    .map(cmd => cmd.trim())
    .filter(cmd => cmd.length > 0);

  // If no double newlines found, treat the entire content as a single command block
  if (commands.length === 0 && commandContent.trim()) {
    commands.push(commandContent.trim());
  }

  // Render each command in its own box with proper left alignment
  const commandBlocks = commands.map(cmd => {
    // Normalize the command text - remove extra spaces and ensure proper line breaks
    const normalizedCmd = cmd
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0)
      .join('\n');
    
    const escapedCmd = md.utils.escapeHtml(normalizedCmd);
    
    return `
      <div class="mb-4">
        <div class="relative rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 overflow-hidden">
          <div class="flex items-center justify-between bg-gray-200 dark:bg-gray-800 px-3 py-1.5 border-b border-gray-300 dark:border-gray-600">
            <span class="text-xs font-medium text-gray-600 dark:text-gray-400">bash</span>
            <button class="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 cursor-pointer" onclick="navigator.clipboard.writeText('${escapedCmd.replace(/'/g, "\\'")}')">copy</button>
          </div>
          <pre class="p-4 m-0 bg-transparent overflow-x-auto font-mono text-sm leading-relaxed text-gray-800 dark:text-gray-100" style="white-space: pre; word-break: normal; text-align: left;">
            <code class="text-gray-800 dark:text-gray-100" style="background-color: transparent !important; display: block; text-align: left;">${escapedCmd}</code>
          </pre>
        </div>
      </div>
    `;
  }).join('\n');

  return `
    <div class="mb-4">
      ${headerLine ? `<div class="mb-2 font-medium text-foreground">${escapedHeader}</div>` : ''}
      ${commandBlocks}
    </div>
  `;
};

import { useMemo } from 'react';

// Custom component to render message content with proper code block handling
const RenderMessageContent: React.FC<{ content: string; isStreaming?: boolean }> = ({ content, isStreaming = false }) => {
  // Parse content into parts: text and code blocks
  const parts = useMemo(() => {
    // Look for bash code blocks specifically
    const bashCodeBlockRegex = /\n([\s\S]*?)/g;
    const result = [];
    let lastIndex = 0;
    let match;

    while ((match = bashCodeBlockRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        // Text before code block
        const textContent = content.substring(lastIndex, match.index);
        if (textContent.trim()) {
          result.push({ type: 'text', content: textContent });
        }
      }
      // Code block content - properly handle the commands
      const codeContent = match[1];
      result.push({ type: 'code', content: codeContent });
      lastIndex = bashCodeBlockRegex.lastIndex;
    }
    
    if (lastIndex < content.length) {
      // Remaining text after last code block
      const remainingContent = content.substring(lastIndex);
      if (remainingContent.trim()) {
        result.push({ type: 'text', content: remainingContent });
      }
    }
    
    // If no bash code blocks found, treat as regular content
    if (result.length === 0) {
      result.push({ type: 'text', content: content });
    }
    
    return result;
  }, [content]);

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      {parts.map((part, idx) => {
        if (part.type === 'text') {
          // Render text as markdown
          const htmlContent = md.render(part.content);
          return (
            <div
              key={idx}
              className="mb-2"
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
        } else if (part.type === 'code') {
          // Render code block with custom UI and proper left alignment
          const commands = part.content
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0);

          return (
            <div key={idx} className="mb-4">
              <div className="mb-2 font-medium text-foreground">Commands</div>
              <div className="relative rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 overflow-hidden">
                <div className="flex items-center justify-between bg-gray-200 dark:bg-gray-800 px-3 py-1.5 border-b border-gray-300 dark:border-gray-600">
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">bash</span>
                  <button 
                    className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 cursor-pointer"
                    onClick={() => navigator.clipboard.writeText(commands.join('\n'))}
                  >
                    copy
                  </button>
                </div>
                <div className="p-4 bg-transparent overflow-x-auto">
                  {commands.map((command, cmdIdx) => (
                    <div key={cmdIdx} className="mb-1 last:mb-0">
                      <code className="font-mono text-sm text-gray-800 dark:text-gray-100 block text-left" style={{ backgroundColor: 'transparent !important' }}>
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

  async streamMessage(message: string, sessionId?: string): Promise<Response> {
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        message,
        session_id: sessionId
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response;
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

// Quick Commands
const QUICK_COMMANDS = [
  {
    category: "Pods",
    commands: [
      { label: "List all pods", command: "Show me all pods in the cluster" },
      { label: "Pod status", command: "Check pod status and health" },
      { label: "Failed pods", command: "Show me failed or problematic pods" },
      { label: "Pod logs", command: "Get logs from pods with issues" }
    ]
  },
  {
    category: "Deployments",
    commands: [
      { label: "List deployments", command: "Show all deployments" },
      { label: "Deployment status", command: "Check deployment health and replica status" },
      { label: "Scale deployment", command: "How do I scale a deployment?" },
      { label: "Rollout status", command: "Check rollout status of deployments" }
    ]
  },
  {
    category: "Services",
    commands: [
      { label: "List services", command: "Show all services in the cluster" },
      { label: "Service endpoints", command: "Check service endpoints and connectivity" },
      { label: "Service troubleshooting", command: "Help troubleshoot service connectivity issues" }
    ]
  },
  {
    category: "Cluster Health",
    commands: [
      { label: "Cluster overview", command: "Give me a cluster health overview" },
      { label: "Node status", command: "Check node health and status" },
      { label: "Resource usage", command: "Show cluster resource usage" },
      { label: "Recent events", command: "Show recent cluster events and warnings" }
    ]
  },
  {
    category: "Troubleshooting",
    commands: [
      { label: "Diagnose issues", command: "Help me diagnose cluster issues" },
      { label: "Common problems", command: "What are common Kubernetes problems and solutions?" },
      { label: "Best practices", command: "Show me Kubernetes best practices" },
      { label: "Performance tips", command: "How can I optimize cluster performance?" }
    ]
  }
];

export default function ChatOpsPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [enableToolResponse, setEnableToolResponse] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [healthStatus, setHealthStatus] = useState<any>(null);

  const { isOpen: isSessionModalOpen, onOpen: onSessionModalOpen, onClose: onSessionModalClose } = useDisclosure();
  const { isOpen: isExportModalOpen, onOpen: onExportModalOpen, onClose: onExportModalClose } = useDisclosure();

  // Load sessions on component mount
  React.useEffect(() => {
    loadSessions();
    checkHealthStatus();
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

  const sendMessage = async (message: string, useStreaming: boolean = true) => {
    if (!message.trim()) return;

    const userMessage: Message = {
      role: 'user',
      content: message,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');

    if (useStreaming) {
      await sendStreamingMessage(message);
    } else {
      await sendRegularMessage(message);
    }
  };

  const sendRegularMessage = async (message: string) => {
    try {
      setIsLoading(true);
      const response = await chatAPI.sendMessage(message, currentSessionId || undefined, enableToolResponse);
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      if (!currentSessionId) {
        setCurrentSessionId(response.session_id);
        await loadSessions(); // Refresh sessions list
      }

      // Show tool information if enabled
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
      addToast({
        title: 'Error',
        description: 'Failed to send message',
        color: 'danger'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const sendStreamingMessage = async (message: string) => {
    try {
      setIsStreaming(true);
      setStreamingMessage('');
      
      const response = await chatAPI.streamMessage(message, currentSessionId || undefined);
      const reader = response.body?.getReader();
      
      if (!reader) {
        throw new Error('No response stream available');
      }

      let fullResponse = '';
      let sessionId = currentSessionId;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data.trim()) {
              try {
                const parsed = JSON.parse(data);
                if (parsed.session_id && !sessionId) {
                  sessionId = parsed.session_id;
                  setCurrentSessionId(sessionId);
                }
              } catch {
                // Regular streaming content
                fullResponse += data;
                setStreamingMessage(fullResponse);
              }
            }
          }
        }
      }

      if (fullResponse) {
        const assistantMessage: Message = {
          role: 'assistant',
          content: fullResponse,
          created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, assistantMessage]);
      }

      if (!currentSessionId && sessionId) {
        await loadSessions(); // Refresh sessions list
      }

    } catch (error) {
      console.error('Failed to stream message:', error);
      addToast({
        title: 'Error',
        description: 'Failed to stream message',
        color: 'danger'
      });
    } finally {
      setIsStreaming(false);
      setStreamingMessage('');
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

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <div className="w-80 border-r border-divider bg-content1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-divider">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-foreground">Chat Sessions</h2>
            <div className="flex gap-2">
              <Button
                isIconOnly
                size="sm"
                variant="light"
                onPress={onExportModalOpen}
                className="text-default-500"
              >
                <Icon icon="solar:download-bold" width={16} />
              </Button>
              <Button
                isIconOnly
                size="sm"
                variant="light"
                onPress={loadSessions}
                isLoading={isLoadingSessions}
                className="text-default-500"
              >
                <Icon icon="solar:refresh-bold" width={16} />
              </Button>
            </div>
          </div>
          
          <Button
            color="primary"
            onPress={() => createNewSession()}
            className="w-full"
            startContent={<Icon icon="solar:add-circle-bold" width={18} />}
          >
            New Chat
          </Button>
        </div>

        {/* Health Status */}
        {healthStatus && (
          <div className="p-4 border-b border-divider">
            <div className="flex items-center gap-2 mb-2">
              <Icon icon="solar:heart-pulse-bold" width={16} />
              <span className="text-sm font-medium">System Status</span>
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span>Overall</span>
                <Chip
                  size="sm"
                  color={healthStatus.status === 'healthy' ? 'success' : 'warning'}
                  variant="flat"
                >
                  {healthStatus.status}
                </Chip>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span>Database</span>
                <Chip
                  size="sm"
                  color={healthStatus.database === 'healthy' ? 'success' : 'danger'}
                  variant="flat"
                >
                  {healthStatus.database}
                </Chip>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span>LLM</span>
                <Chip
                  size="sm"
                  color={healthStatus.llm === 'healthy' ? 'success' : 'danger'}
                  variant="flat"
                >
                  {healthStatus.llm}
                </Chip>
              </div>
            </div>
          </div>
        )}

        {/* Sessions List */}
        <ScrollShadow className="flex-1 p-4">
          <div className="space-y-2">
            {sessions.map((session) => (
              <Card
                key={session.session_id}
                isPressable
                isHoverable
                className={`cursor-pointer transition-all ${
                  currentSessionId === session.session_id
                    ? 'bg-primary-50 border-primary-200 dark:bg-primary-950 dark:border-primary-800'
                    : 'hover:bg-content2'
                }`}
                onPress={() => loadSessionHistory(session.session_id)}
              >
                <CardBody className="p-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate text-foreground">
                        {session.title}
                      </p>
                      <p className="text-xs text-default-500 mt-1">
                        {new Date(session.created_at).toLocaleDateString()}
                      </p>
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
                        >
                          Delete Session
                        </DropdownItem>
                      </DropdownMenu>
                    </Dropdown>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        </ScrollShadow>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        <div className="p-4 border-b border-divider bg-content1">
          <div className="flex items-center gap-3">
            <Icon icon="solar:chat-round-dots-bold" width={24} className="text-primary" />
            <div>
              <h1 className="text-xl font-bold text-foreground">KubeSage Chat</h1>
              <p className="text-sm text-default-500">
                {currentSessionId ? 'Active Session' : 'No active session'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              size="sm"
              isSelected={enableToolResponse}
              onValueChange={setEnableToolResponse}
            >
              <span className="text-sm">Show Tools</span>
            </Switch>
            <Button
              isIconOnly
              size="sm"
              variant="light"
              onPress={onSessionModalOpen}
              className="text-default-500"
            >
              <Icon icon="solar:settings-bold" width={18} />
            </Button>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 flex flex-col">
          <ScrollShadow className="flex-1 p-4">
            {messages.length === 0 && !isStreaming ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <Icon icon="solar:chat-round-dots-bold" width={64} className="text-default-300 mb-4" />
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  Welcome to KubeSage Chat
                </h3>
                <p className="text-default-500 mb-6 max-w-md">
                  Start a conversation about your Kubernetes cluster. Ask questions, get diagnostics, or request help with troubleshooting.
                </p>
                
                {/* Quick Commands */}
                <div className="w-full max-w-4xl">
                  <h4 className="text-sm font-medium text-foreground mb-3">Quick Commands</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {QUICK_COMMANDS.map((category) => (
                      <Card key={category.category} className="p-3">
                        <CardHeader className="pb-2">
                          <h5 className="text-sm font-semibold text-foreground">{category.category}</h5>
                        </CardHeader>
                        <CardBody className="pt-0">
                          <div className="space-y-2">
                            {category.commands.map((cmd, idx) => (
                              <Button
                                key={idx}
                                size="sm"
                                variant="light"
                                className="w-full justify-start text-left h-auto p-2"
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
              <div className="space-y-4 max-w-4xl mx-auto w-full">
                {messages.map((message, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-4 ${
                        message.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-content2 text-foreground'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                          message.role === 'user' ? 'bg-primary-foreground/20' : 'bg-primary/20'
                        }`}>
                          <Icon
                            icon={message.role === 'user' ? 'solar:user-bold' : 'solar:cpu-bolt-bold'}
                            width={16}
                            className={message.role === 'user' ? 'text-primary-foreground' : 'text-primary'}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          {message.role === 'user' ? (
                            <div className="whitespace-pre-wrap break-words">
                              {message.content}
                            </div>
                          ) : (
                            <RenderMessageContent content={message.content} />
                          )}
                          {message.created_at && (
                            <div className="text-xs opacity-70 mt-2">
                              {new Date(message.created_at).toLocaleTimeString()}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}

                {/* Streaming Message */}
                {isStreaming && streamingMessage && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-start"
                  >
                    <div className="max-w-[80%] rounded-lg p-4 bg-content2 text-foreground">
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-primary/20">
                          <Icon icon="solar:cpu-bolt-bold" width={16} className="text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <RenderMessageContent content={streamingMessage} isStreaming={true} />
                          <div className="flex items-center gap-2 mt-2">
                            <Spinner size="sm" />
                            <span className="text-xs text-default-500">Thinking...</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Loading Message */}
                {isLoading && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-start"
                  >
                    <div className="max-w-[80%] rounded-lg p-4 bg-content2 text-foreground">
                      <div className="flex items-center gap-3">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-primary/20">
                          <Spinner size="sm" />
                        </div>
                        <span className="text-sm text-default-500">Processing your request...</span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </div>
            )}
          </ScrollShadow>

          {/* Input Area */}
          <div className="p-4 border-t border-divider bg-content1">
            <div className="max-w-4xl mx-auto">
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <Textarea
                    placeholder="Ask about your Kubernetes cluster..."
                    value={inputMessage}
                    onValueChange={setInputMessage}
                    onKeyDown={handleKeyPress}
                    minRows={1}
                    maxRows={4}
                    className="w-full"
                    disabled={isLoading || isStreaming}
                  />
                </div>
                <Button
                  color="primary"
                  isIconOnly
                  onPress={() => sendMessage(inputMessage)}
                  isDisabled={!inputMessage.trim() || isLoading || isStreaming}
                  isLoading={isLoading || isStreaming}
                  className="h-14"
                >
                  <Icon icon="solar:arrow-up-bold" width={20} />
                </Button>
              </div>
              <div className="flex items-center justify-between mt-2 text-xs text-default-500">
                <div className="flex items-center gap-4">
                  <span>Press <Kbd keys={['enter']}>Enter</Kbd> to send</span>
                  <span>Press <Kbd keys={['shift', 'enter']}>Shift + Enter</Kbd> for new line</span>
                </div>
                <div className="flex items-center gap-2">
                  {currentSessionId && (
                    <Chip size="sm" variant="flat" color="primary">
                      Session Active
                    </Chip>
                  )}
                </div>
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
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-2">Tool Response</h4>
                <Switch
                  isSelected={enableToolResponse}
                  onValueChange={setEnableToolResponse}
                  description="Show detailed information about tools used by the assistant"
                >
                  Enable Tool Response Details
                </Switch>
              </div>
              
              <Divider />
              
              <div>
                <h4 className="text-sm font-medium mb-2">Session Management</h4>
                <div className="space-y-2">
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
              
              <div className="bg-content2 rounded-lg p-3">
                <div className="flex items-center justify-between text-sm">
                  <span>Total Sessions:</span>
                  <span className="font-medium">{sessions.length}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Current Session Messages:</span>
                  <span className="font-medium">{messages.length}</span>
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
              Export
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </div>
  );
}
