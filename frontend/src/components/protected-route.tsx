import React from 'react';
import { Route, RouteProps } from 'react-router-dom';
import { rolePermissions } from '../config/permissions';
interface ProtectedRouteProps extends RouteProps {
  requiredPermission: string;
  component: React.ComponentType<any>;
}
 
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  requiredPermission,
  component: Component,
  ...rest
}) => {
  let role = localStorage.getItem('roles') as string | null;
 
  // Remove extra quotes if present and normalize role string to match keys in rolePermissions
  if (role) {
    try {
      role = JSON.parse(role);
    } catch {
      // If parsing fails, fallback to original string
    }
    role = role.toLowerCase().replace(/\s+/g, '_');
  }
 
  // Check if role exists and has permissions
  const hasRole = role && rolePermissions.hasOwnProperty(role) && rolePermissions[role].length > 0;
 
  // Special case: restrict 'users_only' permission to super_admin only
  let allowed = hasRole && (rolePermissions[role]?.includes(requiredPermission) || rolePermissions[role]?.includes('all'));
  if (requiredPermission === 'users_only') {
    allowed = role === 'super_admin' || role === '"super_admin"';
  }
 
 
 
  return (
    <Route
      {...rest}
      render={(props) =>
        allowed ? <Component {...props} /> : <div style={{ padding: '20px', color: 'red' }}>Access Denied: You do not have permission to view this page.</div>
      }
    />
  );
};
 
 