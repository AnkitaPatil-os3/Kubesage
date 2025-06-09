import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    Card,
    CardBody,
    CardHeader,
    Button,
    Input,
    Textarea,
    Spinner,
    Chip,
    Avatar,
    Divider,
    Modal,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    useDisclosure,
    Tabs,
    Tab,
    ScrollShadow,
    Tooltip,
    Badge,
    Select,
    SelectItem,
    Switch,
    Code,
    Snippet,
    Pagination,
    Kbd,
    Dropdown,
    DropdownTrigger,
    DropdownMenu,
    DropdownItem,
} from '@heroui/react';
import { Icon } from '@iconify/react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

// Initialize markdown parser
const md = new MarkdownIt({
    highlight: function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(str, { language: lang }).value;
            } catch (__) {}
        }
        return '';
    }
});

// Types and Interfaces
interface Message {
    role: 'user' | 'assistant' | 'system';
    content: string;
    session_id?: string;
    created_at?: string;
    id?: string;
}

interface ChatSession {
    id: number;
    session_id: string;
    title: string;
    created_at: string;
    updated_at: string;
    is_active: boolean;
}

interface ChatHistoryEntry {
    role: string;
    content: string;
    created_at: string;
}

interface ChatHistoryResponse {
    session_id: string;
    title: string;
    messages: ChatHistoryEntry[];
    created_at: string;
    updated_at: string;
}

interface MessageResponse {
    role: string;
    content: string;
    session_id: string;
    created_at: string;
}

interface ChatSessionList {
    sessions: ChatSession[];
}

interface StreamingToken {
    token?: string;
    done: boolean;
    session_id?: string;
    error?: string;
}

// API Configuration
const API_BASE_URL = 'https://10.0.32.123:8004/api/v1';

// Helper function to get auth headers
const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
};

const chatAPI = {
    // Main chat endpoint
    sendMessage: async (message: string, sessionId?: string, stream: boolean = false): Promise<MessageResponse> => {
        const response = await axios.post(`${API_BASE_URL}/chat`, {
            message,
            session_id: sessionId,
            stream
        }, {
            headers: getAuthHeaders()
        });
        return response.data;
    },

    // Stream chat message
    streamMessage: async function* (message: string, sessionId?: string): AsyncGenerator<StreamingToken> {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Accept': 'text/event-stream',
            },
            body: JSON.stringify({
                message,
                session_id: sessionId,
                stream: true
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
            throw new Error('No reader available');
        }

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
                            yield data as StreamingToken;
                            if (data.done) return;
                        } catch (e) {
                            console.error('Error parsing streaming data:', e);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    },

    // List chat sessions
    listSessions: async (skip: number = 0, limit: number = 50, includeInactive: boolean = false): Promise<ChatSessionList> => {
        const response = await axios.get(`${API_BASE_URL}/sessions`, {
            params: { skip, limit, include_inactive: includeInactive },
            headers: getAuthHeaders()
        });
        return response.data;
    },

    // Create chat session
    createSession: async (title: string = 'New Chat'): Promise<ChatSession> => {
        const response = await axios.post(`${API_BASE_URL}/sessions`, {
            title
        }, {
            headers: getAuthHeaders()
        });
        return response.data;
    },

    // Update chat session
    updateSession: async (sessionId: string, title?: string, isActive?: boolean): Promise<ChatSession> => {
        const updateData: any = {};
        if (title !== undefined) updateData.title = title;
        if (isActive !== undefined) updateData.is_active = isActive;

        const response = await axios.put(`${API_BASE_URL}/sessions/${sessionId}`, updateData, {
            headers: getAuthHeaders()
        });
        return response.data;
    },

    // Delete chat session
    deleteSession: async (sessionId: string): Promise<void> => {
        await axios.delete(`${API_BASE_URL}/sessions/${sessionId}`, {
            headers: getAuthHeaders()
        });
    },

    // Get session history
    getSessionHistory: async (sessionId: string, limit?: number): Promise<ChatHistoryResponse> => {
        const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}/history`, {
            params: limit ? { limit } : {},
            headers: getAuthHeaders()
        });
        return response.data;
    },

    // Clear session messages
    clearSessionMessages: async (sessionId: string): Promise<void> => {
        await axios.delete(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
            headers: getAuthHeaders()
        });
    },

    // Generate session title
    generateSessionTitle: async (sessionId: string): Promise<{ title: string; session_id: string }> => {
        const response = await axios.post(`${API_BASE_URL}/sessions/${sessionId}/title`, {}, {
            headers: getAuthHeaders()
        });
        return response.data;
    },

    // Health check
    healthCheck: async () => {
        const response = await axios.get(`${API_BASE_URL}/health`, {
            headers: getAuthHeaders()
        });
        return response.data;
    },

    // Debug endpoints
    debugSchema: async () => {
        const response = await axios.get(`${API_BASE_URL}/debug/schema`, {
            headers: getAuthHeaders()
        });
        return response.data;
    },

    debugTestLLM: async () => {
        const response = await axios.get(`${API_BASE_URL}/debug/test-llm`, {
            headers: getAuthHeaders()
        });
        return response.data;
    }
};

export const ChatOps: React.FC = () => {
    // State Management
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamingMessage, setStreamingMessage] = useState('');
    const [selectedTab, setSelectedTab] = useState('chat');
    const [error, setError] = useState<string | null>(null);
    const [isTyping, setIsTyping] = useState(false);
    
    // Session Management
    const [sessionTitle, setSessionTitle] = useState('');
    const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
    const [showInactiveSessions, setShowInactiveSessions] = useState(false);
    
    // Pagination
    const [currentPage, setCurrentPage] = useState(1);
    const [sessionsPerPage] = useState(10);
    
    // Modals
    const { isOpen: isSessionModalOpen, onOpen: onSessionModalOpen, onClose: onSessionModalClose } = useDisclosure();
    const { isOpen: isDebugModalOpen, onOpen: onDebugModalOpen, onClose: onDebugModalClose } = useDisclosure();
    const { isOpen: isHealthModalOpen, onOpen: onHealthModalOpen, onClose: onHealthModalClose } = useDisclosure();
    
    // Debug and Health Data
    const [debugInfo, setDebugInfo] = useState<any>(null);
    const [healthData, setHealthData] = useState<any>(null);
    
    // Refs
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    
    // Settings
    const [streamingEnabled, setStreamingEnabled] = useState(true);
    const [autoScroll, setAutoScroll] = useState(true);
    const [showTimestamps, setShowTimestamps] = useState(false);

    // Check if user is authenticated
    const checkAuth = useCallback(() => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            setError('Authentication required. Please login again.');
            return false;
        }
        return true;
    }, []);

    // Scroll to bottom
    const scrollToBottom = useCallback(() => {
        if (autoScroll && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [autoScroll]);

    // Load sessions
    const loadSessions = useCallback(async () => {
        if (!checkAuth()) return;
        
        try {
            const response = await chatAPI.listSessions(0, 100, showInactiveSessions);
            setSessions(response.sessions || []);
        } catch (error: any) {
            console.error('Error loading sessions:', error);
            if (error.response?.status === 401) {
                setError('Authentication expired. Please login again.');
            } else {
                setError('Failed to load chat sessions');
            }
        }
    }, [showInactiveSessions, checkAuth]);

    // Load chat history
    const loadChatHistory = useCallback(async (sessionId: string) => {
        if (!checkAuth()) return;
        
        try {
            setIsLoading(true);
            const response = await chatAPI.getSessionHistory(sessionId);
            const formattedMessages: Message[] = response.messages.map((msg: ChatHistoryEntry) => ({
                role: msg.role as 'user' | 'assistant',
                content: msg.content,
                created_at: msg.created_at,
                session_id: sessionId
            }));
            setMessages(formattedMessages);
        } catch (error: any) {
            console.error('Error loading chat history:', error);
            if (error.response?.status === 401) {
                setError('Authentication expired. Please login again.');
            } else {
                setError('Failed to load chat history');
            }
        } finally {
            setIsLoading(false);
        }
    }, [checkAuth]);

    // Create new session
    const createNewSession = useCallback(async (title?: string) => {
        if (!checkAuth()) return null;
        
        try {
            const response = await chatAPI.createSession(title);
            setCurrentSessionId(response.session_id);
            setMessages([]);
            await loadSessions();
            return response.session_id;
        } catch (error: any) {
            console.error('Error creating session:', error);
            if (error.response?.status === 401) {
                setError('Authentication expired. Please login again.');
            } else {
                setError('Failed to create new session');
            }
            return null;
        }
    }, [loadSessions, checkAuth]);

    // Send message with streaming
    const sendMessageWithStreaming = useCallback(async (content: string, sessionId?: string) => {
        if (!content.trim() || !checkAuth()) return;

        const userMessage: Message = {
            role: 'user',
            content: content.trim(),
            created_at: new Date().toISOString(),
            session_id: sessionId || currentSessionId || undefined
        };

        setMessages(prev => [...prev, userMessage]);
        setInputMessage('');
        setIsStreaming(true);
        setStreamingMessage('');
        setIsTyping(true);

        try {
            if (streamingEnabled) {
                // Use streaming API
                let fullResponse = '';
                let responseSessionId = sessionId || currentSessionId;

                for await (const chunk of chatAPI.streamMessage(content, sessionId || currentSessionId || undefined)) {
                    if (chunk.token) {
                        fullResponse += chunk.token;
                        setStreamingMessage(fullResponse);
                    }
                    
                    if (chunk.session_id && !currentSessionId) {
                        responseSessionId = chunk.session_id;
                        setCurrentSessionId(chunk.session_id);
                    }
                    
                    if (chunk.error) {
                        setError(chunk.error);
                        setIsStreaming(false);
                        setIsTyping(false);
                        return;
                    }
                    
                    if (chunk.done) {
                        setIsStreaming(false);
                        setIsTyping(false);
                        
                        // Add the complete message to the messages array
                        const assistantMessage: Message = {
                            role: 'assistant',
                            content: fullResponse,
                            created_at: new Date().toISOString(),
                            session_id: responseSessionId || undefined
                        };
                        setMessages(prev => [...prev, assistantMessage]);
                        setStreamingMessage('');
                        
                        // Reload sessions to update the session list
                        await loadSessions();
                        break;
                    }
                }
            } else {
                // Use regular API
                const response = await chatAPI.sendMessage(content, sessionId || currentSessionId || undefined, false);
                
                const assistantMessage: Message = {
                    role: 'assistant',
                    content: response.content,
                    created_at: response.created_at,
                    session_id: response.session_id
                };
                setMessages(prev => [...prev, assistantMessage]);
                
                if (response.session_id && !currentSessionId) {
                    setCurrentSessionId(response.session_id);
                }
                
                // Reload sessions to update the session list
                await loadSessions();
            }
        } catch (error: any) {
          console.error('Error sending message:', error);
          setError('Failed to send message. Please try again.');
          if (error.response?.status === 401) {
              setError('Authentication expired. Please login again.');
          }
      } finally {
          setIsStreaming(false);
          setIsTyping(false);
      }
  }, [currentSessionId, streamingEnabled, loadSessions, checkAuth]);

  // Handle message submit
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
      e.preventDefault();
      if (!inputMessage.trim() || isLoading || isStreaming) return;

      let sessionId = currentSessionId;
      
      // Create new session if none exists
      if (!sessionId) {
          sessionId = await createNewSession();
          if (!sessionId) return;
      }

      await sendMessageWithStreaming(inputMessage, sessionId);
  }, [inputMessage, isLoading, isStreaming, currentSessionId, createNewSession, sendMessageWithStreaming]);

  // Switch session
  const switchSession = useCallback(async (sessionId: string) => {
      setCurrentSessionId(sessionId);
      setMessages([]);
      setError(null);
      await loadChatHistory(sessionId);
  }, [loadChatHistory]);

  // Delete session
  const deleteSession = useCallback(async (sessionId: string) => {
      if (!checkAuth()) return;
      
      try {
          await chatAPI.deleteSession(sessionId);
          if (currentSessionId === sessionId) {
              setCurrentSessionId(null);
              setMessages([]);
          }
          await loadSessions();
      } catch (error: any) {
          console.error('Error deleting session:', error);
          setError('Failed to delete session');
      }
  }, [currentSessionId, loadSessions, checkAuth]);

  // Update session title
  const updateSessionTitle = useCallback(async (sessionId: string, newTitle: string) => {
      if (!checkAuth()) return;
      
      try {
          await chatAPI.updateSession(sessionId, newTitle);
          await loadSessions();
          setEditingSessionId(null);
      } catch (error: any) {
          console.error('Error updating session title:', error);
          setError('Failed to update session title');
      }
  }, [loadSessions, checkAuth]);

  // Generate session title
  const generateTitle = useCallback(async (sessionId: string) => {
      if (!checkAuth()) return;
      
      try {
          const response = await chatAPI.generateSessionTitle(sessionId);
          await loadSessions();
      } catch (error: any) {
          console.error('Error generating title:', error);
          setError('Failed to generate title');
      }
  }, [loadSessions, checkAuth]);

  // Clear session messages
  const clearSession = useCallback(async (sessionId: string) => {
      if (!checkAuth()) return;
      
      try {
          await chatAPI.clearSessionMessages(sessionId);
          if (currentSessionId === sessionId) {
              setMessages([]);
          }
          await loadSessions();
      } catch (error: any) {
          console.error('Error clearing session:', error);
          setError('Failed to clear session');
      }
  }, [currentSessionId, loadSessions, checkAuth]);

  // Health check
  const performHealthCheck = useCallback(async () => {
      if (!checkAuth()) return;
      
      try {
          const health = await chatAPI.healthCheck();
          setHealthData(health);
          onHealthModalOpen();
      } catch (error: any) {
          console.error('Health check failed:', error);
          setError('Health check failed');
      }
  }, [onHealthModalOpen, checkAuth]);

  // Debug info
  const getDebugInfo = useCallback(async () => {
      if (!checkAuth()) return;
      
      try {
          const [schema, llmTest] = await Promise.all([
              chatAPI.debugSchema(),
              chatAPI.debugTestLLM()
          ]);
          setDebugInfo({ schema, llmTest });
          onDebugModalOpen();
      } catch (error: any) {
          console.error('Debug info failed:', error);
          setError('Failed to get debug information');
      }
  }, [onDebugModalOpen, checkAuth]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleSubmit(e as any);
      }
  }, [handleSubmit]);

  // Copy message to clipboard
  const copyToClipboard = useCallback(async (text: string) => {
      try {
          await navigator.clipboard.writeText(text);
      } catch (error) {
          console.error('Failed to copy to clipboard:', error);
      }
  }, []);

  // Format timestamp
  const formatTimestamp = useCallback((timestamp: string) => {
      return new Date(timestamp).toLocaleString();
  }, []);

  // Render message content with markdown
  const renderMessageContent = useCallback((content: string) => {
      const htmlContent = md.render(content);
      return <div dangerouslySetInnerHTML={{ __html: htmlContent }} className="prose prose-sm max-w-none dark:prose-invert" />;
  }, []);

  // Effects
  useEffect(() => {
      if (checkAuth()) {
          loadSessions();
      }
  }, [loadSessions, checkAuth]);

  useEffect(() => {
      scrollToBottom();
  }, [messages, streamingMessage, scrollToBottom]);

  // Pagination for sessions
  const indexOfLastSession = currentPage * sessionsPerPage;
  const indexOfFirstSession = indexOfLastSession - sessionsPerPage;
  const currentSessions = sessions.slice(indexOfFirstSession, indexOfLastSession);
  const totalPages = Math.ceil(sessions.length / sessionsPerPage);

  return (
      <div className="flex h-screen bg-background">
          {/* Sidebar */}
          <div className="w-80 border-r border-divider flex flex-col">
              {/* Header */}
              <div className="p-4 border-b border-divider">
                  <div className="flex items-center justify-between mb-4">
                      <h2 className="text-xl font-bold flex items-center gap-2">
                          <Icon icon="mdi:robot" className="text-primary" />
                          KubeSage Chat
                      </h2>
                      <div className="flex gap-1">
                          <Tooltip content="Health Check">
                              <Button
                                  isIconOnly
                                  size="sm"
                                  variant="light"
                                  onPress={performHealthCheck}
                              >
                                  <Icon icon="mdi:heart-pulse" />
                              </Button>
                          </Tooltip>
                          <Tooltip content="Debug Info">
                              <Button
                                  isIconOnly
                                  size="sm"
                                  variant="light"
                                  onPress={getDebugInfo}
                              >
                                  <Icon icon="mdi:bug" />
                              </Button>
                          </Tooltip>
                      </div>
                  </div>
                  
                  <Button
                      color="primary"
                      variant="flat"
                      onPress={() => createNewSession()}
                      className="w-full"
                      startContent={<Icon icon="mdi:plus" />}
                  >
                      New Chat
                  </Button>
              </div>

              {/* Session Controls */}
              <div className="p-4 border-b border-divider">
                  <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Chat Sessions</span>
                      <Switch
                          size="sm"
                          isSelected={showInactiveSessions}
                          onValueChange={setShowInactiveSessions}
                      >
                          Show Inactive
                      </Switch>
                  </div>
                  
                  {sessions.length > sessionsPerPage && (
                      <Pagination
                          total={totalPages}
                          page={currentPage}
                          onChange={setCurrentPage}
                          size="sm"
                          showControls
                          className="justify-center"
                      />
                  )}
              </div>

              {/* Sessions List */}
              <ScrollShadow className="flex-1 p-2">
                  <div className="space-y-2">
                      {currentSessions.map((session) => (
                          <motion.div
                              key={session.session_id}
                              initial={{ opacity: 0, y: 20 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -20 }}
                          >
                              <Card
                                  isPressable
                                  className={`cursor-pointer transition-colors ${
                                      currentSessionId === session.session_id
                                          ? 'bg-primary/10 border-primary'
                                          : 'hover:bg-default-100'
                                  }`}
                                  onPress={() => switchSession(session.session_id)}
                              >
                                  <CardBody className="p-3">
                                      <div className="flex items-start justify-between">
                                          <div className="flex-1 min-w-0">
                                              {editingSessionId === session.session_id ? (
                                                  <Input
                                                      size="sm"
                                                      value={sessionTitle}
                                                      onChange={(e) => setSessionTitle(e.target.value)}
                                                      onBlur={() => {
                                                          updateSessionTitle(session.session_id, sessionTitle);
                                                      }}
                                                      onKeyDown={(e) => {
                                                          if (e.key === 'Enter') {
                                                              updateSessionTitle(session.session_id, sessionTitle);
                                                          }
                                                      }}
                                                      autoFocus
                                                  />
                                              ) : (
                                                  <div>
                                                      <p className="text-sm font-medium truncate">
                                                          {session.title}
                                                      </p>
                                                      <p className="text-xs text-default-500">
                                                          {formatTimestamp(session.updated_at)}
                                                      </p>
                                                  </div>
                                              )}
                                          </div>
                                          
                                          <div className="flex items-center gap-1 ml-2">
                                              {!session.is_active && (
                                                  <Chip size="sm" color="warning" variant="flat">
                                                      Inactive
                                                  </Chip>
                                              )}
                                              
                                              <Dropdown>
                                                  <DropdownTrigger>
                                                      <Button
                                                          isIconOnly
                                                          size="sm"
                                                          variant="light"
                                                      >
                                                          <Icon icon="mdi:dots-vertical" />
                                                      </Button>
                                                  </DropdownTrigger>
                                                  <DropdownMenu>
                                                      <DropdownItem
                                                          key="edit"
                                                          startContent={<Icon icon="mdi:pencil" />}
                                                          onPress={() => {
                                                              setEditingSessionId(session.session_id);
                                                              setSessionTitle(session.title);
                                                          }}
                                                      >
                                                          Edit Title
                                                      </DropdownItem>
                                                      <DropdownItem
                                                          key="generate"
                                                          startContent={<Icon icon="mdi:auto-fix" />}
                                                          onPress={() => generateTitle(session.session_id)}
                                                      >
                                                          Generate Title
                                                      </DropdownItem>
                                                      <DropdownItem
                                                          key="clear"
                                                          startContent={<Icon icon="mdi:broom" />}
                                                          onPress={() => clearSession(session.session_id)}
                                                      >
                                                          Clear Messages
                                                      </DropdownItem>
                                                      <DropdownItem
                                                          key="delete"
                                                          className="text-danger"
                                                          color="danger"
                                                          startContent={<Icon icon="mdi:delete" />}
                                                          onPress={() => deleteSession(session.session_id)}
                                                      >
                                                          Delete Session
                                                      </DropdownItem>
                                                  </DropdownMenu>
                                              </Dropdown>
                                          </div>
                                      </div>
                                  </CardBody>
                              </Card>
                          </motion.div>
                      ))}
                  </div>
              </ScrollShadow>

              {/* Settings */}
              <div className="p-4 border-t border-divider">
                  <div className="space-y-3">
                      <div className="flex items-center justify-between">
                          <span className="text-sm">Streaming</span>
                          <Switch
                              size="sm"
                              isSelected={streamingEnabled}
                              onValueChange={setStreamingEnabled}
                          />
                      </div>
                      <div className="flex items-center justify-between">
                          <span className="text-sm">Auto Scroll</span>
                          <Switch
                              size="sm"
                              isSelected={autoScroll}
                              onValueChange={setAutoScroll}
                          />
                      </div>
                      <div className="flex items-center justify-between">
                          <span className="text-sm">Timestamps</span>
                          <Switch
                              size="sm"
                              isSelected={showTimestamps}
                              onValueChange={setShowTimestamps}
                          />
                      </div>
                  </div>
              </div>
          </div>

          {/* Main Chat Area */}
          <div className="flex-1 flex flex-col">
              {/* Chat Header */}
              <div className="p-4 border-b border-divider bg-background/60 backdrop-blur">
                  <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                          <Avatar
                              icon={<Icon icon="mdi:kubernetes" />}
                              className="bg-primary/10 text-primary"
                          />
                          <div>
                              <h3 className="font-semibold">
                                  {currentSessionId 
                                      ? sessions.find(s => s.session_id === currentSessionId)?.title || 'Chat Session'
                                      : 'New Chat'
                                  }
                              </h3>
                              <p className="text-sm text-default-500">
                                  Kubernetes AI Assistant
                              </p>
                          </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                          {isStreaming && (
                              <Chip
                                  color="primary"
                                  variant="flat"
                                  startContent={<Spinner size="sm" />}
                              >
                                  Streaming...
                              </Chip>
                          )}
                          
                          {error && (
                              <Chip
                                  color="danger"
                                  variant="flat"
                                  startContent={<Icon icon="mdi:alert" />}
                                  onClose={() => setError(null)}
                              >
                                                                      Error
                                </Chip>
                            )}
                        </div>
                    </div>
                </div>

                {/* Messages Area */}
                <ScrollShadow className="flex-1 p-4">
                    <div className="max-w-4xl mx-auto space-y-4">
                        <AnimatePresence>
                            {messages.map((message, index) => (
                                <motion.div
                                    key={`${message.session_id}-${index}`}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -20 }}
                                    transition={{ duration: 0.3 }}
                                >
                                    <div className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        {message.role === 'assistant' && (
                                            <Avatar
                                                icon={<Icon icon="mdi:robot" />}
                                                className="bg-primary/10 text-primary flex-shrink-0"
                                                size="sm"
                                            />
                                        )}
                                        
                                        <div className={`max-w-[80%] ${message.role === 'user' ? 'order-first' : ''}`}>
                                            <Card className={`${
                                                message.role === 'user' 
                                                    ? 'bg-primary text-primary-foreground' 
                                                    : 'bg-default-50'
                                            }`}>
                                                <CardBody className="p-3">
                                                    <div className="flex items-start justify-between gap-2">
                                                        <div className="flex-1 min-w-0">
                                                            {message.role === 'assistant' ? (
                                                                renderMessageContent(message.content)
                                                            ) : (
                                                                <p className="whitespace-pre-wrap break-words">
                                                                    {message.content}
                                                                </p>
                                                            )}
                                                        </div>
                                                        
                                                        <div className="flex items-center gap-1 flex-shrink-0">
                                                            <Tooltip content="Copy message">
                                                                <Button
                                                                    isIconOnly
                                                                    size="sm"
                                                                    variant="light"
                                                                    onPress={() => copyToClipboard(message.content)}
                                                                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                                                                >
                                                                    <Icon icon="mdi:content-copy" className="text-xs" />
                                                                </Button>
                                                            </Tooltip>
                                                        </div>
                                                    </div>
                                                    
                                                    {showTimestamps && message.created_at && (
                                                        <p className="text-xs opacity-60 mt-2">
                                                            {formatTimestamp(message.created_at)}
                                                        </p>
                                                    )}
                                                </CardBody>
                                            </Card>
                                        </div>
                                        
                                        {message.role === 'user' && (
                                            <Avatar
                                                icon={<Icon icon="mdi:account" />}
                                                className="bg-secondary/10 text-secondary flex-shrink-0"
                                                size="sm"
                                            />
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>

                        {/* Streaming Message */}
                        {isStreaming && streamingMessage && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex gap-3 justify-start"
                            >
                                <Avatar
                                    icon={<Icon icon="mdi:robot" />}
                                    className="bg-primary/10 text-primary flex-shrink-0"
                                    size="sm"
                                />
                                <div className="max-w-[80%]">
                                    <Card className="bg-default-50">
                                        <CardBody className="p-3">
                                            {renderMessageContent(streamingMessage)}
                                            {isTyping && (
                                                <div className="flex items-center gap-1 mt-2">
                                                    <div className="flex space-x-1">
                                                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                                                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                                    </div>
                                                    <span className="text-xs text-default-500 ml-2">AI is typing...</span>
                                                </div>
                                            )}
                                        </CardBody>
                                    </Card>
                                </div>
                            </motion.div>
                        )}

                        {/* Welcome Message */}
                        {messages.length === 0 && !isStreaming && (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="text-center py-12"
                            >
                                <Icon icon="mdi:kubernetes" className="text-6xl text-primary mb-4 mx-auto" />
                                <h3 className="text-2xl font-bold mb-2">Welcome to KubeSage Chat</h3>
                                <p className="text-default-500 mb-6 max-w-md mx-auto">
                                    Your AI-powered Kubernetes assistant. Ask questions about kubectl commands, 
                                    troubleshooting, best practices, and more!
                                </p>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                                    {[
                                        {
                                            icon: "mdi:console",
                                            title: "kubectl Commands",
                                            description: "Get help with kubectl syntax and usage"
                                        },
                                        {
                                            icon: "mdi:bug",
                                            title: "Troubleshooting",
                                            description: "Debug pods, services, and deployments"
                                        },
                                        {
                                            icon: "mdi:chart-line",
                                            title: "Best Practices",
                                            description: "Learn Kubernetes optimization techniques"
                                        },
                                        {
                                            icon: "mdi:security",
                                            title: "Security",
                                            description: "Understand RBAC, policies, and security"
                                        }
                                    ].map((item, index) => (
                                        <Card
                                            key={index}
                                            isPressable
                                            className="p-4 hover:bg-primary/5 transition-colors"
                                            onPress={() => setInputMessage(`Tell me about ${item.title.toLowerCase()}`)}
                                        >
                                            <CardBody className="text-center">
                                                <Icon icon={item.icon} className="text-3xl text-primary mb-2 mx-auto" />
                                                <h4 className="font-semibold mb-1">{item.title}</h4>
                                                <p className="text-sm text-default-500">{item.description}</p>
                                            </CardBody>
                                        </Card>
                                    ))}
                                </div>
                            </motion.div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                </ScrollShadow>

                {/* Input Area */}
                <div className="p-4 border-t border-divider bg-background/60 backdrop-blur">
                    <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
                        <div className="flex gap-3 items-end">
                            <div className="flex-1">
                                <Textarea
                                    ref={inputRef}
                                    value={inputMessage}
                                    onChange={(e) => setInputMessage(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder="Ask me anything about Kubernetes..."
                                    minRows={1}
                                    maxRows={6}
                                    variant="bordered"
                                    classNames={{
                                        input: "resize-none",
                                        inputWrapper: "bg-background"
                                    }}
                                    endContent={
                                        <div className="flex items-center gap-2">
                                            {inputMessage.length > 0 && (
                                                <Chip size="sm" variant="flat">
                                                    {inputMessage.length}
                                                </Chip>
                                            )}
                                            <div className="flex items-center gap-1">
                                                <Kbd keys={["enter"]}>Send</Kbd>
                                                <Kbd keys={["shift", "enter"]}>New Line</Kbd>
                                            </div>
                                        </div>
                                    }
                                />
                            </div>
                            
                            <Button
                                type="submit"
                                color="primary"
                                isDisabled={!inputMessage.trim() || isLoading || isStreaming}
                                isLoading={isLoading || isStreaming}
                                className="px-6"
                                endContent={!isLoading && !isStreaming && <Icon icon="mdi:send" />}
                            >
                                {isLoading || isStreaming ? 'Sending...' : 'Send'}
                            </Button>
                        </div>
                        
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="mt-3"
                            >
                                <Card className="bg-danger/10 border-danger/20">
                                    <CardBody className="p-3">
                                        <div className="flex items-center gap-2">
                                            <Icon icon="mdi:alert-circle" className="text-danger" />
                                            <span className="text-sm text-danger">{error}</span>
                                            <Button
                                                size="sm"
                                                variant="light"
                                                isIconOnly
                                                onPress={() => setError(null)}
                                                className="ml-auto"
                                            >
                                                <Icon icon="mdi:close" />
                                            </Button>
                                        </div>
                                    </CardBody>
                                </Card>
                            </motion.div>
                        )}
                    </form>
                </div>
            </div>

            {/* Health Check Modal */}
            <Modal isOpen={isHealthModalOpen} onClose={onHealthModalClose} size="2xl">
                <ModalContent>
                    <ModalHeader className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                            <Icon icon="mdi:heart-pulse" className="text-success" />
                            System Health Check
                        </div>
                    </ModalHeader>
                    <ModalBody>
                        {healthData && (
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <Card>
                                        <CardBody className="text-center">
                                            <Icon 
                                                icon={healthData.status === 'healthy' ? 'mdi:check-circle' : 'mdi:alert-circle'} 
                                                className={`text-4xl mb-2 ${healthData.status === 'healthy' ? 'text-success' : 'text-danger'}`} 
                                            />
                                            <p className="font-semibold">Overall Status</p>
                                            <p className={healthData.status === 'healthy' ? 'text-success' : 'text-danger'}>
                                                {healthData.status}
                                            </p>
                                        </CardBody>
                                    </Card>
                                    
                                    <Card>
                                        <CardBody className="text-center">
                                            <Icon 
                                                icon={healthData.database === 'connected' ? 'mdi:database-check' : 'mdi:database-alert'} 
                                                className={`text-4xl mb-2 ${healthData.database === 'connected' ? 'text-success' : 'text-danger'}`} 
                                            />
                                            <p className="font-semibold">Database</p>
                                            <p className={healthData.database === 'connected' ? 'text-success' : 'text-danger'}>
                                                {healthData.database}
                                            </p>
                                        </CardBody>
                                    </Card>
                                    
                                    <Card>
                                        <CardBody className="text-center">
                                            <Icon 
                                                icon={healthData.llm === 'connected' ? 'mdi:brain' : 'mdi:brain-off'} 
                                                className={`text-4xl mb-2 ${healthData.llm === 'connected' ? 'text-success' : 'text-danger'}`} 
                                            />
                                            <p className="font-semibold">LLM Service</p>
                                            <p className={healthData.llm === 'connected' ? 'text-success' : 'text-danger'}>
                                                {healthData.llm}
                                            </p>
                                        </CardBody>
                                    </Card>
                                    
                                    <Card>
                                        <CardBody className="text-center">
                                            <Icon icon="mdi:clock" className="text-4xl mb-2 text-primary" />
                                            <p className="font-semibold">Last Check</p>
                                            <p className="text-sm text-default-500">
                                                {formatTimestamp(healthData.timestamp)}
                                            </p>
                                        </CardBody>
                                    </Card>
                                </div>
                            </div>
                        )}
                    </ModalBody>
                    <ModalFooter>
                        <Button color="danger" variant="light" onPress={onHealthModalClose}>
                            Close
                        </Button>
                        <Button color="primary" onPress={performHealthCheck}>
                            Refresh
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>

            {/* Debug Modal */}
            <Modal isOpen={isDebugModalOpen} onClose={onDebugModalClose} size="4xl" scrollBehavior="inside">
                <ModalContent>
                    <ModalHeader className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                            <Icon icon="mdi:bug" className="text-warning" />
                            Debug Information
                        </div>
                    </ModalHeader>
                    <ModalBody>
                        {debugInfo && (
                            <Tabs aria-label="Debug Information">
                                <Tab key="schema" title="Database Schema">
                                    <div className="space-y-4">
                                        <Card>
                                            <CardHeader>
                                                <h4 className="text-lg font-semibold">Database Tables</h4>
                                            </CardHeader>
                                            <CardBody>
                                                <div className="grid grid-cols-2 gap-2">
                                                    {debugInfo.schema.tables.map((table: string) => (
                                                        <Chip key={table} variant="flat" color="primary">
                                                            {table}
                                                        </Chip>
                                                    ))}
                                                </div>
                                            </CardBody>
                                        </Card>
                                        
                                        <Card>
                                            <CardHeader>
                                                <h4 className="text-lg font-semibold">Schema Details</h4>
                                            </CardHeader>
                                            <CardBody>
                                                <ScrollShadow className="max-h-96">
                                                    <Code className="whitespace-pre-wrap text-xs">
                                                        {JSON.stringify(debugInfo.schema.schema, null, 2)}
                                                    </Code>
                                                </ScrollShadow>
                                            </CardBody>
                                        </Card>
                                    </div>
                                </Tab>
                                
                                <Tab key="llm" title="LLM Test">
                                    <div className="space-y-4">
                                        <Card>
                                            <CardHeader>
                                                <h4 className="text-lg font-semibold">LLM Connection Test</h4>
                                            </CardHeader>
                                            <CardBody>
                                                <div className="space-y-3">
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-medium">Status:</span>
                                                        <Chip 
                                                            color={debugInfo.llmTest.status === 'success' ? 'success' : 'danger'}
                                                            variant="flat"
                                                        >
                                                            {debugInfo.llmTest.status}
                                                        </Chip>
                                                    </div>
                                                    
                                                    <div>
                                                        <span className="font-medium">Response:</span>
                                                        <Card className="mt-2">
                                                            <CardBody>
                                                                <p className="text-sm">{debugInfo.llmTest.response}</p>
                                                            </CardBody>
                                                        </Card>
                                                    </div>
                                                    
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-medium">Timestamp:</span>
                                                        <span className="text-sm text-default-500">
                                                            {formatTimestamp(debugInfo.llmTest.timestamp)}
                                                        </span>
                                                    </div>
                                                </div>
                                            </CardBody>
                                        </Card>
                                    </div>
                                </Tab>
                            </Tabs>
                        )}
                    </ModalBody>
                    <ModalFooter>
                        <Button color="danger" variant="light" onPress={onDebugModalClose}>
                            Close
                        </Button>
                        <Button color="primary" onPress={getDebugInfo}>
                            Refresh
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>
        </div>
    );
};

export default ChatOps;