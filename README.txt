Python Pro - Tugas Praktis untuk Tutor (Flask)
=============================================

Instruksi singkat:
1. Install dependencies:
   pip install -r requirements.txt

2. (Optional) set environment variables:
   export FLASK_SECRET_KEY="your_secret_here"
   export OPENWEATHER_API_KEY="your_openweather_key"   # optional but recommended to show real weather

3. Run:
   export FLASK_APP=app.py
   flask run

Fitur:
- Halaman beranda dengan widget cuaca (3 hari)
- Register (cek username dan display_name unik)
- Login / Logout
- Halaman kuis (pertanyaan acak satu-per-satu; jawaban disimpan sebagai skor kumulatif)
- Papan peringkat (leaderboard)
- Footer dengan nama pengembang

Database: SQLite (data.db) - sudah diinisialisasi dengan pertanyaan topic AI