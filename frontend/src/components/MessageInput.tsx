import React, { useRef, useCallback } from 'react'

interface MessageInputProps {
  onSend: (message: string) => void
  isLoading: boolean
  onStop: () => void
  placeholder?: string
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  isLoading,
  onStop,
  placeholder = 'Ask anything...',
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = useCallback(() => {
    const value = textareaRef.current?.value.trim()
    if (!value || isLoading) return
    onSend(value)
    if (textareaRef.current) {
      textareaRef.current.value = ''
      textareaRef.current.style.height = 'auto'
    }
  }, [onSend, isLoading])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSubmit()
      }
    },
    [handleSubmit]
  )

  const handleInput = useCallback(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`
    }
  }, [])

  return (
    <div className="ai-input-area">
      <div className="ai-input-wrapper">
        <textarea
          ref={textareaRef}
          className="ai-input-textarea"
          placeholder={placeholder}
          rows={1}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          disabled={isLoading}
        />
        {isLoading ? (
          <button className="ai-send-btn" onClick={onStop} title="Stop">
            ■
          </button>
        ) : (
          <button className="ai-send-btn" onClick={handleSubmit} title="Send">
            ↑
          </button>
        )}
      </div>
    </div>
  )
}
