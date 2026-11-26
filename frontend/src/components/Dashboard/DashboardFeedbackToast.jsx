import { createPortal } from 'react-dom'

function DashboardFeedbackToast({ feedback, isLightTheme = false, onDismiss }) {
  if (!feedback) return null

  return createPortal(
    <div className={`toast dashboard-feedback-toast is-${feedback.tone}${isLightTheme ? ' is-light' : ''}`}>
      <span className="dashboard-feedback-indicator" aria-hidden="true">
        {feedback.tone === 'success' ? '✓' : '!'}
      </span>
      <div
        className="dashboard-feedback-copy"
        role={feedback.tone === 'error' ? 'alert' : 'status'}
        aria-atomic="true"
      >
        <strong>{feedback.title}</strong>
        <p>{feedback.message}</p>
      </div>
      <button
        type="button"
        className="dashboard-feedback-dismiss"
        onClick={onDismiss}
        aria-label="Dismiss notification"
      >
        ×
      </button>
    </div>,
    document.body,
  )
}

export default DashboardFeedbackToast
