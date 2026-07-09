# 🤖 AI-Based Resume Screening and Job Recommendation System

An AI-powered recruitment platform that automates resume screening, candidate evaluation, and technical interviews using Natural Language Processing (NLP), Sentence Transformers, and OpenAI GPT.

The system securely authenticates users through Gmail OTP, analyzes uploaded resumes, generates personalized interview questions based on the candidate's resume, evaluates interview responses using AI, and provides a final hiring decision with detailed feedback.

---

## 📌 Features

- 🔐 Gmail OTP Authentication
- 📄 PDF Resume Upload
- 🧠 Resume Screening using NLP
- 📊 Semantic Similarity based Resume Scoring
- 🤖 Dynamic AI Interview Questions using OpenAI GPT
- 🎯 Difficulty Distribution
  - 30% Easy
  - 50% Moderate
  - 20% Difficult
- ⏳ 15-Minute Interview Timer
- 📝 AI Evaluation of Interview Answers
- 📈 Resume Score + Interview Score + Final Score
- 💬 AI Generated Feedback
- ✅ Automatic Candidate Selection / Rejection
- 🚫 One Interview Attempt Per Login Session
- 🌙 Professional Dark Theme UI

---

## 🛠 Tech Stack

### Frontend
- HTML5
- CSS3
- JavaScript
- Jinja2 Templates

### Backend
- Python
- Flask

### Artificial Intelligence
- OpenAI GPT API
- Sentence Transformers (all-MiniLM-L6-v2)
- Natural Language Processing (NLP)

### Authentication
- Gmail SMTP
- OTP Verification
- Flask Session

### Libraries
- OpenAI
- Sentence Transformers
- Scikit-learn
- PyMuPDF
- python-dotenv

---

## 🚀 Workflow

```
User Login
      │
      ▼
OTP Verification
      │
      ▼
Resume Upload
      │
      ▼
Resume Screening
      │
      ▼
Resume Score Generated
      │
      ▼
AI Interview
      │
      ▼
Dynamic OpenAI Questions
      │
      ▼
AI Evaluation
      │
      ▼
Final Score
      │
      ▼
Selected / Rejected
```

---

## 📂 Project Structure

```
AI-Based-Resume-Screening/
│
├── app.py
├── interview.py
├── similarity.py
├── resume_parser.py
├── requirements.txt
├── templates/
├── static/
├── README.md
└── .gitignore
```

---

## ⚙ Installation

Clone the repository

```bash
git clone https://github.com/your-username/ai-based-resume-screening-job-recommendation-system.git
```

Move into the project directory

```bash
cd ai-based-resume-screening-job-recommendation-system
```

Create a virtual environment

```bash
python -m venv venv
```

Activate the virtual environment

Windows

```bash
venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create a `.env` file

```env
OPENAI_API_KEY=your_openai_api_key
OTP_SENDER_EMAIL=your_email@gmail.com
OTP_SENDER_APP_PASSWORD=your_app_password
FLASK_SECRET_KEY=your_secret_key
```

Run the project

```bash
python app.py
```

---

## 📊 Evaluation Process

The system evaluates candidates based on:

- Resume Similarity Score
- Technical Knowledge
- Communication Quality
- Role Relevance
- Project Understanding

Final Score

```
Final Score = (Resume Score + Interview Score) / 2
```

Decision

- ✅ Selected
- ❌ Rejected

---

## 🔒 Security Features

- Gmail OTP Authentication
- Session Management
- One Interview Attempt per Login
- Resume Screening Threshold
- AI-Based Candidate Evaluation

---

## 🎯 Future Enhancements

- Candidate Dashboard
- Recruiter Dashboard
- PDF Report Generation
- Interview Analytics
- Email Notifications
- Tab Switching Detection
- Full Screen Interview Mode

---

## 👨‍💻 Developed By

**Ankita S Narayankar**

Final Year Computer Science Engineering Student

---

## 📜 License

This project is developed for educational and academic purposes as a Final Year Engineering Project.