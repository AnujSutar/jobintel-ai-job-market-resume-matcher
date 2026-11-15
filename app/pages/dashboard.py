"""Dashboard page backed by the local JobIntel SQLite database."""

from __future__ import annotations

from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data.analytics import (
    apply_job_filters,
    calculate_metrics,
    city_counts,
    salary_by_experience,
    skill_counts,
    skill_trend,
)
from src.data.cache import clear_job_cache, load_jobs_cached
from src.data.database import database_summary
from src.ui.theme import PRIMARY, empty_state, kpi_card, page_header, section_card, tag


def format_lpa(value: float | None) -> str:
    """Format a computed salary in lakhs per annum."""
    return "—" if value is None or pd.isna(value) else f"₹{value:.1f} LPA"


def format_salary_range(job: pd.Series) -> str:
    """Show only the salary figures available for one job posting."""
    minimum, maximum = job["salary_min_lpa"], job["salary_max_lpa"]
    if pd.notna(minimum) and pd.notna(maximum):
        return f"₹{minimum:.1f}–₹{maximum:.1f} LPA"
    if pd.notna(minimum):
        return f"From ₹{minimum:.1f} LPA"
    if pd.notna(maximum):
        return f"Up to ₹{maximum:.1f} LPA"
    return "Not listed"


def reset_filters() -> None:
    """Restore all dashboard controls to their full-dataset values."""
    st.session_state.update(
        dashboard_role="All roles",
        dashboard_city="All cities",
        dashboard_experience="All experience levels",
        dashboard_date="All available dates",
        dashboard_search="",
        dashboard_page=1,
    )


def render_job_table(jobs: pd.DataFrame) -> None:
    """Render a paginated job table and an actual posting-description view."""
    table_card = section_card("Latest job postings", "Results reflect the active filters and search term.")
    with table_card:
        search = st.text_input("Search jobs", placeholder="Search title, company, city, or skill", key="dashboard_search")
        displayed = jobs.copy()
        if search.strip():
            query = search.strip().lower()
            searchable = displayed.apply(
                lambda row: " ".join(
                    [str(row["title"]), str(row["company"]), str(row["city"]), " ".join(row["skills"])]
                ).lower(),
                axis=1,
            )
            displayed = displayed[searchable.str.contains(query, regex=False)]
        if displayed.empty:
            st.info("No jobs match the current filters. Reset filters or import another dataset.")
            return

        rows_per_page = 5
        total_pages = max(1, (len(displayed) + rows_per_page - 1) // rows_per_page)
        current_page = min(int(st.session_state.get("dashboard_page", 1)), total_pages)
        st.session_state.dashboard_page = current_page
        start = (current_page - 1) * rows_per_page
        page = displayed.iloc[start : start + rows_per_page]

        table_rows: list[str] = []
        for _, job in page.iterrows():
            skills = "".join(tag(skill, "skill") for skill in job["skills"][:4]) or "—"
            location = f"{escape(str(job['city']) or 'Location not listed')} {tag(str(job['work_mode']), 'work_mode')}"
            table_rows.append(
                "<tr>"
                f"<td><strong>{escape(str(job['title']))}</strong><br><span>{escape(str(job['company']) or 'Company not listed')}</span></td>"
                f"<td>{location}</td><td>{format_salary_range(job)}</td><td>{skills}</td></tr>"
            )

        st.markdown(
            """
            <style>
            .jobintel-table { width: 100%; border-collapse: collapse; font-size: .86rem; }
            .jobintel-table th { background: #F8FAFC; color: #64748B; font-size: .68rem;
                letter-spacing: .06em; padding: .75rem; text-align: left; text-transform: uppercase; }
            .jobintel-table td { border-top: 1px solid #E2E8F0; color: #334155; padding: .85rem .75rem; vertical-align: top; }
            .jobintel-table td span { color: #64748B; font-size: .78rem; }
            .jobintel-table tr:hover td { background: #F8FAFC; }
            </style><table class="jobintel-table"><thead><tr><th>Role & company</th><th>Location</th>
            <th>Salary</th><th>Skills</th></tr></thead><tbody>"""
            + "".join(table_rows)
            + "</tbody></table>",
            unsafe_allow_html=True,
        )

        pager_left, pager_right = st.columns([3, 1])
        pager_left.caption(f"Showing {start + 1}–{min(start + rows_per_page, len(displayed))} of {len(displayed)} postings")
        pager_right.selectbox("Page", list(range(1, total_pages + 1)), key="dashboard_page", label_visibility="collapsed")

        details_options = page["id"].tolist()
        selected_id = st.selectbox(
            "View job details",
            details_options,
            format_func=lambda job_id: next(
                f"{row.title} — {row.company or 'Company not listed'}" for row in page.itertuples() if row.id == job_id
            ),
        )
        selected = page.loc[page["id"] == selected_id].iloc[0]
        with st.expander("Posting description"):
            st.write(selected["description"] or "No description was available in this data source.")


page_header("Job Market Intelligence", "Hiring patterns calculated from your locally imported India job postings.")

summary = database_summary()
with st.spinner("Loading job postings..."):
    jobs = load_jobs_cached()
top_left, top_right = st.columns([4, 1])
with top_left:
    if summary.get("sample", 0):
        st.markdown(tag("Sample data", "status"), unsafe_allow_html=True)
        st.caption("The current database includes demo CSV records. Import a legal data source for market analysis.")
    elif jobs.empty:
        st.markdown(tag("No data loaded", "status"), unsafe_allow_html=True)
    else:
        st.markdown(tag("Database loaded", "status"), unsafe_allow_html=True)
with top_right:
    if st.button("Refresh data", use_container_width=True):
        clear_job_cache()
        st.rerun()

if jobs.empty:
    empty_state(
        "No job postings yet",
        "Run python scripts/import_jobs.py --source csv in PowerShell, then choose Refresh data.",
    )
    st.stop()

role_options = ["All roles", *sorted(jobs["title"].dropna().unique())]
city_options = ["All cities", *sorted(city for city in jobs["city"].dropna().unique() if city)]
experience_options = ["All experience levels", *sorted(jobs["experience_band"].dropna().unique())]

filters = section_card("Filters", "Date windows are measured from the latest posting date in the imported data.")
with filters:
    role_column, city_column, experience_column, date_column, reset_column = st.columns([1.2, 1.1, 1.25, 1.25, 0.75])
    role_column.selectbox("Role", role_options, key="dashboard_role")
    city_column.selectbox("City", city_options, key="dashboard_city")
    experience_column.selectbox("Experience", experience_options, key="dashboard_experience")
    date_column.selectbox("Date window", ["All available dates", "Last 30 days", "Last 90 days", "Last 180 days"], key="dashboard_date")
    reset_column.button("Reset", on_click=reset_filters, use_container_width=True)

filtered_jobs = apply_job_filters(
    jobs,
    role=st.session_state.dashboard_role,
    city=st.session_state.dashboard_city,
    experience=st.session_state.dashboard_experience,
    date_window=st.session_state.dashboard_date,
)
if filtered_jobs.empty:
    empty_state("No matching postings", "Use Reset to return to every job in the imported dataset.")
    st.stop()

metrics = calculate_metrics(filtered_jobs)
kpi_columns = st.columns(4)
with kpi_columns[0]:
    kpi_card("Total job postings", f"{metrics.total_jobs:,}", "Filtered records in SQLite")
with kpi_columns[1]:
    kpi_card("Average salary", format_lpa(metrics.average_salary_lpa), "Based on jobs with salary data")
with kpi_columns[2]:
    kpi_card("Top hiring city", metrics.top_city or "—", f"{metrics.top_city_count} matching postings" if metrics.top_city else "No city data available")
with kpi_columns[3]:
    kpi_card("Most in-demand skill", metrics.top_skill or "—", f"Found in {metrics.top_skill_count} matching postings" if metrics.top_skill else "No skills available")

chart_left, chart_right = st.columns(2)
with chart_left:
    skills_card = section_card("Top skills in demand", "Share of filtered postings mentioning each skill.")
    with skills_card:
        skills = skill_counts(filtered_jobs).head(10).sort_values("count")
        if skills.empty:
            st.info("Skill data will appear after extraction or from a CSV skills column.")
        else:
            skills["share"] = skills["count"] / len(filtered_jobs) * 100
            figure = px.bar(skills, x="share", y="skill", orientation="h", text=skills["share"].map(lambda value: f"{value:.0f}%"), color_discrete_sequence=[PRIMARY])
            figure.update_layout(xaxis_title=None, yaxis_title=None, showlegend=False, margin=dict(l=0, r=20, t=10, b=0))
            figure.update_xaxes(range=[0, 100], showgrid=True, gridcolor="#E2E8F0", ticksuffix="%")
            figure.update_yaxes(showgrid=False)
            st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
with chart_right:
    cities_card = section_card("Postings by city", "Counts are based on filtered records with a stated city.")
    with cities_card:
        cities = city_counts(filtered_jobs).head(10)
        if cities.empty:
            st.info("No city information is available in the current records.")
        else:
            figure = px.bar(cities, x="city", y="count", color_discrete_sequence=[PRIMARY])
            figure.update_layout(xaxis_title=None, yaxis_title="Postings", showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
            figure.update_xaxes(showgrid=False)
            figure.update_yaxes(gridcolor="#E2E8F0")
            st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

chart_left, chart_right = st.columns(2)
with chart_left:
    salary_card = section_card("Salary by experience", "25th to 90th percentile range; marker shows median LPA.")
    with salary_card:
        salary_ranges = salary_by_experience(filtered_jobs)
        if salary_ranges.empty:
            st.info("Salary ranges need postings with salary information.")
        else:
            figure = go.Figure()
            figure.add_trace(go.Bar(
                y=salary_ranges["experience_band"], x=salary_ranges["p90"] - salary_ranges["p25"], base=salary_ranges["p25"],
                customdata=salary_ranges[["p90"]], orientation="h", marker_color="#C7D2FE",
                hovertemplate="%{y}<br>25th–90th percentile: ₹%{base:.1f}–₹%{customdata[0]:.1f} LPA<extra></extra>", name="25th–90th percentile"))
            figure.add_trace(go.Scatter(
                y=salary_ranges["experience_band"], x=salary_ranges["median"], mode="markers", marker={"color": PRIMARY, "size": 10},
                hovertemplate="%{y}<br>Median: ₹%{x:.1f} LPA<extra></extra>", name="Median"))
            figure.update_layout(xaxis_title="Salary (LPA)", yaxis_title=None, barmode="overlay", margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.12))
            figure.update_xaxes(gridcolor="#E2E8F0")
            figure.update_yaxes(showgrid=False)
            st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
with chart_right:
    trend_card = section_card("Skill demand trend", "Monthly mentions across available posting dates.")
    with trend_card:
        trend = skill_trend(filtered_jobs)
        if trend.empty or trend["month"].nunique() < 2:
            st.info("Trend charts need records from at least two months. Current data is still shown in the other views.")
        else:
            figure = px.line(trend, x="month", y="count", color="skill", markers=True, color_discrete_sequence=px.colors.qualitative.Safe)
            figure.update_layout(xaxis_title=None, yaxis_title="Postings mentioning skill", margin=dict(l=0, r=0, t=10, b=0), legend_title=None)
            figure.update_yaxes(gridcolor="#E2E8F0")
            st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

render_job_table(filtered_jobs)
