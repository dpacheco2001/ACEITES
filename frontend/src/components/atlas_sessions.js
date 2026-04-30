const STORAGE_KEY = 'oilmine.atlas.sessions.v1'

export function createAtlasSession(messages = []) {
  const now = Date.now()
  return {
    id: typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `atlas-${now}`,
    title: titleFromMessages(messages) || 'Nueva conversacion',
    messages,
    createdAt: now,
    updatedAt: now,
  }
}

export function loadAtlasSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    const sessions = Array.isArray(parsed)
      ? parsed.filter((item) => item?.id && Array.isArray(item.messages))
      : []
    return sessions.length ? sortSessions(sessions) : [createAtlasSession()]
  } catch {
    return [createAtlasSession()]
  }
}

export function saveAtlasSessions(sessions) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sortSessions(sessions)))
}

export function titleFromMessages(messages) {
  const firstUser = messages.find((message) => message.role === 'user')
  const text = firstUser?.parts
    ?.filter((part) => part.type === 'text')
    ?.map((part) => part.text)
    ?.join(' ')
    ?.trim()
  if (!text) return ''
  return text.length > 58 ? `${text.slice(0, 55)}...` : text
}

export function sortSessions(sessions) {
  return sessions.slice().sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))
}
