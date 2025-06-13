import React from "react";
import { Icon } from "@iconify/react";
import { 
  Button, 
  Card, 
  CardBody, 
  CardHeader, 
  Input,
  Avatar,
  Chip,
  Tooltip
} from "@heroui/react";
import { motion, AnimatePresence } from "framer-motion";

interface AIChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Message {
  id: string;
  sender: "user" | "ai";
  content: string;
  timestamp: Date;
}

export const AIChatPanel: React.FC<AIChatPanelProps> = ({ isOpen, onClose }) => {
  const [input, setInput] = React.useState("");
  const [messages, setMessages] = React.useState<Message[]>([
    {
      id: "1",
      sender: "ai",
      content: "Hello! I'm KubeSage AI Assistant. How can I help you manage your Kubernetes clusters today?",
      timestamp: new Date()
    }
  ]);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  
  const handleSend = () => {
    if (!input.trim()) return;
    
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      sender: "user",
      content: input,
      timestamp: new Date()
    };
    
    setMessages([...messages, userMessage]);
    setInput("");
    
    // Simulate AI response after a short delay
    setTimeout(() => {
      const aiResponses: { [key: string]: string } = {
        "help": "I can help you with cluster management, security scanning, compliance checks, and resource optimization. What would you like to know?",
        "status": "Your production cluster is currently healthy with 12 nodes and 156 pods running. CPU usage is at 75% and memory at 62%.",
        "security": "I've detected 2 high severity vulnerabilities in your production cluster. Would you like me to show the details?",
        "optimize": "Based on my analysis, you could save 30% on resources by right-sizing your deployments. Would you like me to generate a detailed report?",
        "compliance": "Your production cluster is 92% compliant with your configured policies. The main issues are related to network policies and pod security.",
        "scale": "I recommend scaling the api-server deployment to 5 replicas based on current traffic patterns. Would you like me to apply this change?",
        "default": "I'll analyze your request and provide assistance. For more specific help, try asking about cluster status, security issues, compliance, or resource optimization."
      };
      
      let responseContent = aiResponses.default;
      
      // Simple keyword matching for demo purposes
      Object.keys(aiResponses).forEach(keyword => {
        if (input.toLowerCase().includes(keyword)) {
          responseContent = aiResponses[keyword];
        }
      });
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: "ai",
        content: responseContent,
        timestamp: new Date()
      };
      
      setMessages(prevMessages => [...prevMessages, aiMessage]);
    }, 1000);
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };
  
  // Scroll to bottom when messages change
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);
  
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ type: "spring", damping: 30, stiffness: 300 }}
          className="fixed top-0 right-0 h-full w-full md:w-96 z-50"
        >
          <Card className="h-full rounded-none md:rounded-l-lg shadow-xl">
            <CardHeader className="flex justify-between items-center border-b border-divider">
              <div className="flex items-center gap-2">
                <div className="bg-primary rounded-full p-1">
                  <Icon icon="lucide:bot" className="text-white text-lg" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">KubeSage AI</h3>
                  <p className="text-xs text-foreground-500">Kubernetes Assistant</p>
                </div>
              </div>
              <Button isIconOnly variant="ghost" onPress={onClose}>
                <Icon icon="lucide:x" />
              </Button>
            </CardHeader>
            <CardBody className="p-0 flex flex-col">
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((message) => (
                  <div 
                    key={message.id} 
                    className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div 
                      className={`flex gap-2 max-w-[80%] ${message.sender === 'user' ? 'flex-row-reverse' : ''}`}
                    >
                      {message.sender === 'ai' ? (
                        <Avatar 
                          src="https://img.heroui.chat/image/ai?w=200&h=200&u=kubesage" 
                          className="mt-1"
                          size="sm"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white font-medium mt-1">
                          U
                        </div>
                      )}
                      <div>
                        <div 
                          className={`p-3 rounded-lg ${
                            message.sender === 'user' 
                              ? 'bg-primary text-white' 
                              : 'bg-content2'
                          }`}
                        >
                          {message.content}
                        </div>
                        <div className="text-xs text-foreground-400 mt-1 px-1">
                          {formatTime(message.timestamp)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
              
              <div className="p-4 border-t border-divider">
                <div className="mb-2 flex gap-1 flex-wrap">
                  <Chip 
                    variant="flat" 
                    size="sm" 
                    color="primary" 
                    onPress={() => setInput("Show cluster status")}
                  >
                    Cluster status
                  </Chip>
                  <Chip 
                    variant="flat" 
                    size="sm" 
                    color="primary" 
                    onPress={() => setInput("Check security issues")}
                  >
                    Security check
                  </Chip>
                  <Chip 
                    variant="flat" 
                    size="sm" 
                    color="primary" 
                    onPress={() => setInput("Help me optimize resources")}
                  >
                    Optimize resources
                  </Chip>
                  <Chip 
                    variant="flat" 
                    size="sm" 
                    color="primary" 
                    onPress={() => setInput("Scale api-server deployment")}
                  >
                    Scale deployment
                  </Chip>
                </div>
                <div className="flex gap-2">
                  <Input
                    placeholder="Type your message..."
                    value={input}
                    onValueChange={setInput}
                    onKeyPress={handleKeyPress}
                    endContent={
                      <Button 
                        isIconOnly 
                        color="primary" 
                        variant="flat" 
                        size="sm" 
                        onPress={handleSend}
                      >
                        <Icon icon="lucide:send" />
                      </Button>
                    }
                  />
                </div>
              </div>
            </CardBody>
          </Card>
        </motion.div>
      )}
    </AnimatePresence>
  );
};