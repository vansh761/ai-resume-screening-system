"""
LLM-powered resume insights: summarization, interview question
generation, and improvement suggestions.

Every prompt explicitly asks for a fixed JSON shape and gives the
model tight constraints (sentence counts, question counts) --
unconstrained prompts to a small/fast model like Flash tend to
ramble or under-deliver; being specific in the prompt is doing real
work here, not just formatting.
"""

from app.ai.llm_client import LLMGenerationError, generate_json


def summarize_resume(resume_text: str) -> str:
    """Produces a 2-3 sentence recruiter-facing summary of a candidate."""
    prompt = f"""You are helping a recruiter quickly understand a candidate.
Summarize the following resume in exactly 2-3 sentences, focused on the
candidate's core expertise and experience level. Be specific and factual --
do not invent skills or experience not present in the text.

Respond with JSON in exactly this shape: {{"summary": "..."}}

Resume text:
{resume_text[:4000]}
"""
    try:
        result = generate_json(prompt, max_output_tokens=200)
        return result["summary"]
    except (LLMGenerationError, KeyError) as exc:
        raise LLMGenerationError(f"Failed to generate summary: {exc}") from exc


def generate_interview_questions(resume_text: str, job_description: str) -> list[str]:
    """
    Generates interview questions tailored to this specific candidate
    against this specific job -- not generic questions, but ones that
    probe the actual gap or overlap between what the resume shows and
    what the job asks for.
    """
    prompt = f"""You are helping a recruiter prepare for a candidate interview.
Given the candidate's resume and the job description below, generate exactly
5 interview questions. Focus on: (1) verifying claimed skills relevant to the
job, (2) probing any gaps between the resume and job requirements, and
(3) understanding depth of experience in the candidate's strongest areas.
Make the questions specific to this candidate and this job, not generic.

Respond with JSON in exactly this shape: {{"questions": ["...", "...", "...", "...", "..."]}}

Resume text:
{resume_text[:3000]}

Job description:
{job_description[:1500]}
"""
    try:
        result = generate_json(prompt, max_output_tokens=600)
        return result["questions"]
    except (LLMGenerationError, KeyError) as exc:
        raise LLMGenerationError(f"Failed to generate interview questions: {exc}") from exc


def suggest_resume_improvements(resume_text: str) -> list[str]:
    """
    Candidate-facing feedback: concrete, actionable suggestions for
    improving their own resume -- not generic "add more keywords"
    advice, but specific to what's actually present or missing in
    this resume's text.
    """
    prompt = f"""You are a career coach reviewing a resume. Give exactly 4
concrete, actionable suggestions for improving this resume. Focus on
clarity, quantifiable impact (e.g. "add measurable outcomes to your bullet
points"), structure, and any obviously missing sections. Be specific to
this resume's actual content, not generic advice that could apply to any
resume.

Respond with JSON in exactly this shape: {{"suggestions": ["...", "...", "...", "..."]}}

Resume text:
{resume_text[:4000]}
"""
    try:
        result = generate_json(prompt, max_output_tokens=500)
        return result["suggestions"]
    except (LLMGenerationError, KeyError) as exc:
        raise LLMGenerationError(f"Failed to generate improvement suggestions: {exc}") from exc
