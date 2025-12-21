from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import pandas as pd
from datetime import datetime

app = Flask(__name__)
DB_NAME = "npt.db"

# ---------- DATABASE CONNECTION ----------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- HOME / VIEW NPT ----------
@app.route("/")
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

    conn = get_db()
    records = conn.execute(base_query, params).fetchall()

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

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    conn = get_db()

    dept_data = conn.execute("""
        SELECT Department, SUM(Time) total
        FROM npt_dataset
        GROUP BY Department
    """).fetchall()

    equip_data = conn.execute("""
        SELECT Equipment, SUM(Time) total
        FROM npt_dataset
        GROUP BY Equipment
    """).fetchall()

    conn.close()
    return render_template("dashboard.html", dept_data=dept_data, equip_data=equip_data)

def normalize_text(value):
    if not value:
        return None
    return value.strip().title()


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
