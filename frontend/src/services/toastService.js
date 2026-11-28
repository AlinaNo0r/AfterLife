const APP_TOAST_EVENT = 'afterlife:toast'

export function showAppToast(message, tone = 'info', title = 'AfterLife', isLightTheme = false) {
  if (!message || typeof window === 'undefined') return
  const lightTheme = isLightTheme
    || document.querySelector('.dashboard-shell.light-theme') !== null

  window.dispatchEvent(new CustomEvent(APP_TOAST_EVENT, {
    detail: { message, tone, title, isLightTheme: lightTheme },
  }))
}

export { APP_TOAST_EVENT }
