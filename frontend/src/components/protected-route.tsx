import React from 'react';
import { Route, Redirect, RouteProps } from 'react-router-dom';
import { rolePermissions, UserRole } from '../config/permissions';

interface ProtectedRouteProps extends RouteProps {
requiredPermission: string;
component: React.ComponentType<any>;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
requiredPermission,
component: Component,
...rest
}) => {
const role = localStorage.getItem('userRole') as UserRole;
const allowed = rolePermissions[role]?.includes(requiredPermission) || rolePermissions[role]?.includes('all');

return (
<Route
{...rest}
render={(props) =>
allowed ? <Component {...props} /> : <Redirect to="/dashboard/overview" />
}
/>
);
};