import os
import gradio as gr
from pypdf import PdfReader
import requests


# ==========================================
# AI TEXT GENERATION (via OpenRouter free API)
# ==========================================
# No local model download needed, so the app runs fine on
# lightweight free hosting (Render, etc.) with no GPU and low RAM.

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")


def qwen_generate(instruction, max_new_tokens=200):
    """Calls OpenRouter's free-tier chat completion API."""
    if not OPENROUTER_API_KEY:
        return "AI generation is not configured: missing OPENROUTER_API_KEY."

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional AI resume analyzer. Follow the user's instructions exactly.",
                    },
                    {"role": "user", "content": instruction},
                ],
                "max_tokens": max_new_tokens,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"AI generation failed: {str(e)}"


def generate_feedback(resume_text, job_description):
    prompt = f"""
Compare this resume with the job description.

RESUME:
{resume_text[:3000]}

JOB DESCRIPTION:
{job_description[:2500]}

Write exactly 4 short sentences:
1. Mention the strongest skills that match the job.
2. Mention the most important missing skill.
3. Mention one relevant project or experience.
4. Give one specific improvement recommendation.

Do not copy the resume word-for-word.
"""
    return qwen_generate(prompt, max_new_tokens=150)


def generate_interview_questions(resume_text, job_description):
    prompt = f"""
Generate exactly 5 technical interview questions using ONLY facts explicitly
contained in the resume and job description.

RESUME:
{resume_text[:3000]}

JOB DESCRIPTION:
{job_description[:2500]}

STRICT RULES:
- Exactly 5 questions.
- Number them 1 to 5.
- Every question must be different.
- Do not invent experience, technologies, responsibilities, or achievements.
- Do not assume the candidate did something merely because they list a skill.
- Ask about what the candidate actually built, used, or learned.
- At least 3 questions must refer directly to actual projects.
- Questions should be appropriate for a Junior Software Engineer.
- Keep each question concise, preferably under 25 words.
- Do not add explanations or answers.
- Output ONLY the 5 numbered questions.
"""
    return qwen_generate(prompt, max_new_tokens=250)


# ==========================================
# SKILL MATCHING
# ==========================================

COMMON_SKILLS = [
    "Python", "Java", "C++", "C#", "JavaScript", "TypeScript", "React",
    "Node.js", "HTML", "CSS", "SQL", "MySQL", "MongoDB", "FastAPI",
    "Django", "Flask", "Flutter", "Machine Learning", "Deep Learning",
    "Artificial Intelligence", "TensorFlow", "PyTorch", "Keras",
    "Scikit-learn", "NLP", "Git", "GitHub", "Docker", "AWS", "Azure",
    "Linux", "Fuzzy Logic", "ANN", "LSTM", "CNN", "BiLSTM",
]


def find_skill_matches(resume_text, job_description):
    resume_lower = resume_text.lower()
    job_lower = job_description.lower()

    resume_skills, job_skills, matched_skills = [], [], []

    for skill in COMMON_SKILLS:
        skill_lower = skill.lower()
        if skill_lower in resume_lower:
            resume_skills.append(skill)
        if skill_lower in job_lower:
            job_skills.append(skill)
        if skill_lower in resume_lower and skill_lower in job_lower:
            matched_skills.append(skill)

    return {
        "resume_skills": resume_skills,
        "job_skills": job_skills,
        "matched_skills": matched_skills,
    }


def calculate_match_score(skill_analysis):
    job_skills = skill_analysis["job_skills"]
    matched_skills = skill_analysis["matched_skills"]
    if len(job_skills) == 0:
        return 0
    return round((len(matched_skills) / len(job_skills)) * 100, 2)


def run_full_analysis(resume_text, job_description):
    skill_analysis = find_skill_matches(resume_text, job_description)
    match_score = calculate_match_score(skill_analysis)
    feedback = generate_feedback(resume_text, job_description)
    interview_questions = generate_interview_questions(resume_text, job_description)

    return {
        "match_score": match_score,
        "resume_skills": skill_analysis["resume_skills"],
        "job_skills": skill_analysis["job_skills"],
        "matched_skills": skill_analysis["matched_skills"],
        "ai_feedback": feedback,
        "interview_questions": interview_questions,
    }


# ==========================================
# PDF TEXT EXTRACTION
# ==========================================

def extract_resume_text(pdf_file):
    if pdf_file is None:
        return ""
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"


# ==========================================
# ANALYZE RESUME (Gradio callback)
# ==========================================

def analyze_uploaded_resume(pdf_file, job_description):
    if pdf_file is None:
        return """
        <div class="result-empty">
            <div class="empty-symbol">01</div>
            <h2>Upload your resume first</h2>
            <p>Select your PDF resume to begin.</p>
        </div>
        """

    if not job_description.strip():
        return """
        <div class="result-empty">
            <div class="empty-symbol">02</div>
            <h2>Add the job description</h2>
            <p>Paste the position you are applying for.</p>
        </div>
        """

    resume_text = extract_resume_text(pdf_file)

    if not resume_text:
        return """
        <div class="result-empty">
            <h2>Couldn't read this PDF</h2>
            <p>Please try another resume PDF.</p>
        </div>
        """

    if resume_text.startswith("ERROR:"):
        return f"""
        <div class="result-empty">
            <h2>Something went wrong</h2>
            <p>{resume_text}</p>
        </div>
        """

    result = run_full_analysis(resume_text, job_description)

    matched = result["matched_skills"]
    if matched:
        matched_html = "".join(f"<span class='skill-tag'>{skill}</span>" for skill in matched)
    else:
        matched_html = '<span class="no-match">No direct skill matches found.</span>'

    score = result["match_score"]
    if score >= 80:
        score_label = "Excellent match"
    elif score >= 60:
        score_label = "Good match"
    elif score >= 40:
        score_label = "Moderate match"
    else:
        score_label = "Needs improvement"

    output = f"""
    <div class="results-content">
        <div class="score-area">
            <div>
                <div class="result-eyebrow">RESUME COMPATIBILITY</div>
                <div class="big-score">{score}%</div>
                <div class="score-status">{score_label}</div>
            </div>
            <div class="score-explanation">
                <h3>How does your resume fit?</h3>
                <p>Your score is calculated from the skills and technologies found in the job description and your resume.</p>
            </div>
        </div>

        <div class="result-block">
            <div class="result-index">01</div>
            <div class="result-body">
                <h2>Matching skills</h2>
                <p class="result-description">Skills that appear in both your resume and the job description.</p>
                <div class="skills">{matched_html}</div>
            </div>
        </div>

        <div class="result-block">
            <div class="result-index">02</div>
            <div class="result-body">
                <h2>Resume feedback</h2>
                <p class="result-description">Practical feedback before you apply.</p>
                <div class="feedback-text">{result["ai_feedback"]}</div>
            </div>
        </div>

        <div class="result-block">
            <div class="result-index">03</div>
            <div class="result-body">
                <h2>Interview preparation</h2>
                <p class="result-description">Questions generated from your actual resume and this position.</p>
                <div class="questions-text">{result["interview_questions"]}</div>
            </div>
        </div>
    </div>
    """
    return output


# ==========================================
# CUSTOM CSS
# ==========================================

custom_css = """
body { background: #F5F2EC !important; }
.gradio-container {
    max-width: 1250px !important;
    width: 92% !important;
    margin: auto !important;
    background: #F5F2EC !important;
    color: #25272A !important;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}
.header { padding: 55px 5px 42px; border-bottom: 1px solid #DCD7CE; margin-bottom: 45px; }
.header h1 { font-family: Georgia, "Times New Roman", serif; font-size: 55px; font-weight: 500; letter-spacing: -2px; margin: 0; color: #24272A; }
.header h1 span { color: #A85D48; }
.header-subtitle { margin-top: 12px; font-size: 16px; color: #77736B; }
.creator { margin-top: 18px; font-size: 12px; color: #969087; letter-spacing: 0.5px; }
.creator strong { color: #45433F; }
.step { margin-bottom: 35px; }
.step-header { display: flex; align-items: baseline; gap: 16px; margin-bottom: 15px; }
.step-number { font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: #A85D48; }
.step-title { font-family: Georgia, "Times New Roman", serif; font-size: 27px; font-weight: 500; color: #25272A; }
.step-description { font-size: 13px; color: #88837B; margin-left: 37px; margin-bottom: 15px; }
.results-hint { display: flex; align-items: center; gap: 15px; margin: 35px 0; color: #9A958C; font-size: 12px; }
.hint-line { flex: 1; height: 1px; background: #DCD7CE; }
.results-heading h2 { font-family: Georgia, "Times New Roman", serif; font-weight: 500; }
.results-wrapper { background: #FFFFFF; border: 1px solid #E4E0D8; border-radius: 14px; padding: 35px; }
.score-area { display: flex; justify-content: space-between; align-items: center; gap: 30px; padding-bottom: 30px; border-bottom: 1px solid #EEEAE1; margin-bottom: 30px; }
.result-eyebrow { font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: #A85D48; }
.big-score { font-family: Georgia, serif; font-size: 60px; font-weight: 500; }
.score-status { font-size: 14px; color: #77736B; }
.score-explanation { max-width: 320px; }
.score-explanation h3 { font-family: Georgia, serif; font-weight: 500; margin: 0 0 6px; }
.score-explanation p { font-size: 12px; color: #89847C; margin: 0; }
.result-block { display: grid; grid-template-columns: 50px 1fr; gap: 15px; margin-bottom: 32px; }
.result-index { color: #A85D48; font-size: 11px; font-weight: 800; letter-spacing: 1px; }
.result-body h2 { font-family: Georgia, "Times New Roman", serif; font-size: 24px; font-weight: 500; margin: 0; color: #25272A; }
.result-description { color: #89847C; font-size: 12px; margin: 5px 0 18px; }
.skills { display: flex; flex-wrap: wrap; gap: 8px; }
.skill-tag { background: #F1E5DD; color: #744A3B; border: 1px solid #E1CFC3; border-radius: 20px; padding: 7px 13px; font-size: 12px; }
.no-match { color: #8C8880; font-size: 13px; }
.feedback-text { background: #F7F4EE; border-left: 3px solid #A85D48; padding: 18px 20px; border-radius: 0 9px 9px 0; color: #555650; font-size: 14px; line-height: 1.8; }
.questions-text { background: #F3F5F0; border: 1px solid #DEE3D9; border-radius: 10px; padding: 18px 20px; color: #50544F; font-size: 14px; line-height: 1.85; }
.result-empty { text-align: center; padding: 150px 20px; }
.result-empty h2 { font-family: Georgia, "Times New Roman", serif; font-weight: 500; color: #444641; }
.result-empty p { color: #8A857D; font-size: 13px; }
.empty-symbol { color: #A85D48; font-size: 13px; font-weight: 800; letter-spacing: 2px; margin-bottom: 12px; }
.footer { text-align: center; padding: 35px 0 25px; color: #9A958C; font-size: 11px; }
.analyze-btn { background: #A85D48 !important; color: white !important; border: none !important; }
@media (max-width: 800px) {
    .gradio-container { width: 94% !important; }
    .header h1 { font-size: 40px; }
    .score-area { flex-direction: column; align-items: flex-start; gap: 20px; }
    .result-block { grid-template-columns: 40px 1fr; }
    .results-wrapper { padding: 22px; }
}
"""


# ==========================================
# BUILD APP
# ==========================================

with gr.Blocks(
    title="Resume Analyzer",
    css=custom_css,
    theme=gr.themes.Base(primary_hue="stone", neutral_hue="stone"),
) as app:

    gr.HTML("""
    <div class="header">
        <h1>Resume <span>Analyzer</span></h1>
        <div class="header-subtitle">See how your resume fits the job before you apply.</div>
        <div class="creator">Created and developed by <strong>Eeman Tariq</strong></div>
    </div>
    """)

    with gr.Column(elem_classes="step"):
        gr.HTML("""
        <div class="step-header">
            <span class="step-number">STEP 01</span>
            <span class="step-title">Your resume</span>
        </div>
        <div class="step-description">Upload the PDF version of your resume.</div>
        """)
        resume_input = gr.File(label="Upload Resume PDF", file_types=[".pdf"], type="filepath")

    with gr.Column(elem_classes="step"):
        gr.HTML("""
        <div class="step-header">
            <span class="step-number">STEP 02</span>
            <span class="step-title">Job description</span>
        </div>
        <div class="step-description">Paste the job description you want to compare against.</div>
        """)
        job_input = gr.Textbox(placeholder="Paste the job description here...", lines=12, show_label=False)

    analyze_button = gr.Button("Analyze my resume  →", elem_classes="analyze-btn")

    gr.HTML("""
    <div class="results-hint">
        <span class="hint-line"></span>
        <span class="hint-text">Your results will appear below ↓</span>
        <span class="hint-line"></span>
    </div>
    <div class="results-heading"><h2>Your results</h2></div>
    """)

    with gr.Column(elem_classes="results-wrapper"):
        results = gr.HTML("""
        <div class="result-empty">
            <div class="empty-symbol">READY</div>
            <h2>Your results will appear here</h2>
            <p>Upload your resume and add a job description to get started.</p>
        </div>
        """)

    gr.HTML("""
    <div class="footer">Resume Analyzer · Developed by Eeman Tariq · Python · Qwen · Gradio</div>
    """)

    analyze_button.click(
        fn=analyze_uploaded_resume,
        inputs=[resume_input, job_input],
        outputs=results,
    )


if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
    )
