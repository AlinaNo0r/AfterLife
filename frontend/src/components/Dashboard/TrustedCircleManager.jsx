import { useEffect, useState } from 'react'
import { Mail, ShieldCheck, Trash2, UsersRound } from 'lucide-react'
import DashboardFeedbackToast from './DashboardFeedbackToast.jsx'

const ROLE_OPTIONS = [
  { value: 'beneficiary', label: 'Beneficiary', description: 'May receive assigned legacy assets' },
  { value: 'witness', label: 'Death witness', description: 'May confirm the owner’s status' },
]

function getSelectedRoles(nominee) {
  return (nominee.role_statuses || []).map((role) => role.role)
}

function RoleStatus({ role }) {
  return (
    <span className={`trusted-role-status trusted-role-${role.consent_status}`}>
      {role.role === 'witness' ? 'Witness' : 'Beneficiary'} · {role.consent_status}
    </span>
  )
}

function TrustedCircleManager({
  nominees,
  settings,
  onCreate,
  onUpdate,
  onDelete,
  onResend,
  onSaveRequiredPeopleCount,
  onStayAlive,
  isCheckingIn,
  isLightTheme = false,
}) {
  const [form, setForm] = useState({
    nominee_name: '',
    nominee_email: '',
    nominee_phone: '',
    relationship: 'friend',
    roles: [],
  })
  const [editingId, setEditingId] = useState(null)
  const [editingRoles, setEditingRoles] = useState([])
  const [requiredPeopleDraft, setRequiredPeopleDraft] = useState(null)
  const requiredPeopleCount = requiredPeopleDraft ?? String(settings?.witness_quorum || 2)
  const peopleWhoAcceptedRole = settings?.accepted_witnesses || 0
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!feedback) return undefined

    const timeoutId = window.setTimeout(() => {
      setFeedback(null)
    }, feedback.tone === 'success' ? 5000 : 8000)

    return () => window.clearTimeout(timeoutId)
  }, [feedback])

  const dismissFeedback = () => setFeedback(null)

  const toggleRole = (role, current, update) => {
    update(current.includes(role)
      ? current.filter((value) => value !== role)
      : [...current, role])
  }

  const handleCreate = async (event) => {
    event.preventDefault()
    setFeedback(null)
    setBusy(true)
    const contactName = form.nominee_name.trim()
    try {
      const result = await onCreate(form)
      setForm({
        nominee_name: '',
        nominee_email: '',
        nominee_phone: '',
        relationship: 'friend',
        roles: [],
      })
      setFeedback(result.invitation_sent
        ? {
          tone: 'success',
          title: 'Contact added',
          message: `Added ${contactName} to your Trusted Circle. We sent the invitation email.`,
        }
        : {
          tone: 'warning',
          title: 'Contact added, invitation not sent',
          message: `Added ${contactName}, but we couldn't send the invitation email. You can retry from the contact card.`,
        })
    } catch (requestError) {
      setFeedback({
        tone: 'error',
        title: 'Contact could not be added',
        message: requestError.message || 'Please check the details and try again.',
      })
    } finally {
      setBusy(false)
    }
  }

  const handleRoleSave = async (nominee) => {
    setFeedback(null)
    setBusy(true)
    try {
      const result = await onUpdate(nominee.id, { roles: editingRoles })
      setEditingId(null)
      setFeedback(result.invitation_sent === false
        ? {
          tone: 'warning',
          title: 'Roles updated, invitation not sent',
          message: 'We couldn’t send the invitation email. You can retry from the contact card.',
        }
        : {
          tone: 'success',
          title: 'Roles updated',
          message: 'Your contact’s Trusted Circle roles have been updated.',
        })
    } catch (requestError) {
      setFeedback({
        tone: 'error',
        title: 'Roles could not be updated',
        message: requestError.message || 'Please try again.',
      })
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async (nominee) => {
    setFeedback(null)
    setBusy(true)
    try {
      await onDelete(nominee.id)
      setFeedback({
        tone: 'success',
        title: 'Contact removed',
        message: `${nominee.nominee_name} is no longer in your Trusted Circle.`,
      })
    } catch (requestError) {
      setFeedback({
        tone: 'error',
        title: 'Contact could not be removed',
        message: requestError.message || 'Please try again.',
      })
    } finally {
      setBusy(false)
    }
  }

  const handleResend = async (nominee) => {
    setFeedback(null)
    setBusy(true)
    try {
      const result = await onResend(nominee.id)
      setFeedback(result.invitation_sent
        ? {
          tone: 'success',
          title: 'Invitation sent',
          message: `We sent an invitation email to ${nominee.nominee_name}.`,
        }
        : {
          tone: 'warning',
          title: 'Invitation not sent',
          message: 'We couldn’t send the invitation email. Please try again later.',
        })
    } catch (requestError) {
      setFeedback({
        tone: 'error',
        title: 'Invitation could not be sent',
        message: requestError.message || 'Please try again.',
      })
    } finally {
      setBusy(false)
    }
  }

  const handleSaveRequiredPeople = async (event) => {
    event.preventDefault()
    setFeedback(null)
    setBusy(true)
    try {
      await onSaveRequiredPeopleCount(Number(requiredPeopleCount))
      setRequiredPeopleDraft(null)
      setFeedback({
        tone: 'success',
        title: 'Confirmation setting saved',
        message: `${requiredPeopleCount} trusted people must confirm before assets can be shared.`,
      })
    } catch (requestError) {
      setFeedback({
        tone: 'error',
        title: 'Confirmation setting could not be saved',
        message: requestError.message || 'Please try again.',
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="trusted-circle-layout">
      {settings?.quorum_frozen && (
        <aside className="trusted-edit-lock" role="status">
          <div>
            <strong>{settings.status === 'released' ? 'Editing is permanently locked' : 'Editing is paused'}</strong>
            <p>
              {settings.status === 'released'
                ? 'Your legacy has already been released, so Trusted Circle changes can no longer be made.'
                : `Your account is ${settings.status}. Confirm your status to unlock adding and changing contacts.`}
            </p>
          </div>
          {settings.status !== 'released' && onStayAlive && (
            <button
              className="feature-primary-action"
              type="button"
              onClick={onStayAlive}
              disabled={isCheckingIn}
            >
              {isCheckingIn ? 'Confirming status…' : 'Confirm status to unlock editing'}
            </button>
          )}
        </aside>
      )}
      <section className="feature-content-card trusted-circle-list">
        <div className="feature-content-heading">
          <div>
            <p className="feature-eyebrow">YOUR PEOPLE</p>
            <h2>Trusted contacts</h2>
          </div>
          <span className="feature-count">{nominees.length}</span>
        </div>
        {nominees.length ? (
          <div className="trusted-contact-list">
            {nominees.map((nominee) => {
              const roles = nominee.role_statuses || []
              const isEditing = editingId === nominee.id
              return (
                <article className="trusted-contact-card" key={nominee.id}>
                  <div className="trusted-contact-avatar" aria-hidden="true">
                    {(nominee.nominee_name || '?').trim().slice(0, 1).toUpperCase()}
                  </div>
                  <div className="trusted-contact-main">
                    <div className="trusted-contact-heading">
                      <div>
                        <h3>{nominee.nominee_name}</h3>
                        <p>{nominee.nominee_email} · {nominee.relationship}</p>
                      </div>
                      <button
                        type="button"
                        className="trusted-icon-action"
                        aria-label={`Remove ${nominee.nominee_name}`}
                        title="Remove contact"
                        onClick={() => handleDelete(nominee)}
                        disabled={busy || settings?.quorum_frozen}
                      >
                        <Trash2 size={16} aria-hidden="true" />
                      </button>
                    </div>
                    {isEditing ? (
                      <div className="trusted-role-editor">
                        {ROLE_OPTIONS.map((role) => (
                          <label key={role.value}>
                            <input
                              type="checkbox"
                              checked={editingRoles.includes(role.value)}
                              onChange={() => toggleRole(role.value, editingRoles, setEditingRoles)}
                            />
                            <span>{role.label}</span>
                          </label>
                        ))}
                        <div className="trusted-contact-actions">
                          <button type="button" onClick={() => handleRoleSave(nominee)} disabled={busy}>
                            Save roles
                          </button>
                          <button type="button" className="trusted-text-action" onClick={() => setEditingId(null)}>
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="trusted-role-badges">
                          {roles.map((role) => <RoleStatus role={role} key={role.id} />)}
                        </div>
                        <div className="trusted-contact-actions">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingId(nominee.id)
                              setEditingRoles(getSelectedRoles(nominee))
                            }}
                            disabled={busy || settings?.quorum_frozen}
                          >
                            Edit roles
                          </button>
                          {roles.some((role) => role.consent_status !== 'accepted') && (
                            <button type="button" className="trusted-secondary-action" onClick={() => handleResend(nominee)} disabled={busy || settings?.quorum_frozen}>
                              <Mail size={14} aria-hidden="true" />
                              Resend invitation
                            </button>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </article>
              )
            })}
          </div>
        ) : (
          <p className="feature-empty-state">No trusted contacts yet. Add the people you want in your circle.</p>
        )}
      </section>

      <section className="feature-content-card trusted-add-card">
        <div className="feature-content-heading">
          <div>
            <p className="feature-eyebrow">INVITE SOMEONE</p>
            <h2>Add a trusted contact</h2>
          </div>
          <UsersRound size={23} aria-hidden="true" />
        </div>
        <form className="trusted-form" onSubmit={handleCreate}>
          <label>
            <span>Full name</span>
            <input
              value={form.nominee_name}
              onChange={(event) => setForm({ ...form, nominee_name: event.target.value })}
              maxLength={100}
              required
            />
          </label>
          <label>
            <span>Email address</span>
            <input
              type="email"
              value={form.nominee_email}
              onChange={(event) => setForm({ ...form, nominee_email: event.target.value })}
              required
            />
          </label>
          <label>
            <span>Phone number <small>(optional)</small></span>
            <input
              value={form.nominee_phone}
              onChange={(event) => setForm({ ...form, nominee_phone: event.target.value })}
              maxLength={15}
            />
          </label>
          <label>
            <span>Relationship</span>
            <select value={form.relationship} onChange={(event) => setForm({ ...form, relationship: event.target.value })}>
              {['spouse', 'child', 'parent', 'sibling', 'friend', 'other'].map((value) => (
                <option key={value} value={value}>{value[0].toUpperCase() + value.slice(1)}</option>
              ))}
            </select>
          </label>
          <fieldset className="trusted-role-choices">
            <legend>Invite them as</legend>
            <p className="trusted-role-hint">Select at least one role to enable adding this contact.</p>
            {ROLE_OPTIONS.map((role) => (
              <label key={role.value}>
                <input
                  type="checkbox"
                  checked={form.roles.includes(role.value)}
                  onChange={() => toggleRole(role.value, form.roles, (roles) => setForm({ ...form, roles }))}
                />
                <span><strong>{role.label}</strong><small>{role.description}</small></span>
              </label>
            ))}
          </fieldset>
          <button className="feature-primary-action trusted-add-submit" type="submit" disabled={busy || form.roles.length === 0 || settings?.quorum_frozen}>
            {busy
              ? 'Sending…'
              : settings?.quorum_frozen
                ? 'Editing is paused'
                : form.roles.length === 0
                  ? 'Choose a role to continue'
                  : 'Add contact and send invitations'}
          </button>
        </form>
      </section>

      <section className="feature-content-card trusted-quorum-card">
        <div className="feature-content-heading">
          <div>
            <p className="feature-eyebrow">BEFORE SHARING YOUR LEGACY</p>
            <h2>People who can confirm your passing</h2>
          </div>
          <ShieldCheck size={23} aria-hidden="true" />
        </div>
        <p className="feature-supporting-copy">
          Choose how many trusted people must confirm your passing before your
          assigned assets are shared. Missing a check-in alone will never share
          your assets. This number locks when a check-in warning starts.
        </p>
        <form className="trusted-quorum-form" onSubmit={handleSaveRequiredPeople}>
          <label htmlFor="required-confirmations">How many people must confirm?</label>
          <input
            id="required-confirmations"
            type="number"
            min="2"
            max="20"
            value={requiredPeopleCount}
            onChange={(event) => setRequiredPeopleDraft(event.target.value)}
            disabled={settings?.quorum_frozen}
          />
          <button type="submit" disabled={busy || settings?.quorum_frozen}>Save number</button>
        </form>
        <p className={`trusted-readiness${settings?.ready ? ' is-ready' : ''}`}>
          {peopleWhoAcceptedRole} of {settings?.witness_quorum || 2} trusted people
          {' '}have accepted the confirmation role.
        </p>
      </section>
      <DashboardFeedbackToast
        feedback={feedback}
        isLightTheme={isLightTheme}
        onDismiss={dismissFeedback}
      />
    </div>
  )
}

export default TrustedCircleManager
