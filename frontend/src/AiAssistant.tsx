import React, { useState } from 'react'
import type { AiAssistantConfig } from './types'
import { ChatWindow } from './components/ChatWindow'
import './styles/assistant.css'

interface AiAssistantProps extends Partial<AiAssistantConfig> {
  endpoint: string
}

export const AiAssistant: React.FC<AiAssistantProps> = (props) => {
  const [isOpen, setIsOpen] = useState(false)

  const config: AiAssistantConfig = {
    endpoint: props.endpoint,
    token: props.token,
    getToken: props.getToken,
    title: props.title,
    placeholder: props.placeholder,
    welcomeMessage: props.welcomeMessage,
    position: props.position || 'bottom-right',
    theme: props.theme || 'dark',
  }

  return (
    <div className="ai-assistant-vars">
      <button
        className={`ai-trigger-btn ${isOpen ? 'ai-hidden' : ''}`}
        onClick={() => setIsOpen(true)}
        title="Open AI Assistant"
      >
        AI
      </button>

      {isOpen && (
        <ChatWindow
          config={config}
          onClose={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}
