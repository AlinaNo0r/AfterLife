import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { completeOnboarding, createNominee, createVaultItem } from '../../services/authService.js'
import { showAppToast } from '../../services/toastService.js'
import onboardingSteps from './onboardingSteps.js'
import './Onboarding.css'

function OnboardingFlow() {
  const navigate = useNavigate()
  const [stepIndex, setStepIndex] = useState(0)
  const [showSetup, setShowSetup] = useState(false)
  const [timeoutDays, setTimeoutDays] = useState('7')
  const [nomineeName, setNomineeName] = useState('')
  const [nomineeEmail, setNomineeEmail] = useState('')
  const [itemTitle, setItemTitle] = useState('')
  const [itemFile, setItemFile] = useState(null)
  const [message, setMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const finishOnboarding = async (setup = false) => {
    setMessage('')
    const hasName = nomineeName.trim().length > 0
    const hasEmail = nomineeEmail.trim().length > 0

    if (setup && hasName !== hasEmail) {
      const validationMessage = 'Enter both the nominee name and email, or leave both empty for now.'
      setMessage(validationMessage)
      showAppToast(validationMessage, 'error', 'Check the nominee details')
      return
    }
    if (setup && itemFile && (!hasName || !itemTitle.trim())) {
      const validationMessage = 'To add a vault file, enter a nominee name and email, plus a title for the file.'
      setMessage(validationMessage)
      showAppToast(validationMessage, 'error', 'Check the vault file details')
      return
    }

    setIsSubmitting(true)
    try {
      let nomineeId
      let invitationSent = true

      if (setup && hasName && hasEmail) {
        const nominee = await createNominee({
          nominee_name: nomineeName.trim(),
          nominee_email: nomineeEmail.trim(),
        })
        nomineeId = nominee.id
        invitationSent = nominee.invitation_sent
      }

      if (setup && itemFile) {
        const itemData = new FormData()
        itemData.append('title', itemTitle.trim())
        itemData.append('file', itemFile)
        itemData.append('recipient', nomineeId)
        itemData.append('release_type', 'killswitch')
        await createVaultItem(itemData)
      }

      await completeOnboarding({
        ...(setup && { timeout_days: Number(timeoutDays) }),
        onboarding_completed: true,
      })

      navigate('/dashboard', {
        replace: true,
        state: { invitationSent },
      })
      showAppToast('Your vault setup is complete.', 'success', 'Setup complete')
    } catch (error) {
      setMessage(error.message || 'Could not save onboarding. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (showSetup) {
    return (
      <main className="onboarding-page">
        <section className="onboarding-layout onboarding-setup">
          <p className="onboarding-eyebrow">YOUR VAULT / FIRST SETUP</p>
          <h1>Set the first safeguards.</h1>
          <p className="onboarding-intro">These choices are optional now. You can update them later from your account.</p>

          <form className="onboarding-form" onSubmit={(event) => { event.preventDefault(); finishOnboarding(true) }}>
            <label>
              <span>Timeout days</span>
              <input
                type="number"
                min="1"
                max="365"
                value={timeoutDays}
                onChange={(event) => setTimeoutDays(event.target.value)}
                required
              />
              <small>How long the vault waits without a check-in before warning nominees.</small>
            </label>

            <div className="onboarding-section-heading">
              <h2>Invite a trusted nominee</h2>
              <span>Optional</span>
            </div>
            <div className="onboarding-fields">
              <label>
                <span>Name</span>
                <input value={nomineeName} onChange={(event) => setNomineeName(event.target.value)} placeholder="Nominee name" />
              </label>
              <label>
                <span>Email</span>
                <input type="email" value={nomineeEmail} onChange={(event) => setNomineeEmail(event.target.value)} placeholder="Nominee email" />
              </label>
            </div>

            <div className="onboarding-section-heading">
              <h2>Add a first vault file</h2>
              <span>Optional</span>
            </div>
            <label>
              <span>File title</span>
              <input value={itemTitle} onChange={(event) => setItemTitle(event.target.value)} placeholder="For example, family letter" />
            </label>
            <label>
              <span>Choose a file</span>
              <input
                type="file"
                accept=".mp4,.mov,.avi,.mkv,.webm,.jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.txt"
                onChange={(event) => setItemFile(event.target.files?.[0] || null)}
              />
              <small>A nominee is needed to assign and release this file.</small>
            </label>

            {message && <p className="form-message" role="alert">{message}</p>}
            <div className="onboarding-actions">
              <button className="onboarding-secondary" type="button" onClick={() => finishOnboarding(false)} disabled={isSubmitting}>
                Finish later
              </button>
              <button className="submit-button" type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : 'Create My Secure Vault'}
              </button>
            </div>
          </form>
        </section>
      </main>
    )
  }

  const currentStep = onboardingSteps[stepIndex]
  const isLastStep = stepIndex === onboardingSteps.length - 1
  const primaryButtonLabel = stepIndex === 0 ? 'Get Started' : isLastStep ? 'Check In' : 'Continue'

  return (
    <main className="onboarding-page">
      <section className="onboarding-layout" aria-live="polite">
        <div className="onboarding-step-count">{String(stepIndex + 1).padStart(2, '0')} <span>/ {String(onboardingSteps.length).padStart(2, '0')}</span></div>
        <p className="onboarding-eyebrow">{currentStep.eyebrow}</p>
        <h1>{currentStep.title}</h1>
        <p className="onboarding-intro">{currentStep.description}</p>
        <div className="onboarding-progress" aria-label={`Slide ${stepIndex + 1} of ${onboardingSteps.length}`}>
          {onboardingSteps.map((step, index) => (
            <span key={step.eyebrow} className={index <= stepIndex ? 'complete' : ''} />
          ))}
        </div>
        <div className="onboarding-actions">
          <button className="onboarding-secondary" type="button" onClick={() => finishOnboarding(false)} disabled={isSubmitting}>
            Skip for now
          </button>
          <button
            className="submit-button onboarding-next"
            type="button"
            onClick={() => isLastStep ? setShowSetup(true) : setStepIndex((index) => index + 1)}
          >
            {primaryButtonLabel}
          </button>
        </div>
        {message && <p className="form-message" role="alert">{message}</p>}
      </section>
    </main>
  )
}

export default OnboardingFlow