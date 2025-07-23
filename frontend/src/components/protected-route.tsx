import React from 'react';
import { Route, RouteProps } from 'react-router-dom';

interface ProtectedRouteProps extends RouteProps {
  requiredPermission: string;
  component: React.ComponentType<any>;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  requiredPermission,
  component: Component,
  ...rest
}) => {
  let permissions = localStorage.getItem('permissions') as string | null;

  // Parse permissions array from localStorage
  let permissionsList: string[] = [];
  if (permissions) {
    try {
      permissionsList = JSON.parse(permissions);
    } catch {
      permissionsList = [];
    }
  }

  // Check if user has required permission or 'all'
  let allowed = permissionsList.includes(requiredPermission) || permissionsList.includes('all');

  // Special case: restrict 'users_only' permission to 'all' or specific roles if needed
  if (requiredPermission === 'users_only') {
    allowed = permissionsList.includes('all');
  }

  // Debug logs
  console.log('ProtectedRoute:', { requiredPermission, allowed, permissions: permissionsList });

  return (
    <Route
      {...rest}
      render={(props) =>
        allowed ? <Component {...props} /> : <div style={{ padding: '20px', color: 'red' }}>Access Denied: You do not have permission to view this page.</div>
      }
    />
  );
};
 
 