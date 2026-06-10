import React, { useEffect, useRef } from 'react'
import type { ChatMessage } from '../types'

interface MessageListProps {
  messages: ChatMessage[]
  welcomeMessage?: string
}

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
            <div className="ai-message-bubble">{msg.content}</div>
          </div>
        ))}
      <div ref={endRef} />
    </div>
  )
}
