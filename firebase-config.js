/*
  ═══════════════════════════════════════════════════════
  AI Exam Proctor — Firebase Configuration
  ═══════════════════════════════════════════════════════
  
  SETUP STEPS (5 minutes):
  1. Go to https://console.firebase.google.com
  2. Click "Add project" → name it "exam-proctor" → Create
  3. Click "Web" icon (</>) to add web app → Register app
  4. Copy the firebaseConfig object and paste it below
  5. In Firebase console → Build → Firestore Database
     → Create database → Start in TEST MODE → Enable
  6. Done! Push to GitHub Pages and it works.

  ═══════════════════════════════════════════════════════
*/

// ── PASTE YOUR FIREBASE CONFIG HERE ──────────────────
// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDQw4bHHvf64cDn8L0eJliQ9rRDeFkp_Eg",
  authDomain: "proctor-ai-87d06.firebaseapp.com",
  projectId: "proctor-ai-87d06",
  storageBucket: "proctor-ai-87d06.firebasestorage.app",
  messagingSenderId: "28127012869",
  appId: "1:28127012869:web:e4f55c75cb7e7e5a8ed46c"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
// ─────────────────────────────────────────────────────

// Initialize Firebase
firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();

/*
  ═══════════════════════════════════
  HELPER FUNCTIONS
  Used by login.html, index.html, faculty.html
  ═══════════════════════════════════
*/

// Simple SHA-256 password hash (browser-native)
async function hashPassword(password) {
  const msgBuffer = new TextEncoder().encode(password);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray  = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// ── FACULTY ──────────────────────────────────────────

async function facultyRegister(name, email, password) {
  const hash = await hashPassword(password);
  const ref  = db.collection('faculty').doc(email.toLowerCase());
  const snap = await ref.get();
  if (snap.exists) throw new Error('Account with this email already exists.');
  await ref.set({ name, email: email.toLowerCase(), password: hash, created: new Date().toISOString() });
}

async function facultyLogin(email, password) {
  const hash = await hashPassword(password);
  const snap = await db.collection('faculty').doc(email.toLowerCase()).get();
  if (!snap.exists || snap.data().password !== hash) throw new Error('Email or password is incorrect.');
  return snap.data();
}

// ── ROOMS ─────────────────────────────────────────────

async function createRoom(code, facultyEmail, examName) {
  await db.collection('rooms').doc(code.toUpperCase()).set({
    code: code.toUpperCase(),
    faculty_email: facultyEmail.toLowerCase(),
    exam_name: examName,
    created: new Date().toISOString(),
    active: true
  });
}

async function validateRoom(code) {
  const snap = await db.collection('rooms').doc(code.toUpperCase()).get();
  if (!snap.exists || !snap.data().active) throw new Error('Invalid room code. Ask your faculty.');
  return snap.data();
}

// ── STUDENTS ──────────────────────────────────────────

async function studentLogin(name, id, subject, code, email, password) {
  // Validate room
  await validateRoom(code);

  const hash     = await hashPassword(password);
  const studRef  = db.collection('students').doc(email.toLowerCase());
  const studSnap = await studRef.get();

  if (studSnap.exists) {
    if (studSnap.data().password !== hash) throw new Error('Incorrect password for this email.');
  } else {
    await studRef.set({ email: email.toLowerCase(), password: hash, created: new Date().toISOString() });
  }

  // Create exam session
  const examId = 'EX-' + Math.floor(Math.random() * 90000 + 10000);
  await db.collection('sessions').doc(examId).set({
    exam_id:       examId,
    student_id:    id,
    student_name:  name,
    student_email: email.toLowerCase(),
    subject,
    room_code:     code.toUpperCase(),
    login_time:    new Date().toISOString(),
    violations:    0,
    integrity:     100,
    status:        'active'
  });

  return { role: 'student', name, id, subject, email, roomCode: code.toUpperCase(), examId, loginTime: new Date().toISOString() };
}

// ── VIOLATIONS ────────────────────────────────────────

async function logViolation(examId, num, timeStr, msg, integrity) {
  // Add to violations subcollection
  await db.collection('sessions').doc(examId)
    .collection('violations').add({ num, time: timeStr, msg, integrity });
  // Update session totals
  await db.collection('sessions').doc(examId).update({
    violations: num,
    integrity,
    status:     num >= 5 ? 'critical' : 'warning',
    last_update: new Date().toISOString()
  });
}

// ── DASHBOARD ─────────────────────────────────────────

function listenToRoom(roomCode, callback) {
  // Real-time listener — updates faculty dashboard instantly
  return db.collection('sessions')
    .where('room_code', '==', roomCode.toUpperCase())
    .onSnapshot(snap => {
      const students = snap.docs.map(d => d.data());
      callback(students);
    });
}

// ── SESSION END ───────────────────────────────────────

async function endSession(examId) {
  await db.collection('sessions').doc(examId).update({
    status: 'ended',
    last_update: new Date().toISOString()
  });
}
