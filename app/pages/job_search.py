"""Resume-guided, outbound job-search assistant."""

from __future__ import annotations

import streamlit as st

from src.ml.job_search import build_search_query, improvement_plan, platform_search_urls
from src.ml.matcher import recommended_skills
from src.ui.theme import empty_state, page_header, section_card, tag


page_header("Job Search Assistant", "Turn your resume analysis into targeted, legal outbound job searches and a focused improvement plan.")

analysis = st.session_state.get("resume_analysis")
if not analysis:
    empty_state(
        "Analyse your resume first",
        "Open Resume Matcher, upload a text-based PDF or DOCX, and choose Analyze resume. Your derived results will appear here for this session.",
    )
    st.stop()

matches = analysis["matches"]
resume_skills = analysis["skills"]
roles = list(dict.fromkeys(match["title"] for match in matches)) or ["Data Analyst"]
cities = ["All India", *sorted({match["city"] for match in matches if match["city"] != "Location not listed"})]

search_card = section_card("Search job platforms", "These buttons open platform searches in a new tab. JobIntel does not scrape LinkedIn, Indeed, or Naukri.")
with search_card:
    role_column, city_column = st.columns(2)
    role = role_column.selectbox("Target role", roles)
    city = city_column.selectbox("Preferred location", cities)
    query = build_search_query(role, resume_skills)
    st.caption(f"Search query: {query}")

    platform_columns = st.columns(3)
    for column, (platform, url) in zip(platform_columns, platform_search_urls(query, city).items()):
        column.link_button(f"Search {platform}", url, use_container_width=True)

matches_card = section_card("Recommended local matches", "These are the strongest matches from the job postings currently stored in your local database.")
with matches_card:
    if not matches:
        st.info("No local matches are available yet.")
    for match in matches[:5]:
        score_tag = tag(f"{match['score']}% match", "status")
        st.markdown(
            f"**{match['title']}** · {match['company']} · {match['city']}  \n"
            f"{tag(match['work_mode'], 'work_mode')} {score_tag}",
            unsafe_allow_html=True,
        )

improvement_card = section_card("What to improve next", "Prioritised by how many of the top local matches list each missing skill.")
with improvement_card:
    plan = improvement_plan(recommended_skills(matches))
    if not plan:
        st.info("No missing curated skills were identified in the displayed matches.")
    for index, (skill, job_count, guidance) in enumerate(plan, start=1):
        st.markdown(f"**{index}. {skill}** · missing from {job_count} displayed matches")
        st.caption(guidance)

resume_card = section_card("Resume improvement checklist", "Use this before applying to a role that interests you.")
with resume_card:
    st.markdown(
        "- Put the target role and strongest matching skills near the top of the resume.\n"
        "- Describe projects with an action, the tools used, and a measurable outcome where available.\n"
        "- Add missing skills only after you have practised them and can discuss your work in an interview.\n"
        "- Tailor the project bullets to the skills shown in the job description."
    )
