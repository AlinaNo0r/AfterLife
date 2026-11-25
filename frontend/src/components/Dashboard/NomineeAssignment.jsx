import { useState } from 'react'

function NomineeAssignment({ nominees, value, onSave, label = 'Assigned beneficiary', disabled = false }) {
  const [selection, setSelection] = useState(null)
  const selectedId = selection ?? (value ? String(value) : '')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const save = async () => {
    setSaving(true)
    setMessage('')
    try {
      await onSave(Number(selectedId))
      setSelection(null)
      setMessage('Saved')
    } catch (error) {
      setMessage(error.message)
    } finally {
      setSaving(false)
    }
  }

  if (!nominees.length) {
    return <p className="assignment-empty">No accepted beneficiaries yet.</p>
  }

  return (
    <div className="nominee-assignment">
      <label>
        <span>{label}</span>
        <select value={selectedId} onChange={(event) => setSelection(event.target.value)} disabled={disabled}>
          <option value="">Choose a beneficiary</option>
          {nominees.map((nominee) => (
            <option key={nominee.id} value={nominee.id}>{nominee.nominee_name}</option>
          ))}
        </select>
      </label>
      <button type="button" onClick={save} disabled={disabled || saving || !selectedId || String(value || '') === selectedId}>
        {saving ? 'Saving…' : 'Save assignment'}
      </button>
      {message && <small role="status">{message}</small>}
    </div>
  )
}

export default NomineeAssignment
