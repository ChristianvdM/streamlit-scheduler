import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime
from io import BytesIO
import base64

# Set black theme using custom CSS
st.set_page_config(page_title="Production Team Scheduler", layout="wide")
st.markdown(
    """
    <style>
        body {
            background-color: #000000;
            color: white;
        }
        .stApp {
            background-color: #000000;
        }
        .stButton>button, .stDownloadButton>button {
            background-color: #444;
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Load and center the logo
with open("image.png", "rb") as img_file:
    encoded = base64.b64encode(img_file.read()).decode()
    st.markdown(f"""
        <div style='text-align: center;'>
            <img src='data:image/png;base64,{encoded}' width='600'>
        </div>
    """, unsafe_allow_html=True)

st.title("📅 CPT Production Team Scheduler")
st.markdown("Upload your **Skills CSV** and **Availability CSV** below. Then click 'Generate Schedule' to preview and download the Excel file.")

skills_file = st.file_uploader("Upload skills CSV", type="csv")
availability_file = st.file_uploader("Upload availability CSV", type="csv")

if skills_file and availability_file:
    skills = pd.read_csv(skills_file)
    availability = pd.read_csv(availability_file)
    skills["Name"] = skills["Name"].str.strip()
    availability["Name"] = availability["Name"].str.strip()

    saturday_dates = [d for d in availability.columns if d != "Name" and datetime.strptime(d, "%Y-%m-%d").weekday() == 5]
    sunday_dates = [d for d in availability.columns if d != "Name" and datetime.strptime(d, "%Y-%m-%d").weekday() == 6]

    CAMPUS = ["Tygerberg", "Stellies"]
    ROLES_SUNDAY = ["Sound", "Lights", "Resi"]
    ROLES_SATURDAY = ["Sound", "Lights", "Resi", "Assistant"]

    schedule = {
        "Tygerberg_Sunday": {d: {} for d in sunday_dates},
        "Stellies_Sunday": {d: {} for d in sunday_dates},
        "Tygerberg_Saturday": {d: {} for d in saturday_dates},
    }
    assignments_count = defaultdict(int)
    detailed_assignments = []

    def get_skill(p, col): return skills.loc[skills["Name"] == p, col].values[0]
    def get_eligible(ppl, col, lvl): return [p for p in ppl if get_skill(p, col) >= lvl]
    def get_least_assigned(ppl): return sorted(ppl, key=lambda p: assignments_count[p])

    # Assign Directors First
    for date in saturday_dates + sunday_dates:
        available = availability[availability[date] == "Yes"]["Name"].tolist()
        if date in saturday_dates:
            eligible = get_eligible(available, "Director", 2)
            pool = eligible if eligible else available
            director = next((p for p in get_least_assigned(pool)), None)
            if director:
                schedule["Tygerberg_Saturday"][date]["Director"] = director
                assignments_count[director] += 1
                detailed_assignments.append((director, "Tygerberg", "Director", "Saturday"))
        if date in sunday_dates:
            for campus in CAMPUS:
                eligible = get_eligible(available, "Director", 2)
                pool = eligible if eligible else available
                director = next((p for p in get_least_assigned(pool)), None)
                if director:
                    schedule[f"{campus}_Sunday"][date]["Director"] = director
                    assignments_count[director] += 1
                    detailed_assignments.append((director, campus, "Director", "Sunday"))

    # Assign Other Roles
    for date in sunday_dates:
        available = availability[availability[date] == "Yes"]["Name"].tolist()
        for campus in CAMPUS:
            used = set(schedule[f"{campus}_Sunday"][date].values())
            for role in ROLES_SUNDAY:
                col = f"{role}_{campus}"
                main = next((p for p in get_least_assigned(get_eligible(available, col, 2)) if p not in used), None)
                if main:
                    schedule[f"{campus}_Sunday"][date][f"{role} Main"] = main
                    used.add(main)
                    assignments_count[main] += 1
                    detailed_assignments.append((main, campus, f"{role} Main", "Sunday"))
                assist = next((p for p in get_least_assigned(get_eligible(available, col, 1)) if p not in used and p != main), None)
                if assist:
                    schedule[f"{campus}_Sunday"][date][f"{role} Assistant"] = assist
                    used.add(assist)
                    assignments_count[assist] += 1
                    detailed_assignments.append((assist, campus, f"{role} Assistant", "Sunday"))

    for date in saturday_dates:
        available = availability[availability[date] == "Yes"]["Name"].tolist()
        used = set(schedule["Tygerberg_Saturday"][date].values())
        for role in ["Sound", "Lights", "Resi"]:
            col = f"{role}_Tygerberg"
            main = next((p for p in get_least_assigned(get_eligible(available, col, 2)) if p not in used), None)
            if main:
                schedule["Tygerberg_Saturday"][date][role] = main
                used.add(main)
                assignments_count[main] += 1
                detailed_assignments.append((main, "Tygerberg", role, "Saturday"))
        def total_skill(p):
            return skills.loc[skills["Name"] == p, ["Sound_Tygerberg", "Lights_Tygerberg", "Resi_Tygerberg", "Director"]].sum(axis=1).values[0]
        eligible_assist = [p for p in available if p not in used and any(get_skill(p, col) >= 1 for col in ["Sound_Tygerberg", "Lights_Tygerberg", "Resi_Tygerberg"])]
        eligible_assist = sorted(eligible_assist, key=lambda p: (total_skill(p), assignments_count[p]))
        assistant = next((p for p in eligible_assist if p not in used), None)
        if assistant:
            schedule["Tygerberg_Saturday"][date]["Assistant"] = assistant
            assignments_count[assistant] += 1
            detailed_assignments.append((assistant, "Tygerberg", "Assistant", "Saturday"))

    # Output to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        role_order_sunday = [
            "Sound Main", "Sound Assistant",
            "Lights Main", "Lights Assistant",
            "Resi Main", "Resi Assistant",
            "Director"
        ]
        role_order_saturday = ["Sound", "Lights", "Resi", "Director", "Assistant"]

        full_block = pd.DataFrame()
        for campus in CAMPUS:
            block = pd.DataFrame(index=role_order_sunday, columns=sunday_dates)
            for d in sunday_dates:
                for r in role_order_sunday:
                    block.at[r, d] = schedule[f"{campus}_Sunday"][d].get(r, "")
            block.index.name = "Role"
            full_block = pd.concat([
                full_block,
                pd.DataFrame([["Campus: " + campus] + [""] * len(sunday_dates)], columns=["Role"] + sunday_dates),
                block.reset_index()
            ], ignore_index=True)
        full_block.to_excel(writer, sheet_name="Sunday_Services", index=False)
        worksheet = writer.sheets["Sunday_Services"]
        for i, col in enumerate(full_block.columns):
            column_len = max(full_block[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.set_column(i, i, column_len)

        sat_df = pd.DataFrame(index=role_order_saturday, columns=saturday_dates)
        for d in saturday_dates:
            for r in role_order_saturday:
                sat_df.at[r, d] = schedule["Tygerberg_Saturday"][d].get(r, "")
        sat_df.index.name = "Role"
        sat_df.to_excel(writer, sheet_name="Tygerberg_Saturday")
        worksheet = writer.sheets["Tygerberg_Saturday"]
        for i, col in enumerate(sat_df.reset_index().columns):
            column_len = max(sat_df.reset_index()[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.set_column(i, i, column_len)

        # Summary sheet grouped by Name and Campus for Sunday counts
        summary_df = pd.DataFrame(detailed_assignments, columns=["Name", "Campus", "Role", "Day"])
        sunday_summary = summary_df[summary_df["Day"] == "Sunday"].groupby(["Name", "Campus"]).size().unstack(fill_value=0).reset_index()
        saturday_summary = summary_df[summary_df["Day"] == "Saturday"].groupby("Name").size().reset_index(name="Saturday Assignments")
        summary_combined = pd.merge(saturday_summary, sunday_summary, on="Name", how="outer").fillna(0)

        # Rename Sunday columns
        sunday_cols = [col for col in summary_combined.columns if col in CAMPUS]
        rename_map = {campus: f"Sunday @ {campus}" for campus in sunday_cols}
        summary_combined = summary_combined.rename(columns=rename_map)

        # Add total assignments column
        assignment_cols = [col for col in summary_combined.columns if col != "Name"]
        summary_combined["Total Assignments"] = summary_combined[assignment_cols].sum(axis=1)

        # Sort by total assignments descending
        summary_combined = summary_combined.sort_values(by="Total Assignments", ascending=False).reset_index(drop=True)

        summary_combined.to_excel(writer, sheet_name="Summary", index=False)
        worksheet = writer.sheets["Summary"]
        for i, col in enumerate(summary_combined.columns):
            column_len = max(summary_combined[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.set_column(i, i, column_len)

    # Final Output Section
    st.success("✅ Schedule successfully generated!")
    st.markdown("### 📊 Preview: Assignment Summary")
    st.dataframe(summary_combined.head(25))
    st.download_button(
        "📥 Download Excel Schedule",
        data=output.getvalue(),
        file_name="production_schedule_august_2025.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
