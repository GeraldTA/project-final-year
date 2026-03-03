import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth, UserRole } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** Which roles are allowed to view this route. Empty = any authenticated user. */
  allowedRoles?: UserRole[];
}

/**
 * Wraps a route to require authentication and optionally a specific role.
 *
 * - Unauthenticated → redirect to /login (preserves intended URL in state)
 * - Wrong role       → redirect to /  (dashboard)
 * - Loading          → blank while token is being validated
 */
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles = [] }) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    // Briefly show nothing while the stored token is being validated
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles.length > 0 && user && !allowedRoles.includes(user.role)) {
    // Authenticated but wrong role → go to dashboard
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
