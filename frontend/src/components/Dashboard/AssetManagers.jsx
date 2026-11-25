import { useState } from 'react'
import { FileText, KeyRound } from 'lucide-react'
import NomineeAssignment from './NomineeAssignment.jsx'

function CredentialsManager({ credentials, nominees, onCreate, onAssign, locked }) {
  const [form, setForm] = useState({
    platform: '',
    platform_url: '',
    username_on_platform: '',
    email_on_platform: '',
    password: '',
    assigned_nominee_id: '',
  })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setMessage('')
    setError('')
    setBusy(true)
    try {
      await onCreate(form)
      setForm({
        platform: '',
        platform_url: '',
        username_on_platform: '',
        email_on_platform: '',
        password: '',
        assigned_nominee_id: '',
      })
      setMessage('Credential saved securely and assigned.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
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
              <NomineeAssignment
                nominees={nominees}
                value={credential.nominee_details?.id}
                onSave={(nomineeId) => onAssign(credential.id, nomineeId)}
                disabled={locked}
              />
            </article>
          ))}
        </div>
      ) : (
        <p className="feature-empty-state">No credentials have been saved yet.</p>
      )}
      <form className="asset-entry-form" onSubmit={submit}>
        <h3>Add a credential</h3>
        <fieldset className="asset-entry-grid asset-entry-fields" disabled={locked}>
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
            <span>Password</span>
            <input type="password" autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required />
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
          {busy ? 'Saving…' : 'Save credential'}
        </button>
        {message && <p className="trusted-feedback" role="status">{message}</p>}
        {error && <p className="trusted-feedback is-error" role="alert">{error}</p>}
      </form>
    </section>
  )
}

function MemoryCapsuleManager({ items, nominees, onCreate, onAssign, locked }) {
  const [title, setTitle] = useState('')
  const [file, setFile] = useState(null)
  const [nomineeId, setNomineeId] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    const formElement = event.currentTarget
    setMessage('')
    setError('')
    setBusy(true)
    try {
      const formData = new FormData()
      formData.append('title', title.trim())
      formData.append('file', file)
      formData.append('recipient', nomineeId)
      formData.append('release_type', 'killswitch')
      await onCreate(formData)
      setTitle('')
      setFile(null)
      setNomineeId('')
      formElement.reset()
      setMessage('Memory capsule saved and assigned.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="feature-content-card asset-manager-card">
      <div className="feature-content-heading">
        <div>
          <p className="feature-eyebrow">PRESERVED FILES</p>
          <h2>Your capsules</h2>
        </div>
        <span className="feature-count">{items.length}</span>
      </div>
      {items.length ? (
        <div className="asset-manager-list">
          {items.map((item) => (
            <article className="asset-manager-row" key={item.id}>
              <div className="asset-manager-title">
                <span className="feature-row-icon" aria-hidden="true"><FileText size={18} /></span>
                <div>
                  <h3>{item.title || 'Memory capsule'}</h3>
                  <p>{item.is_sent ? 'Released' : 'Locked until release conditions are met'}</p>
                </div>
              </div>
              <NomineeAssignment
                nominees={nominees}
                value={item.recipient}
                onSave={(recipient) => onAssign(item.id, recipient)}
                disabled={locked}
              />
            </article>
          ))}
        </div>
      ) : (
        <p className="feature-empty-state">No memory capsules have been saved yet.</p>
      )}
      <form className="asset-entry-form" onSubmit={submit}>
        <h3>Add a memory capsule</h3>
        <fieldset className="asset-entry-grid asset-entry-fields" disabled={locked}>
          <label>
            <span>Title</span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
          </label>
          <label>
            <span>Choose a file</span>
            <input
              type="file"
              accept=".mp4,.mov,.avi,.mkv,.webm,.jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.txt"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              required
            />
          </label>
          <label>
            <span>Beneficiary</span>
            <select value={nomineeId} onChange={(event) => setNomineeId(event.target.value)} required>
              <option value="">Choose a beneficiary</option>
              {nominees.map((nominee) => <option value={nominee.id} key={nominee.id}>{nominee.nominee_name}</option>)}
            </select>
          </label>
        </fieldset>
        <button className="feature-primary-action" type="submit" disabled={locked || busy || nominees.length === 0 || !file}>
          {busy ? 'Saving…' : 'Save memory capsule'}
        </button>
        {message && <p className="trusted-feedback" role="status">{message}</p>}
        {error && <p className="trusted-feedback is-error" role="alert">{error}</p>}
      </form>
    </section>
  )
}

export { CredentialsManager, MemoryCapsuleManager }
