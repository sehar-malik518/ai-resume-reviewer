import streamlit as st
import pdfplumber
import re
import os
import time
import io
import base64

# Optional: OpenAI for advanced feedback (set OPENAI_API_KEY in env if you want this)
try:
    import openai
    OPENAI_AVAILABLE = True
    openai.api_key = os.getenv("OPENAI_API_KEY")
except Exception:
    OPENAI_AVAILABLE = False

# ---------- Styles & Branding (startup look) ----------
PAGE_BG = "linear-gradient(135deg, #0f172a 0%, #1f2937 50%, #0ea5a4 100%);"
CARD_BG = "rgba(255,255,255,0.03)"
ACCENT = "#0ea5a4"

st.set_page_config(page_title="🚀 Sehar's AI Resume Reviewer", page_icon="📄", layout="wide")

# Custom CSS for nicer UI
st.markdown(f"""
<style>
    .report-header {{
        background: {PAGE_BG};
        color: white;
        padding: 30px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 8px 30px rgba(14,165,164,0.15);
    }}
    .small-note {{
        color: #cbd5e1;
        font-size: 0.9rem;
    }}
    .card {{
        background: {CARD_BG};
        padding: 18px;
        border-radius: 10px;
        color: #e6eef0;
    }}
    .metric {{
        font-size: 1.2rem;
        font-weight: 700;
        color: {ACCENT};
    }}
</style>
""", unsafe_allow_html=True)

# Header / Banner
st.markdown('<div class="report-header">'
            '<h1 style="margin:0; font-size:34px;">🚀 AI Resume Reviewer — Startup Edition</h1>'
            '<p style="margin:4px 0 0 0; color:#d1fae5;">Professional, beautiful, and actionable resume reviews — built by Sehar</p>'
            '</div>', unsafe_allow_html=True)
st.markdown("---")

# ---------- Helper functions ----------

def extract_text_from_pdf(uploaded_file):
    """Extract text from an uploaded file-like object using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        st.error("Could not read PDF. Make sure the file is a valid PDF.")
        return ""
    return text.strip()


def analyze_resume(text, job_title):
    sections = ["skills", "education", "experience", "projects", "certifications", "contact"]
    found_sections, missing_sections = [], []
    for section in sections:
        if re.search(r"\b" + re.escape(section) + r"\b", text, re.IGNORECASE):
            found_sections.append(section.capitalize())
        else:
            missing_sections.append(section.capitalize())

    # job-specific keywords (extendable)
    job_keywords = {
        "data scientist": ["Python", "Machine Learning", "Data Analysis", "Pandas", "SQL"],
        "ai engineer": ["Neural Networks", "Deep Learning", "TensorFlow", "PyTorch", "Computer Vision"],
        "web developer": ["HTML", "CSS", "JavaScript", "React", "Node.js"],
        "software engineer": ["Java", "OOP", "APIs", "Agile", "System Design"],
    }

    suggested_keywords = job_keywords.get(job_title.lower(), ["Teamwork", "Problem Solving", "Communication"])
    missing_keywords = [kw for kw in suggested_keywords if kw.lower() not in text.lower()]

    # Basic ATS-like scoring: section coverage + keyword presence influence
    section_score = (len(found_sections) / len(sections)) * 70  # sections weigh 70%
    if suggested_keywords:
        kw_covered = (len(suggested_keywords) - len(missing_keywords)) / len(suggested_keywords)
    else:
        kw_covered = 1
    keyword_score = kw_covered * 30  # keywords weigh 30%
    score = section_score + keyword_score

    # clamp
    score = max(0, min(100, score))
    return found_sections, missing_sections, score, missing_keywords


def generate_ai_feedback(resume_text, job_title, missing_sections, missing_keywords):
    """Use OpenAI to create professional feedback if available; otherwise fallback to a rule-based message."""
    if OPENAI_AVAILABLE and openai.api_key:
        prompt = f"""
You are a professional recruiter and career coach. Provide a concise, structured review of the following resume for the job title: {job_title}.

Resume text: {resume_text}

Missing sections: {missing_sections}
Missing keywords: {missing_keywords}

Respond with:
- Short encouraging opening (1-2 lines)
- 3 Strengths (bullet points)
- 3 Actionable improvements (bullet points, with sample wording or examples)
- One-sentence final verdict (ready / needs improvement / major overhaul)
"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are an expert recruiter."},
                          {"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            # If API fails, fallback to rule-based
            st.warning("AI feedback is temporarily unavailable — showing basic suggestions.")

    # Fallback rule-based feedback
    strengths = []
    if re.search(r"\bexperience\b", resume_text, re.IGNORECASE):
        strengths.append("Includes experience section — shows practical background.")
    if re.search(r"\bskills\b", resume_text, re.IGNORECASE):
        strengths.append("Has a skills section — good for quick scanning.")
    if len(resume_text.split()) > 200:
        strengths.append("Contains substantial content — likely detailed enough.")

    improvements = []
    for s in missing_sections:
        improvements.append(f"Add a {s} section with concise, bullet-pointed content.")
    for kw in missing_keywords[:3]:
        improvements.append(f"Include keyword '{kw}' in an achievements or skills bullet.")

    verdict = "Ready to apply." if (not missing_sections and not missing_keywords) else "Needs improvements before applying."

    msg = "**Opening:**\nYour resume has a solid foundation.\n\n**Strengths:**\n"
    for stg in strengths[:3]:
        msg += f"- {stg}\n"
    msg += "\n**Improvements:**\n"
    for imp in improvements[:5]:
        msg += f"- {imp}\n"
    msg += f"\n**Verdict:** {verdict}"
    return msg


# ---------- UI Layout (startup look) ----------

left_col, right_col = st.columns([1, 2])

with left_col:
    st.markdown("<div class='card'> <h3 style='color:#c8f7f1;'>Quick Tips</h3>", unsafe_allow_html=True)
    st.markdown("- Use action verbs\n- Add metrics to achievements\n- Keep to 1 page for juniors\n- Tailor to job title", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("\n")
    st.info("Made by Sehar — polished for LinkedIn demos")

with right_col:
    st.subheader("Start your review")
    job_title = st.text_input("🎯 Job Title you are applying for (e.g., AI Engineer)")
    uploaded_file = st.file_uploader("📂 Upload your resume (PDF)", type=["pdf"]) 

# Process upload
if uploaded_file is not None and job_title:
    with st.spinner("Reading your resume..."):
        resume_text = extract_text_from_pdf(uploaded_file)

    if not resume_text:
        st.error("Could not extract text from the PDF. Try a different file or a text-based PDF.")
    else:
        found, missing, score, missing_keywords = analyze_resume(resume_text, job_title)

        # Animated score meter
        st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
        st.subheader("📊 ATS Score")
        score_placeholder = st.empty()
        progress = st.progress(0)
        # animate progress up to score
        for i in range(0, int(score) + 1, 3):
            progress.progress(min(i, int(score)))
            score_placeholder.markdown(f"<p class='metric'>{i}%</p>", unsafe_allow_html=True)
            time.sleep(0.02)
        # finalize exact
        progress.progress(int(score))
        score_placeholder.markdown(f"<p class='metric'>{score:.1f}%</p>", unsafe_allow_html=True)

        # Results columns
        a, b = st.columns(2)
        with a:
            st.markdown("<div class='card'><h4 style='color:#9ef6e8;'>✅ Found Sections</h4>", unsafe_allow_html=True)
            if found:
                for s in found:
                    st.write(f"- {s}")
            else:
                st.write("None detected")
            st.markdown("</div>", unsafe_allow_html=True)
        with b:
            st.markdown("<div class='card'><h4 style='color:#ffd3b6;'>❌ Missing Sections</h4>", unsafe_allow_html=True)
            if missing:
                for s in missing:
                    st.write(f"- {s}")
            else:
                st.write("Great — no missing sections!")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        # Missing keywords
        if missing_keywords:
            st.warning(f"Missing keywords for {job_title.title()}: {', '.join(missing_keywords)}")
        else:
            st.success("No essential keywords missing for the selected role.")

        # Verdict card
        if score >= 85 and not missing_keywords:
            st.success("🎉 Verdict: Excellent — Ready to apply with confidence!")
        elif score >= 60:
            st.info("👍 Verdict: Good — Some improvements recommended before applying.")
        else:
            st.error("⚠️ Verdict: Not ready — Major improvements required.")

        # AI feedback
        st.subheader("🤖 AI Recruiter Feedback")
        with st.spinner("Generating personalized feedback..."):
            ai_text = generate_ai_feedback(resume_text, job_title, missing, missing_keywords)
        st.markdown(ai_text)

        # Action Plan (structured)
        st.subheader("🛠 Action Plan (Step-by-step)")
        if missing:
            st.markdown("**Add these sections:**")
            for s in missing:
                st.write(f"- **{s}:** Add 3 concise bullet points focusing on achievements (start with action verbs and include numbers where possible).")
        if missing_keywords:
            st.markdown("**Include these keywords:**")
            for kw in missing_keywords:
                st.write(f"- Place '{kw}' in Skills or under a related project with context (e.g., 'Used {kw} to ...').")
        st.markdown("**Formatting tips:**\n- Use 2–4 bullet points per role.\n- Use consistent date format.\n- Keep font readable (11–12pt).\n- Save as PDF (text-based) for ATS compatibility.")

        # Download report (text + simple PDF fallback using text file)
        report = io.StringIO()
        report.write(f"AI Resume Reviewer - Report by Sehar\n")
        report.write(f"Job Title: {job_title}\n")
        report.write(f"Score: {score:.1f}%\n\n")
        report.write("Found Sections:\n")
        for s in found:
            report.write(f"- {s}\n")
        report.write("\nMissing Sections:\n")
        for s in missing:
            report.write(f"- {s}\n")
        report.write("\nMissing Keywords:\n")
        for k in missing_keywords:
            report.write(f"- {k}\n")
        report.write("\nAI Feedback:\n")
        report.write(ai_text + "\n")

        report_bytes = report.getvalue().encode('utf-8')
        st.download_button("📥 Download Full Report (TXT)", report_bytes, file_name="resume_review_report.txt")

        # Optional: If user wants a PDF report and fpdf is installed, create a simple PDF
        try:
            from fpdf import FPDF
            pdf_buf = io.BytesIO()
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for line in report.getvalue().splitlines():
                pdf.multi_cell(0, 6, line)
            pdf.output(pdf_buf)
            pdf_bytes = pdf_buf.getvalue()
            st.download_button("📥 Download Full Report (PDF)", pdf_bytes, file_name="resume_review_report.pdf")
        except Exception:
            # fpdf not installed — silently skip PDF creation
            pass

st.markdown("---")
st.caption("✨ Startup-style UI — polished for LinkedIn demos. Made with ❤️ by Sehar")
