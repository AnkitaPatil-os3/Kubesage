import React from "react";
import { useLocation } from "react-router-dom";
import { Icon } from "@iconify/react";
import {
  Button,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  Input,
  Avatar,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  useDisclosure,
  Card,
  CardBody,
  Chip,
} from "@heroui/react";
import { motion } from "framer-motion";

interface HeaderProps {
  toggleChat: () => void;
}

interface ApiKey {
  id: number;
  key_name: string;
  api_key?: string;
  api_key_preview: string;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
}

export const Header: React.FC<HeaderProps> = ({ toggleChat }) => {
  const location = useLocation();
  const [isSearchFocused, setIsSearchFocused] = React.useState(false);
  
  const { isOpen, onOpen, onOpenChange } = useDisclosure();
  const [apiKeys, setApiKeys] = React.useState<ApiKey[]>([]);
  const [newKeyName, setNewKeyName] = React.useState("");
  const [expiryDate, setExpiryDate] = React.useState<string>("");
  const [isCreating, setIsCreating] = React.useState(false);
  const [createdKey, setCreatedKey] = React.useState<string | null>(null);
  
  const getPageTitle = () => {
    const path = location.pathname.split('/').pop() || 'overview';
    switch(path) {
      case 'overview': return 'Dashboard';
      case 'upload': return 'Cluster Overview';
      case 'onboarding': return 'Cluster Onboarding';
      case 'chatops': return 'ChatOps Console';
      case 'admin': return 'Admin Dashboard';
      default: return 'Dashboard';
    }
  };

  const fetchApiKeys = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('https://10.0.2.30:8001/api-keys/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const keys = await response.json();
        setApiKeys(keys);
      }
    } catch (error) {
      console.error('Error fetching API keys:', error);
    }
  };

  const createApiKey = async () => {
    if (!newKeyName.trim()) return;
    
    setIsCreating(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('https://10.0.2.30:8001/api-keys/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          key_name: newKeyName,
          expires_at: expiryDate ? new Date(expiryDate).toISOString() : null
        })
      });
      
      if (response.ok) {
        const newKey = await response.json();
        setCreatedKey(newKey.api_key);
        setNewKeyName("");
        setExpiryDate("");
        fetchApiKeys();
      }
    } catch (error) {
      console.error('Error creating API key:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const regenerateApiKey = async (keyId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`https://10.0.2.30:8001/api-keys//${keyId}/regenerate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const regeneratedKey = await response.json();
        setCreatedKey(regeneratedKey.api_key);
        fetchApiKeys();
      }
    } catch (error) {
      console.error('Error regenerating API key:', error);
    }
  };

  const isExpired = (expiresAt: string | null) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  const handleApiKeyManagement = () => {
    fetchApiKeys();
    onOpen();
  };

  const getMinDate = () => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  };

  return (
    <>
      <motion.header
        className="h-16 border-b border-divider bg-content1 backdrop-blur-md bg-opacity-80 flex items-center justify-between px-4 md:px-6"
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="md:hidden">
          <Button isIconOnly variant="ghost" aria-label="Menu">
            <Icon icon="lucide:menu" className="text-xl" />
          </Button>
        </div>
        
        <div className="hidden md:block">
          <motion.h1
            className="text-xl font-semibold"
            key={location.pathname}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {getPageTitle()}
          </motion.h1>
        </div>
        
        <div className="hidden md:flex flex-1 max-w-md mx-6">
          <Input
            placeholder="Search resources..."
            startContent={<Icon icon="lucide:search" className="text-foreground-400" />}
            size="sm"
            className={`transition-all duration-300 ${isSearchFocused ? 'shadow-md' : ''}`}
            onFocus={() => setIsSearchFocused(true)}
            onBlur={() => setIsSearchFocused(false)}
          />
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            color="primary"
            variant="flat"
            startContent={<Icon icon="lucide:message-square" />}
            onPress={toggleChat}
            className="hidden md:flex"
          >
            AI Assistant
          </Button>
          
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Button isIconOnly variant="ghost" aria-label="Notifications">
              <Icon icon="lucide:bell" className="text-xl" />
            </Button>
          </motion.div>
          
          <Dropdown>
            <DropdownTrigger>
              <Avatar
                src="https://img.heroui.chat/image/avatar?w=200&h=200&u=admin"
                size="sm"
                className="cursor-pointer"
              />
            </DropdownTrigger>
            <DropdownMenu aria-label="Actions">
              <DropdownItem key="profile" startContent={<Icon icon="lucide:user" />}>
                Profile
              </DropdownItem>
              <DropdownItem key="settings" startContent={<Icon icon="lucide:settings" />}>
                Settings
              </DropdownItem>
              <DropdownItem 
                key="api-keys" 
                startContent={<Icon icon="lucide:key" />}
                onClick={handleApiKeyManagement}
              >
                Webhook API Keys
              </DropdownItem>
              <DropdownItem key="help" startContent={<Icon icon="lucide:help-circle" />}>
                Help & Documentation
              </DropdownItem>
              <DropdownItem key="feedback" startContent={<Icon icon="lucide:message-square" />}>
                Send Feedback
              </DropdownItem>
              <DropdownItem
                key="logout"
                className="text-danger"
                color="danger"
                startContent={<Icon icon="lucide:log-out" />}
                onClick={async () => {
                  try {
                    const accessToken = localStorage.getItem('access_token');
                    await fetch('/auth/logout', {
                      method: 'POST',
                      headers: {
                        'Authorization': `Bearer ${accessToken}`,
                        'Content-Type': 'application/json'
                      }
                    });
                  } catch (error) {
                    console.error('Logout failed:', error);
                  } finally {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    window.location.href = '/login';
                  }
                }}
              >
                Log Out
              </DropdownItem>
            </DropdownMenu>
          </Dropdown>
        </div>
      </motion.header>

      <Modal isOpen={isOpen} onOpenChange={onOpenChange} size="2xl">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:key" className="text-xl" />
                  Webhook API Key Management
                </div>
              </ModalHeader>
              <ModalBody>
                <Card>
                  <CardBody className="gap-4">
                    <h4 className="text-lg font-semibold">Create New API Key</h4>
                    <Input
                      label="Key Name"
                      placeholder="Enter Webhook API key name"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                    />
                    <Input
                      type="date"
                      label="Expiry Date (Optional)"
                      placeholder="Select expiry date"
                      value={expiryDate}
                      onChange={(e) => setExpiryDate(e.target.value)}
                      min={getMinDate()}
                    />
                    <Button
                      color="primary"
                      onPress={createApiKey}
                      isLoading={isCreating}
                      isDisabled={!newKeyName.trim()}
                    >
                      Create API Key
                    </Button>
                  </CardBody>
                </Card>

                {createdKey && (
                  <Card className="bg-success-50 border-success-200">
                    <CardBody>
                      <div className="flex items-center gap-2 mb-2">
                        <Icon icon="lucide:check-circle" className="text-success" />
                        <span className="font-semibold text-success">Webhook API Key Created!</span>
                      </div>
                      <p className="text-sm text-warning mb-2">
                        Copy this key now - it won't be shown again!
                      </p>
                      <Input
                        value={createdKey}
                        readOnly
                        endContent={
                          <Button
                            size="sm"
                            variant="light"
                            onPress={() => navigator.clipboard.writeText(createdKey)}
                          >
                            <Icon icon="lucide:copy" />
                          </Button>
                        }
                      />
                    </CardBody>
                  </Card>
                )}

                <div className="space-y-3">
                  <h4 className="text-lg font-semibold">Your API Keys</h4>
                  {apiKeys.length === 0 ? (
                    <p className="text-gray-500">No API keys found</p>
                  ) : (
                    apiKeys.map((key) => (
                      <Card key={key.id}>
                        <CardBody className="flex flex-row items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium">{key.key_name}</span>
                              {isExpired(key.expires_at) ? (
                                <Chip color="danger" size="sm">Expired</Chip>
                              ) : (
                                <Chip color="success" size="sm">Active</Chip>
                              )}
                            </div>
                            <p className="text-sm text-gray-500">
                              {key.api_key_preview}
                            </p>
                            {key.expires_at && (
                              <p className="text-xs text-gray-400">
                                Expires: {new Date(key.expires_at).toLocaleDateString()}
                              </p>
                            )}
                          </div>
                          {isExpired(key.expires_at) && (
                            <Button
                              size="sm"
                              color="warning"
                              variant="flat"
                              onPress={() => regenerateApiKey(key.id)}
                            >
                              Regenerate
                            </Button>
                          )}
                        </CardBody>
                      </Card>
                    ))
                  )}
                </div>
              </ModalBody>
              <ModalFooter>
                <Button color="danger" variant="light" onPress={onClose}>
                  Close
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </>
  );
};
