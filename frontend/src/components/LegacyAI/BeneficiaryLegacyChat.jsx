import { useEffect, useRef, useState } from 'react'
import {
  getBeneficiaryLegacyAI,
  getBeneficiaryLegacyChat,
  saveBeneficiaryLegacyAIConsent,
  sendBeneficiaryLegacyMessage,
} from '../../services/authService.js'
import { showAppToast } from '../../services/toastService.js'

function BeneficiaryLegacyChat() {
  const [profile, setProfile] = useState(null)
  const [messages, setMessages] = useState([])
  const [message, setMessage] = useState('')
  const [acceptedNotice, setAcceptedNotice] = useState(false)
  const [spiritualityEnabled, setSpiritualityEnabled] = useState(false)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const messagesEnd = useRef(null)

  const loadConversation = async () => {
    const result = await getBeneficiaryLegacyChat()
    setMessages(result.messages)
  }

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const result = await getBeneficiaryLegacyAI()
        if (!active) return
        setProfile(result)
        setSpiritualityEnabled(result.beneficiary_spirituality_enabled)
        if (result.beneficiary_processing_consent) {
          const conversation = await getBeneficiaryLegacyChat()
          if (active) setMessages(conversation.messages)
        }
      } catch (requestError) {
        if (active) setError(requestError.message)
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [])

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const acceptNotice = async (event) => {
    event.preventDefault()
    setError('')
    setSending(true)
    try {
      const saved = await saveBeneficiaryLegacyAIConsent({
        accepted: acceptedNotice,
        spirituality_enabled: acceptedNotice && spiritualityEnabled,
        faith_tradition: acceptedNotice && spiritualityEnabled ? profile.faith_tradition : '',
      })
      if (!saved.accepted) {
        setProfile((current) => ({ ...current, beneficiary_processing_consent: false }))
        showAppToast('Processing consent withdrawn.', 'success', 'Legacy AI')
        return
      }
      setProfile((current) => ({
        ...current,
        beneficiary_processing_consent: true,
        beneficiary_spirituality_enabled: saved.spirituality_enabled,
      }))
      await loadConversation()
      showAppToast('Consent saved. You can now use Legacy AI.', 'success', 'Legacy AI')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSending(false)
    }
  }

  const withdrawConsent = async () => {
    setError('')
    setSending(true)
    try {
      await saveBeneficiaryLegacyAIConsent({
        accepted: false,
        spirituality_enabled: false,
        faith_tradition: '',
      })
      setProfile((current) => ({ ...current, beneficiary_processing_consent: false }))
      setMessages([])
      showAppToast('Consent withdrawn and local chat history deleted.', 'success', 'Legacy AI')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSending(false)
    }
  }

  const send = async (event) => {
    event.preventDefault()
    const trimmed = message.trim()
    if (!trimmed || sending) return
    setError('')
    setSending(true)
    setMessage('')
    try {
      const result = await sendBeneficiaryLegacyMessage(trimmed)
      setMessages((current) => [
        ...current,
        { role: 'user', content: trimmed },
        result.message,
      ])
      setProfile((current) => ({ ...current, readiness: result.readiness }))
    } catch (requestError) {
      setMessage(trimmed)
      setError(requestError.message)
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return <main className="legacy-chat-page"><p role="status">Loading beneficiary access…</p></main>
  }

  if (!profile) {
    return (
      <main className="legacy-chat-page">
        <section className="legacy-chat-card">
          <h1>Legacy AI</h1>
          <p role="alert">{error || 'Beneficiary access could not be verified.'}</p>
        </section>
      </main>
    )
  }

  return (
    <main className="legacy-chat-page">
      <section className="legacy-chat-card">
        <header>
          <p className="feature-eyebrow">A MEMORY-BASED COMPANION</p>
          <h1>A space to remember {profile.owner_name}</h1>
          <p>This is an AI memorial companion, not the person who died, a therapist, or a substitute for support from people you trust.</p>
        </header>

        {!profile.beneficiary_processing_consent ? (
          <form className="legacy-consent-form" onSubmit={acceptNotice}>
            <h2>Before you start</h2>
            <p>
              Your messages, recent chat history, selected memory excerpts, and owner-provided relationship context
              from {profile.owner_name} will be processed by the local Ollama model running on the app server.
              This app does not send them to a hosted AI provider, but the server operator may access data stored
              by the app. Replies may be incomplete and are not therapy or a message from the deceased. Chat history
              is stored by this app and is not encrypted at rest; withdrawing consent deletes the local chat history.
            </p>
            <label className="legacy-inline-check">
              <input type="checkbox" checked={acceptedNotice} onChange={(event) => setAcceptedNotice(event.target.checked)} required />
              <span>I understand and agree to this local AI processing.</span>
            </label>
            {profile.spirituality_enabled && (
              <label className="legacy-inline-check">
                <input type="checkbox" checked={spiritualityEnabled} onChange={(event) => setSpiritualityEnabled(event.target.checked)} />
                <span>
                  I would like spiritual content in {profile.faith_tradition} when I ask for it.
                  This remains off unless I choose it.
                </span>
              </label>
            )}
            <button type="submit" className="feature-primary-action" disabled={sending || !acceptedNotice}>
              {sending ? 'Saving…' : 'Continue'}
            </button>
          </form>
        ) : (
          <>
            {profile.readiness && !profile.readiness.ready_for_personalized_responses && (
              <p className="legacy-readiness-warning" role="status">
                There are only a few memories available, so replies may not reflect {profile.owner_name}&apos;s personality.
                The companion will acknowledge what it does not know.
              </p>
            )}
            <div className="legacy-chat-messages" aria-live="polite">
              {messages.map((item, index) => (
                <article className={`legacy-chat-message ${item.role}`} key={`${item.created_at || 'new'}-${index}`}>
                  <strong>{item.role === 'assistant' ? 'Legacy AI' : 'You'}</strong>
                  <p>{item.content}</p>
                </article>
              ))}
              <div ref={messagesEnd} />
            </div>
            <button type="button" className="legacy-withdraw-consent" onClick={withdrawConsent} disabled={sending}>
              Withdraw consent and delete this chat history
            </button>
            <form className="legacy-chat-input" onSubmit={send}>
              <label htmlFor="legacy-message">Your message</label>
              <textarea
                id="legacy-message"
                value={message}
                maxLength={2000}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Share a memory or ask a question…"
                disabled={sending}
                required
              />
              <button type="submit" className="feature-primary-action" disabled={sending || !message.trim()}>
                {sending ? 'Replying…' : 'Send'}
              </button>
            </form>
            <p className="legacy-chat-support">
              If you may hurt yourself or are in immediate danger, contact local emergency services or a trusted person now.
              This chat is not crisis support.
            </p>
          </>
        )}
        {error && <p className="trusted-feedback is-error" role="alert">{error}</p>}
      </section>
    </main>
  )
}

export default BeneficiaryLegacyChat
