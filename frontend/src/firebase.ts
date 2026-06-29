import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

// Firebase web config is read from VITE_FIREBASE_* env vars (see frontend/.env).
// These are public client identifiers, not secrets. The fallbacks keep local dev
// working but should be overridden via .env (e.g. after rotating the API key).
const env = import.meta.env;
const firebaseConfig = {
  apiKey: env.VITE_FIREBASE_API_KEY ?? "AIzaSyBgDw2Gu2D_ykZVNQhopYO7e1CXsVxrNuY",
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN ?? "ostr-499118.firebaseapp.com",
  projectId: env.VITE_FIREBASE_PROJECT_ID ?? "ostr-499118",
  storageBucket: env.VITE_FIREBASE_STORAGE_BUCKET ?? "ostr-499118.firebasestorage.app",
  messagingSenderId: env.VITE_FIREBASE_MESSAGING_SENDER_ID ?? "315681122809",
  appId: env.VITE_FIREBASE_APP_ID ?? "1:315681122809:web:bf2040e027170220a7b528",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
