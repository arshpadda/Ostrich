import './style.css'
import { signInWithPopup, signOut, onAuthStateChanged } from 'firebase/auth'
import { auth, provider } from './src/firebase'

// DOM Elements
const loginBtn = document.querySelector('#login-btn')
const logoutBtn = document.querySelector('#logout-btn')
const profileCard = document.querySelector('#profile-card')
const userInfo = document.querySelector('#user-info')

const API_URL = 'http://localhost:8000'

// Auth State Listener
onAuthStateChanged(auth, async (user) => {
  if (user) {
    // User is signed in
    loginBtn.style.display = 'none'
    profileCard.classList.remove('hidden')
    userInfo.innerHTML = '<p>Loading profile...</p>'
    
    try {
      const token = await user.getIdToken()
      
      // Attempt to create user or get profile
      await createUserProfile(token, user)
      const profile = await fetchUserProfile(token)
      
      showProfile(profile)
    } catch (error) {
      console.error("Error fetching user profile", error)
      userInfo.innerHTML = `<p class="error">Failed to load profile. Ensure the backend is running!</p>`
    }
  } else {
    // User is signed out
    loginBtn.style.display = 'flex'
    profileCard.classList.add('hidden')
    userInfo.innerHTML = ''
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

// API Calls
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

async function fetchUserProfile(token) {
  const res = await fetch(`${API_URL}/users/me`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  if (!res.ok) throw new Error("Failed to fetch")
  return await res.json()
}

// UI Rendering
function showProfile(profile) {
  userInfo.innerHTML = `
    <div class="profile-avatar">${profile.first_name[0].toUpperCase()}</div>
    <h2>Welcome, ${profile.first_name}!</h2>
    <div class="profile-details">
      <p><span>Email:</span> ${profile.email}</p>
      <p><span>ID:</span> <small>${profile.id}</small></p>
      <p><span>Joined:</span> ${new Date(profile.created_at).toLocaleDateString()}</p>
    </div>
  `
}
