"""In-memory resume upload and local job matching page."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.data.cache import clear_job_cache, load_jobs_cached
from src.data.database import database_summary
from src.ml.matcher import EmbeddingModelError, rank_jobs, recommended_skills
from src.ml.resume_parser import ResumeReadError, extract_resume_text
from src.ml.skills import extract_skills, group_skills
from src.ui.theme import empty_state, kpi_card, page_header, score_ring, section_card, tag


def run_analysis(uploaded_file: Any) -> None:
    """Analyse an upload without persisting its contents or writing it to disk."""
    jobs = load_jobs_cached()
    try:
        with st.spinner("Reading your resume and comparing it with local job postings..."):
            resume_text = extract_resume_text(uploaded_file, uploaded_file.name)
            skills = extract_skills(resume_text)
            matches = rank_jobs(resume_text, skills, jobs)
    except (ResumeReadError, EmbeddingModelError) as error:
        st.error(str(error))
        return
    except Exception as error:
        st.error(f"Resume analysis could not complete: {error}")
        return

    # Do not retain resume_text: the session only needs derived skills and results.
    st.session_state.resume_analysis = {
        "skills": skills,
        "groups": group_skills(skills),
        "matches": [match.to_dict() for match in matches],
    }


def render_match(match: dict[str, Any], index: int) -> None:
    """Render one ranked, explainable job-match card."""
    card = section_card(f"{index}. {match['title']}", f"{match['company']} · {match['city']}")
    with card:
        detail_column, score_column = st.columns([5, 1])
        with detail_column:
            st.markdown(tag(match["work_mode"], "work_mode"), unsafe_allow_html=True)
            st.caption(
                f"Semantic similarity: {match['semantic_similarity']:.0%} · "
                f"Skill coverage: {match['skill_coverage']:.0%}"
            )
        with score_column:
            score_ring(float(match["score"]))
        st.markdown("**Matched skills**")
        matched_tags = "".join(tag(skill, "matched") for skill in match["matched_skills"]) or "No direct curated-skill match"
        st.markdown(matched_tags, unsafe_allow_html=True)
        st.markdown("**Skills to develop for this role**")
        missing_tags = "".join(tag(skill, "missing") for skill in match["missing_skills"]) or "No missing curated skills identified"
        st.markdown(missing_tags, unsafe_allow_html=True)


page_header("Resume Matcher", "Compare an uploaded resume with job postings stored in your local SQLite database.")

summary = database_summary()
with st.spinner("Loading jobs for matching..."):
    jobs = load_jobs_cached()
status_column, refresh_column = st.columns([4, 1])
with status_column:
    if summary.get("sample", 0):
        st.markdown(tag("Sample data", "status"), unsafe_allow_html=True)
        st.caption("Match results are against the demo CSV until you import a legal data source.")
    elif not jobs.empty:
        st.markdown(tag("Database loaded", "status"), unsafe_allow_html=True)
with refresh_column:
    if st.button("Refresh data", use_container_width=True):
        clear_job_cache()
        st.rerun()

if jobs.empty:
    empty_state(
        "No jobs are available for matching",
        "Run python scripts/import_jobs.py --source csv in PowerShell, then choose Refresh data.",
    )
    st.stop()

upload_card = section_card("Upload your resume", "PDF and DOCX files are read in memory for this session and are not saved by the app.")
with upload_card:
    uploaded_file = st.file_uploader("Choose a PDF or DOCX resume", type=["pdf", "docx"])
    analyze_clicked = st.button("Analyze resume", type="primary", disabled=uploaded_file is None)
    st.caption("A first analysis may download the `all-MiniLM-L6-v2` matching model to your computer.")

if analyze_clicked and uploaded_file is not None:
    run_analysis(uploaded_file)

analysis = st.session_state.get("resume_analysis")
if not analysis:
    empty_state("Ready when you are", "Upload a text-based PDF or DOCX and choose Analyze resume to see matching jobs.")
    st.stop()

matches: list[dict[str, Any]] = analysis["matches"]
skills: list[str] = analysis["skills"]
groups: dict[str, list[str]] = analysis["groups"]
top_score = matches[0]["score"] if matches else None
target_roles = list(dict.fromkeys(match["title"] for match in matches))

kpi_columns = st.columns(3)
with kpi_columns[0]:
    kpi_card("Match index", f"{top_score}%" if top_score is not None else "—", "Highest score among displayed jobs")
with kpi_columns[1]:
    kpi_card("Extracted skills", str(len(skills)), "Curated skills found in the uploaded text")
with kpi_columns[2]:
    kpi_card("Target roles", str(len(target_roles)), ", ".join(target_roles[:3]) or "No matching job roles")

skills_card = section_card("Extracted resume skills", "Grouped using the project’s curated skills catalogue.")
with skills_card:
    if not groups:
        st.warning("No curated skills were found. Add specific tools or technologies to the resume text, then analyse again.")
    for category, category_skills in groups.items():
        st.markdown(f"**{category}**")
        st.markdown("".join(tag(skill, "skill") for skill in category_skills), unsafe_allow_html=True)

matches_column, learn_column = st.columns([3, 1])
with matches_column:
    st.subheader("Top job matches")
    if not matches:
        st.info("The database did not return any jobs to compare.")
    for index, match in enumerate(matches, start=1):
        render_match(match, index)
with learn_column:
    learning_card = section_card("Skills to learn next", "Ranked by the number of displayed jobs that list each missing skill.")
    with learning_card:
        recommendations = recommended_skills(matches)
        if not recommendations:
            st.info("No missing curated skills were identified in the displayed matches.")
        for skill, jobs_unlocked in recommendations:
            st.markdown(
                f"{tag(skill, 'missing')} **{jobs_unlocked}** of {len(matches)} displayed matches",
                unsafe_allow_html=True,
            )
