import { useState } from 'react'
import { Mail, Plus, ShieldCheck, Trash2, UsersRound } from 'lucide-react'

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
  onUpdateQuorum,
  onStayAlive,
  isCheckingIn,
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
  const [quorumDraft, setQuorumDraft] = useState(null)
  const quorumValue = quorumDraft ?? String(settings?.witness_quorum || 2)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const toggleRole = (role, current, update) => {
    update(current.includes(role)
      ? current.filter((value) => value !== role)
      : [...current, role])
  }

  const handleCreate = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setBusy(true)
    try {
      const result = await onCreate(form)
      setForm({
        nominee_name: '',
        nominee_email: '',
        nominee_phone: '',
        relationship: 'friend',
        roles: [],
      })
      setMessage(result.invitation_sent
        ? 'Contact added. Role invitations were sent.'
        : 'Contact saved, but at least one invitation could not be sent. Retry it below.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const handleRoleSave = async (nominee) => {
    setError('')
    setMessage('')
    setBusy(true)
    try {
      const result = await onUpdate(nominee.id, { roles: editingRoles })
      setEditingId(null)
      setMessage(result.invitation_sent === false
        ? 'Roles saved, but an invitation could not be sent. Retry it below.'
        : 'Contact roles updated.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async (nominee) => {
    setError('')
    setMessage('')
    setBusy(true)
    try {
      await onDelete(nominee.id)
      setMessage(`${nominee.nominee_name} was removed from your circle.`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const handleResend = async (nominee) => {
    setError('')
    setMessage('')
    setBusy(true)
    try {
      const result = await onResend(nominee.id)
      setMessage(result.invitation_sent
        ? 'Pending role invitations were sent.'
        : 'One or more invitations could not be sent. Try again later.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const handleQuorumSave = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setBusy(true)
    try {
      await onUpdateQuorum(Number(quorumValue))
      setQuorumDraft(null)
      setMessage('Witness quorum saved.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="trusted-circle-layout">
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
          <button className="feature-primary-action" type="submit" disabled={busy || form.roles.length === 0 || settings?.quorum_frozen}>
            <Plus size={16} aria-hidden="true" />
            {busy ? 'Sending…' : 'Add contact and send invitations'}
          </button>
        </form>
      </section>

      <section className="feature-content-card trusted-quorum-card">
        <div className="feature-content-heading">
          <div>
            <p className="feature-eyebrow">RELEASE SAFEGUARD</p>
            <h2>Witness quorum</h2>
          </div>
          <ShieldCheck size={23} aria-hidden="true" />
        </div>
        <p className="feature-supporting-copy">
          At least two accepted witnesses must confirm death. The quorum is frozen
          when a warning begins, and inactivity alone never releases assets.
        </p>
        <form className="trusted-quorum-form" onSubmit={handleQuorumSave}>
          <label htmlFor="witness-quorum">Required confirmations</label>
          <input
            id="witness-quorum"
            type="number"
            min="2"
            max="20"
            value={quorumValue}
            onChange={(event) => setQuorumDraft(event.target.value)}
            disabled={settings?.quorum_frozen}
          />
          <button type="submit" disabled={busy || settings?.quorum_frozen}>Save quorum</button>
        </form>
        <p className={`trusted-readiness${settings?.ready ? ' is-ready' : ''}`}>
          {settings?.accepted_witnesses || 0} accepted witness
          {(settings?.accepted_witnesses || 0) === 1 ? '' : 'es'} of {settings?.witness_quorum || 2} required
        </p>
        {settings?.quorum_frozen && (
          <>
            <p className="trusted-quorum-note">
              {settings.status === 'released'
                ? 'Your legacy has been released, so Trusted Circle changes are permanently locked.'
                : `Trusted Circle changes are locked while your account is ${settings.status}.`}
            </p>
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
          </>
        )}
      </section>

      {(message || error) && (
        <p className={`trusted-feedback${error ? ' is-error' : ''}`} role={error ? 'alert' : 'status'}>
          {error || message}
        </p>
      )}
    </div>
  )
}

export default TrustedCircleManager
