import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import MapViewPage from './pages/MapViewPage';
import FlaggedAreasPage from './pages/FlaggedAreasPage';
import CaseDetailsPage from './pages/CaseDetailsPage';
import ReportsPage from './pages/ReportsPage';
import AdminPage from './pages/AdminPage';
import { DataProvider } from './context/DataContext';

function App() {
  return (
    <ThemeProvider>
      <DataProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/map" element={<MapViewPage />} />
              <Route path="/flagged-areas" element={<FlaggedAreasPage />} />
              <Route path="/case/:id" element={<CaseDetailsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/admin" element={<AdminPage />} />
            </Routes>
          </Layout>
        </Router>
      </DataProvider>
    </ThemeProvider>
  );
}

export default App;