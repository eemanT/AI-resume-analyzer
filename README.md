# AI Resume Analyzer

An AI-powered web app that compares a resume (PDF) against a job description and gives you:

- ✅ A compatibility match score
- ✅ Matched skills between your resume and the job
- ✅ AI-generated feedback on your resume
- ✅ AI-generated, resume-specific interview questions

**Live demo:** [Add your Hugging Face Space link here after deploying]

## Tech Stack

- **Python**
- **Gradio** – web UI
- **pypdf** – PDF text extraction
- **OpenRouter free API** – feedback & interview question generation (no local model needed)

## Run it locally

```bash
git clone https://github.com/YOUR-USERNAME/resume-analyzer.git
cd resume-analyzer
pip install -r requirements.txt
export OPENROUTER_API_KEY=your-key-here
python app.py
```

Then open the local URL shown in your terminal.

## Deploying for free

This app is designed to run on Render's free tier (or any similar free Python host) since it calls OpenRouter's API instead of loading a large model locally. See the deployment guide for step-by-step instructions.

## How it works

1. Upload your resume as a PDF.
2. Paste in the job description you're targeting.
3. The app extracts your resume text, detects overlapping skills between the resume and job description, and calculates a match score.
4. A local open-source LLM (Qwen2.5-1.5B-Instruct) generates written feedback and interview questions based only on what's actually in your resume and the job post.

## Author

Developed by **Eeman Tariq**
