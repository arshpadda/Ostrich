import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: "",
  authDomain: "ostr-499118.firebaseapp.com",
  projectId: "ostr-499118",
  storageBucket: "ostr-499118.firebasestorage.app",
  messagingSenderId: "315681122809",
  appId: "1:315681122809:web:bf2040e027170220a7b528"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const provider = new GoogleAuthProvider();
