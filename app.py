from flask import Flask, render_template, request, redirect, url_for, send_file, session
import csv
import os
from datetime import datetime
import io

app = Flask(__name__)
app.secret_key = "supersecretkey123"

# ------------------------- CONFIG -------------------------
CURRENT_YEAR = "2025/2026"
ADMIN_PASSWORD = "fieldadmin2026"

DATA_FILE = "data/observations.csv"
GROUPS_FILE = "data/groups.csv"
ARCHIVE_FOLDER = "data/archive"

os.makedirs("data", exist_ok=True)
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)


# ------------------------- HOME / LOG OBSERVATIONS -------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = {
            "academic_year": CURRENT_YEAR,
            "year_group": request.form.get("year_group"),
            "group_id": request.form.get("group_id"),
            "member_name": request.form.get("member_name"),
            "species": request.form.get("species"),
            "count": request.form.get("count"),
            "habitat": request.form.get("habitat"),
            "location": request.form.get("location"),
            "notes": request.form.get("notes"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow(data)
        return redirect(url_for("index"))

    return render_template("index.html", year=CURRENT_YEAR)


# ------------------------- GROUP LOGIN -------------------------
@app.route("/group", methods=["GET", "POST"])
def group_login():
    error = None
    if request.method == "POST":
        group_id = request.form.get("group_id").strip()
        password = request.form.get("password").strip()
        valid = False

        if os.path.isfile(GROUPS_FILE):
            with open(GROUPS_FILE, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["group_id"].strip() == group_id and row["password"].strip() == password:
                        valid = True
                        break

        if valid:
            session["group_id"] = group_id
            return redirect(url_for("view_group"))
        else:
            error = "Invalid Group ID or Password"

    return render_template("group_login.html", error=error)


# ------------------------- VIEW GROUP DATA -------------------------
@app.route("/view_group")
def view_group():
    if "group_id" not in session:
        return redirect(url_for("group_login"))

    rows = []
    if os.path.isfile(DATA_FILE):
        with open(DATA_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["group_id"].strip() == session["group_id"]:
                    rows.append(row)

    return render_template("group.html", rows=rows, group_id=session["group_id"])


# ------------------------- DOWNLOAD GROUP DATA -------------------------
@app.route("/download_group")
def download_group():
    if "group_id" not in session:
        return redirect(url_for("group_login"))

    filtered = []
    if os.path.isfile(DATA_FILE):
        with open(DATA_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["group_id"].strip() == session["group_id"]:
                    filtered.append(row)

    if not filtered:
        return "No data available", 404

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=filtered[0].keys())
    writer.writeheader()
    writer.writerows(filtered)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        as_attachment=True,
        download_name=f"{session['group_id']}_{CURRENT_YEAR}.csv"
    )


# ------------------------- MANAGE GROUPS -------------------------
@app.route("/manage_groups", methods=["GET", "POST"])
def manage_groups():
    error = None
    success = None

    if request.method == "POST":
        entered_admin = request.form.get("admin_password")
        new_group_id = request.form.get("group_id").strip()
        new_password = request.form.get("password").strip()

        if entered_admin != ADMIN_PASSWORD:
            error = "Invalid admin password!"
        elif not new_group_id or not new_password:
            error = "Provide both Group ID and Password."
        else:
            file_exists = os.path.isfile(GROUPS_FILE)
            with open(GROUPS_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["group_id", "password"])
                if not file_exists or os.stat(GROUPS_FILE).st_size == 0:
                    writer.writeheader()
                writer.writerow({"group_id": new_group_id, "password": new_password})
                success = f"Group {new_group_id} added successfully!"

    return render_template("manage_groups.html", error=error, success=success)


# ------------------------- ADMIN LOGIN -------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        entered = request.form.get("admin_password")
        if entered == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("view_archive"))
        else:
            error = "Invalid admin password!"
    return render_template("admin_login.html", error=error)


# ------------------------- ADMIN LOGOUT -------------------------
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


# ------------------------- ARCHIVE CURRENT DATA -------------------------
@app.route("/admin/archive", methods=["GET", "POST"])
def archive_data():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    msg = None
    if request.method == "POST":
        if not os.path.isfile(DATA_FILE):
            msg = "No data to archive"
        else:
            archive_name = f"{ARCHIVE_FOLDER}/observations_{CURRENT_YEAR.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            os.rename(DATA_FILE, archive_name)
            msg = f"Data archived successfully as {archive_name}"
    return render_template("archive.html", message=msg)


# ------------------------- VIEW ARCHIVE FILES -------------------------
@app.route("/admin/view_archive")
def view_archive():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    files = sorted(os.listdir(ARCHIVE_FOLDER), reverse=True)
    return render_template("archive.html", files=files)


# ------------------------- DOWNLOAD ARCHIVE FILE -------------------------
@app.route("/admin/download_archive/<filename>")
def download_archive(filename):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    path = os.path.join(ARCHIVE_FOLDER, filename)
    if os.path.isfile(path):
        return send_file(path, as_attachment=True)
    return "File not found", 404


# ------------------------- HELP -------------------------
@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/logout")
def group_logout():
    session.pop("group_id", None)
    return redirect(url_for("index"))

@app.route('/dashboard')
def go_to_stats():
    # Redirect the user to the Streamlit port
    return redirect("https://milton-develop-ecofield-eco-stats-6k4jtq.streamlit.app/")

if __name__ == '__main__':
    app.run(debug=True, port=5000)


# ------------------------- RUN APP -------------------------
if __name__ == "__main__":
    # Change port to 5002
    app.run(host="0.0.0.0", debug=True) 
