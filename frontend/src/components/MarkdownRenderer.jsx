import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

const MarkdownRenderer = React.memo(function MarkdownRenderer({ content }) {
  if (!content) return null

  return (
    <div className="st-markdown-container">
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
        components={{
          h1: ({ children }) => <h2 className="st-chat-h1">{children}</h2>,
          h2: ({ children }) => <h3 className="st-chat-h2">{children}</h3>,
          h3: ({ children }) => <h4 className="st-chat-h3">{children}</h4>,
          h4: ({ children }) => <h5 className="st-chat-h4">{children}</h5>,
          p: ({ children }) => <p className="st-chat-p">{children}</p>,
          ul: ({ children }) => <ul className="st-chat-ul">{children}</ul>,
          ol: ({ children }) => <ol className="st-chat-ol">{children}</ol>,
          li: ({ children }) => <li className="st-chat-li">{children}</li>,
          hr: () => <hr className="st-chat-hr" />,
          blockquote: ({ children }) => (
            <blockquote className="st-chat-blockquote">{children}</blockquote>
          ),
          code: ({ inline, className, children, ...props }) => {
            if (inline) {
              return (
                <code className="st-chat-inline-code" {...props}>
                  {children}
                </code>
              )
            }
            return (
              <div className="st-chat-code-card">
                <pre className="st-chat-pre" {...props}>
                  <code className={className || 'language-text'}>{children}</code>
                </pre>
              </div>
            )
          },
          table: ({ children }) => (
            <div className="st-chat-table-wrapper">
              <table className="st-chat-table">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="st-chat-th">{children}</th>,
          td: ({ children }) => <td className="st-chat-td">{children}</td>,
          strong: ({ children }) => <strong className="st-chat-strong">{children}</strong>,
          em: ({ children }) => <em className="st-chat-em">{children}</em>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
})

export default MarkdownRenderer
