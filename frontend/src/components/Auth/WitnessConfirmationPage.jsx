import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { submitWitnessVote } from '../../services/authService.js'
import { showAppToast } from '../../services/toastService.js'

function WitnessConfirmationPage() {
  const { token } = useParams()
  const [message, setMessage] = useState('')
  const [decision, setDecision] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const vote = async (choice) => {
    setSubmitting(true)
    setMessage('')
    try {
      const result = await submitWitnessVote(token, choice)
      setDecision(choice)
      setMessage(result.message)
      showAppToast(result.message, 'success', 'Witness response recorded')
    } catch (error) {
      setMessage(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="public-decision-page">
      <section className="public-decision-card">
        <p className="public-decision-eyebrow">AFTERLIFE / WITNESS CHECK</p>
        <h1>Confirm their status</h1>
        <p className="public-decision-copy">
          Your response is one part of the owner’s witness quorum. Assets stay
          locked unless the configured number of accepted witnesses confirms
          death. Choose only what you know to be true.
        </p>
        {!decision && (
          <div className="public-decision-actions">
            <button type="button" onClick={() => vote('alive')} disabled={submitting}>
              {submitting ? 'Saving…' : 'They are alive'}
            </button>
            <button type="button" className="public-decline" onClick={() => vote('death')} disabled={submitting}>
              They have passed away
            </button>
          </div>
        )}
        {message && <p className="public-decision-message" role="status">{message}</p>}
        <Link to="/login" className="public-decision-link">Return to AfterLife</Link>
      </section>
    </main>
  )
}

export default WitnessConfirmationPage
