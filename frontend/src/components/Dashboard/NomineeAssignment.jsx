import { useEffect, useState } from 'react'
import DashboardFeedbackToast from './DashboardFeedbackToast.jsx'

function NomineeAssignment({
  nominees,
  value,
  onSave,
  label = 'Assigned beneficiary',
  disabled = false,
  isLightTheme = false,
}) {
  const [selection, setSelection] = useState(null)
  const selectedId = selection ?? (value ? String(value) : '')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)

  useEffect(() => {
    if (!feedback) return undefined

    const timeoutId = window.setTimeout(() => setFeedback(null), feedback.tone === 'success' ? 5000 : 8000)
    return () => window.clearTimeout(timeoutId)
  }, [feedback])

  const save = async () => {
    setSaving(true)
    setFeedback(null)
    try {
      await onSave(Number(selectedId))
      setSelection(null)
      const selectedNominee = nominees.find((nominee) => String(nominee.id) === selectedId)
      setFeedback({
        tone: 'success',
        title: 'Beneficiary saved',
        message: `Assignment saved for ${selectedNominee?.nominee_name || 'this beneficiary'}. They can receive it after release conditions are met.`,
      })
    } catch (error) {
      setFeedback({
        tone: 'error',
        title: 'Assignment could not be saved',
        message: error.message || 'Please try again.',
      })
    } finally {
      setSaving(false)
    }
  }

  if (!nominees.length) {
    return <p className="assignment-empty">No accepted beneficiaries yet. Ask a contact to accept the beneficiary invitation first.</p>
  }

  const alreadyAssigned = String(value || '') === selectedId

  return (
    <div className="nominee-assignment">
      <label>
        <span>{label} <small>Shared only after release conditions are met</small></span>
        <select
          value={selectedId}
          onChange={(event) => {
            setSelection(event.target.value)
            setFeedback(null)
          }}
          disabled={disabled || saving}
        >
          <option value="">Choose a beneficiary</option>
          {nominees.map((nominee) => (
            <option key={nominee.id} value={nominee.id}>{nominee.nominee_name}</option>
          ))}
        </select>
      </label>
      <button
        type="button"
        onClick={save}
        disabled={disabled || saving || !selectedId || alreadyAssigned}
        aria-busy={saving}
      >
        {saving
          ? 'Saving…'
          : disabled
            ? 'Editing paused'
            : !selectedId
              ? 'Choose a beneficiary'
              : alreadyAssigned
                ? 'Already assigned'
                : 'Save beneficiary'}
      </button>
      <DashboardFeedbackToast
        feedback={feedback}
        isLightTheme={isLightTheme}
        onDismiss={() => setFeedback(null)}
      />
    </div>
  )
}

export default NomineeAssignment
