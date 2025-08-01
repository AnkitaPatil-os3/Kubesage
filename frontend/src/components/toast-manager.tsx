import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardBody, Button } from '@heroui/react';
import { Icon } from '@iconify/react';
 
export interface Toast {
  id: string;
  title: string;
  description?: string;
  color: 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
  duration?: number;
  action?: {
    label: string;
    onPress: () => void;
  };
}
 
interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
}
 
const ToastContext = React.createContext<ToastContextType | undefined>(undefined);
 
export const useToast = () => {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
 
export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = React.useState<Toast[]>([]);
 
  const addToast = React.useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newToast: Toast = {
      ...toast,
      id,
      duration: toast.duration ?? 5000,
    };
 
    setToasts(prev => [...prev, newToast]);
 
    // Auto remove toast after duration
    if (newToast.duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, newToast.duration);
    }
  }, []);
 
  const removeToast = React.useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);
 
  const clearToasts = React.useCallback(() => {
    setToasts([]);
  }, []);
 
  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, clearToasts }}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  );
};
 
interface ToastContainerProps {
  toasts: Toast[];
  removeToast: (id: string) => void;
}
 
const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, removeToast }) => {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
        ))}
      </AnimatePresence>
    </div>
  );
};
 
interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}
 
const ToastItem: React.FC<ToastItemProps> = ({ toast, onRemove }) => {
  const getColorClasses = (color: Toast['color']) => {
    switch (color) {
      case 'success':
        return 'border-success bg-success/10';
      case 'warning':
        return 'border-warning bg-warning/10';
      case 'danger':
        return 'border-danger bg-danger/10';
      case 'primary':
        return 'border-primary bg-primary/10';
      case 'secondary':
        return 'border-secondary bg-secondary/10';
      default:
        return 'border-default bg-default/10';
    }
  };
 
  const getIcon = (color: Toast['color']) => {
    switch (color) {
      case 'success':
        return 'lucide:check-circle';
      case 'warning':
        return 'lucide:alert-triangle';
      case 'danger':
        return 'lucide:x-circle';
      case 'primary':
        return 'lucide:info';
      default:
        return 'lucide:bell';
    }
  };
 
  const getIconColor = (color: Toast['color']) => {
    switch (color) {
      case 'success':
        return 'text-success';
      case 'warning':
        return 'text-warning';
      case 'danger':
        return 'text-danger';
      case 'primary':
        return 'text-primary';
      case 'secondary':
        return 'text-secondary';
      default:
        return 'text-default-500';
    }
  };
 
  return (
    <motion.div
      initial={{ opacity: 0, x: 300, scale: 0.3 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 300, scale: 0.5, transition: { duration: 0.2 } }}
      className={`border-l-4 ${getColorClasses(toast.color)} backdrop-blur-md`}
    >
      <Card className="bg-transparent shadow-lg">
        <CardBody className="p-4">
          <div className="flex items-start gap-3">
            <Icon
              icon={getIcon(toast.color)}
              className={`text-lg mt-0.5 ${getIconColor(toast.color)}`}
            />
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-sm">{toast.title}</h4>
              {toast.description && (
                <p className="text-xs text-foreground-600 mt-1">{toast.description}</p>
              )}
              {toast.action && (
                <Button
                  size="sm"
                  variant="flat"
                  color={toast.color}
                  className="mt-2"
                  onPress={toast.action.onPress}
                >
                  {toast.action.label}
                </Button>
              )}
            </div>
            <Button
              isIconOnly
              size="sm"
              variant="light"
              onPress={() => onRemove(toast.id)}
              className="min-w-unit-6 w-unit-6 h-unit-6"
            >
              <Icon icon="lucide:x" className="text-xs" />
            </Button>
          </div>
        </CardBody>
      </Card>
    </motion.div>
  );
};
 
// Convenience function for adding toasts (can be used outside of components)
let globalAddToast: ((toast: Omit<Toast, 'id'>) => void) | null = null;
 
export const addToast = (toast: Omit<Toast, 'id'>) => {
  if (globalAddToast) {
    globalAddToast(toast);
  } else {
    console.warn('Toast system not initialized. Make sure ToastProvider is mounted.');
  }
};
 
// Hook to set the global add toast function
export const useGlobalToast = () => {
  const { addToast: contextAddToast } = useToast();
  
  React.useEffect(() => {
    globalAddToast = contextAddToast;
    return () => {
      globalAddToast = null;
    };
  }, [contextAddToast]);
};
 
 