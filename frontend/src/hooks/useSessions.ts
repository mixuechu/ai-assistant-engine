import { useState, useCallback } from 'react'
import type { ChatSession, AiAssistantConfig } from '../types'

export function useSessions(config: AiAssistantConfig) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  const getAuthToken = useCallback(() => {
    if (config.getToken) return config.getToken()
    if (config.token) return config.token
    return localStorage.getItem('access_token')
  }, [config])

  const headers = useCallback(() => {
    const token = getAuthToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [getAuthToken])

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${config.endpoint}/sessions`, {
        headers: headers(),
      })
      if (res.ok) {
        setSessions(await res.json())
      }
    } catch {
      // silently fail
    }
  }, [config, headers])

  const deleteSession = useCallback(async (id: string) => {
    try {
      await fetch(`${config.endpoint}/sessions/${id}`, {
        method: 'DELETE',
        headers: headers(),
      })
      setSessions(prev => prev.filter(s => s.id !== id))
      if (currentSessionId === id) {
        setCurrentSessionId(null)
      }
    } catch {
      // silently fail
    }
  }, [config, headers, currentSessionId])

  const renameSession = useCallback(async (id: string, title: string) => {
    try {
      const res = await fetch(`${config.endpoint}/sessions/${id}/title`, {
        method: 'PUT',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      })
      if (res.ok) {
        const updated = await res.json()
        setSessions(prev => prev.map(s => s.id === id ? updated : s))
      }
    } catch {
      // silently fail
    }
  }, [config, headers])

  const startNewSession = useCallback(() => {
    setCurrentSessionId(null)
  }, [])

  return {
    sessions,
    currentSessionId,
    setCurrentSessionId,
    fetchSessions,
    deleteSession,
    renameSession,
    startNewSession,
  }
}
