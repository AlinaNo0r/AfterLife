import {
  ArrowRight,
  CalendarClock,
  FileText,
  Heart,
  KeyRound,
  MessageCircleHeart,
  Monitor,
  UsersRound,
} from 'lucide-react'

function initials(name = '') {
  return name.trim().split(/\s+/).filter(Boolean).map((part) => part[0]).join('').slice(0, 2).toUpperCase()
}

function countText(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`
}

export function Hero({ lastPulse }) {
  const pulseText = lastPulse
    ? `LAST PULSE: ${new Date(lastPulse).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
    : 'CHECK IN TO UPDATE YOUR PULSE'

  return (
    <header className="hero">
      <h2>Your Legacy<br /><span>at a Glance.</span></h2>
      <div className="hero-meta">
        <span className="status-badge"><span className="status-dot" /> VAULT ENCRYPTED</span>
        <span className="status-badge">{pulseText}</span>
      </div>
    </header>
  )
}

export function TrustedCircleCard({ nominees, loading, onNavigate }) {
  const visibleNominees = nominees.slice(0, 3)
  const extraCount = Math.max(nominees.length - visibleNominees.length, 0)

  return (
    <article className="card trusted-circle" id="trusted-circle">
      <div className="card-topline">
        <div className="card-icon-wrap trusted-icon">
          <UsersRound size={22} strokeWidth={1.8} aria-hidden="true" />
        </div>
        <span className="card-label">YOUR PEOPLE</span>
      </div>
      <h3>Trusted Circle</h3>
      <p>
        {loading
          ? 'Loading your trusted circle...'
          : nominees.length
            ? `${countText(nominees.length, 'trusted person', 'trusted people')} can help verify your release plan and receive selected memories.`
            : 'Add trusted people to help verify your release plan and receive selected memories.'}
      </p>
      <div className="trusted-avatars">
        {visibleNominees.map((nominee, index) => (
          <span className={`ta ta-${index}`} key={nominee.id} title={nominee.nominee_name}>
            {initials(nominee.nominee_name)}
          </span>
        ))}
        {extraCount > 0 && <span className="ta ta-more">+{extraCount}</span>}
      </div>
      <button
        className="card-action-button"
        type="button"
        onClick={() => onNavigate('trusted-circle')}
      >
        <span>View trusted contacts</span>
        <ArrowRight size={16} aria-hidden="true" />
      </button>
    </article>
  )
}

export function PulseCard({ onStayAlive, isCheckingIn, onNavigate }) {
  return (
    <article className="card pulse-card">
      <div className="pulse-icon">
        <Heart size={22} fill="currentColor" strokeWidth={1.5} aria-hidden="true" />
      </div>
      <div className="card-label">ACTIVITY MONITOR</div>
      <h3>Keep your status active</h3>
      <button className="update-sig-btn" onClick={onStayAlive} disabled={isCheckingIn}>
        {isCheckingIn ? 'CONFIRMING STATUS...' : 'CONFIRM STATUS'}
      </button>
      <button
        className="card-inline-action"
        type="button"
        onClick={() => onNavigate('activity-monitor')}
      >
        Activity details <ArrowRight size={14} aria-hidden="true" />
      </button>
    </article>
  )
}

export function HiddenKeysCard({ count, loading, onNavigate }) {
  return (
    <article className="card hidden-keys-card" id="keys">
      <div className="keys-icon">
        <KeyRound size={18} strokeWidth={1.8} aria-hidden="true" />
        <span className="keys-heading">Hidden Keys</span>
      </div>
      <div className="keys-count">{loading ? '—' : count}</div>
      <p>
        {loading
          ? 'Checking your saved credentials...'
          : `${countText(count, 'encrypted credential')} secured in your vault.`}
      </p>
      <button
        className="card-action-button compact-card-action"
        type="button"
        onClick={() => onNavigate('hidden-keys')}
      >
        <span>Review credentials</span>
        <ArrowRight size={15} aria-hidden="true" />
      </button>
    </article>
  )
}

export function CapsulesCard({ items, loading, onNavigate }) {
  return (
    <article className="card capsules-card" id="capsules">
      <div className="card-icon-wrap capsule-icon">
        <Monitor size={22} strokeWidth={1.8} aria-hidden="true" />
      </div>
      <h3>Memory Capsules</h3>
      <p>
        {loading
          ? 'Loading your vault items...'
          : items.length
            ? `${countText(items.length, 'memory', 'memories')} saved in your vault.`
            : 'Preserve letters, photos, and videos for meaningful moments and chosen release dates.'}
      </p>
      {items.length > 0 && (
        <div className="capsule-imgs" aria-label="Recent vault items">
          {items.slice(0, 3).map((item) => (
            <div className="capsule-img" key={item.id} title={item.title}>
              <FileText size={20} strokeWidth={1.7} aria-hidden="true" />
              <span>{item.title}</span>
            </div>
          ))}
        </div>
      )}
      <button
        className="card-action-button"
        type="button"
        onClick={() => onNavigate('memory-capsules')}
      >
        <span>Browse capsules</span>
        <ArrowRight size={16} aria-hidden="true" />
      </button>
    </article>
  )
}

export function LegacyAICard({ onNavigate }) {
  return (
    <article className="card ai-card" id="legacyai">
      <div className="card-topline">
        <div className="card-icon-wrap legacy-ai-icon">
          <MessageCircleHeart size={22} strokeWidth={1.8} aria-hidden="true" />
        </div>
        <span className="card-label">LEGACY AI</span>
      </div>
      <h3>A voice shaped by its owner.</h3>
      <p>
        A conversational digital twin, shaped by its owner’s personality and
        memories, for trusted-circle members to access when permitted.
      </p>
      <button
        className="card-action-button"
        type="button"
        onClick={() => onNavigate('legacy-ai')}
      >
        <span>Learn about Legacy AI</span>
        <ArrowRight size={16} aria-hidden="true" />
      </button>
    </article>
  )
}

export function ReleasePlanCard({ items, loading, onNavigate }) {
  const scheduledCount = items.filter((item) => item.release_type === 'scheduled').length
  const recurringCount = items.filter((item) => item.release_type === 'recurring').length

  return (
    <article className="card release-plan-card">
      <div className="card-topline">
        <div className="card-icon-wrap release-plan-icon">
          <CalendarClock size={22} strokeWidth={1.8} aria-hidden="true" />
        </div>
        <span className="card-label">WHEN TO SHARE</span>
      </div>
      <h3>Release Plan</h3>
      <p>
        {loading
          ? 'Checking your saved release instructions...'
          : items.length
            ? `${countText(items.length, 'capsule')} with ${scheduledCount} scheduled and ${recurringCount} recurring release${recurringCount === 1 ? '' : 's'}.`
            : 'Choose who should receive each capsule and when it should be shared.'}
      </p>
      <button
        className="card-action-button"
        type="button"
        onClick={() => onNavigate('release-plan')}
      >
        <span>View release plan</span>
        <ArrowRight size={16} aria-hidden="true" />
      </button>
    </article>
  )
}
