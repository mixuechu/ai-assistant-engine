import React from 'react'
import type { ChatSession } from '../types'

interface SessionListProps {
  sessions: ChatSession[]
  currentSessionId: string | null
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onNewChat: () => void
  onClose: () => void
}

export const SessionList: React.FC<SessionListProps> = ({
  sessions,
  currentSessionId,
  onSelect,
  onDelete,
  onNewChat,
  onClose,
}) => {
  return (
    <div className="ai-sessions-panel">
      <div className="ai-sessions-header">
        <span className="ai-sessions-title">History</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="ai-header-btn" onClick={onNewChat} title="New chat">
            +
          </button>
          <button className="ai-header-btn" onClick={onClose} title="Close">
            &times;
          </button>
        </div>
      </div>
      <div className="ai-sessions-list">
        {sessions.map(s => (
          <div
            key={s.id}
            className={`ai-session-item ${s.id === currentSessionId ? 'ai-active' : ''}`}
            onClick={() => onSelect(s.id)}
          >
            <span className="ai-session-item-title">{s.title}</span>
            <button
              className="ai-session-item-delete"
              onClick={e => {
                e.stopPropagation()
                onDelete(s.id)
              }}
              title="Delete"
            >
              &times;
            </button>
          </div>
        ))}
        {sessions.length === 0 && (
          <div style={{ padding: 16, textAlign: 'center', color: 'var(--ai-text-secondary)', fontSize: 13 }}>
            No conversations yet
          </div>
        )}
      </div>
    </div>
  )
}
