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


def _fallback_resume_analysis(resume_score):
    return {
        "matched_skills": [],
        "missing_skills": [],
        "reason": (
            f"The resume shows a {resume_score:.2f}% semantic similarity to the job description. "
            "Review the listed skills and project experience against the role requirements."
        ),
        "recommendation": (
            "Align listed skills and project outcomes with the job description "
            "to improve screening results."
        ),
    }


def _normalize_resume_analysis(parsed, resume_score):
    fallback = _fallback_resume_analysis(resume_score)
    if not isinstance(parsed, dict):
        return fallback

    matched = parsed.get("matched_skills", [])
    missing = parsed.get("missing_skills", [])
    improvement = parsed.get("improvement_skills", [])

    if not isinstance(improvement, list):
        improvement = []
    if not isinstance(matched, list):
        matched = []
    if not isinstance(missing, list):
        missing = []

    return {
        "matched_skills": [str(skill).strip() for skill in matched if str(skill).strip()],
        "missing_skills": [str(skill).strip() for skill in missing if str(skill).strip()],
        "improvement_skills": [str(skill).strip() for skill in improvement if str(skill).strip()],
        "reason": str(parsed.get("reason", fallback["reason"])).strip() or fallback["reason"],
        "recommendation": (
            str(parsed.get("recommendation", fallback["recommendation"])).strip()
            or fallback["recommendation"]
        ),
    }


def generate_resume_feedback(resume_text, job_description, resume_score):
    system_prompt = (
        "You are an experienced HR Recruiter and Technical Hiring Manager. "
        "Return only valid JSON."
    )
    user_prompt = f"""
You are an experienced HR Recruiter and Technical Hiring Manager.

Analyze the uploaded resume against the given job description.

Job Description:
{job_description}

Resume:
{(resume_text or '')[:6000]}

Resume Similarity Score:
{resume_score:.2f}%

Instructions:

Instructions:

1. Extract the important technical skills present in the resume.

2. Compare them with the required skills in the job description.

3. If the Resume Similarity Score is 50% or above:

   - Return the important Matched Skills.
   - Instead of "Missing Skills", return only Areas to Strengthen.
   - Areas to Strengthen should include advanced skills that would improve the candidate's profile, not mandatory missing skills.
   - Explain why the resume satisfies the minimum screening criteria.
   - Give professional recommendations for future improvement.

4. If the Resume Similarity Score is below 50%:

   - Return important Matched Skills.
   - Return Missing Skills that prevented selection.
   - Explain why the resume does not satisfy the job requirements.
   - Recommend skills that should be learned.

5. Never invent skills.

6. Do not decide Selected or Rejected.

7. Do not decide interview eligibility.

8. Return ONLY valid JSON.

Return JSON in this exact format:

{{
    
    "matched_skills": [],
    "improvement_skills": [],
    "missing_skills": [],
    "reason": "",
    "recommendation": ""

}}
"""
    raw = _openai_generate(system_prompt, user_prompt, temperature=0.2)
    if not raw:
        return _fallback_resume_analysis(resume_score)
    return _normalize_resume_analysis(_safe_json_loads(raw), resume_score)


def _fallback_candidate_assessment():
    return {
        "strengths": [
            "Strong foundational technical ability",
            "Project-driven problem solving",
            "Clear communication during interviews",
            "Relevant experience for Python and AI-focused roles",
        ],
        "areas_for_improvement": [
            "Cloud deployment experience",
            "Testing and debugging discipline",
            "System design depth",
            "Broader industry exposure",
        ],
        "recommended_role": "Python Developer",
        "other_suitable_roles": [
            "Machine Learning Engineer",
            "AI Engineer",
            "Data Analyst",
        ],
        "ai_feedback": (
            "The candidate shows a solid foundation in technical work and practical project experience that supports entry-level to junior roles in Python and AI-focused development. "
            "Their interview responses suggest good problem-solving ability and a willingness to learn. Strengthening cloud deployment, testing, and system design skills would make them more competitive for higher-impact responsibilities. "
            "The recommended role aligns well with their present profile and long-term growth trajectory."
        ),
    }


def _normalize_candidate_assessment(parsed):
    fallback = _fallback_candidate_assessment()
    if not isinstance(parsed, dict):
        return fallback

    strengths = parsed.get("strengths", [])
    improvements = parsed.get("areas_for_improvement", [])
    other_roles = parsed.get("other_suitable_roles", [])

    if not isinstance(strengths, list):
        strengths = []
    if not isinstance(improvements, list):
        improvements = []
    if not isinstance(other_roles, list):
        other_roles = []

    return {
        "strengths": [str(item).strip() for item in strengths if str(item).strip()],
        "areas_for_improvement": [str(item).strip() for item in improvements if str(item).strip()],
        "recommended_role": str(parsed.get("recommended_role", "")).strip() or fallback["recommended_role"],
        "other_suitable_roles": [str(item).strip() for item in other_roles if str(item).strip()],
        "ai_feedback": str(parsed.get("ai_feedback", "")).strip() or fallback["ai_feedback"],
    }


def generate_candidate_assessment(
    resume_text,
    job_description,
    resume_score,
    interview_questions,
    candidate_answers,
    interview_score,
    final_score,
    final_decision,
):
    system_prompt = (
        "You are an experienced HR Recruitment Assistant specializing in technical hiring. "
        "Analyze the candidate profile for hiring insights only."
    )
    user_prompt = f"""
You are an experienced HR Recruitment Assistant specializing in technical hiring.

Analyze the candidate profile and return ONLY valid JSON.

Important rules:
- Do not decide whether the candidate is Selected or Rejected.
- Do not modify or reinterpret the resume score, interview score, or final score.
- Focus only on hiring insights, role fit, strengths, improvement areas, and growth guidance.
- Use the provided resume, project experience, interview responses, and job description.

Resume Text:
{(resume_text or '')[:8000]}

Job Description:
{job_description}

Resume Score:
{resume_score:.2f}

Interview Questions:
{json.dumps(interview_questions or [], ensure_ascii=True)}

Candidate Answers:
{json.dumps(candidate_answers or [], ensure_ascii=True)}

Interview Score:
{interview_score:.2f}

Final Score:
{final_score:.2f}

Final Decision:
{final_decision}

Return ONLY valid JSON.

Rules:

1. strengths
- Return ONLY short skill names.
- Do NOT write complete sentences.
- Maximum 5 items.

Good Examples:

"Python Programming"

"Machine Learning"

"NLP"

"Problem Solving"

"Flask Development"

"Project Implementation"

2. areas_for_improvement

Return ONLY short skill names.

Do NOT write complete sentences.

Examples:

"Docker"

"AWS"

"Cloud Deployment"

"SQL"

"Communication"

Maximum 4 items.

3. recommended_role

Return only ONE role.

Examples:

"Machine Learning Engineer"

"Python Developer"

"AI Engineer"

"NLP Engineer"

"Data Analyst"

4. other_suitable_roles

Return 2 to 4 role names only.

Example:

[
"Python Developer",
"AI Engineer",
"Data Analyst"
]

5. ai_feedback

Write one professional paragraph of around 80-100 words.

Do NOT repeat Resume Score.

Do NOT repeat Interview Score.

Do NOT repeat Final Score.

Explain:

• Technical strengths

• Interview performance

• Why the recommended role is suitable

• Future learning suggestions

Return JSON exactly like this:

{{
    "strengths":[
        "Python Programming",
        "Machine Learning",
        "NLP",
        "Problem Solving"
    ],

    "areas_for_improvement":[
        "Docker",
        "AWS",
        "Cloud Deployment"
    ],

    "recommended_role":"Machine Learning Engineer",

    "other_suitable_roles":[
        "Python Developer",
        "AI Engineer",
        "Data Analyst"
    ],

    "ai_feedback":"Professional paragraph here."
}}
"""
    raw = _openai_generate(system_prompt, user_prompt, temperature=0.3)
    if not raw:
        return _fallback_candidate_assessment()
    return _normalize_candidate_assessment(_safe_json_loads(raw))


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
        session.pop("resume_text", None)
        session.pop("resume_score", None)
        session.pop("resume_feedback", None)
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

        resume_feedback = generate_resume_feedback(
            resume_text=resume_text,
            job_description=JOB_DESCRIPTION,
            resume_score=resume_score,
        )

        if resume_score >= 50:
            resume_status = "Selected"
        else:
            resume_status = "Rejected"

        resume_feedback["status"] = resume_status
        session["resume_feedback"] = resume_feedback
        session.pop("interview_questions", None)
        session.pop("interview_started", None)
        return redirect("/screening")

    return render_template("upload.html", error=error)


@app.route("/screening")
def screening():
    if not _is_authenticated():
        return redirect("/login")
    if session.get("resume_score") is None or not session.get("resume_feedback"):
        return redirect("/upload")

    resume_score = float(session.get("resume_score", 0))
    resume_feedback = session.get("resume_feedback", {})
    shortlisted = resume_feedback["status"] == "Selected"

    return render_template(
        "screening.html",
        resume_score=resume_score,
        resume_feedback=resume_feedback,
        shortlisted=shortlisted,
    )


@app.route("/interview_rules")
def interview_rules():
    if not _is_authenticated():
        return redirect("/login")
    if session.get("resume_score") is None or not session.get("resume_feedback"):
        return redirect("/upload")
    if session.get("resume_feedback", {}).get("status") != "Selected":
        return redirect("/screening")
    if session.get("interview_completed"):
        return redirect("/completed")
    return render_template("rules.html")


@app.route("/interview", methods=["GET"])
def interview():
    if not _is_authenticated():
        return redirect("/login")
    if session.get("interview_completed"):
        return redirect("/completed")
    if session.get("resume_feedback", {}).get("status") != "Selected":
        return redirect("/screening")

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
    if session.get("resume_feedback", {}).get("status") != "Selected":
        return redirect("/screening")
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
    if session.get("resume_feedback", {}).get("status") != "Selected":
        return redirect("/screening")

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
    candidate_answers = [
        {
            "question": questions[idx],
            "answer": answer_map.get(f"answer_{idx}", "").strip(),
        }
        for idx in range(len(questions))
    ]
    candidate_assessment = generate_candidate_assessment(
        resume_text=resume_text,
        job_description=JOB_DESCRIPTION,
        resume_score=resume_score,
        interview_questions=questions,
        candidate_answers=candidate_answers,
        interview_score=interview_score,
        final_score=final_score,
        final_decision=decision,
    )
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
            resume_feedback=session.get("resume_feedback"),
            candidate_assessment=candidate_assessment,
        )
    )
    return response


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)