import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { DataProvider } from './context/DataContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import MapViewPage from './pages/MapViewPage';
import FlaggedAreasPage from './pages/FlaggedAreasPage';
import CaseDetailsPage from './pages/CaseDetailsPage';
import ReportsPage from './pages/ReportsPage';
import AdminPage from './pages/AdminPage';
import AccountPage from './pages/AccountPage';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <DataProvider>
          <Router>
            <Routes>
              {/* Public: login page (no Layout/nav) */}
              <Route path="/login" element={<LoginPage />} />

              {/* Protected: everything else gets the Layout shell */}
              <Route
                path="*"
                element={
                  <Layout>
                    <Routes>
                      <Route
                        path="/"
                        element={
                          <ProtectedRoute allowedRoles={['admin', 'employee']}>
                            <HomePage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/map"
                        element={
                          <ProtectedRoute allowedRoles={['admin']}>
                            <MapViewPage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/flagged-areas"
                        element={
                          <ProtectedRoute allowedRoles={['admin', 'employee']}>
                            <FlaggedAreasPage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/case/:id"
                        element={
                          <ProtectedRoute allowedRoles={['admin', 'employee']}>
                            <CaseDetailsPage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/reports"
                        element={
                          <ProtectedRoute allowedRoles={['admin', 'employee']}>
                            <ReportsPage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/admin"
                        element={
                          <ProtectedRoute allowedRoles={['admin']}>
                            <AdminPage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/account"
                        element={
                          <ProtectedRoute allowedRoles={['admin', 'employee']}>
                            <AccountPage />
                          </ProtectedRoute>
                        }
                      />
                    </Routes>
                  </Layout>
                }
              />
            </Routes>
          </Router>
        </DataProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;