function AuthTabs({ mode, onModeChange }) {
  return (
    <div className="auth-tabs">
      <button
        className={mode === 'login' ? 'active' : ''}
        onClick={() => onModeChange('login')}
      >
        Log in
      </button>

      <button
        className={mode === 'signup' ? 'active' : ''}
        onClick={() => onModeChange('signup')}
      >
        Sign up
      </button>
    </div>
  )
}

export default AuthTabs