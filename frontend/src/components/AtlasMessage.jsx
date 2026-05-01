import AtlasMarkdown from './AtlasMarkdown.jsx'
import AtlasToolPart from './AtlasToolPart.jsx'

export default function AtlasMessage({ message }) {
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
