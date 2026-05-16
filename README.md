# 🧠 Life Coach Agent MVP

An AI-powered Life Coach built with **Google ADK (Agent Development Kit)** and **FastAPI**. Specializes in writing coaching, self-discovery, life guidance, and MCQ generation.

## Features

- 💬 **Multi-session chat** with persistent history (SQLite)
- ✍️ **Writing Coach** — develop your writing skills with expert feedback
- 🔍 **Self-Discovery** — guided questions to help you find yourself
- 🎯 **Life Guidance** — goal setting and life planning support
- 📝 **MCQ Generation** — auto-generate multiple choice questions
- 🎨 **Beautiful UI** — modern, responsive chat interface

## Tech Stack

- **Backend:** Python, FastAPI, Google ADK
- **Frontend:** Vanilla HTML/CSS/JS
- **Database:** SQLite
- **AI Model:** Gemini (via Google AI)

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/usechatgpto4-debug/life-coach-agent.git
cd life-coach-agent
```

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp life_coach_agent/.env.example life_coach_agent/.env
```

Edit `life_coach_agent/.env` and add your Google API key:
```
GOOGLE_API_KEY="your-actual-api-key"
```

Get your API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 5. Run the server

```bash
uvicorn server:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## License

MIT
