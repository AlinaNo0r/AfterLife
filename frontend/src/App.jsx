import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import AuthPage from './components/Auth/AuthPage.jsx'
import EmailVerificationPage from './components/Auth/EmailVerificationPage.jsx'
import OnboardingFlow from './components/Onboarding/OnboardingFlow.jsx'
import DashboardPage from './components/Dashboard/DashboardPage.jsx'

function RequireAuth({ children }) {
  return localStorage.getItem('accessToken')
    ? children
    : <Navigate to="/login" replace />
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<AuthPage />} />
        <Route path="/signup" element={<AuthPage />} />
        <Route path="/verify-email" element={<EmailVerificationPage />} />
        <Route path="/onboarding" element={<RequireAuth><OnboardingFlow /></RequireAuth>} />
        <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
        <Route path="/dashboard/:featureId" element={<RequireAuth><DashboardPage /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
