import React, { useState, useEffect, useCallback } from 'react'
import type { AiAssistantConfig } from '../types'
import { useChat } from '../hooks/useChat'
import { useSessions } from '../hooks/useSessions'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { SessionList } from './SessionList'

interface ChatWindowProps {
  config: AiAssistantConfig
  onClose: () => void
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ config, onClose }) => {
  const [showSessions, setShowSessions] = useState(false)

  const {
    sessions,
    currentSessionId,
    setCurrentSessionId,
    fetchSessions,
    deleteSession,
    startNewSession,
  } = useSessions(config)

  const {
    messages,
    isLoading,
    sendMessage,
    stopGeneration,
    loadMessages,
    clearMessages,
  } = useChat({
    config,
    sessionId: currentSessionId,
    onSessionCreated: (id) => {
      setCurrentSessionId(id)
      fetchSessions()
    },
  })

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  const handleSelectSession = useCallback(
    (id: string) => {
      setCurrentSessionId(id)
      loadMessages(id)
      setShowSessions(false)
    },
    [setCurrentSessionId, loadMessages]
  )

  const handleNewChat = useCallback(() => {
    startNewSession()
    clearMessages()
    setShowSessions(false)
  }, [startNewSession, clearMessages])

  const title = config.title || 'AI Assistant'

  return (
    <div className="ai-chat-window">
      <div className="ai-chat-header">
        <div className="ai-chat-header-left">
          <div className="ai-chat-header-dot" />
          <span className="ai-chat-header-title">{title}</span>
        </div>
        <div className="ai-chat-header-actions">
          <button
            className="ai-header-btn"
            onClick={() => {
              setShowSessions(!showSessions)
              if (!showSessions) fetchSessions()
            }}
            title="History"
          >
            &#9776;
          </button>
          <button className="ai-header-btn" onClick={handleNewChat} title="New chat">
            +
          </button>
          <button className="ai-header-btn" onClick={onClose} title="Close">
            &minus;
          </button>
        </div>
      </div>

      <MessageList
        messages={messages}
        welcomeMessage={config.welcomeMessage}
      />

      <MessageInput
        onSend={sendMessage}
        isLoading={isLoading}
        onStop={stopGeneration}
        placeholder={config.placeholder}
      />

      {showSessions && (
        <SessionList
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelect={handleSelectSession}
          onDelete={deleteSession}
          onNewChat={handleNewChat}
          onClose={() => setShowSessions(false)}
        />
      )}
    </div>
  )
}
