import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import AuthTabs from './AuthTabs.jsx'
import { loginUser, registerUser } from '../../services/authService.js'

const EMPTY_FORM = {
  fullName: '',
  email: '',
  phone: '',
  dob: '',
  gender: '',
  password: '',
  confirmPassword: '',
}

const COUNTRY_CODES = [
  ['PK', 'Pakistan', '+92'],
  ['US', 'United States', '+1'],
  ['GB', 'United Kingdom', '+44'],
  ['CA', 'Canada', '+1'],
  ['AU', 'Australia', '+61'],
  ['AE', 'United Arab Emirates', '+971'],
  ['SA', 'Saudi Arabia', '+966'],
  ['IN', 'India', '+91'],
  ['BD', 'Bangladesh', '+880'],
  ['TR', 'Türkiye', '+90'],
  ['DE', 'Germany', '+49'],
  ['FR', 'France', '+33'],
  ['IT', 'Italy', '+39'],
  ['ES', 'Spain', '+34'],
  ['NL', 'Netherlands', '+31'],
  ['SE', 'Sweden', '+46'],
  ['NO', 'Norway', '+47'],
  ['NZ', 'New Zealand', '+64'],
  ['MY', 'Malaysia', '+60'],
  ['SG', 'Singapore', '+65'],
]

function PasswordField({ name, value, onChange, placeholder }) {
  const [isVisible, setIsVisible] = useState(false)

  return (
    <div className="password-field">
      <input
        type={isVisible ? 'text' : 'password'}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required
      />
      <button
        type="button"
        className="password-toggle"
        onClick={() => setIsVisible((current) => !current)}
        aria-label={isVisible ? 'Hide password' : 'Show password'}
      >
        {isVisible ? 'Hide' : 'Show'}
      </button>
    </div>
  )
}

function AuthPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState(location.pathname === '/signup' ? 'signup' : 'login')
  const [rememberMe, setRememberMe] = useState(false)
  const [countryCode, setCountryCode] = useState('+92')
  const [message, setMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState(EMPTY_FORM)

  const handleChange = (event) => {
    const { name, value } = event.target
    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  const resetForm = () => {
    setFormData(EMPTY_FORM)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setMessage('')

    if (mode === 'signup' && formData.password !== formData.confirmPassword) {
      setMessage('Passwords do not match.')
      return
    }

    if (mode === 'signup') {
      const password = formData.password
      if (password.length < 8 || !/[A-Z]/.test(password) || !/\d/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
        setMessage('Password needs 8 characters, an uppercase letter, a number, and a special character.')
        return
      }

      const cleanedPhone = formData.phone.trim().replace(/[\s()-]/g, '')
      const phoneDigits = cleanedPhone.replace(/\D/g, '')
      const dialDigits = countryCode.slice(1)
      const internationalPhone = !cleanedPhone
        ? ''
        : cleanedPhone.startsWith('+')
          ? `+${phoneDigits}`
          : `+${phoneDigits.startsWith(dialDigits) ? phoneDigits : `${dialDigits}${phoneDigits.replace(/^0+/, '')}`}`

      if (cleanedPhone && !/^\+[1-9]\d{6,14}$/.test(internationalPhone)) {
        setMessage('Enter a valid phone number with country code, for example +923001234567.')
        return
      }
    }
    setIsSubmitting(true)

    try {
      if (mode === 'login') {
        const data = await loginUser({
          email: formData.email,
          password: formData.password,
        })
        localStorage.setItem('accessToken', data.access)
        localStorage.setItem('refreshToken', data.refresh)
        navigate(data.onboarding_completed ? '/dashboard' : '/onboarding', { replace: true })
      } else {
        await registerUser({
          full_name: formData.fullName,
          email: formData.email,
          password: formData.password,
          phone: formData.phone.trim()
            ? (formData.phone.trim().startsWith('+')
              ? `+${formData.phone.trim().replace(/\D/g, '')}`
              : `+${formData.phone.trim().replace(/\D/g, '').startsWith(countryCode.slice(1))
                ? formData.phone.trim().replace(/\D/g, '')
                : `${countryCode.slice(1)}${formData.phone.trim().replace(/\D/g, '').replace(/^0+/, '')}`}`)
            : '',
          gender: formData.gender || 'Other',
          ...(formData.dob && { dob: formData.dob }),
        })
        sessionStorage.setItem('verificationEmail', formData.email)
        navigate('/verify-email', { state: { email: formData.email } })
        resetForm()
      }
    } catch (error) {
      setMessage(error.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleModeChange = (nextMode) => {
    setMode(nextMode)
    navigate(nextMode === 'login' ? '/login' : '/signup')
    setMessage('')
    resetForm()
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-label={`${mode === 'login' ? 'Login' : 'Sign up'} form`}>
        <div className="auth-panel-inner">
          <AuthTabs mode={mode} onModeChange={handleModeChange} />

          <form onSubmit={handleSubmit}>
            {mode === 'signup' && (
              <label>
                <span>Full Name</span>
                <input
                  type="text"
                  name="fullName"
                  value={formData.fullName}
                  onChange={handleChange}
                  placeholder="Full Name"
                  required
                />
              </label>
            )}

            <label>
              <span>Email</span>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Email"
                required
              />
            </label>

            {mode === 'signup' && (
              <>
                <label>
                  <span>Phone</span>
                  <div className="phone-input-group">
                    <div className="select-wrap country-code-wrap">
                      <select
                        aria-label="Country calling code"
                        value={countryCode}
                        onChange={(event) => setCountryCode(event.target.value)}
                      >
                        {COUNTRY_CODES.map(([country, name, code]) => (
                          <option key={country} value={code}>{name} ({code})</option>
                        ))}
                      </select>
                    </div>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      placeholder="300 1234567"
                      autoComplete="tel-national"
                    />
                  </div>
                </label>

                <label className="date-field">
                  <span>Date of Birth</span>
                  <div className="input-with-icon">
                    <input
                      type="date"
                      name="dob"
                      value={formData.dob}
                      onChange={handleChange}
                      placeholder="mm/dd/yyyy"
                    />
                  </div>
                </label>

                <label>
                  <span>Gender</span>
                  <div className="select-wrap">
                    <select name="gender" value={formData.gender} onChange={handleChange}>
                      <option value="">Select Gender</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </label>
              </>
            )}

            <label>
              <span>Password</span>
              <PasswordField
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Password"
              />
            </label>

            {mode === 'signup' && (
              <label>
                <span>Confirm Password</span>
                <PasswordField
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Confirm Password"
                />
              </label>
            )}

            {mode === 'login' && (
              <div className="form-options">
                <label className="remember-option">
                  <input type="checkbox" checked={rememberMe} onChange={() => setRememberMe(!rememberMe)} />
                  <span>Remember me</span>
                </label>
                <button type="button" className="text-button">Forgot password?</button>
              </div>
            )}

            <button className="submit-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Please wait...' : (mode === 'login' ? 'Unlock Vault' : 'Create Profile')}
            </button>

            <p className="switch-text">
              {mode === 'login' ? "Don't have an account?" : 'Already have an account?'}
              <button type="button" className="text-link" onClick={() => handleModeChange(mode === 'login' ? 'signup' : 'login')}>
                {mode === 'login' ? 'Sign up' : 'Login'}
              </button>
            </p>

            {message && <p className="form-message" role="status">{message}</p>}
          </form>
        </div>
      </section>
    </main>
  )
}

export default AuthPage