# AI Exam Proctor — Setup Instructions

## Project Structure

```
your-project/
├── app.py                  ← Python Flask backend (RUN THIS)
├── requirements.txt        ← Python libraries
├── proctor.db              ← SQLite database (auto-created)
└── static/                 ← ALL your HTML/JS/CSS files go here
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

## Step 2 — Put Files in /static Folder

Copy these files into the `static/` folder:
- login.html
- index.html
- faculty.html
- phone-cam.html
- freesound_community-siren-alert-96052.mp3
- model/ folder (with model.json, weights.bin, metadata.json)

## Step 3 — Run the Server

```bash
python app.py
```

You will see:
```
✅ Database ready: proctor.db
🚀 AI Exam Proctor Backend
   Open: http://localhost:5000
```

## Step 4 — Open in Browser

Go to: http://localhost:5000

## Python Backend API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/faculty/register | Faculty signup |
| POST | /api/faculty/login | Faculty login |
| POST | /api/rooms/create | Create exam room |
| GET  | /api/rooms/validate/:code | Validate room code |
| POST | /api/student/login | Student login |
| POST | /api/violations/log | Log a violation |
| GET  | /api/dashboard/:room_code | Faculty dashboard data |
| POST | /api/session/end | End student session |
| GET  | /api/health | Check server is running |

## What Changed from Pure HTML Version

| Before (localStorage) | After (Python Backend) |
|----------------------|----------------------|
| Data stored in browser only | Data stored in SQLite database |
| Data lost on browser clear | Data persists permanently |
| Faculty can only see own tab | Faculty sees all students in real-time |
| Passwords stored as plain text | Passwords hashed with SHA-256 |
| No real backend | Flask REST API backend |
