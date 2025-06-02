import React from "react";
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
  Tabs,
  Tab,
  Tooltip
} from "@heroui/react";

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

export const ChatOps: React.FC<ChatOpsProps> = ({ selectedCluster = "production" }) => {
  const [input, setInput] = React.useState("");
  const [messages, setMessages] = React.useState<Message[]>([
    {
      id: "1",
      sender: "ai",
      content: `Welcome to KubeSage ChatOps! You're connected to the ${selectedCluster} cluster. How can I help you today?`,
      timestamp: new Date(),
      type: "info"
    }
  ]);
  const [activeTab, setActiveTab] = React.useState("chat");
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  
  // Sample command suggestions
  const suggestions = [
    { text: "Show pod status", command: "kubectl get pods" },
    { text: "List deployments", command: "kubectl get deployments" },
    { text: "Check node status", command: "kubectl get nodes" },
    { text: "Scale deployment", command: "kubectl scale deployment/frontend --replicas=5" },
    { text: "Describe service", command: "kubectl describe service api-gateway" },
    { text: "View logs", command: "kubectl logs deployment/frontend" }
  ];
  
  const handleSend = () => {
    if (!input.trim()) return;
    
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      sender: "user",
      content: input,
      timestamp: new Date(),
      type: input.startsWith("kubectl") ? "command" : undefined,
      cluster: selectedCluster
    };
    
    setMessages([...messages, userMessage]);
    setInput("");
    
    // Simulate AI response after a short delay
    setTimeout(() => {
      let responseContent = "";
      let responseType: Message["type"] = "info";
      
      // Simple pattern matching for demo purposes
      if (input.includes("get pods") || input.includes("list pods")) {
        responseContent = `NAME                                    READY   STATUS    RESTARTS   AGE
api-server-5d8c7b9f68-2xvqz           1/1     Running   0          2d
frontend-6f7d9c4b5-1qaz2              1/1     Running   0          1d
redis-master-0                        1/1     Running   0          5d
postgres-0                            1/1     Running   0          3d
monitoring-6f7d9c4b5-1qaz2            1/1     Running   0          4d`;
        responseType = "result";
      } else if (input.includes("get deployments") || input.includes("list deployments")) {
        responseContent = `NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
api-server               3/3     3            3           7d
frontend                 5/5     5            5           5d
monitoring               1/1     1            1           10d`;
        responseType = "result";
      } else if (input.includes("scale deployment")) {
        responseContent = `deployment.apps/frontend scaled`;
        responseType = "result";
      } else if (input.includes("delete") || input.includes("remove")) {
        responseContent = `⚠️ This is a destructive operation. Please confirm by typing: "confirm delete"`;
        responseType = "warning";
      } else if (input.toLowerCase() === "confirm delete") {
        responseContent = `Operation completed successfully. Resource deleted.`;
        responseType = "result";
      } else if (input.includes("error") || input.includes("fail")) {
        responseContent = `Error: Unable to complete the requested operation. Please check your permissions and try again.`;
        responseType = "error";
      } else {
        responseContent = `I'll process your request: "${input}". For Kubernetes operations, try using kubectl commands or ask me to perform specific actions on your cluster.`;
      }
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: "ai",
        content: responseContent,
        timestamp: new Date(),
        type: responseType,
        cluster: selectedCluster
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
  
  const getMessageClass = (type?: string) => {
    switch(type) {
      case "command": return "bg-primary-100 text-primary-700 font-mono";
      case "result": return "bg-content2 text-foreground font-mono";
      case "info": return "bg-primary-100 text-primary-700";
      case "warning": return "bg-warning-100 text-warning-700";
      case "error": return "bg-danger-100 text-danger-700";
      default: return "bg-content2";
    }
  };

  return (
    <div className="space-y-6">
      <Card className="h-[calc(100vh-180px)]">
        <CardHeader className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Icon icon="lucide:terminal" className="text-primary" />
              <h2 className="text-xl font-semibold">ChatOps Console</h2>
            </div>
            <Chip color="success" variant="flat" size="sm">
              Connected to {selectedCluster}
            </Chip>
          </div>
          <p className="text-sm text-foreground-500">Interact with your Kubernetes clusters using natural language or commands</p>
        </CardHeader>
        <CardBody className="p-0 flex flex-col">
          <Tabs 
            aria-label="ChatOps options" 
            selectedKey={activeTab} 
            onSelectionChange={setActiveTab as any}
            classNames={{
              tabList: "px-4 border-b border-divider",
            }}
          >
            <Tab 
              key="chat" 
              title={
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:message-square" />
                  <span>Chat</span>
                </div>
              }
            >
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((message) => (
                  <motion.div 
                    key={message.id} 
                    className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
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
                              ? message.type === 'command' 
                                ? 'bg-primary-100 text-primary-700 font-mono' 
                                : 'bg-primary text-white'
                              : getMessageClass(message.type)
                          }`}
                        >
                          {message.content}
                        </div>
                        <div className="text-xs text-foreground-400 mt-1 px-1 flex items-center gap-1">
                          {message.cluster && message.sender === 'user' && (
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
                ))}
                <div ref={messagesEndRef} />
              </div>
              
              <div className="p-4 border-t border-divider">
                <div className="mb-2 flex gap-1 flex-wrap">
                  {suggestions.map((suggestion, index) => (
                    <Tooltip key={index} content={suggestion.command}>
                      <Chip 
                        variant="flat" 
                        size="sm" 
                        color="primary" 
                        onPress={() => setInput(suggestion.command)}
                      >
                        {suggestion.text}
                      </Chip>
                    </Tooltip>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input
                    placeholder="Type a command or ask a question..."
                    value={input}
                    onValueChange={setInput}
                    onKeyPress={handleKeyPress}
                    startContent={<Icon icon="lucide:terminal" className="text-foreground-400" />}
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
            </Tab>
            <Tab 
              key="history" 
              title={
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:history" />
                  <span>Command History</span>
                </div>
              }
            >
              <div className="p-4">
                <div className="space-y-2">
                  {messages
                    .filter(m => m.sender === 'user' && m.type === 'command')
                    .map((command) => (
                      <div key={command.id} className="flex items-center justify-between p-2 border-b border-divider">
                        <div className="flex items-center gap-2">
                          <Icon icon="lucide:terminal" className="text-primary" />
                          <code className="text-sm">{command.content}</code>
                        </div>
                        <div className="flex items-center gap-2">
                          <Chip size="sm" variant="flat">{command.cluster}</Chip>
                          <span className="text-xs text-foreground-400">{formatTime(command.timestamp)}</span>
                          <Button isIconOnly size="sm" variant="light" onPress={() => setInput(command.content)}>
                            <Icon icon="lucide:repeat" />
                          </Button>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </Tab>
            <Tab 
              key="templates" 
              title={
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:bookmark" />
                  <span>Templates</span>
                </div>
              }
            >
              <div className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className="p-3 cursor-pointer hover:border-primary transition-colors">
                    <div className="flex items-start gap-2">
                      <Icon icon="lucide:search" className="text-primary mt-1" />
                      <div>
                        <h3 className="font-medium">Resource Inspection</h3>
                        <p className="text-xs text-foreground-500 mb-2">Common commands for checking cluster resources</p>
                        <div className="space-y-1">
                          <div className="flex items-center justify-between">
                            <code className="text-xs">kubectl get pods -n default</code>
                            <Button size="sm" variant="light" isIconOnly onPress={() => setInput("kubectl get pods -n default")}>
                              <Icon icon="lucide:copy" size={14} />
                            </Button>
                          </div>
                          <div className="flex items-center justify-between">
                            <code className="text-xs">kubectl get deployments --all-namespaces</code>
                            <Button size="sm" variant="light" isIconOnly onPress={() => setInput("kubectl get deployments --all-namespaces")}>
                              <Icon icon="lucide:copy" size={14} />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Card>
                  
                  <Card className="p-3 cursor-pointer hover:border-primary transition-colors">
                    <div className="flex items-start gap-2">
                      <Icon icon="lucide:trending-up" className="text-primary mt-1" />
                      <div>
                        <h3 className="font-medium">Scaling Operations</h3>
                        <p className="text-xs text-foreground-500 mb-2">Commands for scaling resources</p>
                        <div className="space-y-1">
                          <div className="flex items-center justify-between">
                            <code className="text-xs">kubectl scale deployment/frontend --replicas=5</code>
                            <Button size="sm" variant="light" isIconOnly onPress={() => setInput("kubectl scale deployment/frontend --replicas=5")}>
                              <Icon icon="lucide:copy" size={14} />
                            </Button>
                          </div>
                          <div className="flex items-center justify-between">
                            <code className="text-xs">kubectl autoscale deployment/api --min=2 --max=10</code>
                            <Button size="sm" variant="light" isIconOnly onPress={() => setInput("kubectl autoscale deployment/api --min=2 --max=10")}>
                              <Icon icon="lucide:copy" size={14} />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Card>
                  
                  <Card className="p-3 cursor-pointer hover:border-primary transition-colors">
                    <div className="flex items-start gap-2">
                      <Icon icon="lucide:shield" className="text-primary mt-1" />
                      <div>
                        <h3 className="font-medium">Security Checks</h3>
                        <p className="text-xs text-foreground-500 mb-2">Commands for security auditing</p>
                        <div className="space-y-1">
                          <div className="flex items-center justify-between">
                            <code className="text-xs">kubectl auth can-i list pods</code>
                            <Button size="sm" variant="light" isIconOnly onPress={() => setInput("kubectl auth can-i list pods")}>
                              <Icon icon="lucide:copy" size={14} />
                            </Button>
                          </div>
                          <div className="flex items-center justify-between">
                            <code className="text-xs">kubectl get psp</code>
                            <Button size="sm" variant="light" isIconOnly onPress={() => setInput("kubectl get psp")}>
                              <Icon icon="lucide:copy" size={14} />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Card>
                  
                  <Card className="p-3 cursor-pointer hover:border-primary transition-colors">
                    <div className="flex items-start gap-2">
                      <Icon icon="lucide:activity" className="text-primary mt-1" />
                      <div>
                        <h3 className="font-medium">Troubleshooting</h3>
                        <p className="text-xs text-foreground-500 mb-2">Commands for debugging issues</p>
                        <div className="space-y-1">
                          <div className="flex items-center justify-between">
                            <code className="text-xs">kubectl logs deployment/frontend</code>
                            <Button size="sm" variant="light" isIconOnly onPress={() => setInput("kubectl logs deployment/frontend")}>
                              <Icon icon="lucide:copy" size={14} />
                            </Button>
                          </div>
                          <div className="flex items-center justify-between">
                            <code className="text-xs">kubectl describe pod frontend-6f7d9c4b5-1qaz2</code>
                            <Button size="sm" variant="light" isIconOnly onPress={() => setInput("kubectl describe pod frontend-6f7d9c4b5-1qaz2")}>
                              <Icon icon="lucide:copy" size={14} />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Card>
                </div>
              </div>
            </Tab>
          </Tabs>
        </CardBody>
      </Card>
    </div>
  );
};