import { useState, useCallback, useRef } from 'react'
import type { ChatMessage, AiAssistantConfig } from '../types'

interface UseChatOptions {
  config: AiAssistantConfig
  sessionId: string | null
  onSessionCreated?: (id: string) => void
}

export function useChat({ config, sessionId, onSessionCreated }: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const getAuthToken = useCallback(() => {
    if (config.getToken) return config.getToken()
    if (config.token) return config.token
    return localStorage.getItem('access_token')
  }, [config])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }

    const assistantMessage: ChatMessage = {
      id: `temp-assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      isStreaming: true,
    }

    setMessages(prev => [...prev, userMessage, assistantMessage])
    setIsLoading(true)

    abortRef.current = new AbortController()

    try {
      const token = getAuthToken()
      const response = await fetch(`${config.endpoint}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: content,
          session_id: sessionId,
        }),
        signal: abortRef.current.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventType = line.slice(7).trim()
            continue
          }
          if (!line.startsWith('data: ')) continue

          const data = line.slice(6)

          // Parse the event type from the preceding event line
          // SSE format: event: xxx\ndata: yyy
          const eventMatch = lines.find(l =>
            l.startsWith('event: ') && lines.indexOf(l) < lines.indexOf(line)
          )

          // We handle events by checking buffer context
          if (data === '') continue

          try {
            // Try to parse as JSON first (for session, tool_call events)
            const parsed = JSON.parse(data)
            if (parsed.session_id && !sessionId) {
              onSessionCreated?.(parsed.session_id)
            }
          } catch {
            // Plain text — streaming content
            setMessages(prev => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last && last.role === 'assistant' && last.isStreaming) {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + data,
                }
              }
              return updated
            })
          }
        }
      }

      // Mark streaming as complete
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last && last.isStreaming) {
          updated[updated.length - 1] = { ...last, isStreaming: false }
        }
        return updated
      })
    } catch (err: any) {
      if (err.name === 'AbortError') return
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last && last.isStreaming) {
          updated[updated.length - 1] = {
            ...last,
            content: `Error: ${err.message}`,
            isStreaming: false,
          }
        }
        return updated
      })
    } finally {
      setIsLoading(false)
      abortRef.current = null
    }
  }, [config, sessionId, isLoading, getAuthToken, onSessionCreated])

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort()
    setIsLoading(false)
  }, [])

  const loadMessages = useCallback(async (sid: string) => {
    const token = getAuthToken()
    try {
      const res = await fetch(`${config.endpoint}/sessions/${sid}/messages`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(data)
      }
    } catch {
      // silently fail
    }
  }, [config, getAuthToken])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return {
    messages,
    isLoading,
    sendMessage,
    stopGeneration,
    loadMessages,
    clearMessages,
  }
}
