import React, { useEffect, useState } from 'react';
import { useHistory } from 'react-router-dom';
import { Spinner } from '@heroui/react';
import authService from '../services/auth';
import { addToast } from './toast-manager';
 
interface WithAuthProps {
  requireAdmin?: boolean;
}
 
const withAuth = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  options: WithAuthProps = {}
) => {
  const AuthenticatedComponent: React.FC<P> = (props) => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [user, setUser] = useState<any>(null);
    const history = useHistory();
 
    useEffect(() => {
      checkAuthentication();
    }, []);
 
    const checkAuthentication = async () => {
      try {
        setIsLoading(true);
 
        // Check if user is authenticated
        if (!authService.isAuthenticated()) {
          addToast({
            title: "Authentication Required",
            description: "Please login to access this page",
            color: "warning"
          });
          history.push('/login');
          return;
        }
 
        // Get user info and verify with backend
        const userData = await authService.getCurrentUser();
        if (!userData) {
          addToast({
            title: "Session Expired",
            description: "Your session has expired. Please login again.",
            color: "warning"
          });
          history.push('/login');
          return;
        }
 
        // Check admin requirement
        if (options.requireAdmin) {
          const adminStatus = await authService.checkAdminStatus();
          if (!adminStatus.is_admin) {
            addToast({
              title: "Access Denied",
              description: "You don't have permission to access this page",
              color: "danger"
            });
            history.push('/dashboard');
            return;
          }
        }
 
        setUser(userData);
        setIsAuthenticated(true);
 
      } catch (error: any) {
        console.error('Authentication check failed:', error);
        addToast({
          title: "Authentication Error",
          description: error.message || "Failed to verify authentication",
          color: "danger"
        });
        history.push('/login');
      } finally {
        setIsLoading(false);
      }
    };
 
    if (isLoading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <Spinner size="lg" />
            <p className="text-foreground-600 mt-4">Verifying authentication...</p>
          </div>
        </div>
      );
    }
 
    if (!isAuthenticated) {
      return null;
    }
 
    return <WrappedComponent {...props} user={user} />;
  };
 
  AuthenticatedComponent.displayName = `withAuth(${WrappedComponent.displayName || WrappedComponent.name})`;
 
  return AuthenticatedComponent;
};
 
export default withAuth;
 
 