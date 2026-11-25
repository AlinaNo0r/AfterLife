import { useState } from 'react'
import { MessageCircleHeart, UserRoundX } from 'lucide-react'

function LegacyAIAccessManager({ nominees, accesses, onAssign, onRemove, locked }) {
  const [nomineeId, setNomineeId] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const assignedIds = new Set(accesses.map((access) => access.nominee))
  const availableNominees = nominees.filter((nominee) => !assignedIds.has(nominee.id))

  const assign = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setBusy(true)
    try {
      await onAssign(Number(nomineeId))
      setNomineeId('')
      setMessage('Legacy AI access assigned.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (access) => {
    setError('')
    setMessage('')
    setBusy(true)
    try {
      await onRemove(access.id)
      setMessage(`Access removed for ${access.nominee_name}.`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="feature-content-card legacy-access-card">
      <div className="feature-content-heading">
        <div>
          <p className="feature-eyebrow">ASSIGNED ACCESS</p>
          <h2>Legacy AI beneficiaries</h2>
        </div>
        <MessageCircleHeart size={24} aria-hidden="true" />
      </div>
      <p className="feature-supporting-copy">
        Choose accepted beneficiaries who may access the future Legacy AI experience
        after the release safeguards are satisfied. Training and conversations are
        not connected in this build.
      </p>
      {accesses.length ? (
        <div className="legacy-access-list">
          {accesses.map((access) => (
            <article className="legacy-access-row" key={access.id}>
              <div>
                <strong>{access.nominee_name}</strong>
                <span>{access.nominee_email}</span>
              </div>
              <button
                type="button"
                aria-label={`Remove Legacy AI access for ${access.nominee_name}`}
                title="Remove access"
                onClick={() => remove(access)}
                disabled={busy || locked}
              >
                <UserRoundX size={17} aria-hidden="true" />
              </button>
            </article>
          ))}
        </div>
      ) : (
        <p className="feature-empty-state">No beneficiaries have Legacy AI access yet.</p>
      )}
      <form className="legacy-access-form" onSubmit={assign}>
        <label>
          <span>Add an accepted beneficiary</span>
          <select value={nomineeId} onChange={(event) => setNomineeId(event.target.value)} required disabled={locked}>
            <option value="">Choose a beneficiary</option>
            {availableNominees.map((nominee) => (
              <option value={nominee.id} key={nominee.id}>{nominee.nominee_name}</option>
            ))}
          </select>
        </label>
        <button type="submit" className="feature-primary-action" disabled={busy || locked || !nomineeId}>
          {busy ? 'Saving…' : 'Assign access'}
        </button>
      </form>
      {message && <p className="trusted-feedback" role="status">{message}</p>}
      {error && <p className="trusted-feedback is-error" role="alert">{error}</p>}
    </section>
  )
}

export default LegacyAIAccessManager
