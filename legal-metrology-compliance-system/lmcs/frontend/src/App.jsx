import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ScanUpload from "./pages/ScanUpload";
import Repository from "./pages/Repository";
import ProductHistory from "./pages/ProductHistory";
import Reports from "./pages/Reports";
import ReportView from "./pages/ReportView";

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/scan" element={<ProtectedRoute><ScanUpload /></ProtectedRoute>} />
          <Route path="/repository" element={<ProtectedRoute><Repository /></ProtectedRoute>} />
          <Route path="/repository/:productId" element={<ProtectedRoute><ProductHistory /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
          <Route path="/reports/:reportId" element={<ProtectedRoute><ReportView /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
