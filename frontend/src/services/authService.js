async function sendApiRequest(endpoint, payload, { method = 'POST', authenticated = false, multipart = false } = {}) {
  const headers = {}
  const accessToken = localStorage.getItem('accessToken')

  if (!multipart) {
    headers['Content-Type'] = 'application/json'
  }
  if (authenticated && accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  let response
  try {
    response = await fetch(endpoint, {
      method,
      headers,
      body: method === 'GET' ? undefined : multipart ? payload : JSON.stringify(payload),
    })
  } catch {
    throw new Error("Can't reach the AfterLife server. Check that the Django backend is running, then try again.")
  }

  let data = {}
  try {
    data = await response.json()
  } catch {
    // Some server errors return an HTML page instead of a JSON API response.
  }

  if (!response.ok) {
    const fieldErrors = Object.values(data || {}).flatMap((value) => Array.isArray(value) ? value : [])
    const backendError = data?.error || data?.detail || data?.message || fieldErrors[0]
    const message = backendError || (
      [502, 503].includes(response.status)
        ? 'The AfterLife backend is unavailable. Start Django on port 8000, then try again.'
        : response.status >= 500
          ? `The server couldn't complete this request (${response.status}). Please try again.`
          : `The request couldn't be completed (${response.status}). Please check your details and try again.`
    )
    throw new Error(message)
  }

  return data
}

export function loginUser(credentials) {
  return sendApiRequest('/api/login/', credentials)
}

export function registerUser(accountDetails) {
  return sendApiRequest('/api/register/', accountDetails)
}

export function verifyRegistrationCode(verification) {
  return sendApiRequest('/api/register/verify/', verification)
}

export function resendRegistrationCode(email) {
  return sendApiRequest('/api/register/resend-code/', { email })
}

export function completeOnboarding(onboardingData) {
  return sendApiRequest('/api/onboarding/complete/', onboardingData, { authenticated: true, method: 'PATCH' })
}

export function createNominee(nomineeData) {
  return sendApiRequest('/nominees/', nomineeData, { authenticated: true })
}

export function updateNominee(id, nomineeData) {
  return sendApiRequest(`/nominees/${id}/`, nomineeData, { authenticated: true, method: 'PATCH' })
}

export function deleteNominee(id) {
  return sendApiRequest(`/nominees/${id}/`, undefined, { authenticated: true, method: 'DELETE' })
}

export function resendNomineeInvitation(id) {
  return sendApiRequest(`/nominees/${id}/resend-invitation/`, {}, { authenticated: true })
}

export function getNomineeInvitation(token) {
  return sendApiRequest(`/api/nominee/confirm/${encodeURIComponent(token)}/`, undefined, { method: 'GET' })
}

export function respondToNomineeInvitation(token, decision) {
  return sendApiRequest(`/api/nominee/confirm/${encodeURIComponent(token)}/`, { decision })
}

export function submitWitnessVote(token, decision) {
  const action = decision === 'death' ? 'vote-death' : 'vote-alive'
  return sendApiRequest(`/api/killswitch/${action}/${encodeURIComponent(token)}/`, {})
}

export function setNomineePassword(uid, token, passwordData) {
  return sendApiRequest(`/set-password/${encodeURIComponent(uid)}/${encodeURIComponent(token)}/`, passwordData)
}

export function createVaultItem(itemData) {
  return sendApiRequest('/vault-items/', itemData, { authenticated: true, multipart: true })
}

export function updateVaultItem(id, itemData) {
  return sendApiRequest(`/vault-items/${id}/`, itemData, { authenticated: true, method: 'PATCH', multipart: true })
}

export function deleteVaultItem(id) {
  return sendApiRequest(`/vault-items/${id}/`, undefined, { authenticated: true, method: 'DELETE' })
}

export function createCredential(credentialData) {
  return sendApiRequest('/api/credentials/', credentialData, { authenticated: true })
}

export function updateCredential(id, credentialData) {
  return sendApiRequest(`/api/credentials/${id}/`, credentialData, { authenticated: true, method: 'PATCH' })
}

export function deleteCredential(id) {
  return sendApiRequest(`/api/credentials/${id}/`, undefined, { authenticated: true, method: 'DELETE' })
}

export function getLegacyAIAccess() {
  return sendApiRequest('/legacy-ai-access/', undefined, { authenticated: true, method: 'GET' })
}

export function assignLegacyAIAccess(nomineeId) {
  return sendApiRequest('/legacy-ai-access/', { nominee: nomineeId }, { authenticated: true })
}

export function removeLegacyAIAccess(id) {
  return sendApiRequest(`/legacy-ai-access/${id}/`, undefined, { authenticated: true, method: 'DELETE' })
}

export function getTrustedCircleSettings() {
  return sendApiRequest('/api/trusted-circle/settings/', undefined, { authenticated: true, method: 'GET' })
}

export function updateTrustedCircleSettings(settings) {
  return sendApiRequest('/api/trusted-circle/settings/', settings, { authenticated: true, method: 'PATCH' })
}

export function getCurrentUser() {
  return sendApiRequest('/api/user/', undefined, { authenticated: true, method: 'GET' })
}

export function getNominees() {
  return sendApiRequest('/nominees/', undefined, { authenticated: true, method: 'GET' })
}

export function getCredentials() {
  return sendApiRequest('/api/credentials/', undefined, { authenticated: true, method: 'GET' })
}

export function getVaultItems() {
  return sendApiRequest('/vault-items/', undefined, { authenticated: true, method: 'GET' })
}

export function sendStayAlive() {
  return sendApiRequest('/api/stay-alive/', {}, { authenticated: true })
}