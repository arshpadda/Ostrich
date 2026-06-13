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
let currentUserToken = null;

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
      
    } catch (error) {
      console.error("Error setting up chat", error)
      alert("Failed to connect to backend. Please make sure the server is running.")
    }
  } else {
    // User is signed out
    currentUserToken = null;
    loginView.classList.remove('hidden')
    chatView.classList.add('hidden')
    chatMessages.innerHTML = `
      <div class="message bot-message">
        <p>Welcome! Type a message below and it will be saved to your sandbox.</p>
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
      messages.forEach(msg => {
        appendMessage(msg.content, msg.is_bot)
      })
    }
  }
}

// Handle sending new messages
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault()
  
  const text = chatInput.value.trim()
  if (!text || !currentUserToken) return
  
  // Immediately show in UI
  appendMessage(text, false)
  chatInput.value = ''
  
  try {
    // Send to backend
    await fetch(`${API_URL}/chat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentUserToken}`
      },
      body: JSON.stringify({ content: text })
    })
  } catch (error) {
    console.error("Failed to send message", error)
    appendMessage("Failed to send message to server.", true)
  }
})

function appendMessage(text, isBot) {
  const msgDiv = document.createElement('div')
  msgDiv.className = `message ${isBot ? 'bot-message' : 'user-message'}`
  msgDiv.textContent = text
  chatMessages.appendChild(msgDiv)
  
  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight
}
