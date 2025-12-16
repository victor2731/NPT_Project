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
    query = "SELECT * FROM npt_records WHERE 1=1"
    params = []

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    department = request.args.get("department")
    equipment = request.args.get("equipment")

    if from_date:
        query += " AND npt_date >= ?"
        params.append(from_date)

    if to_date:
        query += " AND npt_date <= ?"
        params.append(to_date)

    if department:
        query += " AND department = ?"
        params.append(department)

    if equipment:
        query += " AND equipment = ?"
        params.append(equipment)

    conn = get_db()
    records = conn.execute(query, params).fetchall()

    departments = conn.execute(
        "SELECT DISTINCT department FROM npt_records"
    ).fetchall()

    equipments = conn.execute(
        "SELECT DISTINCT equipment FROM npt_records"
    ).fetchall()

    conn.close()

    return render_template(
        "view_npt.html",
        records=records,
        departments=departments,
        equipments=equipments
    )

# ---------- ADD NPT ----------
@app.route("/add", methods=["GET", "POST"])
def add_npt():
    if request.method == "POST":
        data = request.form

        conn = get_db()
        conn.execute("""
            INSERT INTO npt_records
            (npt_date, day_no, npt_category, department, equipment,
             npt_hours, time_period, reason, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["npt_date"],
            data["day_no"],
            data["npt_category"],
            data["department"],
            data["equipment"],
            data["npt_hours"],
            data["time_period"],
            data["reason"],
            data["remarks"]
        ))

        conn.commit()
        conn.close()
        return redirect(url_for("view_npt"))

    return render_template("add_npt.html")

# ---------- DOWNLOAD EXCEL ----------
@app.route("/download")
def download_excel():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM npt_records", conn)
    conn.close()

    file_name = "NPT_Report_Upto_" + datetime.now().strftime("%d_%m_%Y") + ".xlsx"
    df.to_excel(file_name, index=False)

    return send_file(file_name, as_attachment=True)

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    conn = get_db()

    dept_data = conn.execute("""
        SELECT department, SUM(npt_hours) total
        FROM npt_records
        GROUP BY department
    """).fetchall()

    equip_data = conn.execute("""
        SELECT equipment, SUM(npt_hours) total
        FROM npt_records
        GROUP BY equipment
    """).fetchall()

    conn.close()
    return render_template("dashboard.html", dept_data=dept_data, equip_data=equip_data)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
