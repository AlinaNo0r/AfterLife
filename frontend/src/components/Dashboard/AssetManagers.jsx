import { useEffect, useRef, useState } from 'react'
import { FileText, KeyRound, Pencil, Trash2 } from 'lucide-react'
import DashboardFeedbackToast from './DashboardFeedbackToast.jsx'
import NomineeAssignment from './NomineeAssignment.jsx'

const emptyCredentialForm = () => ({
  platform: '',
  platform_url: '',
  username_on_platform: '',
  email_on_platform: '',
  password: '',
  assigned_nominee_id: '',
})

function CredentialsManager({
  credentials,
  nominees,
  onCreate,
  onAssign,
  onUpdate,
  onDelete,
  locked,
  isLightTheme,
}) {
  const [form, setForm] = useState(emptyCredentialForm)
  const [editingId, setEditingId] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [pendingDeleteId, setPendingDeleteId] = useState(null)

  useEffect(() => {
    if (!feedback) return undefined

    const timeoutId = window.setTimeout(() => setFeedback(null), feedback.tone === 'success' ? 5000 : 8000)
    return () => window.clearTimeout(timeoutId)
  }, [feedback])

  const cancelEdit = () => {
    setEditingId(null)
    setForm(emptyCredentialForm())
    setFeedback(null)
  }

  const submit = async (event) => {
    event.preventDefault()
    setFeedback(null)
    setBusy(true)
    try {
      const credentialData = {
        ...form,
        assigned_nominee_id: Number(form.assigned_nominee_id),
      }
      if (editingId && !credentialData.password) {
        delete credentialData.password
      }

      if (editingId) {
        await onUpdate(editingId, credentialData)
        setFeedback({
          tone: 'success',
          title: 'Credential updated',
          message: 'Your saved password stayed unchanged unless you entered a replacement.',
        })
      } else {
        await onCreate(credentialData)
        setFeedback({
          tone: 'success',
          title: 'Credential saved',
          message: 'Your chosen beneficiary can receive it after release conditions are met.',
        })
      }
      setEditingId(null)
      setForm(emptyCredentialForm())
    } catch (requestError) {
      setFeedback({
        tone: 'error',
        title: editingId ? 'Credential could not be updated' : 'Credential could not be saved',
        message: requestError.message || 'Please check the details and try again.',
      })
    } finally {
      setBusy(false)
    }
  }

  const beginEdit = (credential) => {
    setPendingDeleteId(null)
    setEditingId(credential.id)
    setForm({
      platform: credential.platform || '',
      platform_url: credential.platform_url || '',
      username_on_platform: credential.username_on_platform || '',
      email_on_platform: credential.email_on_platform || '',
      password: '',
      assigned_nominee_id: credential.nominee_details?.id
        ? String(credential.nominee_details.id)
        : '',
    })
    setFeedback(null)
  }

  const removeCredential = async (credential) => {
    setFeedback(null)
    setDeletingId(credential.id)
    try {
      await onDelete(credential.id)
      setPendingDeleteId(null)
      if (editingId === credential.id) cancelEdit()
      setFeedback({
        tone: 'success',
        title: 'Credential deleted',
        message: `${credential.platform || 'Credential'} was removed from your Hidden Keys.`,
      })
    } catch (requestError) {
      setFeedback({
        tone: 'error',
        title: 'Credential could not be deleted',
        message: requestError.message || 'Please try again.',
      })
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section className="feature-content-card asset-manager-card">
      <div className="feature-content-heading">
        <div>
          <p className="feature-eyebrow">ACCOUNT RECORDS</p>
          <h2>Saved credentials</h2>
        </div>
        <span className="feature-count">{credentials.length}</span>
      </div>
      <p className="feature-supporting-copy">
        Passwords are never displayed here or sent by email. Assign each credential
        to a contact who has accepted the beneficiary role.
      </p>
      {credentials.length ? (
        <div className="asset-manager-list">
          {credentials.map((credential) => (
            <article className="asset-manager-row" key={credential.id}>
              <div className="asset-manager-title">
                <span className="feature-row-icon" aria-hidden="true"><KeyRound size={18} /></span>
                <div>
                  <h3>{credential.platform || 'Saved account'}</h3>
                  <p>{credential.username_on_platform || credential.email_on_platform || credential.platform_url}</p>
                </div>
              </div>
              <div className="credential-actions">
                {pendingDeleteId === credential.id ? (
                  <>
                    <span className="credential-delete-confirm" role="status">
                      Delete this credential? This cannot be undone.
                    </span>
                    <button
                      type="button"
                      className="credential-action is-danger"
                      onClick={() => removeCredential(credential)}
                      disabled={locked || busy || deletingId !== null}
                    >
                      <Trash2 size={15} aria-hidden="true" />
                      {deletingId === credential.id ? 'Deleting…' : 'Confirm delete'}
                    </button>
                    <button
                      type="button"
                      className="credential-action"
                      onClick={() => setPendingDeleteId(null)}
                      disabled={deletingId !== null}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      className="credential-action"
                      onClick={() => beginEdit(credential)}
                      disabled={locked || busy || deletingId !== null}
                    >
                      <Pencil size={15} aria-hidden="true" />
                      Edit
                    </button>
                    <button
                      type="button"
                      className="credential-action is-danger"
                      onClick={() => {
                        setFeedback(null)
                        setPendingDeleteId(credential.id)
                      }}
                      disabled={locked || busy || deletingId !== null}
                    >
                      <Trash2 size={15} aria-hidden="true" />
                      Delete
                    </button>
                  </>
                )}
              </div>
              <NomineeAssignment
                nominees={nominees}
                value={credential.nominee_details?.id}
                onSave={(nomineeId) => onAssign(credential.id, nomineeId)}
                disabled={locked}
                isLightTheme={isLightTheme}
              />
            </article>
          ))}
        </div>
      ) : (
        <p className="feature-empty-state">No credentials have been saved yet.</p>
      )}
      <DashboardFeedbackToast
        feedback={feedback}
        isLightTheme={isLightTheme}
        onDismiss={() => setFeedback(null)}
      />
      <form className="asset-entry-form" onSubmit={submit}>
        <h3>{editingId ? 'Edit credential' : 'Add a credential'}</h3>
        <fieldset className="asset-entry-grid asset-entry-fields" disabled={locked || busy}>
          <label>
            <span>Platform</span>
            <input value={form.platform} onChange={(event) => setForm({ ...form, platform: event.target.value })} required />
          </label>
          <label>
            <span>Platform URL</span>
            <input type="url" value={form.platform_url} onChange={(event) => setForm({ ...form, platform_url: event.target.value })} required />
          </label>
          <label>
            <span>Username</span>
            <input value={form.username_on_platform} onChange={(event) => setForm({ ...form, username_on_platform: event.target.value })} required />
          </label>
          <label>
            <span>Account email</span>
            <input type="email" value={form.email_on_platform} onChange={(event) => setForm({ ...form, email_on_platform: event.target.value })} required />
          </label>
          <label>
            <span>{editingId ? 'New password (optional)' : 'Password'}</span>
            <input
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
              required={!editingId}
              placeholder={editingId ? 'Leave blank to keep the current password' : ''}
            />
          </label>
          <label>
            <span>Beneficiary</span>
            <select value={form.assigned_nominee_id} onChange={(event) => setForm({ ...form, assigned_nominee_id: event.target.value })} required>
              <option value="">Choose a beneficiary</option>
              {nominees.map((nominee) => <option value={nominee.id} key={nominee.id}>{nominee.nominee_name}</option>)}
            </select>
          </label>
        </fieldset>
        <button className="feature-primary-action" type="submit" disabled={locked || busy || nominees.length === 0}>
          {busy ? 'Saving…' : editingId ? 'Save changes' : 'Save credential'}
        </button>
        {editingId && (
          <button type="button" className="credential-cancel-edit" onClick={cancelEdit} disabled={busy}>
            Cancel editing
          </button>
        )}
        {nominees.length === 0 && (
          <p className="credential-help">
            A contact must accept the beneficiary invitation before you can save or reassign a credential.
          </p>
        )}
      </form>
    </section>
  )
}

function MemoryCapsuleManager({
  items,
  nominees,
  onCreate,
  onUpdate,
  onDelete,
  locked,
  isLightTheme,
}) {
  const [title, setTitle] = useState('')
  const [file, setFile] = useState(null)
  const [nomineeId, setNomineeId] = useState('')
  const [releaseType, setReleaseType] = useState('killswitch')
  const [scheduledDate, setScheduledDate] = useState('')
  const [recurringIntervalDays, setRecurringIntervalDays] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [pendingDeleteId, setPendingDeleteId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  const formRef = useRef(null)

  useEffect(() => {
    if (!feedback) return undefined

    const timeoutId = window.setTimeout(
      () => setFeedback(null),
      feedback.tone === 'success' ? 5000 : 8000,
    )
    return () => window.clearTimeout(timeoutId)
  }, [feedback])

  const resetForm = () => {
    setEditingId(null)
    setTitle('')
    setFile(null)
    setNomineeId('')
    setReleaseType('killswitch')
    setScheduledDate('')
    setRecurringIntervalDays('')
  }

  const beginEdit = (item) => {
    setPendingDeleteId(null)
    setEditingId(item.id)
    setTitle(item.title || '')
    setFile(null)
    setNomineeId(String(item.recipient))
    setReleaseType(item.release_type || 'killswitch')
    setScheduledDate(item.scheduled_date || '')
    setRecurringIntervalDays(item.recurring_interval_days ? String(item.recurring_interval_days) : '')
    setFeedback(null)
    requestAnimationFrame(() => {
      formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }

  const submit = async (event) => {
    event.preventDefault()
    const formElement = event.currentTarget
    const isEditing = editingId !== null
    setFeedback(null)
    setBusy(true)
    try {
      const formData = new FormData()
      formData.append('title', title.trim())
      formData.append('recipient', nomineeId)
      formData.append('release_type', releaseType)
      if (file) formData.append('file', file)
      if (scheduledDate) formData.append('scheduled_date', scheduledDate)
      if (releaseType === 'recurring' && recurringIntervalDays) {
        formData.append('recurring_interval_days', recurringIntervalDays)
      }

      if (isEditing) {
        await onUpdate(editingId, formData)
      } else {
        await onCreate(formData)
      }
      resetForm()
      formElement.reset()
      setFeedback({
        tone: 'success',
        title: isEditing ? 'Vault item updated' : 'Vault item saved',
        message: isEditing
          ? 'Your vault item details were updated.'
          : 'Your vault item was saved and assigned to the selected beneficiary.',
      })
    } catch (requestError) {
      setFeedback({
        tone: 'error',
        title: isEditing ? 'Vault item could not be updated' : 'Vault item could not be saved',
        message: requestError.message || 'Please check the details and try again.',
      })
    } finally {
      setBusy(false)
    }
  }

  const removeVaultItem = async (item) => {
    setFeedback(null)
    setDeletingId(item.id)
    try {
      await onDelete(item.id)
      setPendingDeleteId(null)
      if (editingId === item.id) resetForm()
      setFeedback({
        tone: 'success',
        title: 'Vault item deleted',
        message: `${item.title || 'Vault item'} was permanently removed.`,
      })
    } catch (requestError) {
      setFeedback({
        tone: 'error',
        title: 'Vault item could not be deleted',
        message: requestError.message || 'Please try again.',
      })
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section className="feature-content-card asset-manager-card">
      <div className="feature-content-heading">
        <div>
          <p className="feature-eyebrow">PRESERVED FILES</p>
          <h2>Your vault items</h2>
        </div>
        <span className="feature-count">{items.length}</span>
      </div>
      {items.length ? (
        <div className="asset-manager-list">
          {items.map((item) => (
            <article
              className={`asset-manager-row vault-item-row${editingId === item.id ? ' is-editing' : ''}`}
              key={item.id}
            >
              <div className="asset-manager-title">
                <span className="feature-row-icon" aria-hidden="true"><FileText size={18} /></span>
                <div>
                  <h3>{item.title || 'Vault item'}</h3>
                  <p>
                    {item.is_sent
                      ? 'Released'
                      : item.last_sent_at
                        ? `Recurring · last sent ${item.last_sent_at}`
                        : item.release_type === 'scheduled'
                          ? `Scheduled for ${item.scheduled_date || 'a selected date'}`
                          : item.release_type === 'recurring'
                            ? `Recurring from ${item.scheduled_date || 'a selected date'}`
                            : 'Shared after required witnesses confirm passing'}
                  </p>
                </div>
              </div>
              <div className="vault-item-beneficiary">
                <span>Beneficiary</span>
                <strong>
                  {nominees.find((nominee) => String(nominee.id) === String(item.recipient))?.nominee_name
                    || 'Contact unavailable'}
                </strong>
              </div>
              <div className="credential-actions vault-item-actions">
                {pendingDeleteId === item.id ? (
                  <>
                    <span className="credential-delete-confirm" role="status">
                      Delete this vault item? This cannot be undone.
                    </span>
                    <button
                      type="button"
                      className="credential-action is-danger"
                      onClick={() => removeVaultItem(item)}
                      disabled={locked || busy || deletingId !== null}
                    >
                      <Trash2 size={15} aria-hidden="true" />
                      {deletingId === item.id ? 'Deleting…' : 'Confirm delete'}
                    </button>
                    <button
                      type="button"
                      className="credential-action"
                      onClick={() => setPendingDeleteId(null)}
                      disabled={deletingId !== null}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      className="credential-action"
                      onClick={() => beginEdit(item)}
                      disabled={locked || busy || deletingId !== null}
                    >
                      <Pencil size={15} aria-hidden="true" />
                      Edit
                    </button>
                    <button
                      type="button"
                      className="credential-action is-danger"
                      onClick={() => {
                        setFeedback(null)
                        setPendingDeleteId(item.id)
                      }}
                      disabled={locked || busy || deletingId !== null}
                    >
                      <Trash2 size={15} aria-hidden="true" />
                      Delete
                    </button>
                  </>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p className="feature-empty-state">No vault items have been saved yet.</p>
      )}
      <DashboardFeedbackToast
        feedback={feedback}
        isLightTheme={isLightTheme}
        onDismiss={() => setFeedback(null)}
      />
      <form className="asset-entry-form" onSubmit={submit} ref={formRef}>
        <h3>{editingId !== null ? 'Edit vault item' : 'Add a vault item'}</h3>
        <fieldset
          className="asset-entry-grid asset-entry-fields"
          disabled={locked || busy || deletingId !== null}
        >
          <label>
            <span>Title</span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
          </label>
          <label>
            <span>{editingId !== null ? 'Replace file (optional)' : 'Choose a file'}</span>
            <input
              type="file"
              key={editingId ?? 'new-vault-item'}
              accept=".mp4,.mov,.avi,.mkv,.webm,.jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.txt"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              required={editingId === null}
            />
            <small className="vault-item-help">
              Supported files: MP4, MOV, AVI, MKV, WEBM; JPG, JPEG, PNG, GIF; PDF, DOC, DOCX, TXT.
              {editingId !== null && ' Leave blank to keep the current file.'}
            </small>
          </label>
          <label>
            <span>Beneficiary</span>
            <select value={nomineeId} onChange={(event) => setNomineeId(event.target.value)} required>
              <option value="">Choose a beneficiary</option>
              {nominees.map((nominee) => <option value={nominee.id} key={nominee.id}>{nominee.nominee_name}</option>)}
            </select>
          </label>
          <label>
            <span>Release type</span>
            <select value={releaseType} onChange={(event) => setReleaseType(event.target.value)}>
              <option value="killswitch">After confirmed passing</option>
              <option value="scheduled">On a specific date</option>
              <option value="recurring">Repeat on a schedule</option>
            </select>
          </label>
          {releaseType !== 'killswitch' && (
            <label>
              <span>{releaseType === 'recurring' ? 'First release date' : 'Release date'}</span>
              <input
                type="date"
                value={scheduledDate}
                onChange={(event) => setScheduledDate(event.target.value)}
                required
              />
            </label>
          )}
          {releaseType === 'recurring' && (
            <label>
              <span>Repeat every (days)</span>
              <input
                type="number"
                min="1"
                step="1"
                value={recurringIntervalDays}
                onChange={(event) => setRecurringIntervalDays(event.target.value)}
                required
              />
            </label>
          )}
        </fieldset>
        <p className="vault-item-help" aria-live="polite">
          {releaseType === 'killswitch'
            ? 'A missed check-in starts a warning. This item is shared only after the required witnesses confirm passing; inactivity alone never releases it.'
            : releaseType === 'scheduled'
              ? 'This item is sent once on or after the selected date, provided the beneficiary has accepted their role.'
              : 'This item is first sent on or after the selected date, then sent again every set number of days to an accepted beneficiary.'}
        </p>
        <div className="vault-item-form-actions">
          <button
            className="feature-primary-action vault-item-submit"
            type="submit"
            disabled={
              locked ||
              busy ||
              deletingId !== null ||
              nominees.length === 0 ||
              (editingId === null && !file)
            }
          >
            {busy ? 'Saving…' : editingId !== null ? 'Save changes' : 'Save vault item'}
          </button>
          {editingId !== null && (
            <button
              type="button"
              className="credential-cancel-edit"
              onClick={resetForm}
              disabled={busy || deletingId !== null}
            >
              Cancel editing
            </button>
          )}
        </div>
      </form>
    </section>
  )
}

export { CredentialsManager, MemoryCapsuleManager }
