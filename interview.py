import os
from openai import OpenAI

client = OpenAI(api_key="")

def generate_questions(skills):
    prompt = f"""
Generate exactly 10 technical interview questions for a candidate skilled in {skills}.
Number them from 1 to 10.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400
    )

    return response.choices[0].message.content


def evaluate_answers(questions, answers):
    prompt = f"""
You are an interview evaluator.

Evaluate the candidate's answers strictly.

For each answer:
- Give score out of 10
- Give short feedback

At the end:
Write total score clearly in this format:
TOTAL_SCORE: XX

Questions:
{questions}

Answers:
{answers}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600
    )

    return response.choices[0].message.content