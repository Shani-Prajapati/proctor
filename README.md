# AI Exam Proctor

Light-themed AI exam proctoring system with strict Quiz Mode tab enforcement and low-latency real-time alerts.

## What changed in this version

1. **Professional light theme** — every page (login, student, faculty, phone-cam) now uses the same clean cream/maroon palette previously only on the faculty dashboard.
2. **Strict Quiz Mode (2-tab rule)** — when the student presses *Enable Quiz Mode*, exactly **2 tabs** are allowed (proctor + quiz). The moment a 3rd tab from the same browser opens, an alert is fired to the faculty dashboard.
3. **Low-latency pipeline** — model prediction loop runs every ~250 ms, model is pre-warmed at load, violations push to Firebase as fire-and-forget parallel writes (no UI await), faculty dashboard uses pure real-time Firestore listeners (no polling timer).

## Quick start (Firebase mode — recommended)

The HTML pages use Firebase by default. Edit `static/firebase-config.js` and put in your Firebase project config, then just open `static/login.html` in a browser, or serve the `static/` folder with any static server.

## Quick start (local Python mode)

```

your-project/
├── app.py                  ← Python Flask backend (RUN THIS)
├── requirements.txt        ← Python libraries
├── proctor.db              ← SQLite database (auto-created)
├── login.html
├── index.html
├── faculty.html
├── phone-cam.html
├── freesound_community-siren-alert-96052.mp3
└── model/
        ├── model.json
        ├── weights.bin
        └── metadata.json
```

## Step 1 — Install Python Libraries

```bash
pip install -r requirements.txt
```

## Step 2 — Keep Files as it is

- login.html
- index.html
- faculty.html
- phone-cam.html
- freesound_community-siren-alert-96052.mp3
- model/ folder (with model.json, weights.bin, metadata.json)

## Step 3 — Run the Server

```bash

pip install -r requirements.txt
(Changhes completed)
python app.py
# open http://localhost:5000
```

Flask serves everything in `static/` and adds API endpoints for an SQLite-backed alternative if you don't want Firebase.

## Files

- `app.py` — optional Flask backend (SQLite)
- `requirements.txt` — Python deps
- `static/login.html` — sign in (student / faculty)
- `static/index.html` — student exam page (camera + AI detection + Quiz Mode)
- `static/faculty.html` — faculty live dashboard
- `static/phone-cam.html` — phone-as-camera companion page (PeerJS)
- `static/firebase-config.js` — Firebase init + helpers
- `static/freesound_community-siren-alert-96052.mp3` — alert siren
- `static/model/` — Teachable Machine model (`model.json`, `weights.bin`, `metadata.json`)

## How Quiz Mode works (the 2-tab rule)

Each open tab on the student's browser registers itself on a `BroadcastChannel` named after the exam ID and sends a heartbeat every 800 ms with its tab ID. The proctor tab counts how many distinct tabs have heartbeated within the last 2 seconds.

- Quiz Mode OFF → tab switches are detected via `visibilitychange` (original behaviour).
- Quiz Mode ON → tab switches are allowed (student is taking their quiz in another tab), BUT if more than 2 tabs are alive at once, a violation is logged to Firebase, faculty dashboard is notified instantly, and the student sees a red banner.
