import './style.css'
import { signInWithPopup, signOut, onAuthStateChanged } from 'firebase/auth'
import { auth, provider } from './src/firebase'

// DOM Elements
const loginView = document.querySelector('#login-view')
const chatView = document.querySelector('#chat-view')
const loginBtn = document.querySelector('#login-btn')
const logoutBtn = document.querySelector('#logout-btn')
const chatForm = document.querySelector('#chat-form')
const chatInput = document.querySelector('#chat-input')
const chatMessages = document.querySelector('#chat-messages')

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_URL = API_URL.replace(/^http/, 'ws')
let currentUserToken = null;
let ws = null;

// Auth State Listener
onAuthStateChanged(auth, async (user) => {
  if (user) {
    // User is signed in
    loginView.classList.add('hidden')
    chatView.classList.remove('hidden')
    
    try {
      currentUserToken = await user.getIdToken()
      
      // Ensure user profile exists in Postgres
      await createUserProfile(currentUserToken, user)
      
      // Load chat history
      await loadChatHistory(currentUserToken)

      // Connect WebSocket for bidirectional channel
      connectWebSocket(currentUserToken)
      
    } catch (error) {
      console.error("Error setting up chat", error)
      alert("Failed to connect to backend. Please make sure the server is running.")
    }
  } else {
    // User is signed out
    currentUserToken = null;
    if (ws) {
      ws.close()
      ws = null;
    }
    loginView.classList.remove('hidden')
    chatView.classList.add('hidden')
    chatMessages.innerHTML = `
      <div class="message bot-message">
        <p>Welcome! Type a message below and it will be sent to your sandbox.</p>
      </div>
    `
  }
})

// Login Action
loginBtn.addEventListener('click', async () => {
  try {
    await signInWithPopup(auth, provider)
  } catch (error) {
    console.error("Login failed", error)
  }
})

// Logout Action
logoutBtn.addEventListener('click', () => {
  signOut(auth)
})

// API Calls - Auth
async function createUserProfile(token, user) {
  const payload = {
    email: user.email,
    first_name: user.displayName?.split(' ')[0] || 'User',
    last_name: user.displayName?.split(' ')[1] || ''
  }

  await fetch(`${API_URL}/users/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  }).catch(() => {}) // Ignore 400 user exists
}

// API Calls - Chat
async function loadChatHistory(token) {
  const res = await fetch(`${API_URL}/chat/`, {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  
  if (res.ok) {
    const messages = await res.json()
    // Keep the welcome message if empty, otherwise render history
    if (messages.length > 0) {
      chatMessages.innerHTML = ''
      const fragment = document.createDocumentFragment()
      messages.forEach(msg => {
        appendMessage(msg.content, msg.is_bot, fragment)
      })
      chatMessages.appendChild(fragment)
      chatMessages.scrollTop = chatMessages.scrollHeight
    }
  }
}

// WebSocket Connection
function connectWebSocket(token) {
  if (ws) ws.close();
  ws = new WebSocket(`${WS_URL}/ws/chat?token=${token}`);
  
  ws.onmessage = (event) => {
    console.log("Raw WebSocket Message Received:", event.data);
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'system') {
        console.log("System Message:", data.message);
      } else if (data.content) {
        // Assume messages coming back from ws are from the sandbox (bot)
        if (data.role !== 'user') {
          appendMessage(data.content, true);
        }
      }
    } catch (e) {
      // If it's not JSON, treat it as a raw string
      appendMessage(event.data, true);
    }
  };
  
  ws.onclose = () => {
    console.log("WebSocket closed");
  };
}

// Handle sending new messages
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault()
  
  const text = chatInput.value.trim()
  if (!text || !currentUserToken) return
  
  // Immediately show in UI
  appendMessage(text, false)
  chatInput.value = ''
  
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(text);
  } else {
    appendMessage("Failed to send message: Sandbox disconnected.", true)
  }
})

function appendMessage(text, isBot, targetNode = chatMessages) {
  const msgDiv = document.createElement('div')
  msgDiv.className = `message ${isBot ? 'bot-message' : 'user-message'}`
  msgDiv.textContent = text
  targetNode.appendChild(msgDiv)
  
  // Only scroll if we are appending directly to the visible chat container
  if (targetNode === chatMessages) {
    chatMessages.scrollTop = chatMessages.scrollHeight
  }
}
