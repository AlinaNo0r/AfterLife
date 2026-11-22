import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Archive,
  Bell,
  KeyRound,
  LayoutDashboard,
  Moon,
  Sparkles,
  Sun,
  UsersRound,
} from 'lucide-react'
import {
  getCredentials,
  getCurrentUser,
  getNominees,
  getVaultItems,
  sendStayAlive,
} from '../../services/authService.js'
import {
  CapsulesCard,
  Hero,
  HiddenKeysCard,
  LegacyAICard,
  PulseCard,
  ReleasePlanCard,
  TrustedCircleCard,
} from './DashboardCards.jsx'
import DashboardFeatureView from './DashboardFeatureView.jsx'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'trusted-circle', label: 'Trusted Circle', icon: UsersRound },
  { id: 'hidden-keys', label: 'Hidden Keys', icon: KeyRound },
  { id: 'memory-capsules', label: 'Memory Capsules', icon: Archive },
  { id: 'legacy-ai', label: 'Legacy AI', icon: Sparkles },
]

function getList(data) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.results) ? data.results : []
}

function getInitials(name = '') {
  return name.trim().split(/\s+/).filter(Boolean).map((part) => part[0]).join('').slice(0, 2).toUpperCase()
}

function DashboardPage() {
  const navigate = useNavigate()
  const { featureId } = useParams()
  const activePage = featureId || 'dashboard'
  const contentRef = useRef(null)
  const [user, setUser] = useState(null)
  const [nominees, setNominees] = useState([])
  const [credentials, setCredentials] = useState([])
  const [vaultItems, setVaultItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastPulse, setLastPulse] = useState(null)
  const [notice, setNotice] = useState('')
  const [isCheckingIn, setIsCheckingIn] = useState(false)
  const [theme, setTheme] = useState(() => (
    localStorage.getItem('dashboardTheme') === 'light' ? 'light' : 'dark'
  ))

  useEffect(() => {
    let isMounted = true

    const loadDashboard = async () => {
      const [userResult, nomineesResult, credentialsResult, vaultItemsResult] = await Promise.allSettled([
        getCurrentUser(),
        getNominees(),
        getCredentials(),
        getVaultItems(),
      ])

      if (!isMounted) return

      if (userResult.status === 'fulfilled') setUser(userResult.value)
      else setNotice(userResult.reason?.message || 'Could not load your account.')

      setNominees(nomineesResult.status === 'fulfilled' ? getList(nomineesResult.value) : [])
      setCredentials(credentialsResult.status === 'fulfilled' ? getList(credentialsResult.value) : [])
      setVaultItems(vaultItemsResult.status === 'fulfilled' ? getList(vaultItemsResult.value) : [])
      setLoading(false)
    }

    loadDashboard()
    return () => { isMounted = false }
  }, [])

  useEffect(() => {
    if (contentRef.current) contentRef.current.scrollTop = 0
  }, [featureId])

  const handleLogout = () => {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    navigate('/login', { replace: true })
  }

  const handleThemeToggle = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark'
    localStorage.setItem('dashboardTheme', nextTheme)
    setTheme(nextTheme)
  }

  const handleStayAlive = async () => {
    setIsCheckingIn(true)
    setNotice('')
    try {
      const response = await sendStayAlive()
      setLastPulse(response.last_seen)
      setNotice(response.message || 'Check-in received. Your vault is active.')
    } catch (error) {
      setNotice(error.message || 'Could not update your check-in.')
    } finally {
      setIsCheckingIn(false)
    }
  }

  const handleNavigate = (id) => {
    navigate(id === 'dashboard' ? '/dashboard' : `/dashboard/${id}`)
  }

  const fullName = user
    ? [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || 'User'
    : 'User'
  const initials = getInitials(fullName)

  return (
    <div className={`dashboard-shell reference-dashboard${theme === 'light' ? ' light-theme' : ''}`}>
      <aside className="sidebar">
        <div className="sidebar-logo" onClick={() => handleNavigate('dashboard')}>
          <h1>DIGITAL VAULT</h1>
          <p>Protect your Digital Life</p>
        </div>

        <nav className="sidebar-nav" aria-label="Dashboard navigation">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item${activePage === item.id ? ' active' : ''}`}
              onClick={() => handleNavigate(item.id)}
            >
              <item.icon className="nav-icon" size={18} strokeWidth={1.8} aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button type="button" className="user-card" onClick={handleLogout} title="Log out">
            <span className="user-avatar">{initials}</span>
            <span className="user-info">
              <span className="user-name">{fullName}</span>
              <span className="user-status">STATUS: {user?.onboarding_completed ? 'ACTIVE' : 'SETUP'}</span>
            </span>
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="topbar-actions">
            <button
              type="button"
              className="icon-btn theme-toggle"
              onClick={handleThemeToggle}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              aria-pressed={theme === 'light'}
            >
              {theme === 'dark'
                ? <Sun size={18} strokeWidth={1.8} aria-hidden="true" />
                : <Moon size={18} strokeWidth={1.8} aria-hidden="true" />}
              <span className="theme-toggle-label">
                {theme === 'dark' ? 'Light mode' : 'Dark mode'}
              </span>
            </button>
            <button type="button" className="icon-btn" title="Notifications" aria-label="Notifications" onClick={() => setNotice('You are all caught up.')}>
              <Bell size={18} strokeWidth={1.8} aria-hidden="true" />
            </button>
            <button type="button" className="avatar-btn" title="Log out" aria-label={`Log out ${fullName}`} onClick={handleLogout}>{initials}</button>
          </div>
        </header>

        <div className="content" ref={contentRef}>
          {featureId ? (
            <DashboardFeatureView
              featureId={featureId}
              nominees={nominees}
              credentials={credentials}
              items={vaultItems}
              lastPulse={lastPulse}
              onBack={() => handleNavigate('dashboard')}
              onStayAlive={handleStayAlive}
              isCheckingIn={isCheckingIn}
            />
          ) : (
            <section id="dashboard">
              <Hero lastPulse={lastPulse} />
              <div className="grid-main">
                <TrustedCircleCard
                  nominees={nominees}
                  loading={loading}
                  onNavigate={handleNavigate}
                />
                <div className="side-cards">
                  <PulseCard
                    onStayAlive={handleStayAlive}
                    isCheckingIn={isCheckingIn}
                    onNavigate={handleNavigate}
                  />
                  <HiddenKeysCard
                    count={credentials.length}
                    loading={loading}
                    onNavigate={handleNavigate}
                  />
                </div>
              </div>
              <div className="grid-bottom">
                <CapsulesCard
                  items={vaultItems}
                  loading={loading}
                  onNavigate={handleNavigate}
                />
                <LegacyAICard onNavigate={handleNavigate} />
                <ReleasePlanCard
                  items={vaultItems}
                  loading={loading}
                  onNavigate={handleNavigate}
                />
              </div>
            </section>
          )}
          {notice && (
            <div className="toast show" role="status" onClick={() => setNotice('')}>
              <div className="toast-icon success"><span aria-hidden="true">✓</span></div>
              <div className="toast-text"><h5>Digital Vault</h5><p>{notice}</p></div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default DashboardPage
