import { useState, useCallback, useRef } from 'react'
import type { ChatMessage, AiAssistantConfig, ToolStatus } from '../types'

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
      let currentEvent = ''
      let dataLines: string[] = []

      const flushEvent = () => {
        if (!currentEvent || dataLines.length === 0) return
        const data = dataLines.join('\n')

        if (currentEvent === 'session') {
          try {
            const parsed = JSON.parse(data)
            if (parsed.session_id) {
              onSessionCreated?.(parsed.session_id)
            }
          } catch { /* ignore */ }
        } else if (currentEvent === 'text') {
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
        } else if (currentEvent === 'tool_executing') {
          try {
            const parsed = JSON.parse(data)
            const toolStatus: ToolStatus = { name: parsed.name || 'tool', status: 'executing' }
            setMessages(prev => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last && last.role === 'assistant' && last.isStreaming) {
                const statuses = [...(last.toolStatuses || []), toolStatus]
                updated[updated.length - 1] = { ...last, toolStatuses: statuses }
              }
              return updated
            })
          } catch { /* ignore */ }
        } else if (currentEvent === 'tool_result') {
          try {
            const parsed = JSON.parse(data)
            setMessages(prev => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last && last.role === 'assistant' && last.isStreaming && last.toolStatuses) {
                const statuses = last.toolStatuses.map(ts =>
                  ts.name === (parsed.name || '') ? { ...ts, status: 'done' as const } : ts
                )
                updated[updated.length - 1] = { ...last, toolStatuses: statuses, content: '' }
              }
              return updated
            })
          } catch { /* ignore */ }
        } else if (currentEvent === 'error') {
          setMessages(prev => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last && last.isStreaming) {
              updated[updated.length - 1] = {
                ...last,
                content: `Error: ${data}`,
                isStreaming: false,
              }
            }
            return updated
          })
        }

        currentEvent = ''
        dataLines = []
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true }).replace(/\r/g, '')
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            flushEvent()
            currentEvent = line.slice(7).trim()
            continue
          }

          if (line.startsWith('data:')) {
            dataLines.push(line.startsWith('data: ') ? line.slice(6) : line.slice(5))
            continue
          }

          if (line.trim() === '') {
            flushEvent()
          }
        }
      }
      flushEvent()

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
