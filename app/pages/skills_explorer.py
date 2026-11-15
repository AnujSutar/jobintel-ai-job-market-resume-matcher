"""Skills Explorer page driven by imported job-posting records."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data.analytics import (
    apply_job_filters,
    city_counts,
    co_occurring_skills,
    jobs_for_skill,
    roles_for_skill,
    salary_by_experience,
    skill_counts,
    skill_growth_percent,
)
from src.data.cache import clear_job_cache, load_jobs_cached
from src.data.database import database_summary
from src.ui.theme import PRIMARY, empty_state, kpi_card, page_header, section_card, tag


def choose_skill(skill: str) -> None:
    """Set the search field from a quick-compare button callback."""
    st.session_state.skill_search = skill


def reset_skill_filters() -> None:
    """Restore the explorer controls to their full-dataset values."""
    st.session_state.update(skills_role="All roles", skills_city="All cities", skill_search="")


def resolve_skill(query: str, available_skills: list[str]) -> str | None:
    """Resolve exact case-insensitive input, or use the top available skill."""
    if not available_skills:
        return None
    if not query.strip():
        return available_skills[0]
    query_lower = query.strip().casefold()
    exact = next((skill for skill in available_skills if skill.casefold() == query_lower), None)
    return exact


def salary_text(value: float | None) -> str:
    """Format salary or represent unavailable data without a made-up value."""
    return "—" if value is None or pd.isna(value) else f"₹{value:.1f} LPA"


page_header("Skills Explorer", "Inspect the job-posting demand, pay, and role context behind a skill.")

summary = database_summary()
with st.spinner("Loading skill data..."):
    jobs = load_jobs_cached()
status_column, refresh_column = st.columns([4, 1])
with status_column:
    if summary.get("sample", 0):
        st.markdown(tag("Sample data", "status"), unsafe_allow_html=True)
        st.caption("Insights reflect the demo CSV until you import another legal data source.")
    elif not jobs.empty:
        st.markdown(tag("Database loaded", "status"), unsafe_allow_html=True)
with refresh_column:
    if st.button("Refresh data", use_container_width=True):
        clear_job_cache()
        st.rerun()

if jobs.empty:
    empty_state(
        "No job postings yet",
        "Run python scripts/import_jobs.py --source csv in PowerShell, then choose Refresh data.",
    )
    st.stop()

all_skills = skill_counts(jobs)["skill"].tolist()
role_options = ["All roles", *sorted(jobs["title"].dropna().unique())]
city_options = ["All cities", *sorted(city for city in jobs["city"].dropna().unique() if city)]

controls = section_card("Find a skill", "Use exact skill names from the imported data for the clearest comparison.")
with controls:
    search_column, role_column, city_column, reset_column = st.columns([2.2, 1.2, 1.1, 0.7])
    search_column.text_input("Skill search", placeholder="For example: Python, SQL, AWS", key="skill_search")
    role_column.selectbox("Role", role_options, key="skills_role")
    city_column.selectbox("City", city_options, key="skills_city")
    reset_column.button("Reset", on_click=reset_skill_filters, use_container_width=True)

    st.caption("Quick compare")
    quick_skills = all_skills[:6]
    quick_columns = st.columns(max(1, len(quick_skills)))
    for column, quick_skill in zip(quick_columns, quick_skills):
        column.button(quick_skill, key=f"quick_skill_{quick_skill}", on_click=choose_skill, args=(quick_skill,), use_container_width=True)

filtered_jobs = apply_job_filters(jobs, role=st.session_state.skills_role, city=st.session_state.skills_city)
selected_skill = resolve_skill(st.session_state.skill_search, all_skills)
if selected_skill is None:
    if st.session_state.skill_search.strip():
        st.warning("That skill was not found as an exact match. Choose a quick-compare skill or clear the search.")
    else:
        empty_state("No skills available", "Import postings that include a skills field, then return to this page.")
    st.stop()

skill_jobs = jobs_for_skill(filtered_jobs, selected_skill)
if skill_jobs.empty:
    empty_state(f"No filtered jobs mention {selected_skill}", "Reset the role or city filter to broaden the search.")
    st.stop()

salary_midpoints = skill_jobs[["salary_min_lpa", "salary_max_lpa"]].apply(pd.to_numeric, errors="coerce").mean(axis=1).dropna()
cities = city_counts(skill_jobs)
top_city = cities.iloc[0]["city"] if not cities.empty else None
growth = skill_growth_percent(filtered_jobs, selected_skill)
demand_share = len(skill_jobs) / len(filtered_jobs) * 100 if not filtered_jobs.empty else 0.0

kpi_columns = st.columns(4)
with kpi_columns[0]:
    kpi_card("Demand share", f"{demand_share:.0f}%", f"{len(skill_jobs)} of {len(filtered_jobs)} filtered postings")
with kpi_columns[1]:
    kpi_card("Average compensation", salary_text(float(salary_midpoints.mean()) if not salary_midpoints.empty else None), "From postings with salary data")
with kpi_columns[2]:
    kpi_card("Top city", str(top_city) if top_city else "—", f"{int(cities.iloc[0]['count'])} matching postings" if top_city else "No city data")
with kpi_columns[3]:
    growth_text = "—" if growth is None else f"{growth:+.0f}%"
    growth_detail = "Needs two observed months" if growth is None else "Compared with previous observed month"
    kpi_card("Demand growth", growth_text, growth_detail)

chart_left, chart_right = st.columns(2)
with chart_left:
    city_card = section_card(f"Top cities requiring {selected_skill}", "Counts are based on filtered job postings.")
    with city_card:
        if cities.empty:
            st.info("The matching jobs do not contain city information.")
        else:
            figure = px.bar(cities.head(10).sort_values("count"), x="count", y="city", orientation="h", color_discrete_sequence=[PRIMARY])
            figure.update_layout(xaxis_title="Postings", yaxis_title=None, showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
            figure.update_xaxes(gridcolor="#E2E8F0")
            figure.update_yaxes(showgrid=False)
            st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
with chart_right:
    salary_card = section_card("Salary by experience tier", "25th to 90th percentile range; marker shows median LPA.")
    with salary_card:
        ranges = salary_by_experience(skill_jobs)
        if ranges.empty:
            st.info("Salary information is not available for this skill's matching postings.")
        else:
            figure = go.Figure()
            figure.add_trace(go.Bar(
                y=ranges["experience_band"], x=ranges["p90"] - ranges["p25"], base=ranges["p25"], customdata=ranges[["p90"]],
                orientation="h", marker_color="#C7D2FE", name="25th–90th percentile",
                hovertemplate="%{y}<br>25th–90th percentile: ₹%{base:.1f}–₹%{customdata[0]:.1f} LPA<extra></extra>"))
            figure.add_trace(go.Scatter(y=ranges["experience_band"], x=ranges["median"], mode="markers", marker={"color": PRIMARY, "size": 10}, name="Median"))
            figure.update_layout(xaxis_title="Salary (LPA)", yaxis_title=None, barmode="overlay", margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.12))
            figure.update_xaxes(gridcolor="#E2E8F0")
            figure.update_yaxes(showgrid=False)
            st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

lower_left, lower_right = st.columns(2)
with lower_left:
    co_occurring_card = section_card("Co-occurring skills", "Salary impact compares the pair average against the selected-skill average; it does not show causation.")
    with co_occurring_card:
        pairs = co_occurring_skills(filtered_jobs, selected_skill)
        if pairs.empty:
            st.info("No co-occurring skills were found in the matching postings.")
        else:
            for _, pair in pairs.iterrows():
                impact = pair["salary_impact_lpa"]
                impact_text = "Salary not listed" if pd.isna(impact) else f"{impact:+.1f} LPA average salary difference"
                st.markdown(
                    f"{tag(str(pair['skill']), 'skill')} **{pair['pair_share']:.0f}%** of matching postings  \n"
                    f"<span style='color:#64748B;font-size:.8rem'>{int(pair['job_count'])} postings · {impact_text}</span>",
                    unsafe_allow_html=True,
                )
with lower_right:
    roles_card = section_card(f"Roles hiring for {selected_skill}", "Role summaries from the currently filtered job postings.")
    with roles_card:
        roles = roles_for_skill(filtered_jobs, selected_skill)
        if roles.empty:
            st.info("No role-level information is available for this skill.")
        else:
            display_roles = roles.rename(columns={"role": "Role", "postings": "Postings", "average_salary_lpa": "Average salary (LPA)", "top_city": "Top city"})
            st.dataframe(
                display_roles,
                hide_index=True,
                use_container_width=True,
                column_config={"Average salary (LPA)": st.column_config.NumberColumn(format="₹%.1f")},
            )
