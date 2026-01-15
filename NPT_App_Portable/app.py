from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import pandas as pd
from datetime import datetime

app = Flask(__name__)
DB_NAME = "npt.db"

# ---------- COLOR PALETTE ----------
COLOR_PALETTE = [
    "#f97316", "#ef4444", "#3b82f6", "#10b981", "#8b5cf6", 
    "#06b6d4", "#ec4899", "#14b8a6", "#f43f5e", "#84cc16", 
    "#0ea5e9", "#d946ef", "#f59e0b", "#6366f1", "#06b6d4",
    "#a855f7", "#ec4899", "#f87171", "#4ade80", "#22d3ee",
    "#a78bfa", "#fb923c", "#34d399", "#60a5fa", "#fbbf24"
]

# Generate consistent color for an item based on its name
def get_color_for_item(item_name, used_index=None):
    """Get a consistent color for a department/equipment"""
    if used_index is not None:
        return COLOR_PALETTE[used_index % len(COLOR_PALETTE)]
    # Use hash for consistent coloring based on name
    hash_value = hash(item_name) % len(COLOR_PALETTE)
    return COLOR_PALETTE[hash_value]

# ---------- DATABASE CONNECTION ----------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- HOME / VIEW NPT ----------
@app.route("/view")
def view_npt():
    base_query = "SELECT Date, Category, Department, Equipment, Time, Reason FROM npt_dataset WHERE 1=1"
    params = []

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    department = request.args.get("department")
    equipment = request.args.get("equipment")

    if from_date:
        base_query += " AND Date >= ?"
        params.append(from_date)

    if to_date:
        base_query += " AND Date <= ?"
        params.append(to_date)

    if department:
        base_query += " AND Department = ?"
        params.append(department)

    if equipment:
        base_query += " AND Equipment = ?"
        params.append(equipment)

    base_query += " ORDER BY Date DESC"

    conn = get_db()
    records = conn.execute(base_query, params).fetchall()

    # Calculate total NPT from filtered records
    total_npt = sum(float(r['Time']) for r in records if r['Time'])

    # Departments → always all
    departments = conn.execute(
        "SELECT DISTINCT Department FROM npt_dataset"
    ).fetchall()

    # Equipments → depend on department
    if department:
        equipments = conn.execute(
            "SELECT DISTINCT Equipment FROM npt_dataset WHERE Department = ?",
            (department,)
        ).fetchall()
    else:
        equipments = conn.execute(
            "SELECT DISTINCT Equipment FROM npt_dataset"
        ).fetchall()

    conn.close()

    return render_template(
        "view_npt.html",
        records=records,
        departments=departments,
        equipments=equipments,
        total_npt=total_npt,
        selected_department=department,
        selected_equipment=equipment
    )

# ---------- ADD NPT ----------
@app.route("/add", methods=["GET", "POST"])
def add_npt():
    if request.method == "POST":
        data = request.form

        conn = get_db()
        conn.execute("""
            INSERT INTO npt_dataset
            (Date, Category, Department, Equipment, Time, Reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["Date"],
            normalize_text(data["Category"]),
            normalize_text(data["Department"]),
            normalize_text(data["Equipment"]),
            data["Time"],
            data["Reason"]
        ))

        conn.commit()
        conn.close()
        return redirect(url_for("view_npt"))

    return render_template("add_npt.html")


# ---------- DOWNLOAD EXCEL ----------
@app.route("/download")
def download_excel():
    query = "SELECT Date, Category, Department, Equipment, Time, Reason FROM npt_dataset WHERE 1=1"
    params = []

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    department = request.args.get("department")
    equipment = request.args.get("equipment")

    if from_date:
        query += " AND Date >= ?"
        params.append(from_date)

    if to_date:
        query += " AND Date <= ?"
        params.append(to_date)

    if department:
        query += " AND Department = ?"
        params.append(department)

    if equipment:
        query += " AND Equipment = ?"
        params.append(equipment)

    conn = get_db()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    file_path = "filtered_npt.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

@app.route("/")
def dashboard():
    conn = get_db()

    # ----- Department-wise NPT -----
    dept_data = conn.execute("""
        SELECT Department, SUM(Time) AS total
        FROM npt_dataset
        GROUP BY Department
        ORDER BY total DESC
    """).fetchall()

    # ----- Equipment-wise NPT -----
    equip_data = conn.execute("""
        SELECT Equipment, SUM(Time) AS total
        FROM npt_dataset
        GROUP BY Equipment
        ORDER BY total DESC
    """).fetchall()

    # ----- Date-wise Overall NPT (for Bar Graph) -----
    date_data = conn.execute("""
        SELECT DATE(Date) as Date, SUM(Time) AS total
        FROM npt_dataset
        GROUP BY DATE(Date)
        ORDER BY DATE(Date)
    """).fetchall()

    # ----- KPI values -----
    total_npt = conn.execute("SELECT SUM(Time) FROM npt_dataset").fetchone()[0]
    avg_npt = conn.execute("SELECT AVG(Time) FROM npt_dataset").fetchone()[0]

    conn.close()

    # ----- Generate colors dynamically -----
    dept_colors = [get_color_for_item(d['Department'], idx) for idx, d in enumerate(dept_data)]
    equip_colors = [get_color_for_item(e['Equipment'], idx) for idx, e in enumerate(equip_data)]

    return render_template(
        "dashboard.html",
        dept_data=dept_data,
        equip_data=equip_data,
        date_data=date_data,
        total_npt=total_npt or 0,
        avg_npt=round(avg_npt or 0, 2),
        dept_colors=dept_colors,
        equip_colors=equip_colors
    )


#----------------------------------------
def normalize_text(value):
    if not value:
        return None
    return value.strip().title()


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
