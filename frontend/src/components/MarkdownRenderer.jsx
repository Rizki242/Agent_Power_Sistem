import React, { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

/**
 * Memecah konten teks menjadi blok Markdown standar dan blok Tabel Markdown.
 * Mendukung format tabel baris baru biasa maupun baris tabel yang tergabung oleh '| |'.
 */
function parseMarkdownBlocks(text) {
  if (!text || typeof text !== 'string') return []

  // Normalisasi jika ada baris tabel yang tersambung dengan '| |'
  const normalized = text.replace(/\|\s*\|\s*(?=[^|\n]+?\|)/g, '|\n| ')
  const lines = normalized.split('\n')
  const blocks = []
  let currentText = []
  let inTable = false
  let tableLines = []

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i]
    const trimmed = rawLine.trim()
    const isTableRow = trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length > 2

    if (isTableRow) {
      if (!inTable) {
        if (currentText.length > 0) {
          blocks.push({ type: 'markdown', content: currentText.join('\n') })
          currentText = []
        }
        inTable = true
        tableLines = []
      }
      tableLines.push(trimmed)
    } else {
      if (inTable) {
        blocks.push({ type: 'table', lines: tableLines })
        inTable = false
        tableLines = []
      }
      currentText.push(rawLine)
    }
  }

  if (inTable && tableLines.length > 0) {
    blocks.push({ type: 'table', lines: tableLines })
  } else if (currentText.length > 0) {
    blocks.push({ type: 'markdown', content: currentText.join('\n') })
  }

  return blocks
}

/**
 * Parsing baris tabel markdown menjadi struktur { headers, rows }
 */
function parseTableData(lines) {
  const parseRow = (line) => {
    const trimmed = line.replace(/^\|/, '').replace(/\|$/, '')
    return trimmed.split('|').map((c) => c.trim())
  }
  const isSeparator = (line) => /^\|?(\s*:?-+:?\s*\|?)+$/.test(line)

  let headerRow = null
  const dataRows = []

  for (let i = 0; i < lines.length; i++) {
    const l = lines[i]
    if (isSeparator(l)) {
      continue
    }
    if (!headerRow) {
      headerRow = parseRow(l)
    } else {
      dataRows.push(parseRow(l))
    }
  }

  return { headers: headerRow || [], rows: dataRows }
}

const markdownComponents = {
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
  strong: ({ children }) => <strong className="st-chat-strong">{children}</strong>,
  em: ({ children }) => <em className="st-chat-em">{children}</em>,
}

// Komponen renderer untuk sel tabel (agar rumus KaTeX dan format bold dalam sel tetap aktif)
function TableCellContent({ text }) {
  if (!text) return null
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
      components={markdownComponents}
    >
      {text}
    </ReactMarkdown>
  )
}

function RenderedTableBlock({ lines }) {
  const { headers, rows } = useMemo(() => parseTableData(lines), [lines])

  if (!headers.length && !rows.length) {
    return null
  }

  return (
    <div className="st-chat-table-wrapper">
      <table className="st-chat-table">
        {headers.length > 0 && (
          <thead className="st-chat-thead">
            <tr className="st-chat-tr">
              {headers.map((h, i) => (
                <th key={i} className="st-chat-th">
                  <TableCellContent text={h} />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="st-chat-tbody">
          {rows.map((row, rIdx) => (
            <tr key={rIdx} className="st-chat-tr">
              {row.map((cell, cIdx) => (
                <td key={cIdx} className="st-chat-td">
                  <TableCellContent text={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const MarkdownRenderer = React.memo(function MarkdownRenderer({ content }) {
  if (!content) return null

  const blocks = useMemo(() => parseMarkdownBlocks(content), [content])

  return (
    <div className="st-markdown-container">
      {blocks.map((block, idx) => {
        if (block.type === 'table') {
          return <RenderedTableBlock key={idx} lines={block.lines} />
        }
        return (
          <ReactMarkdown
            key={idx}
            remarkPlugins={[remarkMath]}
            rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
            components={markdownComponents}
          >
            {block.content}
          </ReactMarkdown>
        )
      })}
    </div>
  )
})

export default MarkdownRenderer
