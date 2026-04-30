import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function AtlasMarkdown({ children, compact = false }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children: node }) => (
          <p className={compact ? 'mb-1 last:mb-0' : 'mb-2 last:mb-0'}>{node}</p>
        ),
        ul: ({ children: node }) => (
          <ul className="mb-2 ml-4 list-disc space-y-1 last:mb-0">{node}</ul>
        ),
        ol: ({ children: node }) => (
          <ol className="mb-2 ml-4 list-decimal space-y-1 last:mb-0">{node}</ol>
        ),
        li: ({ children: node }) => <li className="pl-1">{node}</li>,
        strong: ({ children: node }) => (
          <strong className="font-semibold text-inherit">{node}</strong>
        ),
        h1: ({ children: node }) => (
          <h3 className="mb-2 text-base font-semibold text-on-surface">{node}</h3>
        ),
        h2: ({ children: node }) => (
          <h3 className="mb-2 text-sm font-semibold text-on-surface">{node}</h3>
        ),
        h3: ({ children: node }) => (
          <h4 className="mb-1 text-sm font-semibold text-on-surface">{node}</h4>
        ),
        code: ({ inline, children: node }) =>
          inline ? (
            <code className="rounded bg-surface-container-high px-1 py-0.5 font-mono text-[0.9em]">
              {node}
            </code>
          ) : (
            <code className="block overflow-x-auto rounded bg-surface-container-high p-2 font-mono text-xs">
              {node}
            </code>
          ),
        pre: ({ children: node }) => <pre className="mb-2 overflow-x-auto">{node}</pre>,
        table: ({ children: node }) => (
          <div className="mb-2 overflow-x-auto rounded border border-outline-variant/50">
            <table className="w-full text-left text-xs">{node}</table>
          </div>
        ),
        th: ({ children: node }) => (
          <th className="border-b border-outline-variant/50 bg-surface-container-low px-2 py-1 font-semibold">
            {node}
          </th>
        ),
        td: ({ children: node }) => (
          <td className="border-b border-outline-variant/30 px-2 py-1">{node}</td>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  )
}
