import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { APP_TOAST_EVENT } from '../services/toastService.js'

function AppToastHost() {
  const [toasts, setToasts] = useState([])
  const nextId = useRef(0)
  const recentMessages = useRef(new Map())
  const timers = useRef(new Map())

  const dismiss = useCallback((id) => {
    window.clearTimeout(timers.current.get(id))
    timers.current.delete(id)
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  useEffect(() => {
    const activeTimers = timers.current
    const handleToast = (event) => {
      const { message, tone = 'info', title = 'AfterLife', isLightTheme = false } = event.detail || {}
      if (!message) return

      const now = Date.now()
      const previousTime = recentMessages.current.get(`${tone}:${message}`)
      if (previousTime && now - previousTime < 1000) return
      recentMessages.current.set(`${tone}:${message}`, now)

      const id = nextId.current++
      const toast = { id, message, tone, title, isLightTheme }
      setToasts((current) => [...current.slice(-2), toast])
      timers.current.set(id, window.setTimeout(() => dismiss(id), tone === 'error' ? 8000 : 5500))
    }

    window.addEventListener(APP_TOAST_EVENT, handleToast)
    return () => {
      window.removeEventListener(APP_TOAST_EVENT, handleToast)
      activeTimers.forEach((timer) => window.clearTimeout(timer))
      activeTimers.clear()
    }
  }, [dismiss])

  if (!toasts.length) return null

  return createPortal(
    <div className="app-toast-stack" aria-label="Notifications">
      {toasts.map((toast) => (
        <div
          className={`app-toast is-${toast.tone}${toast.isLightTheme ? ' is-light' : ''}`}
          key={toast.id}
          role={toast.tone === 'error' ? 'alert' : 'status'}
          aria-atomic="true"
        >
          <span className="app-toast-indicator" aria-hidden="true">
            {toast.tone === 'success' ? '✓' : toast.tone === 'error' ? '!' : 'i'}
          </span>
          <div className="app-toast-copy">
            <strong>{toast.title}</strong>
            <p>{toast.message}</p>
          </div>
          <button type="button" onClick={() => dismiss(toast.id)} aria-label="Dismiss notification">×</button>
        </div>
      ))}
    </div>,
    document.body,
  )
}

export default AppToastHost
