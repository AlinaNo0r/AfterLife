import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getNomineeInvitation, respondToNomineeInvitation } from '../../services/authService.js'
import { showAppToast } from '../../services/toastService.js'

function NomineeInvitationPage() {
  const { token } = useParams()
  const [invitation, setInvitation] = useState(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let active = true
    getNomineeInvitation(token)
      .then((data) => {
        if (active) setInvitation(data)
      })
      .catch((error) => {
        if (active) setMessage(error.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [token])

  const respond = async (decision) => {
    setSubmitting(true)
    setMessage('')
    try {
      const result = await respondToNomineeInvitation(token, decision)
      setInvitation((current) => ({ ...current, consent_status: result.consent_status }))
      setMessage(result.message || 'Your response has been recorded.')
      showAppToast(result.message || 'Your response has been recorded.', 'success', 'Invitation updated')
    } catch (error) {
      setMessage(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  const alreadyResponded = invitation && invitation.consent_status !== 'pending'

  return (
    <main className="public-decision-page">
      <section className="public-decision-card">
        <p className="public-decision-eyebrow">AFTERLIFE / TRUSTED CIRCLE</p>
        <h1>Invitation confirmation</h1>
        {loading ? (
          <p className="public-decision-copy">Checking this invitation…</p>
        ) : invitation ? (
          <>
            <p className="public-decision-copy">
              {invitation.owner_name} invited you to be a{' '}
              <strong>{invitation.role_display.toLowerCase()}</strong>.
              This decision applies only to this role.
            </p>
            {alreadyResponded ? (
              <p className="public-decision-result">
                You have already {invitation.consent_status} this invitation.
              </p>
            ) : (
              <div className="public-decision-actions">
                <button type="button" onClick={() => respond('accept')} disabled={submitting}>
                  {submitting ? 'Saving…' : 'Accept this role'}
                </button>
                <button type="button" className="public-decline" onClick={() => respond('decline')} disabled={submitting}>
                  Decline
                </button>
              </div>
            )}
          </>
        ) : null}
        {message && <p className="public-decision-message" role="status">{message}</p>}
        <Link to="/login" className="public-decision-link">Return to AfterLife</Link>
      </section>
    </main>
  )
}

export default NomineeInvitationPage
