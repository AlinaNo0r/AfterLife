import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { resendRegistrationCode, verifyRegistrationCode } from '../../services/authService.js'

function EmailVerificationPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [email, setEmail] = useState(
    location.state?.email || sessionStorage.getItem('verificationEmail') || '',
  )
  const [otp, setOtp] = useState('')
  const [message, setMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [resendCooldown, setResendCooldown] = useState(0)

  const handleVerify = async (event) => {
    event.preventDefault()
    setMessage('')
    setIsSubmitting(true)

    try {
      const data = await verifyRegistrationCode({ email, otp })
      localStorage.setItem('accessToken', data.access)
      localStorage.setItem('refreshToken', data.refresh)
      sessionStorage.removeItem('verificationEmail')
      navigate('/onboarding', { replace: true })
    } catch (error) {
      setMessage(error.message || 'Could not verify the code. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleResend = async () => {
    if (resendCooldown > 0) return

    setMessage('')
    setIsSubmitting(true)
    setResendCooldown(30)

    try {
      const data = await resendRegistrationCode(email)
      setMessage(data.message)
    } catch (error) {
      setMessage(error.message || 'Could not send a new code. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  useState(() => {
    if (resendCooldown <= 0) return undefined

    const timer = window.setInterval(() => {
      setResendCooldown((current) => {
        if (current <= 1) {
          window.clearInterval(timer)
          return 0
        }
        return current - 1
      })
    }, 1000)

    return () => window.clearInterval(timer)
  })

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="verification-title">
        <div className="auth-panel-inner">
          <h1 id="verification-title" className="auth-page-title">Verify your email</h1>
          <p className="auth-page-copy">Enter the six-digit code we sent to your email address.</p>
          <form onSubmit={handleVerify}>
            <label>
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
              />
            </label>
            <label>
              <span>Verification code</span>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                value={otp}
                onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="6-digit code"
                required
              />
            </label>
            <button className="submit-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Please wait...' : 'Verify email'}
            </button>
            <button className="text-button verification-resend" type="button" onClick={handleResend} disabled={isSubmitting || !email || resendCooldown > 0}>
              {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : 'Resend code'}
            </button>
            {message && <p className="form-message" role="status">{message}</p>}
          </form>
          <p className="switch-text verification-back">Wrong email? <Link to="/signup">Go back to signup</Link></p>
        </div>
      </section>
    </main>
  )
}

export default EmailVerificationPage