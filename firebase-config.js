/*
  ═══════════════════════════════════════════════════════
  AI Exam Proctor — Firebase Configuration
  ═══════════════════════════════════════════════════════
  SETUP: Replace the values below with your Firebase project config.
  Get it from: Firebase Console → Project Overview → </> Web app
  ═══════════════════════════════════════════════════════
*/

// ── PASTE YOUR FIREBASE CONFIG HERE ──────────────────
const firebaseConfig = {
  apiKey:            "YOUR_API_KEY",
  authDomain:        "YOUR_PROJECT.firebaseapp.com",
  projectId:         "YOUR_PROJECT_ID",
  storageBucket:     "YOUR_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId:             "YOUR_APP_ID"
};
// ─────────────────────────────────────────────────────

// Initialize Firebase (compat SDK — no import needed)
if (!firebase.apps.length) {
  firebase.initializeApp(firebaseConfig);
}
const db = firebase.firestore();

// ── Password hashing ──────────────────────────────────
async function hashPassword(password) {
  const msgBuffer  = new TextEncoder().encode(password);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray  = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2,'0')).join('');
}

// ── FACULTY ──────────────────────────────────────────
async function fb_facultyRegister(name, email, password) {
  const hash = await hashPassword(password);
  const ref  = db.collection('faculty').doc(email.toLowerCase());
  const snap = await ref.get();
  if (snap.exists) throw new Error('Account with this email already exists.');
  await ref.set({ name, email: email.toLowerCase(), password: hash, created: new Date().toISOString() });
}

async function fb_facultyLogin(email, password) {
  const hash = await hashPassword(password);
  const snap = await db.collection('faculty').doc(email.toLowerCase()).get();
  if (!snap.exists || snap.data().password !== hash) throw new Error('Email or password is incorrect.');
  return snap.data();
}

// ── ROOMS ─────────────────────────────────────────────
async function fb_createRoom(code, facultyEmail, examName) {
  await db.collection('rooms').doc(code.toUpperCase()).set({
    code:          code.toUpperCase(),
    faculty_email: facultyEmail.toLowerCase(),
    exam_name:     examName,
    created:       new Date().toISOString(),
    active:        true
  });
}

async function fb_validateRoom(code) {
  const snap = await db.collection('rooms').doc(code.toUpperCase()).get();
  if (!snap.exists || !snap.data().active) throw new Error('Invalid room code. Ask your faculty.');
  return snap.data();
}

// ── STUDENTS ──────────────────────────────────────────
async function fb_studentLogin(name, id, subject, code, email, password) {
  await fb_validateRoom(code);
  const hash     = await hashPassword(password);
  const studRef  = db.collection('students').doc(email.toLowerCase());
  const studSnap = await studRef.get();
  if (studSnap.exists) {
    if (studSnap.data().password !== hash) throw new Error('Incorrect password for this email.');
  } else {
    await studRef.set({ email: email.toLowerCase(), password: hash, created: new Date().toISOString() });
  }
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
  return { role:'student', name, id, subject, email, roomCode:code.toUpperCase(), examId, loginTime:new Date().toISOString() };
}

// ── VIOLATIONS ────────────────────────────────────────
async function fb_logViolation(examId, num, timeStr, msg, integrity) {
  await db.collection('sessions').doc(examId)
    .collection('violations').add({ num, time: timeStr, msg, integrity });
  await db.collection('sessions').doc(examId).update({
    violations:  num,
    integrity,
    status:      num >= 5 ? 'critical' : 'warning',
    last_update: new Date().toISOString()
  });
}

// ── DASHBOARD ─────────────────────────────────────────
function fb_listenToRoom(roomCode, callback) {
  return db.collection('sessions')
    .where('room_code', '==', roomCode.toUpperCase())
    .onSnapshot(snap => {
      callback(snap.docs.map(d => d.data()));
    });
}

// ── SESSION END ───────────────────────────────────────
async function fb_endSession(examId) {
  await db.collection('sessions').doc(examId).update({
    status:      'ended',
    last_update: new Date().toISOString()
  });
}
