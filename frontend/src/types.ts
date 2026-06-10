export interface ToolStatus {
  name: string
  status: 'executing' | 'done'
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  tool_calls_json?: string | null
  created_at: string
  isStreaming?: boolean
  toolStatuses?: ToolStatus[]
}

export interface ChatSession {
  id: string
  title: string
  message_count: number
  model?: string | null
  created_at: string
  updated_at: string
}

export interface AiAssistantConfig {
  endpoint: string
  token?: string
  getToken?: () => string | null
  title?: string
  placeholder?: string
  welcomeMessage?: string
  position?: 'bottom-right' | 'bottom-left'
  theme?: 'dark' | 'light' | 'auto'
}
