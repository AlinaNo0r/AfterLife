import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { setNomineePassword } from '../../services/authService.js'

function SetNomineePasswordPage() {
  const { uid, token } = useParams()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [complete, setComplete] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setSubmitting(true)
    try {
      const result = await setNomineePassword(uid, token, {
        password,
        confirm_password: confirmPassword,
      })
      setComplete(true)
      setMessage(result.message)
      setPassword('')
      setConfirmPassword('')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="public-decision-page">
      <section className="public-decision-card">
        <p className="public-decision-eyebrow">AFTERLIFE / BENEFICIARY ACCESS</p>
        <h1>Set your password</h1>
        {complete ? (
          <>
            <p className="public-decision-message" role="status">{message}</p>
            <Link to="/login" className="public-decision-link">Continue to sign in</Link>
          </>
        ) : (
          <form className="public-password-form" onSubmit={submit}>
            <p className="public-decision-copy">
              Create a password to sign in and view assets that have been released
              to you. The link can only be used while it remains valid.
            </p>
            <label>
              <span>New password</span>
              <input
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            <label>
              <span>Confirm password</span>
              <input
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
              />
            </label>
            <button type="submit" disabled={submitting}>
              {submitting ? 'Saving…' : 'Set password'}
            </button>
          </form>
        )}
        {error && <p className="public-decision-message" role="alert">{error}</p>}
      </section>
    </main>
  )
}

export default SetNomineePasswordPage
