import {
  Activity,
  ArrowLeft,
  CalendarClock,
  Clock3,
  FileText,
  KeyRound,
  MessageCircleHeart,
  ShieldCheck,
  UsersRound,
} from 'lucide-react';

const FEATURES = {
  'trusted-circle': {
    icon: UsersRound,
    eyebrow: 'PEOPLE YOU TRUST',
    title: 'Trusted Circle',
    description:
      'Choose the people who may receive your selected memories and help verify your release plan.',
  },
  'hidden-keys': {
    icon: KeyRound,
    eyebrow: 'PRIVATE CREDENTIALS',
    title: 'Hidden Keys',
    description:
      'Keep an organized record of important accounts and the trusted person assigned to each one.',
  },
  'memory-capsules': {
    icon: FileText,
    eyebrow: 'YOUR MEMORIES',
    title: 'Memory Capsules',
    description:
      'Preserve personal files and choose how and when each capsule should be shared.',
  },
  'legacy-ai': {
    icon: MessageCircleHeart,
    eyebrow: 'A VOICE SHAPED BY YOU',
    title: 'Legacy AI',
    description:
      'Learn about the planned conversational companion, shaped by its owner’s personality and memories.',
  },
  'activity-monitor': {
    icon: Activity,
    eyebrow: 'ACCOUNT ACTIVITY',
    title: 'Activity Monitor',
    description:
      'Check in to confirm your account is active and review the release plan tied to your activity.',
  },
  'release-plan': {
    icon: CalendarClock,
    eyebrow: 'WHEN TO SHARE',
    title: 'Release Plan',
    description:
      'Review the release timing and current status of the memory capsules you have saved.',
  },
};

function EmptyState({ children }) {
  return <p className="feature-empty-state">{children}</p>;
}

function FeatureRows({ rows, icon: RowIcon, emptyMessage }) {
  if (!rows.length) {
    return <EmptyState>{emptyMessage}</EmptyState>;
  }

  return (
    <div className="feature-rows">
      {rows.map((row) => (
        <article className="feature-row" key={row.id}>
          <div className="feature-row-icon" aria-hidden="true">
            <RowIcon size={18} />
          </div>
          <div className="feature-row-copy">
            <h3>{row.title}</h3>
            {row.description && <p>{row.description}</p>}
          </div>
          {row.status && <span className="feature-row-status">{row.status}</span>}
        </article>
      ))}
    </div>
  );
}

function TrustedCircleDetails({ nominees = [] }) {
  return (
    <section className="feature-content-card">
      <div className="feature-content-heading">
        <div>
          <p className="feature-eyebrow">YOUR PEOPLE</p>
          <h2>Trusted contacts</h2>
        </div>
        <span className="feature-count">{nominees.length}</span>
      </div>
      <FeatureRows
        icon={UsersRound}
        emptyMessage="No trusted contacts have been added yet."
        rows={nominees.map((nominee) => ({
          id: nominee.id,
          title: nominee.nominee_name || nominee.name || 'Trusted contact',
          description: [nominee.relationship, nominee.email].filter(Boolean).join(' · '),
          status: nominee.is_active === false ? 'Inactive' : 'On your list',
        }))}
      />
    </section>
  );
}

function HiddenKeysDetails({ credentials = [] }) {
  return (
    <section className="feature-content-card">
      <div className="feature-content-heading">
        <div>
          <p className="feature-eyebrow">ACCOUNT RECORDS</p>
          <h2>Saved credentials</h2>
        </div>
        <span className="feature-count">{credentials.length}</span>
      </div>
      <p className="feature-supporting-copy">
        Passwords are never displayed on this overview.
      </p>
      <FeatureRows
        icon={KeyRound}
        emptyMessage="No credentials have been saved yet."
        rows={credentials.map((credential) => ({
          id: credential.id,
          title: credential.platform || 'Saved account',
          description:
            credential.username_on_platform ||
            credential.email_on_platform ||
            credential.platform_url ||
            'Account details are stored securely.',
          status: 'Protected',
        }))}
      />
    </section>
  );
}

function CapsuleRows({ items = [] }) {
  return (
    <FeatureRows
      icon={FileText}
      emptyMessage="No memory capsules have been saved yet."
      rows={items.map((item) => ({
        id: item.id,
        title: item.title || 'Memory capsule',
        description: item.scheduled_date
          ? `Release date: ${new Date(item.scheduled_date).toLocaleDateString()}`
          : `Release rule: ${item.release_type || 'Not specified'}`,
        status: item.is_sent ? 'Released' : 'Saved',
      }))}
    />
  );
}

function MemoryCapsulesDetails({ items = [] }) {
  return (
    <section className="feature-content-card">
      <div className="feature-content-heading">
        <div>
          <p className="feature-eyebrow">PRESERVED FILES</p>
          <h2>Your capsules</h2>
        </div>
        <span className="feature-count">{items.length}</span>
      </div>
      <CapsuleRows items={items} />
    </section>
  );
}

function LegacyAIDetails() {
  return (
    <>
      <section className="feature-content-card legacy-ai-explainer">
        <div className="feature-content-heading">
          <div>
            <p className="feature-eyebrow">THE IDEA</p>
            <h2>A familiar voice, preserved with care</h2>
          </div>
          <MessageCircleHeart size={25} aria-hidden="true" />
        </div>
        <p>
          Legacy AI is intended to reflect the owner’s personality and way of
          speaking, using the memories they choose to preserve. Its purpose is
          to let approved people in their Trusted Circle have a meaningful
          conversation with that digital legacy.
        </p>
        <div className="legacy-ai-points">
          <div>
            <ShieldCheck size={19} aria-hidden="true" />
            <span>Access is intended for the owner’s trusted circle.</span>
          </div>
          <div>
            <FileText size={19} aria-hidden="true" />
            <span>Preserved memories help shape the experience.</span>
          </div>
        </div>
      </section>
      <section className="feature-content-card feature-status-card">
        <span className="feature-status-label">CURRENT AVAILABILITY</span>
        <p>
          This build does not yet include a connected chatbot service. This
          page describes the planned Legacy AI experience; it does not generate
          conversations.
        </p>
      </section>
    </>
  );
}

function ActivityMonitorDetails({ lastPulse, onStayAlive, isCheckingIn }) {
  return (
    <section className="feature-content-card activity-detail-card">
      <div className="feature-content-heading">
        <div>
          <p className="feature-eyebrow">LAST CHECK-IN</p>
          <h2>Keep your account active</h2>
        </div>
        <Activity size={24} aria-hidden="true" />
      </div>
      <p className="feature-supporting-copy">
        {lastPulse
          ? `You checked in at ${new Date(lastPulse).toLocaleString()}.`
          : 'No check-in has been recorded during this session.'}
      </p>
      <button
        className="feature-primary-action"
        type="button"
        onClick={onStayAlive}
        disabled={isCheckingIn}
      >
        {isCheckingIn ? 'Checking in…' : 'Check in now'}
      </button>
    </section>
  );
}

function ReleasePlanDetails({ items = [] }) {
  const scheduledCount = items.filter((item) => item.release_type === 'scheduled').length;
  const recurringCount = items.filter((item) => item.release_type === 'recurring').length;

  return (
    <>
      <section className="feature-content-card release-summary-card">
        <div className="release-summary">
          <div>
            <Clock3 size={20} aria-hidden="true" />
            <strong>{scheduledCount}</strong>
            <span>scheduled</span>
          </div>
          <div>
            <CalendarClock size={20} aria-hidden="true" />
            <strong>{recurringCount}</strong>
            <span>recurring</span>
          </div>
          <div>
            <FileText size={20} aria-hidden="true" />
            <strong>{items.length}</strong>
            <span>capsules</span>
          </div>
        </div>
      </section>
      <section className="feature-content-card">
        <div className="feature-content-heading">
          <div>
            <p className="feature-eyebrow">RELEASE INSTRUCTIONS</p>
            <h2>Capsule schedule</h2>
          </div>
        </div>
        <CapsuleRows items={items} />
      </section>
    </>
  );
}

export default function DashboardFeatureView({
  featureId,
  nominees,
  credentials,
  items,
  lastPulse,
  onBack,
  onStayAlive,
  isCheckingIn,
}) {
  const feature = FEATURES[featureId];

  if (!feature) {
    return (
      <section className="feature-view">
        <button className="feature-back-button" type="button" onClick={onBack}>
          <ArrowLeft size={16} aria-hidden="true" />
          Back to dashboard
        </button>
        <div className="feature-content-card">
          <h2>Feature not found</h2>
          <p className="feature-supporting-copy">
            This dashboard destination is unavailable.
          </p>
        </div>
      </section>
    );
  }

  const FeatureIcon = feature.icon;

  return (
    <section className="feature-view">
      <button className="feature-back-button" type="button" onClick={onBack}>
        <ArrowLeft size={16} aria-hidden="true" />
        Back to dashboard
      </button>

      <header className="feature-overview">
        <div className="feature-overview-icon" aria-hidden="true">
          <FeatureIcon size={26} />
        </div>
        <div>
          <p className="feature-eyebrow">{feature.eyebrow}</p>
          <h1>{feature.title}</h1>
          <p className="feature-overview-description">{feature.description}</p>
        </div>
      </header>

      {featureId === 'trusted-circle' && <TrustedCircleDetails nominees={nominees} />}
      {featureId === 'hidden-keys' && <HiddenKeysDetails credentials={credentials} />}
      {featureId === 'memory-capsules' && <MemoryCapsulesDetails items={items} />}
      {featureId === 'legacy-ai' && <LegacyAIDetails />}
      {featureId === 'activity-monitor' && (
        <ActivityMonitorDetails
          lastPulse={lastPulse}
          onStayAlive={onStayAlive}
          isCheckingIn={isCheckingIn}
        />
      )}
      {featureId === 'release-plan' && <ReleasePlanDetails items={items} />}
    </section>
  );
}
