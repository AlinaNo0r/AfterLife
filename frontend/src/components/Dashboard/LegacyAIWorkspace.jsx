import { useEffect, useState } from 'react'
import { RotateCcw, Send, Trash2 } from 'lucide-react'
import {
  deleteLegacyMemory,
  getLegacyAIPersona,
  getLegacyAIReadiness,
  getLegacyMemorySources,
  previewLegacyAI,
  saveLegacyAIPersona,
  uploadLegacyMemory,
} from '../../services/authService.js'
import { showAppToast } from '../../services/toastService.js'

function LegacyAIWorkspace({ nominees, accesses, onAssign, onRemove, locked }) {
  const [selectedId, setSelectedId] = useState('')
  const [persona, setPersona] = useState(null)
  const [readiness, setReadiness] = useState(null)
  const [sources, setSources] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [text, setText] = useState('')
  const [consent, setConsent] = useState(false)
  const [nomineeToAssign, setNomineeToAssign] = useState('')
  const [previewQuestion, setPreviewQuestion] = useState('')
  const [previewMessages, setPreviewMessages] = useState([])
  const [busy, setBusy] = useState(false)
  const [loadedId, setLoadedId] = useState('')

  const selectedAccess = accesses.find((access) => String(access.nominee) === selectedId)
  const effectiveSelectedId = selectedAccess
    ? selectedId
    : String(accesses[0]?.nominee || '')
  const dataIsCurrent = loadedId === effectiveSelectedId

  useEffect(() => {
    let active = true
    if (!effectiveSelectedId) return () => { active = false }

    Promise.all([
      getLegacyAIPersona(effectiveSelectedId),
      getLegacyAIReadiness(effectiveSelectedId),
      getLegacyMemorySources(effectiveSelectedId),
    ]).then(([personaResult, readinessResult, sourceResult]) => {
      if (!active) return
      setPersona(personaResult)
      setConsent(personaResult.owner_data_consent)
      setReadiness(readinessResult.readiness)
      setSources(sourceResult)
      setLoadedId(effectiveSelectedId)
    }).catch((requestError) => {
      if (active) {
        showAppToast(requestError.message, 'error', 'Legacy AI')
        setLoadedId(effectiveSelectedId)
      }
    })

    return () => { active = false }
  }, [effectiveSelectedId])

  const refreshMemoryData = async () => {
    const [readinessResult, sourceResult] = await Promise.all([
      getLegacyAIReadiness(effectiveSelectedId),
      getLegacyMemorySources(effectiveSelectedId),
    ])
    setReadiness(readinessResult.readiness)
    setSources(sourceResult)
  }

  const savePersona = async (event) => {
    event.preventDefault()
    setBusy(true)
    try {
      const saved = await saveLegacyAIPersona(effectiveSelectedId, {
        bond_context: persona.bond_context,
        voice_preferences: persona.voice_preferences,
        spirituality_enabled: persona.spirituality_enabled,
        faith_tradition: persona.faith_tradition,
        owner_data_consent: consent,
      })
      setPersona(saved)
      setReadiness(saved.readiness)
      showAppToast('Beneficiary settings saved.', 'success', 'Legacy AI')
    } catch (requestError) {
      showAppToast(requestError.message, 'error', 'Legacy AI')
    } finally {
      setBusy(false)
    }
  }

  const uploadMemory = async (event) => {
    event.preventDefault()
    if (!effectiveSelectedId || (!selectedFile && !text.trim())) return
    setBusy(true)
    try {
      const formData = new FormData()
      formData.append('nominee_ids', JSON.stringify([Number(effectiveSelectedId)]))
      if (selectedFile) formData.append('file', selectedFile)
      else {
        formData.append('text', text)
        formData.append('display_name', 'Personal notes')
      }
      await uploadLegacyMemory(formData)
      setSelectedFile(null)
      setText('')
      event.target.reset()
      await refreshMemoryData()
      showAppToast('Memory was added and indexed.', 'success', 'Legacy AI')
    } catch (requestError) {
      showAppToast(requestError.message, 'error', 'Legacy AI')
    } finally {
      setBusy(false)
    }
  }

  const removeMemory = async (sourceId) => {
    setBusy(true)
    try {
      await deleteLegacyMemory(sourceId)
      await refreshMemoryData()
      showAppToast('Memory source removed.', 'success', 'Legacy AI')
    } catch (requestError) {
      showAppToast(requestError.message, 'error', 'Legacy AI')
    } finally {
      setBusy(false)
    }
  }

  const acceptedBeneficiaries = nominees.filter((nominee) => (
    nominee.role_statuses?.some((role) => role.role === 'beneficiary' && role.consent_status === 'accepted')
  ))
  const assignedIds = new Set(accesses.map((access) => String(access.nominee)))
  const availableBeneficiaries = acceptedBeneficiaries.filter((nominee) => !assignedIds.has(String(nominee.id)))

  const assignAccess = async (event) => {
    event.preventDefault()
    if (!nomineeToAssign) return
    setBusy(true)
    try {
      await onAssign(Number(nomineeToAssign))
      setSelectedId(nomineeToAssign)
      setNomineeToAssign('')
      setPreviewQuestion('')
      setPreviewMessages([])
      showAppToast('Legacy AI access assigned.', 'success', 'Legacy AI')
    } catch (requestError) {
      showAppToast(requestError.message, 'error', 'Legacy AI')
    } finally {
      setBusy(false)
    }
  }

  const removeAccess = async (access) => {
    setBusy(true)
    try {
      await onRemove(access.id)
      showAppToast(`Legacy AI access removed for ${access.nominee_name}.`, 'success', 'Legacy AI')
    } catch (requestError) {
      showAppToast(requestError.message, 'error', 'Legacy AI')
    } finally {
      setBusy(false)
    }
  }

  const sendPreview = async (event) => {
    event.preventDefault()
    const question = previewQuestion.trim()
    if (!effectiveSelectedId || !question || busy || !consent) return

    setBusy(true)
    try {
      const result = await previewLegacyAI(
        Number(effectiveSelectedId),
        question,
        previewMessages.slice(-6),
      )
      setPreviewMessages((current) => [
        ...current,
        { role: 'user', content: question },
        result.message,
      ])
      setPreviewQuestion('')
    } catch (requestError) {
      showAppToast(requestError.message, 'error', 'Preview failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="legacy-ai-workspace">
      <section className="feature-content-card legacy-ai-disclosure">
        <h2>Memory-based support, not model training</h2>
        <p>
          Selected memories, relationship/tone context, and messages are processed by a local Ollama model
          running on the app server; this app does not send them to a hosted AI provider. The coverage estimate
          describes available memories; it cannot guarantee personality accuracy or mental-health outcomes.
          Uploaded files and memory text are also stored in this app's existing database/media storage,
          which this feature does not encrypt at rest. Only upload material if you trust the person operating
          the server and agree to this local processing.
        </p>
      </section>

      <section className="feature-content-card legacy-access-card">
        <div className="feature-content-heading">
          <div>
            <p className="feature-eyebrow">BENEFICIARY ACCESS</p>
            <h2>Legacy AI beneficiaries</h2>
          </div>
        </div>
        {accesses.length > 0 && (
          <div className="legacy-beneficiary-picker">
            <label>
              <span>Configure memories for</span>
              <select value={effectiveSelectedId} onChange={(event) => {
                setSelectedId(event.target.value)
                setSelectedFile(null)
                setText('')
                setPreviewQuestion('')
                setPreviewMessages([])
              }}>
                {accesses.map((access) => (
                  <option value={access.nominee} key={access.id}>{access.nominee_name}</option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="legacy-access-remove"
              onClick={() => removeAccess(selectedAccess || accesses[0])}
              disabled={busy || locked}
            >
              <Trash2 size={16} aria-hidden="true" />
              Remove access
            </button>
          </div>
        )}
        {!accesses.length && <p className="feature-empty-state">Assign an accepted beneficiary to start preparing their private memory collection.</p>}
        <form className="legacy-access-form" onSubmit={assignAccess}>
          <label>
            <span>Add an accepted beneficiary</span>
            <select value={nomineeToAssign} onChange={(event) => setNomineeToAssign(event.target.value)} disabled={locked}>
              <option value="">Choose a beneficiary</option>
              {availableBeneficiaries.map((nominee) => (
                <option value={nominee.id} key={nominee.id}>{nominee.nominee_name}</option>
              ))}
            </select>
          </label>
          <button type="submit" className="feature-primary-action" disabled={busy || locked || !nomineeToAssign}>
            Assign access
          </button>
        </form>
      </section>

      {effectiveSelectedId && (
        <>
          {!dataIsCurrent && <p role="status">Loading beneficiary settings…</p>}
          {dataIsCurrent && persona && (
            <section className="feature-content-card">
              <div className="feature-content-heading">
                <div>
                  <p className="feature-eyebrow">INDIVIDUAL BOND</p>
                  <h2>{persona.nominee_name}&apos;s experience</h2>
                </div>
              </div>
              <form className="legacy-persona-form" onSubmit={savePersona}>
                <label>
                  <span>How did you relate to this beneficiary?</span>
                  <textarea
                    value={persona.bond_context}
                    maxLength={4000}
                    onChange={(event) => setPersona({ ...persona, bond_context: event.target.value })}
                    placeholder="Share the tone, traditions, or memories that are specific to your bond."
                    disabled={locked}
                  />
                </label>
                <label>
                  <span>Voice and communication preferences</span>
                  <input
                    value={persona.voice_preferences}
                    maxLength={500}
                    onChange={(event) => setPersona({ ...persona, voice_preferences: event.target.value })}
                    placeholder="For example: gentle, brief, reassuring"
                    disabled={locked}
                  />
                </label>
                <label className="legacy-inline-check">
                  <input
                    type="checkbox"
                    checked={persona.spirituality_enabled}
                    onChange={(event) => setPersona({ ...persona, spirituality_enabled: event.target.checked })}
                    disabled={locked}
                  />
                  <span>Allow spiritual support only when this beneficiary also opts in</span>
                </label>
                {persona.spirituality_enabled && (
                  <label>
                    <span>Owner&apos;s faith or tradition</span>
                    <input
                      value={persona.faith_tradition}
                      maxLength={120}
                      onChange={(event) => setPersona({ ...persona, faith_tradition: event.target.value })}
                      placeholder="Name the tradition, or leave spiritual support disabled"
                      disabled={locked}
                    />
                  </label>
                )}
                <label className="legacy-inline-check legacy-consent-check">
                  <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} disabled={locked} />
                  <span>
                    I consent to processing selected memories, relationship/tone context, and conversation
                    messages with the local Ollama model running on the app server. I understand the server
                    operator may access data stored by this app and that memories are not encrypted at rest.
                  </span>
                </label>
                <button type="submit" className="feature-primary-action" disabled={busy || locked}>
                  {busy ? 'Saving…' : 'Save beneficiary settings'}
                </button>
              </form>
            </section>
          )}

          {dataIsCurrent && persona && (
            <section className="feature-content-card legacy-preview-card">
              <div className="feature-content-heading">
                <div>
                  <p className="feature-eyebrow">PRIVATE OWNER PREVIEW</p>
                  <h2>Test the experience before release</h2>
                </div>
              </div>
              <p className="feature-supporting-copy">
                Preview questions and selected memories are processed by the local Ollama model under your saved consent.
                This conversation is temporary, is not saved to beneficiary chat history, and is not
                visible to {persona.nominee_name}.
              </p>
              <div className="legacy-preview-messages" aria-live="polite">
                {previewMessages.length === 0
                  ? <p className="legacy-preview-empty">Ask a question to test the current memories and tone.</p>
                  : previewMessages.map((message, index) => (
                    <article className={`legacy-chat-message ${message.role}`} key={`${index}-${message.role}`}>
                      <strong>{message.role === 'assistant' ? 'Preview reply' : 'Your test question'}</strong>
                      <p>{message.content}</p>
                    </article>
                  ))}
              </div>
              <form className="legacy-preview-form" onSubmit={sendPreview}>
                <label>
                  <span>Ask a test question</span>
                  <textarea
                    value={previewQuestion}
                    maxLength={2000}
                    onChange={(event) => setPreviewQuestion(event.target.value)}
                    placeholder="For example, what values did I try to teach you?"
                    disabled={!consent || busy || locked}
                    required
                  />
                </label>
                <div className="legacy-preview-actions">
                  <button
                    type="submit"
                    className="feature-primary-action"
                    disabled={!consent || busy || locked || !previewQuestion.trim()}
                  >
                    <Send size={15} aria-hidden="true" />
                    {busy ? 'Testing…' : 'Send test'}
                  </button>
                  <button
                    type="button"
                    className="legacy-preview-clear"
                    onClick={() => setPreviewMessages([])}
                    disabled={!previewMessages.length || busy}
                  >
                    <RotateCcw size={15} aria-hidden="true" />
                    Clear preview
                  </button>
                </div>
              </form>
              {!consent && <p className="legacy-readiness-warning">Save the processing consent above to use the private preview.</p>}
            </section>
          )}

          {dataIsCurrent && readiness && (
            <section className="feature-content-card legacy-readiness-card">
              <div className="feature-content-heading">
                <div>
                  <p className="feature-eyebrow">{readiness.label}</p>
                  <h2>{readiness.level === 'limited' ? 'More memories are needed' : readiness.level === 'developing' ? 'Memory coverage is growing' : 'Broad memory coverage'}</h2>
                </div>
                <strong className="legacy-readiness-score">{readiness.score}%</strong>
              </div>
              <progress max="100" value={readiness.score} aria-label={`${readiness.label}: ${readiness.score}%`} />
              <p>
                {readiness.word_count.toLocaleString()} of {readiness.target_words.toLocaleString()} reference words
                {readiness.words_needed > 0 ? ` · approximately ${readiness.words_needed.toLocaleString()} more recommended` : ''}
                {' · '}{readiness.source_count} of {readiness.target_sources} suggested sources
                {readiness.sources_needed > 0 ? ` · ${readiness.sources_needed} more recommended` : ''}
              </p>
              {!readiness.ready_for_personalized_responses && (
                <p className="legacy-readiness-warning" role="status">
                  Personalization is limited with the current material. The companion may not reflect your voice;
                  add varied, meaningful memories. This estimate is not a measure of model training.
                </p>
              )}
              {readiness.missing_categories.length > 0 && (
                <p>Topics with little or no coverage: {readiness.missing_categories.map((category) => category.replaceAll('_', ' ')).join(', ')}.</p>
              )}
              <ul className="legacy-memory-source-list">
                {sources.map((source) => (
                  <li key={source.id}>
                    <span>{source.display_name} · {source.word_count.toLocaleString()} words · {source.status}</span>
                    <button type="button" onClick={() => removeMemory(source.id)} disabled={busy || locked}>Remove</button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="feature-content-card">
            <div className="feature-content-heading">
              <div>
                <p className="feature-eyebrow">ADD CONTEXT</p>
                <h2>Upload memories or add text</h2>
              </div>
            </div>
            <p>Supported: PDF, TXT, or Markdown up to 5 MB. Choose memories relevant to {persona?.nominee_name || 'this beneficiary'}; they are not shared with other beneficiaries unless you upload them for each person.</p>
            {!consent && <p className="legacy-readiness-warning">Save the local AI processing consent above before uploading.</p>}
            <form className="legacy-upload-form" onSubmit={uploadMemory}>
              <label>
                <span>Choose a file</span>
                <input
                  key={effectiveSelectedId}
                  type="file"
                  accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
                  onChange={(event) => {
                    setSelectedFile(event.target.files?.[0] || null)
                    if (event.target.files?.[0]) setText('')
                  }}
                  disabled={!consent || locked}
                />
              </label>
              <label>
                <span>Or paste personal writing</span>
                <textarea
                  value={text}
                  maxLength={50000}
                  onChange={(event) => {
                    setText(event.target.value)
                    if (event.target.value) setSelectedFile(null)
                  }}
                  placeholder="Letters, stories, values, or messages you want preserved"
                  disabled={!consent || locked}
                />
              </label>
              <button type="submit" className="feature-primary-action" disabled={busy || locked || !consent || (!selectedFile && !text.trim())}>
                {busy ? 'Processing…' : 'Add memory'}
              </button>
            </form>
          </section>
        </>
      )}
    </div>
  )
}

export default LegacyAIWorkspace
