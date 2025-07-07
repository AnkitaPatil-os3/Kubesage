//welcome
//scrollbar
//chat histroy
import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Icon } from "@iconify/react";
import {
  Card,
  CardBody,
  CardHeader,
  Input,
  Button,
  Avatar,
  Chip,
  Divider,
  Tooltip
} from "@heroui/react";
 
import MarkdownIt from "markdown-it";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";
 
interface ChatOpsProps {
  selectedCluster?: string;
}
 
interface Message {
  id: string;
  sender: "user" | "ai";
  content: string;
  timestamp: Date;
  type?: "command" | "result" | "info" | "warning" | "error";
  cluster?: string;
}
 
interface ChatSession {
  id: string;
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}
 
export const ChatOps: React.FC<ChatOpsProps> = ({ selectedCluster = "production" }) => {
  // Sidebar visibility and minimized state
  const [isSidebarVisible, setIsSidebarVisible] = useState(true);
  const [isSidebarMinimized, setIsSidebarMinimized] = useState(false);
 
  // Initialize MarkdownIt with syntax highlighting
  const md = new MarkdownIt({
    highlight: function (str, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(str, { language: lang }).value;
        } catch (__) {}
      }
      return ''; // use external default escaping
    }
  });
 
  // Function to render markdown content with syntax highlighting
  const renderMarkdown = (text: string) => {
    if (!text) return '';
    return md.render(text);
  };
 
  // Chat sessions and active session
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
 
  // Chat messages for active session
  const [messages, setMessages] = useState<Message[]>([]);
 
  // Input and loading/error states
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
 
  const messagesEndRef = useRef<HTMLDivElement>(null);
 
  // Helper to get auth token
  const getAuthToken = () => {
    return localStorage.getItem("access_token") || "";
  };
 
  // Fetch chat sessions on mount
  useEffect(() => {
    fetchChatSessions();
  }, []);
 
  // Fetch chat sessions from backend
  const fetchChatSessions = async () => {
    try {
      const response = await fetch("https://10.0.32.103:8003/chat/sessions", {
        headers: {
          Authorization: `Bearer ${getAuthToken()}`
        }
      });
      if (!response.ok) throw new Error("Failed to fetch chat sessions");
      const data = await response.json();
      setChatSessions(data.sessions || []);
      if (data.sessions && data.sessions.length > 0) {
        setActiveSessionId(data.sessions[0].session_id);
      }
    } catch (err) {
      console.error(err);
    }
  };
 
  // Fetch chat history when activeSessionId changes
  useEffect(() => {
    if (activeSessionId) {
      fetchChatHistory(activeSessionId);
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);
 
  // Fetch chat history messages for a session
  const fetchChatHistory = async (sessionId: string) => {
    try {
      const response = await fetch(`/chat/history/${sessionId}`, {
        headers: {
          Authorization: `Bearer ${getAuthToken()}`
        }
      });
      if (!response.ok) throw new Error("Failed to fetch chat history");
      const data = await response.json();
      const mappedMessages: Message[] = data.messages.map((msg: any, index: number) => ({
        id: index.toString(),
        sender: msg.role === "user" ? "user" : "ai",
        content: msg.content,
        timestamp: new Date(msg.created_at),
        type: msg.role === "user" ? "command" : "info"
      }));
      setMessages(mappedMessages);
    } catch (err) {
      console.error(err);
      setMessages([]);
    }
  };
 
  // Handle sending a message
  const handleSend = async () => {
    if (!input.trim() || !activeSessionId) return;
 
    setError(null);
    setLoading(true);
 
    const userMessage: Message = {
      id: Date.now().toString(),
      sender: "user",
      content: input,
      timestamp: new Date(),
      type: input.startsWith("kubectl") ? "command" : undefined,
      cluster: selectedCluster
    };
 
    setMessages(prev => [...prev, userMessage]);
    setInput("");
 
    try {
      const payload = {
        content: input,
        session_id: activeSessionId,
        cluster: selectedCluster
      };
 
      const response = await fetch("/chat/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAuthToken()}`
        },
        body: JSON.stringify(payload)
      });
 
      if (!response.ok) throw new Error(`API error: ${response.statusText}`);
 
      const data = await response.json();
 
      if (data.session_id && data.session_id !== activeSessionId) {
        setActiveSessionId(data.session_id);
      }
 
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: "ai",
        content: data.content || "No response from AI",
        timestamp: new Date(),
        type: "info",
        cluster: selectedCluster
      };
 
      setMessages(prev => [...prev, aiMessage]);
    } catch (err: any) {
      setError(err.message || "Failed to send message");
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        sender: "ai",
        content: `Error: ${err.message || "Failed to send message"}`,
        timestamp: new Date(),
        type: "error",
        cluster: selectedCluster
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };
 
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);
 
  // Format time for display
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };
 
  // Delete a chat session
  const deleteSession = async (sessionId: string) => {
    try {
      const response = await fetch(`/chat/sessions/${sessionId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${getAuthToken()}`
        }
      });
      if (!response.ok) throw new Error("Failed to delete session");
      setChatSessions(prev => prev.filter(s => s.session_id !== sessionId));
      if (activeSessionId === sessionId) {
        if (chatSessions.length > 1) {
          setActiveSessionId(chatSessions[0].session_id);
        } else {
          setActiveSessionId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };
 
  // Toggle sidebar visibility
  const toggleSidebar = () => {
    setIsSidebarVisible(!isSidebarVisible);
  };
 
  // Toggle sidebar minimized state
  const toggleSidebarMinimized = () => {
    setIsSidebarMinimized(!isSidebarMinimized);
  };
 
  // Function to handle prompt usage from welcome screen
  const usePrompt = (prompt: string) => {
    setInput(prompt);
    // Optionally, send the prompt immediately
    // handleSend();
  };
 
  return (
    <div className="flex flex-col">
      {/* Header moved above all divs */}
      <div className="flex flex-col items-center gap-1 w-full p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <div className="flex items-center gap-2">
          <Icon icon="lucide:terminal" className="text-primary" />
          <h2 className="text-xl font-semibold">ChatOps Console</h2>
          <Chip color="success" variant="flat" size="sm" className="ml-4">
            Connected to {selectedCluster}
          </Chip>
        </div>
        <p className="text-sm text-foreground-500">
          Interact with your Kubernetes clusters using natural language or commands
        </p>
      </div>
 
      {/* Sidebar and Main Chat Area Wrapper */}
      <div className="flex flex-1" style={{ height: 'calc(100vh - 80px)' }}>
        {/* Sidebar */}
        {isSidebarVisible && (
          <div
            className={`flex flex-col bg-white border-r border-gray-200 dark:bg-gray-800 dark:border-gray-700 transition-all duration-300 ${
              isSidebarMinimized ? "w-20" : "w-72"
            }`}
          >
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              {!isSidebarMinimized && (
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Chat History
                </h2>
              )}
              <button
                onClick={toggleSidebarMinimized}
                className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
                title={isSidebarMinimized ? "Expand sidebar" : "Minimize sidebar"}
              >
                <Icon icon={isSidebarMinimized ? "lucide:chevron-right" : "lucide:chevron-left"} />
              </button>
            </div>
          <div className="flex-1 overflow-y-auto">
            {chatSessions.map(session => {
              const isActive = session.session_id === activeSessionId;
              return (
                <div
                  key={session.session_id}
                  className={`flex items-center justify-between p-3 cursor-pointer border-l-4 ${
                    isActive
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                      : "border-transparent hover:border-blue-500 hover:bg-gray-100 dark:hover:bg-gray-700/30"
                  }`}
                  onClick={() => setActiveSessionId(session.session_id)}
                  title={session.title || session.session_id}
                >
                  <div className="truncate text-sm text-gray-900 dark:text-gray-100">
                    {session.title || session.session_id}
                  </div>
                  {!isSidebarMinimized && (
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        deleteSession(session.session_id);
                      }}
                      className="text-red-500 hover:text-red-700"
                      title="Delete session"
                    >
                      <Icon icon="lucide:trash" />
                    </button>
                  )}
                </div>
              );
            })}
            <div className="p-4 border-t border-gray-200 dark:border-gray-700">
              <Button
                onClick={() => {
                  // Create new chat session
                  fetch("/chat/sessions", {
                    method: "POST",
                    headers: {
                      "Content-Type": "application/json",
                      Authorization: `Bearer ${getAuthToken()}`
                    },
                    body: JSON.stringify({ title: "New Chat" })
                  })
                    .then(res => res.json())
                    .then(data => {
                      setChatSessions(prev => [data, ...prev]);
                      setActiveSessionId(data.session_id);
                      setMessages([]);
                    })
                    .catch(err => console.error(err));
                }}
                fullWidth
                color="primary"
              >
                New Chat
              </Button>
            </div>
          </div>
          </div>
        )}
 
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col bg-white dark:bg-gray-900">
          <Card className="flex flex-col h-full">
          <CardBody className="flex flex-col flex-1 p-0">
              {messages.length === 0 ? (
                <div
                  className="welcome-screen max-w-3xl mx-auto text-center p-8 flex flex-col justify-center items-center h-full"
                  style={{ marginLeft: isSidebarMinimized ? '5rem' : '17rem', height: '72vh' }}
                >
                  <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-green-500 to-green-600 bg-clip-text text-transparent">
                    Welcome to KubeSage
                  </h1>
                  <p className="text-lg text-gray-600 dark:text-gray-400 mb-10">
                    Your intelligent GenAI assistant for seamless Kubernetes operations and troubleshooting
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div
                      onClick={() => usePrompt('Explain my cluster health status')}
                      className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col items-center"
                    >
                      <i className="fas fa-heartbeat text-2xl text-green-500 mb-3"></i>
                      <span className="text-gray-700 dark:text-gray-300">Explain my cluster health status</span>
                    </div>
                    <div
                      onClick={() => usePrompt('Troubleshoot pod crashes in namespace default')}
                      className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col items-center"
                    >
                      <i className="fas fa-bug text-2xl text-green-500 mb-3"></i>
                      <span className="text-gray-700 dark:text-gray-300">Troubleshoot pod crashes</span>
                    </div>
                    <div
                      onClick={() => usePrompt('Optimize resource usage in my cluster')}
                      className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col items-center"
                    >
                      <i className="fas fa-tachometer-alt text-2xl text-green-500 mb-3"></i>
                      <span className="text-gray-700 dark:text-gray-300">Optimize resource usage</span>
                    </div>
                    <div
                      onClick={() => usePrompt('Explain best practices for Kubernetes security')}
                      className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col items-center"
                    >
                      <i className="fas fa-shield-alt text-2xl text-green-500 mb-3"></i>
                      <span className="text-gray-700 dark:text-gray-300">Kubernetes security best practices</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="overflow-y-auto p-4 space-y-4" style={{ height: '700px' , overflowY: 'auto' }}>
{messages.map(message => {
  // Determine header title based on message type
  let headerTitle = "Message";
  if (message.type === "command") headerTitle = "bash";
  else if (message.type === "info") headerTitle = "yaml";
  else if (message.type === "result") headerTitle = "result";
  else if (message.type === "warning") headerTitle = "warning";
  else if (message.type === "error") headerTitle = "error";
 
  return (
    <motion.div
      key={message.id}
      className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div
        className={`flex gap-2 max-w-[80%] items-start`}
      >
        {message.sender === "ai" ? (
          <div className="w-10 h-10 rounded-full border-2 border-primary shadow-md overflow-hidden mt-1 flex-shrink-0">
            <img
              src="https://img.heroui.chat/image/ai?w=200&h=200&u=kubesage"
              alt="AI Avatar"
              className="w-full h-full object-cover rounded-full"
            />
          </div>
        ) : (
          <></>
        )}
        <div>
{/* Header box */}
<div
  className={`font-mono text-sm px-3 py-1 rounded-t-md select-none ${
    message.sender === "user"
      ? message.type === "command"
        ? "bg-primary-400 text-primary-700"
        : message.type === "info"
          ? "bg-green-700 text-green-100"
          : "bg-primary-100 text-primary-700"
      : getMessageClass(message.type)
  }`}
  style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0 }}
>
  {headerTitle}
</div>
{/* Content box */}
<div
  className={`p-3 rounded-b-lg prose dark:prose-invert ${
    message.sender === "user"
      ? message.type === "command"
        ? "bg-primary-100 text-primary-700 font-mono"
        : "bg-primary-100 text-primary-700"
      : getMessageClass(message.type)
  }`}
  style={{ borderTopLeftRadius: 0, borderTopRightRadius: 0 }}
  dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
>
</div>
          <div className="text-xs text-foreground-400 mt-1 px-1 flex items-center gap-1">
            {message.cluster && message.sender === "user" && (
              <>
                <Chip size="sm" variant="flat" color="primary" className="text-xs py-0 px-1 h-4">
                  {message.cluster}
                </Chip>
                <span>•</span>
              </>
            )}
            {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    </motion.div>
  );
})}
                  {loading && (
                    <div className="text-center text-sm text-foreground-500">Loading...</div>
                  )}
                  {error && (
                    <div className="text-center text-sm text-danger-600">Error: {error}</div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
              <div className="p-4 border-t border-divider">
                <div className="flex gap-2">
                  <Input
                    placeholder="Type a command or ask a question..."
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyPress={e => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                    startContent={<Icon icon="lucide:terminal" className="text-foreground-400" />}
                    endContent={
                      <Button isIconOnly color="primary" variant="flat" size="sm" onClick={handleSend} disabled={loading}>
                        <Icon icon="lucide:send" />
                      </Button>
                    }
                  />
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
 
function getMessageClass(type?: string) {
  switch (type) {
    case "command":
      return "bg-primary-100 text-primary-700 font-mono";
    case "result":
      return "bg-content2 text-foreground font-mono";
case "info":
  return "bg-green-200 text-green-900"; // Darker green for header title
    case "warning":
      return "bg-warning-100 text-warning-700";
    case "error":
      return "bg-danger-100 text-danger-700";
    default:
      return "bg-content2";
  }
}
};
 
 