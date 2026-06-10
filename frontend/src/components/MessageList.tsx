import React, { useEffect, useRef } from 'react'
import type { ChatMessage, ToolStatus } from '../types'

interface MessageListProps {
  messages: ChatMessage[]
  welcomeMessage?: string
}

const ToolStatusIndicator: React.FC<{ statuses: ToolStatus[] }> = ({ statuses }) => (
  <div className="ai-tool-statuses">
    {statuses.map((ts, i) => (
      <div key={i} className={`ai-tool-status ai-tool-status-${ts.status}`}>
        <span className="ai-tool-status-icon">
          {ts.status === 'executing' ? '⟳' : '✓'}
        </span>
        <span className="ai-tool-status-text">
          {ts.status === 'executing' ? `正在查询 ${ts.name}...` : `${ts.name} 完成`}
        </span>
      </div>
    ))}
  </div>
)

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  welcomeMessage = 'Hi! Ask me anything about the system.',
}) => {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="ai-welcome">
        <div className="ai-welcome-icon">AI</div>
        <div className="ai-welcome-text">{welcomeMessage}</div>
      </div>
    )
  }

  return (
    <div className="ai-message-list">
      {messages
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .map(msg => (
          <div
            key={msg.id}
            className={`ai-message ai-message-${msg.role} ${msg.isStreaming ? 'ai-streaming' : ''}`}
          >
            {msg.toolStatuses && msg.toolStatuses.length > 0 && (
              <ToolStatusIndicator statuses={msg.toolStatuses} />
            )}
            {msg.content && <div className="ai-message-bubble">{msg.content}</div>}
          </div>
        ))}
      <div ref={endRef} />
    </div>
  )
}
