import { useEffect } from 'react'
import { showAppToast } from '../../services/toastService.js'

function DashboardFeedbackToast({ feedback, isLightTheme = false, onDismiss }) {
  useEffect(() => {
    if (!feedback) return
    showAppToast(feedback.message, feedback.tone, feedback.title, isLightTheme)
    onDismiss?.()
  }, [feedback, isLightTheme, onDismiss])

  return null
}

export default DashboardFeedbackToast
