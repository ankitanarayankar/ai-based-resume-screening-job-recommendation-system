from flask import Flask, render_template, request, redirect, session, make_response
import json
import os
import random
import re
import smtplib
import time

from resume_parser import extract_text_from_pdf
from similarity import calculate_similarity

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "ankita2narayankar")


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Surrogate-Control"] = "no-store"
    return response

# ------------------ PROJECT CONFIG ------------------
JOB_DESCRIPTION = """
Looking for a Python developer with Machine Learning skills and data analysis experience.
Candidate should be able to build end-to-end ML applications and explain implementation decisions clearly.
"""
RESUME_THRESHOLD = 0.5

# Set these in your environment for production use.
OTP_SENDER_EMAIL = os.getenv("OTP_SENDER_EMAIL", "ankitanarayankar148@gmail.com")
OTP_SENDER_APP_PASSWORD = os.getenv("OTP_SENDER_APP_PASSWORD", "pjwtqdclumbzrdzw")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _safe_json_loads(raw_text):
    try:
        return json.loads(raw_text)
    except Exception:
        pass
    match = re.search(r"(\{.*\}|\[.*\])", raw_text or "", flags=re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _get_openai_client():
    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        return None


def _openai_generate(system_prompt, user_prompt, temperature=0.8):
    client = _get_openai_client()
    if not client:
        return None
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content
    except Exception:
        return None


def _fallback_questions():
    pool = [
        "Explain one project in your resume and your exact role in it.",
        "How do you design scalable Flask APIs for production?",
        "How would you handle missing values in a real-world dataset?",
        "What is overfitting, and how do you reduce it?",
        "How do you evaluate a machine learning model before deployment?",
        "What are your steps to debug a failing ML pipeline?",
        "How do you optimize Python code performance for large data?",
        "How do you choose metrics for classification tasks?",
        "How do you ensure clean and maintainable code quality?",
        "How would you explain your model results to non-technical users?",
        "How do Pandas and NumPy help in data analysis tasks?",
        "How do you handle model drift after production deployment?",
        "What logging strategy would you use for AI applications?",
        "How do you structure testing for ML-enabled web apps?",
        "Describe a difficult technical issue and how you solved it.",
    ]
    return random.sample(pool, 10)


def generate_interview_questions(resume_text, job_description, total=10):
    nonce = f"{int(time.time())}-{random.randint(1000, 9999)}"
    system_prompt = "You are a senior technical interviewer."
    user_prompt = f"""
Generate EXACTLY {total} interview questions tailored to this resume.

Difficulty Distribution:
- Questions 1-3 : Easy (30%)
- Questions 4-8 : Moderate (50%)
- Questions 9-10 : Difficult (20%)

Rules:
- Base questions on skills, projects and technologies in the resume.
- Include project-based questions.
- Include Python, Machine Learning, SQL, Flask, NLP, Data Analysis topics if present.
- Make questions different every time.
- Suitable for final year engineering students.
- Return ONLY a JSON array of strings.

Request ID:
{nonce}

Job Description:
{job_description}

Resume:
{(resume_text or '')[:7000]}
"""
    raw = _openai_generate(system_prompt, user_prompt, temperature=1.0)
    if not raw:
        return _fallback_questions()

    parsed = _safe_json_loads(raw)
    if isinstance(parsed, list):
        questions = [str(item).strip() for item in parsed if str(item).strip()]
        if len(questions) >= total:
            return questions[:total]
    return _fallback_questions()


def evaluate_interview_answers(resume_text, questions, answers_map, job_description):

    answers_payload = [
        {
            "question": q,
            "answer": answers_map.get(f"answer_{idx}", "").strip(),
        }
        for idx, q in enumerate(questions)
    ]
    # Reject meaningless answers
    total_words = sum(
        len(item["answer"].split())
        for item in answers_payload
)

    if total_words < 30:
        return 5, "Most answers were too short to evaluate properly."

    system_prompt = "You are an unbiased hiring interview evaluator."

    user_prompt = f"""
Evaluate this candidate and return ONLY JSON:
{{
  "score": <0 to 100 number>,
  "feedback": "<one short paragraph>"
}}

Rubric:
- Technical correctness: 40
- Depth and clarity: 30
- Role relevance: 20
- Communication quality: 10
Important Rules:
- Single-letter answers like "A", "B", "C" must score extremely low.
- One-word answers should receive near zero marks.
- Incorrect technical answers should be heavily penalized.
- Empty answers should receive zero marks.
- If most answers are meaningless, final score should be below 20.
- Give high scores only for detailed, technically correct responses.

Job Description:
{job_description}

Resume:
{(resume_text or '')[:5000]}

Q&A:
{json.dumps(answers_payload, ensure_ascii=True)}
"""

    raw = _openai_generate(system_prompt, user_prompt, temperature=0.2)

    if not raw:

        word_count = sum(
            len(item["answer"].split())
            for item in answers_payload
        )

        if word_count < 20:
            return 5, "Very poor interview responses."

        elif word_count < 50:
            return 20, "Insufficient detail provided."

        elif word_count < 100:
            return 40, "Average interview responses."

        else:
            return 60, "Responses contain some detail but were not AI evaluated."

    parsed = _safe_json_loads(raw)

    if isinstance(parsed, dict) and isinstance(parsed.get("score"), (int, float)):
        score = max(0, min(100, float(parsed["score"])))
        feedback = str(
            parsed.get(
                "feedback",
                "Good effort shown in responses."
            )
        )
        return score, feedback

    return 60.0, "Could not parse model output. Baseline score applied."


def send_otp(email, otp):
    if (
        OTP_SENDER_EMAIL in {"", "your_sender_gmail@gmail.com"}
        or OTP_SENDER_APP_PASSWORD in {"", "your_gmail_app_password"}
    ):
        return False, "Please set OTP sender Gmail and app password in environment variables."

    message = f"Subject: OTP Verification\n\nYour OTP is {otp}"
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(OTP_SENDER_EMAIL, OTP_SENDER_APP_PASSWORD)
            server.sendmail(OTP_SENDER_EMAIL, email, message)
        return True, "OTP sent successfully."
    except Exception:
        return False, "Unable to send OTP. Check Gmail app password and network."


def _is_authenticated():
    return session.get("is_authenticated", False)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email.endswith("@gmail.com"):
            error = "Please enter a valid Gmail address."
            return render_template("login.html", error=error)

        otp = random.randint(100000, 999999)
        session["otp"] = str(otp)
        session["email"] = email
        session.pop("interview_completed", None)
        session.pop("interview_questions", None)
        session.pop("interview_started", None)
        session["is_authenticated"] = False

        sent, message = send_otp(email, otp)
        if not sent:
            error = message
            return render_template("login.html", error=error)

        return redirect("/verify_otp")

    return render_template("login.html", error=error)


@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    error = None
    if request.method == "POST":
        user_otp = request.form.get("otp", "").strip()
        if user_otp == session.get("otp"):
            session["is_authenticated"] = True
            return redirect("/upload")
        error = "Invalid OTP. Please enter the correct code."
    return render_template("otp.html", error=error)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not _is_authenticated():
        return redirect("/login")

    error = None
    if request.method == "POST":
        file = request.files.get("resume")
        if not file or not file.filename.lower().endswith(".pdf"):
            error = "Please upload a valid PDF resume."
            return render_template("upload.html", error=error)

        resume_text = extract_text_from_pdf(file)
        session["resume_text"] = resume_text

        score = calculate_similarity(resume_text, JOB_DESCRIPTION)
        resume_score = round(score * 100, 2)
        session["resume_score"] = resume_score

        if score < RESUME_THRESHOLD:
            return render_template(
                "result.html",
                resume_score=resume_score,
                interview_score=0,
                final_score=resume_score,
                decision="Rejected at Resume Stage",
                feedback="The resume did not meet the minimum job matching threshold.",
            )

        session["interview_questions"] = generate_interview_questions(
            resume_text=resume_text,
            job_description=JOB_DESCRIPTION,
            total=10,
        )
        return redirect("/interview")

    return render_template("upload.html", error=error)


@app.route("/interview", methods=["GET"])
def interview():
    if not _is_authenticated():
        return redirect("/login")
    if session.get("interview_completed"):
        return redirect("/completed")

    questions = session.get("interview_questions")
    if not questions:
        resume_text = session.get("resume_text", "")
        questions = generate_interview_questions(
            resume_text=resume_text,
            job_description=JOB_DESCRIPTION,
            total=10,
        )
        session["interview_questions"] = questions
    return render_template(
        "interview.html",
        questions=questions,
        interview_started=session.get("interview_started", False),
    )


@app.route("/start_interview", methods=["POST"])
def start_interview():
    if not _is_authenticated():
        return redirect("/login")
    if session.get("interview_completed"):
        return redirect("/completed")
    session["interview_started"] = True
    return {"status": "ok"}


@app.route("/completed")
def completed():
    if not _is_authenticated():
        return redirect("/login")
    if not session.get("interview_completed"):
        return redirect("/upload")
    return render_template("completed.html")


@app.route("/evaluate", methods=["POST"])
def evaluate():
    if not _is_authenticated():
        return redirect("/login")
    if session.get("interview_completed"):
        return redirect("/completed")

    questions = session.get("interview_questions", [])
    resume_text = session.get("resume_text", "")
    resume_score = float(session.get("resume_score", 0))

    answer_map = {key: value for key, value in request.form.items() if key.startswith("answer_")}
    interview_score, feedback = evaluate_interview_answers(
        resume_text=resume_text,
        questions=questions,
        answers_map=answer_map,
        job_description=JOB_DESCRIPTION,
    )

    final_score = (resume_score + interview_score) / 2
    decision = "Selected" if final_score >= 70 else "Rejected"
    session["interview_completed"] = True
    session["interview_started"] = False

    response = make_response(
        render_template(
            "result.html",
            resume_score=round(resume_score, 2),
            interview_score=round(interview_score, 2),
            final_score=round(final_score, 2),
            decision=decision,
            feedback=feedback,
        )
    )
    return response


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)