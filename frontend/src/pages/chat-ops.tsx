//fizex
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
import '../../styles/chat-ops.css';

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
        <div class="flex items-center justify-between bg-gray-200 dark:bg-gray-800 px-3 py-0.5 border-b border-gray-300 dark:border-gray-600">
          <span class="text-xs font-medium text-gray-600 dark:text-gray-400">bash</span>
          <button class="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 cursor-pointer" onclick="navigator.clipboard.writeText('${escapedCmd.replace(/'/g, "\\'")}')">copy</button>
        </div>
        <pre class="p-0 m-0 bg-transparent overflow-x-auto font-mono text-sm text-gray-800 dark:text-gray-100" 
        style="white-space: pre; word-break: normal; text-align: left;
         padding-top: 0.03rem; padding-bottom: 0.03rem;">
          <code class="text-gray-800 dark:text-gray-100" 
          style="background-color: transparent !important; display: block;
           margin-top:-20px; margin-bottom: -20px;        
            text-align: left;">${escapedCmd}</code>
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
    const bashCodeBlockRegex = /```bash\n([\s\S]*?)```/g;
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
const API_BASE_URL = 'https://10.0.32.105:8003/api/v1';

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
  const [showShellPanel, setShowShellPanel] = React.useState(false);
  const [bottomPanelHeight, setBottomPanelHeight] = React.useState(50);
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
        
        let assistantContent = '';
        let isFirstMessage = true;

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

                    // Update or create the assistant message
                    setMessages(prev => {
                      const newMessages = [...prev];
                      const lastMessage = newMessages[newMessages.length - 1];
                      
                      if (lastMessage && lastMessage.role === 'assistant' && !isFirstMessage) {
  newMessages[newMessages.length - 1] = {
    ...lastMessage,
    content: assistantContent,
  };
} else {
  newMessages.push({
    role: 'assistant',
    content: assistantContent,
    created_at: new Date().toISOString()
  });
  isFirstMessage = false;
}
                      
                      return newMessages;
                    });
                  } else if (data.done) {
  setIsStreaming(false);
  // Final update to last assistant message
  // Yeh line add karo:
  console.log('Final assistantContent:', assistantContent);
  setMessages(prev => {
  const newMessages = [...prev];
  const lastMessage = newMessages[newMessages.length - 1];
  if (lastMessage && lastMessage.role === 'assistant') {
    newMessages[newMessages.length - 1] = {
      ...lastMessage,
      content: assistantContent,
    };
  }
  return newMessages;
});
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

  // Render message content with markdown or plain text during streaming
  // filepath: /home/vaishnavi/new-kubesage/frontend/src/pages/chat-ops.tsx
const renderMessageContent = (content: string, isStreaming: boolean) => {
  // Streaming ke dauraan agar code block open hai toh close kar do (rendering ke liye)
  let safeContent = content;
  const codeBlockOpen = (safeContent.match(/```/g) || []).length % 2 === 1;
  if (isStreaming && codeBlockOpen) {
    safeContent += '\n```';
  }
  return <RenderMessageContent content={safeContent} isStreaming={isStreaming} />;
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
                <h2 className="font-semibold text-foreground">ChatOps</h2>
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
          <ScrollShadow className="flex-1 p-2 bg-content1 dark:bg-content1">
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
                    className={`p-2 sm:p-3 rounded-lg cursor-pointer transition-colors group ${
                      currentSession?.session_id === session.session_id
                        ? 'bg-primary/10 dark:bg-primary/20 border border-primary/20 dark:border-primary/30'
                        : 'hover:bg-content2 dark:hover:bg-content2'
                    }`}
                    onClick={() => switchSession(session)}
                  >
                    <div className="flex items-start justify-between min-w-0">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate text-foreground">{session.title}</p>
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
                            className="opacity-0 group-hover:opacity-100 flex-shrink-0 ml-2"
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
      <div className="flex-1 flex flex-col relative min-w-0 bg-background">
        {/* Chat Header */}
        <div className="p-3 sm:p-4 border-b border-divider bg-content1 dark:bg-content1 shadow-sm dark:shadow-lg flex-shrink-0">
          <div className="flex items-center justify-between min-w-0 gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <Icon icon="lucide:terminal" className="text-primary text-xl flex-shrink-0" />
                <div className="min-w-0">
                  <h1 className="font-semibold text-foreground truncate">
                    {currentSession?.title || 'KubeSage ChatOps'}
                  </h1>
                  <p className="text-xs text-foreground-500 hidden sm:block">
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
                  className="hidden md:flex flex-shrink-0"
                >
                  {healthStatus.status}
                </Chip>
              )}
            </div>
            
            <div className="flex items-center gap-2 flex-shrink-0">
              <Button
                variant="flat"
                size="sm"
                startContent={<Icon icon="lucide:zap" />}
                onPress={() => setShowQuickCommands(!showQuickCommands)}
                className="hidden sm:flex"
              >
                <span className="hidden lg:inline">Quick Commands</span>
              </Button>
              <Button
                variant="flat"
                size="sm"
                isIconOnly
                onPress={() => setShowQuickCommands(!showQuickCommands)}
                className="sm:hidden"
              >
                <Icon icon="lucide:zap" />
              </Button>
              <Switch
                size="sm"
                isSelected={streamingEnabled}
                onValueChange={setStreamingEnabled}
                startContent={<Icon icon="lucide:zap" />}
                endContent={<Icon icon="lucide:message-circle" />}
                className="hidden md:flex"
              >
                <span className="hidden lg:inline">Stream</span>
              </Switch>
              <Button
                variant="flat"
                size="sm"
                color={showShellPanel ? "primary" : "default"}
                startContent={<Icon icon="lucide:chevron-up" />}
                onPress={() => setShowShellPanel(!showShellPanel)}
                className="hidden sm:flex"
              >
                <span className="hidden lg:inline">Shell</span>
              </Button>
              <Button
                variant="flat"
                size="sm"
                color={showShellPanel ? "primary" : "default"}
                isIconOnly
                onPress={() => setShowShellPanel(!showShellPanel)}
                className="sm:hidden"
              >
                <Icon icon="lucide:chevron-up" />
              </Button>
            </div>
          </div>
        </div>

        {/* Quick Commands Overlay Background */}
        <AnimatePresence>
          {showQuickCommands && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.3 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black z-30"
              onClick={() => setShowQuickCommands(false)}
            />
          )}
        </AnimatePresence>

        {/* Quick Commands Panel */}
        <AnimatePresence>
          {showQuickCommands && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="absolute  top-16 sm:top-20 left-0 right-0 z-40 border-b border-divider bg-content1 dark:bg-content1 shadow-lg"
            >
              <div className="flex items-center justify-between p-3  sm:p-4 pb-2 border-b border-divider">
                <div className="flex items-center gap-2 min-w-0">
                  <Icon icon="lucide:zap" className="text-primary flex-shrink-0" />
                  <h3 className="font-semibold text-foreground">Quick Commands</h3>
                  <span className="text-xs text-foreground-500 hidden sm:inline">Click any command to insert</span>
                </div>
                <Button
                  isIconOnly
                  variant="light"
                  size="sm"
                  onPress={() => setShowQuickCommands(false)}
                  className="text-foreground-500 hover:text-foreground flex-shrink-0"
                >
                  <Icon icon="lucide:x" />
                </Button>
              </div>

              <ScrollShadow orientation="horizontal" className="p-3 sm:p-4">
                <div className="flex gap-3 sm:gap-4">
                  {QUICK_COMMANDS.map((category) => (
                    <Card 
                      key={category.category} 
                      className="bg-content2 dark:bg-content2 border border-divider flex-shrink-0"
                      style={{ minWidth: '300px', maxWidth: '180px' }}
                    >
                      <CardHeader className="pb-2">
                        <h4 className="text-sm font-semibold text-foreground">{category.category}</h4>
                      </CardHeader>
                      <CardBody className="pt-0">
                        <div className="space-y-1">
                          {category.commands.map((cmd, index) => (
                            <Button
                              key={index}
                              variant="light"
                              size="sm"
                              className="justify-start h-auto p-2 w-full"
                              onPress={() => insertQuickCommand(cmd.command)}
                            >
                              <div className="text-left w-full">
                                <p className="text-xs font-medium text-foreground">{cmd.label}</p>
                                <Code className="text-xs mt-1 bg-content3 dark:bg-content3">{cmd.command}</Code>
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
        <ScrollShadow className={`flex-1 p-3 sm:p-4 bg-background ${showShellPanel ? 'max-h-[50vh]' : ''} overflow-y-auto`}>
          <div className="max-w-4.5xl mx-auto space-y-4">
            <AnimatePresence>
              {messages.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-8 sm:py-12"
                >
                  <Icon icon="lucide:message-square" className="text-4xl sm:text-6xl text-foreground-300 mx-auto mb-4" />
                  <h3 className="text-lg sm:text-xl font-semibold mb-2 text-foreground">Welcome to KubeSage ChatOps</h3>
                  <p className="text-foreground-500 mb-6 text-sm sm:text-base px-4">
                    Your AI-powered Kubernetes operations assistant. Ask questions, run commands, and manage your cluster.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 max-w-2xl mx-auto px-4">
                    <Card className="p-3 sm:p-4 bg-content1 dark:bg-content1 border border-divider">
                      <div className="flex items-center gap-3">
                        <Icon icon="lucide:search" className="text-primary text-lg sm:text-xl flex-shrink-0" />
                        <div className="text-left min-w-0">
                          <p className="font-medium text-foreground text-sm sm:text-base">Ask Questions</p>
                          <p className="text-xs sm:text-sm text-foreground-500 truncate">
                            "Show me all failing pods"
                          </p>
                        </div>
                      </div>
                    </Card>
                    <Card className="p-3 sm:p-4 bg-content1 dark:bg-content1 border border-divider">
                      <div className="flex items-center gap-3">
                        <Icon icon="lucide:terminal" className="text-primary text-lg sm:text-xl flex-shrink-0" />
                        <div className="text-left min-w-0">
                          <p className="font-medium text-foreground text-sm sm:text-base">Run Commands</p>
                          <p className="text-xs sm:text-sm text-foreground-500 truncate">
                            "kubectl get pods -n production"
                          </p>
                        </div>
                      </div>
                    </Card>
                    <Card className="p-3 sm:p-4 bg-content1 dark:bg-content1 border border-divider">
                      <div className="flex items-center gap-3">
                        <Icon icon="lucide:wrench" className="text-primary text-lg sm:text-xl flex-shrink-0" />
                        <div className="text-left min-w-0">
                          <p className="font-medium text-foreground text-sm sm:text-base">Troubleshoot</p>
                          <p className="text-xs sm:text-sm text-foreground-500 truncate">
                            "Why is my deployment failing?"
                          </p>
                        </div>
                      </div>
                    </Card>
                    <Card className="p-3 sm:p-4 bg-content1 dark:bg-content1 border border-divider">
                      <div className="flex items-center gap-3">
                        <Icon icon="lucide:scale" className="text-primary text-lg sm:text-xl flex-shrink-0" />
                        <div className="text-left min-w-0">
                          <p className="font-medium text-foreground text-sm sm:text-base">Scale Resources</p>
                          <p className="text-xs sm:text-sm text-foreground-500 truncate">
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
                    <div className={`max-w-[85%] sm:max-w-[80%] ${message.role === 'user' ? 'order-2' : 'order-1'}`}>
                      <Card className={`${
                        message.role === 'user' 
                          ? 'bg-primary text-primary-foreground border border-primary/20' 
                          : 'bg-content1 dark:bg-content1 border border-divider'
                      } shadow-sm`}>
                        <CardBody className="p-3 sm:p-4">
                          <div className="flex items-start gap-3">
                            <div className={`p-2 rounded-full flex-shrink-0 ${
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
                                <p className="whitespace-pre-wrap break-words text-sm sm:text-base">{message.content}</p>
                              ) : (
                                renderMessageContent(message.content, isStreaming && index === messages.length - 1)
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
            {(isStreaming || (isLoading && !isStreaming)) && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <Card className="bg-content1 dark:bg-content1 border border-divider shadow-sm">
                  <CardBody className="p-3 sm:p-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-full bg-primary/20 flex-shrink-0">
                        <Icon icon="lucide:bot" className="text-sm text-primary" />
                      </div>
                      <div className="flex items-center gap-2 min-w-0">
                        <Spinner size="sm" />
                        <span className="text-sm text-foreground">KubeSage is thinking...</span>
                        {isStreaming && (
                          <Button
                            size="sm"
                            variant="flat"
                            color="danger"
                            onPress={stopStreaming}
                            className="flex-shrink-0"
                          >
                            Stop
                          </Button>
                        )}
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
        <div className="p-3 sm:p-4 border-t border-divider bg-content1 dark:bg-content1 shadow-sm dark:shadow-lg flex-shrink-0">
          <div className="max-w-4.5xl mx-auto">
            <div className="flex gap-2 sm:gap-3">
              <div className="flex-1 min-w-0">
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
                    input: "resize-none text-sm sm:text-base",
                    inputWrapper: "bg-content2 dark:bg-content2 border-divider"
                  }}
                  endContent={
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <Kbd keys={["enter"]} className="hidden sm:inline-flex">Send</Kbd>
                      <Kbd keys={["shift", "enter"]} className="hidden lg:inline-flex">New line</Kbd>
                    </div>
                  }
                />
              </div>
              <div className="flex flex-col gap-2 flex-shrink-0">
                <Button
                  color="primary"
                  isDisabled={!inputMessage.trim() || isLoading}
                  isLoading={isLoading}
                  onPress={sendMessage}
                  className="h-12 sm:h-14 px-3 sm:px-4"
                  size="lg"
                >
                  <Icon icon="lucide:send" className="text-lg" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Panel - Shell Terminal */}
      <AnimatePresence>
        {showShellPanel && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: `${bottomPanelHeight}vh`, opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="absolute bottom-0 left-0 right-0 flex flex-col bg-content1 dark:bg-content1 border-t border-divider overflow-hidden z-50 shadow-lg dark:shadow-2xl"
          >
            {/* Bottom Panel Header */}
            <div className="p-3 sm:p-4 border-b border-divider bg-content1 dark:bg-content1 flex-shrink-0">
              <div className="flex items-center justify-between min-w-0 gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <Icon icon="lucide:terminal" className="text-primary flex-shrink-0" />
                  <div className="min-w-0">
                    <h3 className="font-semibold text-foreground">Shell Terminal</h3>
                    <p className="text-xs text-foreground-500 hidden sm:block">
                      Execute kubectl commands directly
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <Button
                    variant="flat"
                    size="sm"
                    startContent={<Icon icon="lucide:maximize-2" />}
                    onPress={() => setBottomPanelHeight(80)}
                    className="hidden sm:flex"
                  >
                    Maximize
                  </Button>
                  <Button
                    variant="flat"
                    size="sm"
                    startContent={<Icon icon="lucide:minimize-2" />}
                    onPress={() => setBottomPanelHeight(30)}
                    className="hidden sm:flex"
                  >
                    Minimize
                  </Button>
                  <Button
                    variant="flat"
                    size="sm"
                    color="danger"
                    isIconOnly
                    onPress={() => setShowShellPanel(false)}
                  >
                    <Icon icon="lucide:x" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Command Input */}
            <div className="p-3 sm:p-4 border-b border-divider bg-content1 dark:bg-content1 flex-shrink-0">
              <div className="flex gap-2">
                <Input
                  placeholder="kubectl command..."
                  value={commandInput}
                  onValueChange={setCommandInput}
                  onKeyDown={handleCommandKeyDown}
                  variant="bordered"
                  size="sm"
                  startContent={<span className="text-xs text-foreground-500 flex-shrink-0">kubectl</span>}
                  className="flex-1 min-w-0"
                  classNames={{
                    inputWrapper: "bg-content2 dark:bg-content2 border-divider"
                  }}
                />
                <Button
                  color="primary"
                  size="sm"
                  isDisabled={!commandInput.trim() || isExecuting}
                  isLoading={isExecuting}
                  onPress={executeCommand}
                  className="flex-shrink-0"
                >
                  <Icon icon="lucide:play" />
                  <span className="hidden sm:inline ml-1">Run</span>
                </Button>
                <Button
                  variant="flat"
                  size="sm"
                  onPress={() => setExecuteResults([])}
                  className="flex-shrink-0"
                >
                  <Icon icon="lucide:trash-2" />
                  <span className="hidden sm:inline ml-1">Clear</span>
                </Button>
              </div>
            </div>

            {/* Command Results */}
            <ScrollShadow className="flex-1 p-3 sm:p-4 bg-background overflow-y-auto">
              <div className="space-y-3">
                {executeResults.length === 0 ? (
                  <div className="text-center py-6 sm:py-8">
                    <Icon icon="lucide:terminal" className="text-3xl sm:text-4xl text-foreground-300 mx-auto mb-2" />
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
                      <Card className="bg-content1 dark:bg-content1 border border-divider shadow-sm">
                        <CardHeader className="pb-2">
                          <div className="flex items-center justify-between w-full min-w-0 gap-3">
                            <div className="flex items-center gap-2 min-w-0">
                              <Chip
                                size="sm"
                                color={result.status === 'success' ? 'success' : 'danger'}
                                variant="flat"
                                className="flex-shrink-0"
                              >
                                {result.status}
                              </Chip>
                              <span className="text-xs text-foreground-500 truncate">
                                {new Date(result.timestamp).toLocaleTimeString()}
                              </span>
                            </div>
                            {result.execution_time && (
                              <span className="text-xs text-foreground-500 flex-shrink-0">
                                {result.execution_time}ms
                              </span>
                            )}
                          </div>
                        </CardHeader>
                        <CardBody className="pt-0">
                          <Code className="text-xs mb-2 block bg-content2 dark:bg-content2 p-2 rounded overflow-x-auto">
                            {result.command}
                          </Code>
                          {result.output && (
                            <pre className="text-xs bg-content3 dark:bg-content3 p-2 rounded overflow-x-auto whitespace-pre-wrap break-words text-foreground">
                              {result.output}
                            </pre>
                          )}
                          {result.error && (
                            <pre className="text-xs bg-danger/10 dark:bg-danger/20 text-danger p-2 rounded overflow-x-auto whitespace-pre-wrap break-words border border-danger/20">
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
        )}
      </AnimatePresence>

      {/* New Session Modal */}
      <Modal 
        isOpen={isNewSessionOpen} 
        onClose={onNewSessionClose}
        size="md"
        classNames={{
          base: "mx-4",
          backdrop: "bg-black/50",
          wrapper: "items-center justify-center",
          body: "bg-content1 dark:bg-content1",
          header: "bg-content1 dark:bg-content1 border-b border-divider",
          footer: "bg-content1 dark:bg-content1 border-t border-divider"
        }}
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="text-foreground">Create New Chat Session</ModalHeader>
              <ModalBody>
                <Input
                  label="Session Title"
                  placeholder="e.g., Production Troubleshooting"
                  variant="bordered"
                  classNames={{
                    inputWrapper: "bg-content2 dark:bg-content2 border-divider"
                  }}
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
      <Modal 
        isOpen={isSettingsOpen} 
        onClose={onSettingsClose}
        size="lg"
        scrollBehavior="inside"
        classNames={{
          base: "mx-4",
          backdrop: "bg-black/50",
          wrapper: "items-center justify-center",
          body: "bg-content1 dark:bg-content1",
          header: "bg-content1 dark:bg-content1 border-b border-divider",
          footer: "bg-content1 dark:bg-content1 border-t border-divider"
        }}
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="text-foreground">ChatOps Settings</ModalHeader>
              <ModalBody>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-foreground">Streaming Responses</p>
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
                    <p className="font-medium mb-2 text-foreground">Quick Commands</p>
                    <p className="text-sm text-foreground-500 mb-3">
                      Manage your frequently used kubectl commands
                    </p>
                    <Button variant="flat" size="sm" className="bg-content2 dark:bg-content2">
                      Customize Commands
                    </Button>
                  </div>
                  
                  <Divider />
                  
                  <div>
                    <p className="font-medium mb-2 text-foreground">Export/Import</p>
                    <p className="text-sm text-foreground-500 mb-3">
                      Backup your chat sessions and settings
                    </p>
                    <div className="flex gap-2">
                      <Button 
                        variant="flat" 
                        size="sm" 
                        className="bg-content2 dark:bg-content2"
                        onPress={() => exportSessions(sessions, messages)}
                      >
                        Export Sessions
                      </Button>
                      <Button variant="flat" size="sm" className="bg-content2 dark:bg-content2">
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
      <Modal 
        isOpen={isHealthOpen} 
        onClose={onHealthClose}
        size="2xl"
        scrollBehavior="inside"
        classNames={{
          base: "mx-4",
          backdrop: "bg-black/50",
          wrapper: "items-center justify-center",
          body: "bg-content1 dark:bg-content1",
          header: "bg-content1 dark:bg-content1 border-b border-divider",
          footer: "bg-content1 dark:bg-content1 border-t border-divider"
        }}
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="text-foreground">System Health Status</ModalHeader>
              <ModalBody>
                {healthStatus ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-foreground">Overall Status</span>
                      <Chip
                        color={getStatusColor(healthStatus.status)}
                        variant="flat"
                      >
                        {healthStatus.status}
                      </Chip>
                    </div>
                    
                    <Divider />
                    
                    <div className="space-y-3">
                      <h4 className="font-medium text-foreground">Components</h4>
                      
                      {healthStatus.components && (
                        <>
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-foreground">Database</span>
                            <Chip
                              size="sm"
                              color={healthStatus.components.database === 'connected' ? 'success' : 'danger'}
                              variant="flat"
                            >
                              {healthStatus.components.database}
                            </Chip>
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-foreground">LLM Service</span>
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
                                <span className="text-sm text-foreground">Kubernetes Client</span>
                                <Chip
                                  size="sm"
                                  color={healthStatus.components.kubernetes.client_available ? 'success' : 'danger'}
                                  variant="flat"
                                >
                                  {healthStatus.components.kubernetes.client_available ? 'Available' : 'Unavailable'}
                                </Chip>
                              </div>
                              
                              <div className="flex items-center justify-between">
                                <span className="text-sm text-foreground">Cluster Access</span>
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
                                  <span className="text-sm text-foreground">Cluster Version</span>
                                  <Code size="sm" className="bg-content2 dark:bg-content2">{healthStatus.components.kubernetes.cluster_version}</Code>
                                </div>
                              )}
                              
                              <div className="flex items-center justify-between">
                                <span className="text-sm text-foreground">Nodes</span>
                                <span className="text-sm text-foreground">{healthStatus.components.kubernetes.node_count}</span>
                              </div>
                              
                              <div className="flex items-center justify-between">
                                <span className="text-sm text-foreground">Namespaces</span>
                                <span className="text-sm text-foreground">{healthStatus.components.kubernetes.namespace_count}</span>
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
                          <h4 className="font-medium mb-2 text-foreground">Capabilities</h4>
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
                              <div key={index} className="p-2 bg-danger/10 dark:bg-danger/20 rounded text-sm text-danger border border-danger/20">
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
                <Button variant="flat" onPress={loadHealthStatus} className="bg-content2 dark:bg-content2">
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