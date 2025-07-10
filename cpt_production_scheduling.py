import pandas as pd
import numpy as np
from collections import defaultdict
from pandas import ExcelWriter
from datetime import datetime

# Reload cleaned skills and generated availability
skills = pd.read_csv("CPT_production_skills.csv")
availability = pd.read_csv("availability_august_2025.csv")

skills["Name"] = skills["Name"].str.strip()
availability["Name"] = availability["Name"].str.strip()

# Get all Saturdays and Sundays
saturday_dates = [d for d in availability.columns if d != "Name" and datetime.strptime(d, "%Y-%m-%d").weekday() == 5]
sunday_dates = [d for d in availability.columns if d != "Name" and datetime.strptime(d, "%Y-%m-%d").weekday() == 6]
CAMPUS = ["Tygerberg", "Stellies"]
ROLES_SUNDAY = ["Sound", "Lights", "Resi"]
ROLES_SATURDAY = ["Sound", "Lights", "Resi", "Assistant"]

# Setup schedule structures
schedule = {
    "Tygerberg_Sunday": {d: {} for d in sunday_dates},
    "Stellies_Sunday": {d: {} for d in sunday_dates},
    "Tygerberg_Saturday": {d: {} for d in saturday_dates}
}
assignments_count = defaultdict(int)
detailed_assignments = []

# Helpers
def get_skill(p, col): return skills.loc[skills["Name"] == p, col].values[0]
def get_eligible(ppl, col, lvl): return [p for p in ppl if get_skill(p, col) >= lvl]
def get_least_assigned(ppl): return sorted(ppl, key=lambda p: assignments_count[p])

# === Assign ALL Directors first ===
for date in saturday_dates + sunday_dates:
    available = availability[availability[date] == "Yes"]["Name"].tolist()

    # Saturday Director (Tygerberg)
    if date in saturday_dates:
        eligible = get_eligible(available, "Director", 2)
        pool = eligible if eligible else available
        director = next((p for p in get_least_assigned(pool)), None)
        if director:
            schedule["Tygerberg_Saturday"][date]["Director"] = director
            assignments_count[director] += 1
            detailed_assignments.append((director, "Tygerberg", "Director", "Saturday"))

    # Sunday Directors (Tygerberg & Stellies)
    if date in sunday_dates:
        for campus in CAMPUS:
            eligible = get_eligible(available, "Director", 2)
            pool = eligible if eligible else available
            director = next((p for p in get_least_assigned(pool)), None)
            if director:
                schedule[f"{campus}_Sunday"][date]["Director"] = director
                assignments_count[director] += 1
                detailed_assignments.append((director, campus, "Director", "Sunday"))

# === Assign Other Roles ===
# Sunday Roles (Sound, Lights, Resi Main & Assistant)
for date in sunday_dates:
    available = availability[availability[date] == "Yes"]["Name"].tolist()

    for campus in CAMPUS:
        used = set(schedule[f"{campus}_Sunday"][date].values())

        for role in ROLES_SUNDAY:
            col = f"{role}_{campus}"

            # Main
            main = next((p for p in get_least_assigned(get_eligible(available, col, 2)) if p not in used), None)
            if main:
                schedule[f"{campus}_Sunday"][date][f"{role} Main"] = main
                used.add(main)
                assignments_count[main] += 1
                detailed_assignments.append((main, campus, f"{role} Main", "Sunday"))

            # Assistant
            assist = next((p for p in get_least_assigned(get_eligible(available, col, 1)) if p not in used and p != main), None)
            if assist:
                schedule[f"{campus}_Sunday"][date][f"{role} Assistant"] = assist
                used.add(assist)
                assignments_count[assist] += 1
                detailed_assignments.append((assist, campus, f"{role} Assistant", "Sunday"))

# Saturday Roles (Sound, Lights, Resi, Assistant)
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

    # Assistant (any Tygerberg skill ≥1, prefer lower total skill)
    def total_skill(p):
        return skills.loc[skills["Name"] == p, ["Sound_Tygerberg", "Lights_Tygerberg", "Resi_Tygerberg", "Director"]].sum(axis=1).values[0]

    eligible_assist = [p for p in available if p not in used and any(get_skill(p, col) >= 1 for col in ["Sound_Tygerberg", "Lights_Tygerberg", "Resi_Tygerberg"])]
    eligible_assist = sorted(eligible_assist, key=lambda p: (total_skill(p), assignments_count[p]))
    assistant = next((p for p in eligible_assist if p not in used), None)
    if assistant:
        schedule["Tygerberg_Saturday"][date]["Assistant"] = assistant
        assignments_count[assistant] += 1
        detailed_assignments.append((assistant, "Tygerberg", "Assistant", "Saturday"))

# === Export to Excel ===
role_order_sunday = [
    "Sound Main", "Sound Assistant",
    "Lights Main", "Lights Assistant",
    "Resi Main", "Resi Assistant",
    "Director"
]
role_order_saturday = ["Sound", "Lights", "Resi", "Director", "Assistant"]

output_path = "production_schedule_august_2025.xlsx"
with ExcelWriter(output_path, engine="xlsxwriter") as writer:
    # Sunday Services sheet
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

    # Saturday sheet
    sat_df = pd.DataFrame(index=role_order_saturday, columns=saturday_dates)
    for d in saturday_dates:
        for r in role_order_saturday:
            sat_df.at[r, d] = schedule["Tygerberg_Saturday"][d].get(r, "")
    sat_df.index.name = "Role"
    sat_df.to_excel(writer, sheet_name="Tygerberg_Saturday")

    # Summary
    summary_df = pd.DataFrame(detailed_assignments, columns=["Name", "Campus", "Role", "Day"])
    summary_grouped = summary_df.groupby(["Day", "Name", "Campus", "Role"]).size().reset_index(name="Count")
    summary_grouped.to_excel(writer, sheet_name="Summary", index=False)

output_path

