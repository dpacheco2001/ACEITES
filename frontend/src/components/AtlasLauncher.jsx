import { useEffect, useMemo, useRef, useState } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { Compass, History, Plus, Send, StopCircle, Trash2, X } from 'lucide-react'
import AtlasMarkdown from './AtlasMarkdown.jsx'
import AtlasToolPart from './AtlasToolPart.jsx'
import LoadingProgress from './LoadingProgress.jsx'
import {
  createAtlasSession,
  loadAtlasSessions,
  saveAtlasSessions,
  titleFromMessages,
} from './atlas_sessions.js'

const INITIAL_SESSIONS = loadAtlasSessions()

export default function AtlasLauncher() {
  const [open, setOpen] = useState(false)
  const [showSessions, setShowSessions] = useState(false)
  const [sessions, setSessions] = useState(() => INITIAL_SESSIONS)
  const [activeSessionId, setActiveSessionId] = useState(() => INITIAL_SESSIONS[0].id)
  const [input, setInput] = useState('')
  const endRef = useRef(null)
  const skipPersistRef = useRef(false)
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: '/atlas-api/chat',
        credentials: 'include',
      }),
    [],
  )
  const activeSession = sessions.find((session) => session.id === activeSessionId) || sessions[0]
  const { messages, setMessages, sendMessage, status, error, stop } = useChat({
    transport,
    messages: activeSession?.messages || [],
  })
  const busy = status === 'submitted' || status === 'streaming'

  useEffect(() => {
    if (!activeSession) return
    skipPersistRef.current = true
    setMessages(activeSession.messages || [])
  }, [activeSessionId])

  useEffect(() => {
    if (!activeSession) return
    if (skipPersistRef.current) {
      skipPersistRef.current = false
      return
    }
    const updated = sessions.map((session) =>
      session.id === activeSessionId
        ? {
            ...session,
            messages,
            title: titleFromMessages(messages) || session.title,
            updatedAt: Date.now(),
          }
        : session,
    )
    setSessions(updated)
    saveAtlasSessions(updated)
  }, [messages])

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  function newSession() {
    const session = createAtlasSession()
    const updated = [session, ...sessions]
    setSessions(updated)
    saveAtlasSessions(updated)
    setActiveSessionId(session.id)
    setInput('')
    setShowSessions(false)
  }

  function openSession(sessionId) {
    setActiveSessionId(sessionId)
    setShowSessions(false)
    setInput('')
  }

  function deleteSession(sessionId) {
    const remaining = sessions.filter((session) => session.id !== sessionId)
    const updated = remaining.length ? remaining : [createAtlasSession()]
    setSessions(updated)
    saveAtlasSessions(updated)
    if (sessionId === activeSessionId) setActiveSessionId(updated[0].id)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    await sendMessage({ text })
  }

  return (
    <div className="fixed bottom-5 right-5 z-[80] flex flex-col items-end gap-3">
      {open && (
        <section className="w-[calc(100vw-2.5rem)] sm:w-[420px] h-[620px] max-h-[calc(100vh-7rem)] bg-surface-container-lowest border border-outline-variant/70 rounded-xl shadow-[0_24px_80px_rgba(15,23,42,0.22)] flex flex-col overflow-hidden">
          <header className="px-4 py-3 border-b border-outline-variant/60 bg-surface-container-low flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h2 className="font-headline text-sm font-semibold text-on-surface">Atlas</h2>
              <p className="text-[11px] font-mono text-on-surface-variant truncate">
                {activeSession?.title || 'Analista results-first'}
              </p>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setShowSessions((value) => !value)}
                className="w-8 h-8 rounded-lg hover:bg-surface-container-high flex items-center justify-center"
                aria-label="Conversaciones Atlas"
              >
                <History size={18} />
              </button>
              <button
                type="button"
                onClick={newSession}
                className="w-8 h-8 rounded-lg hover:bg-surface-container-high flex items-center justify-center"
                aria-label="Nueva conversación Atlas"
              >
                <Plus size={18} />
              </button>
              {busy && (
                <button
                  type="button"
                  onClick={stop}
                  className="w-8 h-8 rounded-lg hover:bg-surface-container-high flex items-center justify-center"
                  aria-label="Detener respuesta"
                >
                  <StopCircle size={18} />
                </button>
              )}
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="w-8 h-8 rounded-lg hover:bg-surface-container-high flex items-center justify-center"
                aria-label="Cerrar Atlas"
              >
                <X size={18} />
              </button>
            </div>
          </header>

          {showSessions && (
            <div className="border-b border-outline-variant/60 bg-surface-container-lowest p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
                  Conversaciones
                </span>
                <button
                  type="button"
                  onClick={newSession}
                  className="inline-flex items-center gap-1 rounded-lg bg-surface-container-low px-2 py-1 text-xs text-on-surface hover:bg-surface-container-high"
                >
                  <Plus size={13} />
                  Nueva
                </button>
              </div>
              <div className="max-h-40 space-y-1 overflow-y-auto">
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => openSession(session.id)}
                    className={`group flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs transition-colors ${
                      session.id === activeSessionId
                        ? 'bg-surface-container-high text-on-surface'
                        : 'text-on-surface-variant hover:bg-surface-container-low'
                    }`}
                  >
                    <span className="min-w-0 flex-1 truncate">{session.title}</span>
                    <span className="font-mono text-[10px] opacity-70">
                      {(session.messages || []).length}
                    </span>
                    <span
                      role="button"
                      tabIndex={0}
                      onClick={(event) => {
                        event.stopPropagation()
                        deleteSession(session.id)
                      }}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault()
                          event.stopPropagation()
                          deleteSession(session.id)
                        }
                      }}
                      className="rounded p-1 opacity-0 hover:bg-error/10 hover:text-error group-hover:opacity-100"
                      aria-label="Eliminar conversación"
                    >
                      <Trash2 size={13} />
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-surface">
            {messages.length === 0 && (
              <div className="rounded-lg bg-surface-container-low p-3 text-sm text-on-surface-variant">
                Pide un resumen ejecutivo, compara equipos críticos, explica una métrica o solicita un gráfico con Python.
              </div>
            )}
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {busy && (
              <LoadingProgress
                active={busy}
                label="Atlas cargando resultados"
                note="Espera que terminen las herramientas antes de tomar una conclusion."
              />
            )}
            {error && (
              <div className="rounded-lg border border-error/30 bg-error/10 p-3 text-sm text-error">
                {error.message}
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form onSubmit={handleSubmit} className="p-3 border-t border-outline-variant/60 bg-surface-container-low">
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) handleSubmit(event)
                }}
                rows={2}
                className="flex-1 resize-none rounded-lg border border-outline-variant/70 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface focus:outline focus:outline-2 focus:outline-primary-container/20"
                placeholder="Ej: compara HT017 vs HT025, explica los drivers oficiales, crea un slice y grafica Fierro/TBN si hace falta"
              />
              <button
                type="submit"
                disabled={busy || !input.trim()}
                className="w-10 h-10 rounded-lg bg-primary-container text-on-primary flex items-center justify-center disabled:opacity-40"
                aria-label="Enviar"
              >
                <Send size={18} />
              </button>
            </div>
          </form>
        </section>
      )}

      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="w-14 h-14 rounded-full bg-primary-container text-on-primary shadow-[0_18px_50px_rgba(15,23,42,0.28)] flex items-center justify-center hover:opacity-95"
        aria-label={open ? 'Cerrar Atlas' : 'Abrir Atlas'}
      >
        {open ? <X size={24} /> : <Compass size={25} />}
      </button>
    </div>
  )
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <article className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[92%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
          isUser
            ? 'bg-primary-container text-on-primary'
            : 'bg-surface-container-lowest border border-outline-variant/50 text-on-surface'
        }`}
      >
        {(message.parts || []).map((part, index) => (
          <MessagePart key={`${message.id}-${index}`} part={part} />
        ))}
      </div>
    </article>
  )
}

function MessagePart({ part }) {
  if (part.type === 'text') {
    return <AtlasMarkdown>{part.text}</AtlasMarkdown>
  }
  if (String(part.type).startsWith('tool-')) {
    return <AtlasToolPart part={part} />
  }
  return null
}
