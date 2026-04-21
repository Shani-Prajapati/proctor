// AI Exam Proctor — Firebase Config
// IMPORTANT: Replace with YOUR Firebase config values

var firebaseConfig = {
  apiKey:            "AIzaSy...",        // your real key
  authDomain:        "proctor-ai-87d06.firebaseapp.com",
  projectId:         "proctor-ai-87d06", // from your Firebase URL
  storageBucket:     "proctor-ai-87d06.appspot.com",
  messagingSenderId: "...",
  appId:             "..."
};

if (!firebase.apps.length) {
  firebase.initializeApp(firebaseConfig);
}
var db = firebase.firestore();

async function hashPassword(p) {
  var buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(p));
  return Array.from(new Uint8Array(buf)).map(b=>b.toString(16).padStart(2,'0')).join('');
}

async function fb_facultyRegister(name, email, password) {
  var hash = await hashPassword(password);
  var ref  = db.collection('faculty').doc(email.toLowerCase());
  var snap = await ref.get();
  if (snap.exists) throw new Error('Account with this email already exists.');
  await ref.set({ name:name, email:email.toLowerCase(), password:hash, created:new Date().toISOString() });
}

async function fb_facultyLogin(email, password) {
  var hash = await hashPassword(password);
  var snap = await db.collection('faculty').doc(email.toLowerCase()).get();
  if (!snap.exists || snap.data().password !== hash) throw new Error('Email or password is incorrect.');
  return snap.data();
}

async function fb_createRoom(code, facultyEmail, examName) {
  await db.collection('rooms').doc(code.toUpperCase()).set({
    code: code.toUpperCase(), faculty_email: facultyEmail.toLowerCase(),
    exam_name: examName, created: new Date().toISOString(), active: true
  });
}

async function fb_validateRoom(code) {
  var snap = await db.collection('rooms').doc(code.toUpperCase()).get();
  if (!snap.exists || !snap.data().active) throw new Error('Invalid room code. Ask your faculty.');
  return snap.data();
}

async function fb_studentLogin(name, id, subject, code, email, password) {
  await fb_validateRoom(code);
  var hash = await hashPassword(password);
  var studRef  = db.collection('students').doc(email.toLowerCase());
  var studSnap = await studRef.get();
  if (studSnap.exists) {
    if (studSnap.data().password !== hash) throw new Error('Incorrect password for this email.');
  } else {
    await studRef.set({ email:email.toLowerCase(), password:hash, created:new Date().toISOString() });
  }
  var examId = 'EX-' + Math.floor(Math.random()*90000+10000);
  await db.collection('sessions').doc(examId).set({
    exam_id:examId, student_id:id, student_name:name,
    student_email:email.toLowerCase(), subject:subject,
    room_code:code.toUpperCase(), login_time:new Date().toISOString(),
    violations:0, integrity:100, status:'active'
  });
  return { role:'student', name:name, id:id, subject:subject, email:email, roomCode:code.toUpperCase(), examId:examId, loginTime:new Date().toISOString() };
}

async function fb_logViolation(examId, num, timeStr, msg, integrity) {
  await db.collection('sessions').doc(examId).collection('violations').add({ num:num, time:timeStr, msg:msg, integrity:integrity });
  await db.collection('sessions').doc(examId).update({ violations:num, integrity:integrity, status:num>=5?'critical':'warning', last_update:new Date().toISOString() });
}

function fb_listenToRoom(roomCode, callback) {
  return db.collection('sessions').where('room_code','==',roomCode.toUpperCase()).onSnapshot(function(snap){
    callback(snap.docs.map(function(d){ return d.data(); }));
  });
}

async function fb_endSession(examId) {
  await db.collection('sessions').doc(examId).update({ status:'ended', last_update:new Date().toISOString() });
}
