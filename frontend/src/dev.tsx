import React from 'react'
import ReactDOM from 'react-dom/client'
import { AiAssistant } from './AiAssistant'

function DevApp() {
  return (
    <>
      <div className="dev-header">
        <h1>AI Assistant Engine</h1>
        <p>Development preview &mdash; click the button in the bottom-right corner</p>
      </div>
      <div className="dev-hint">Click the AI button &rarr;</div>
      <AiAssistant
        endpoint="/api/v1/ai"
        title="AI Assistant (Dev)"
        placeholder="Type a message..."
        welcomeMessage="Welcome! This is the standalone dev preview. The backend should be running on port 8001."
        getToken={() => 'dev-token'}
      />
    </>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(<DevApp />)
