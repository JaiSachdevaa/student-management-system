import csv
import io
import os

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_

db = SQLAlchemy()

PER_PAGE = 8


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    course = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False, default=1)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "course": self.course,
            "year": self.year,
        }


SORT_LABELS = {
    "newest": "Newest first",
    "oldest": "Oldest first",
    "name": "Name A to Z",
    "course": "Course",
    "year": "Year",
}

SORT_COLUMNS = {
    "newest": Student.id.desc(),
    "oldest": Student.id.asc(),
    "name": func.lower(Student.name),
    "course": Student.course,
    "year": Student.year,
}

DEMO_STUDENTS = [
    {"name": "Aarav Sharma", "email": "aarav@example.com", "course": "CSE", "year": 3},
    {"name": "Diya Mehta", "email": "diya@example.com", "course": "CSE", "year": 2},
    {"name": "Rohan Gupta", "email": "rohan@example.com", "course": "ECE", "year": 4},
    {"name": "Ananya Singh", "email": "ananya@example.com", "course": "IT", "year": 1},
    {"name": "Kabir Verma", "email": "kabir@example.com", "course": "ME", "year": 2},
    {"name": "Isha Reddy", "email": "isha@example.com", "course": "ECE", "year": 3},
    {"name": "Vihaan Joshi", "email": "vihaan@example.com", "course": "IT", "year": 4},
    {"name": "Meera Nair", "email": "meera@example.com", "course": "CSE", "year": 1},
]


def clean_payload(data):
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    course = (data.get("course") or "").strip()
    try:
        year = int(data.get("year") or 1)
    except (TypeError, ValueError):
        return None
    if not name or not email or "@" not in email or not course:
        return None
    if year < 1 or year > 6:
        return None
    return {"name": name, "email": email, "course": course, "year": year}


def filtered_query(args):
    query = Student.query
    search = (args.get("q") or "").strip()
    course = (args.get("course") or "").strip()
    year = args.get("year", type=int)
    sort = args.get("sort") or "newest"
    if sort not in SORT_COLUMNS:
        sort = "newest"
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Student.name.ilike(like),
                Student.email.ilike(like),
                Student.course.ilike(like),
            )
        )
    if course:
        query = query.filter(Student.course == course)
    if year:
        query = query.filter(Student.year == year)
    filters = {"q": search, "course": course, "year": year or "", "sort": sort}
    return query.order_by(SORT_COLUMNS[sort]), filters


def active_filters(filters):
    active = {key: value for key, value in filters.items() if value != ""}
    if active.get("sort") == "newest":
        del active["sort"]
    return active


def build_stats():
    total = Student.query.count()
    by_course = (
        db.session.query(Student.course, func.count(Student.id))
        .group_by(Student.course)
        .order_by(func.count(Student.id).desc(), Student.course)
        .all()
    )
    by_year = (
        db.session.query(Student.year, func.count(Student.id))
        .group_by(Student.year)
        .order_by(Student.year)
        .all()
    )
    average = db.session.query(func.avg(Student.year)).scalar()
    course_max = max([count for _, count in by_course], default=1)
    year_max = max([count for _, count in by_year], default=1)
    return {
        "total": total,
        "courses": len(by_course),
        "top_course": by_course[0][0] if by_course else "None",
        "avg_year": round(float(average), 1) if average else 0,
        "by_course": [
            {"label": label, "count": count, "pct": round(count * 100 / course_max)}
            for label, count in by_course[:6]
        ],
        "by_year": [
            {
                "label": f"Year {label}",
                "count": count,
                "pct": round(count * 100 / year_max),
            }
            for label, count in by_year
        ],
    }


def safe_cell(value):
    text = str(value)
    if text and text[0] in "=+-@":
        return "'" + text
    return text


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///students.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if test_config:
        app.config.update(test_config)

    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("postgres://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = uri.replace(
            "postgres://", "postgresql://", 1
        )

    db.init_app(app)

    with app.app_context():
        db.create_all()

    def render_index(status=200, error=None):
        query, filters = filtered_query(request.args)
        page = request.args.get("page", 1, type=int)
        pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)
        courses = [
            row[0]
            for row in db.session.query(Student.course)
            .distinct()
            .order_by(Student.course)
            .all()
        ]
        page_html = render_template(
            "index.html",
            pagination=pagination,
            students=pagination.items,
            filters=filters,
            active=active_filters(filters),
            courses=courses,
            stats=build_stats(),
            sort_labels=SORT_LABELS,
            error=error,
        )
        return page_html, status

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.route("/")
    def index():
        return render_index()

    @app.route("/add", methods=["POST"])
    def add_student():
        payload = clean_payload(request.form)
        if payload is None:
            return render_index(400, "Please fill every field correctly.")
        if Student.query.filter_by(email=payload["email"]).first():
            return render_index(409, "That email is already registered.")
        db.session.add(Student(**payload))
        db.session.commit()
        flash(f"Added {payload['name']}", "success")
        return redirect(url_for("index"))

    @app.route("/edit/<int:student_id>", methods=["GET", "POST"])
    def edit_student(student_id):
        student = db.session.get(Student, student_id)
        if student is None:
            flash("Student not found", "error")
            return redirect(url_for("index"))
        if request.method == "POST":
            payload = clean_payload(request.form)
            error = None
            status = 400
            if payload is None:
                error = "Please fill every field correctly."
            else:
                clash = Student.query.filter_by(email=payload["email"]).first()
                if clash and clash.id != student.id:
                    error = "That email belongs to another student."
                    status = 409
            if error:
                page_html = render_template(
                    "edit.html", student=student, form=request.form, error=error
                )
                return page_html, status
            for key, value in payload.items():
                setattr(student, key, value)
            db.session.commit()
            flash(f"Updated {student.name}", "success")
            return redirect(url_for("index"))
        return render_template(
            "edit.html", student=student, form=student.to_dict(), error=None
        )

    @app.route("/delete/<int:student_id>", methods=["POST"])
    def delete_student(student_id):
        student = db.session.get(Student, student_id)
        if student is None:
            flash("Student not found", "error")
            return redirect(url_for("index"))
        db.session.delete(student)
        db.session.commit()
        flash("Student removed", "info")
        return redirect(url_for("index"))

    @app.route("/seed", methods=["POST"])
    def seed():
        added = 0
        for item in DEMO_STUDENTS:
            if not Student.query.filter_by(email=item["email"]).first():
                db.session.add(Student(**item))
                added += 1
        db.session.commit()
        if added:
            flash(f"Added {added} demo students", "success")
        else:
            flash("Demo students already exist", "info")
        return redirect(url_for("index"))

    @app.route("/export.csv")
    def export_csv():
        query, _ = filtered_query(request.args)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "name", "email", "course", "year"])
        for student in query.all():
            writer.writerow(
                [
                    student.id,
                    safe_cell(student.name),
                    safe_cell(student.email),
                    safe_cell(student.course),
                    student.year,
                ]
            )
        return Response(
            buffer.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=students.csv"},
        )

    @app.route("/api-docs")
    def api_docs():
        return render_template("api.html")

    @app.route("/api/students", methods=["GET"])
    def api_list():
        students = Student.query.order_by(Student.id).all()
        return jsonify([s.to_dict() for s in students])

    @app.route("/api/students", methods=["POST"])
    def api_create():
        payload = clean_payload(request.get_json(silent=True) or {})
        if payload is None:
            return jsonify(error="invalid data"), 400
        if Student.query.filter_by(email=payload["email"]).first():
            return jsonify(error="email already exists"), 409
        student = Student(**payload)
        db.session.add(student)
        db.session.commit()
        return jsonify(student.to_dict()), 201

    @app.route("/api/students/<int:student_id>", methods=["GET"])
    def api_get(student_id):
        student = db.session.get(Student, student_id)
        if student is None:
            return jsonify(error="not found"), 404
        return jsonify(student.to_dict())

    @app.route("/api/students/<int:student_id>", methods=["PUT"])
    def api_update(student_id):
        student = db.session.get(Student, student_id)
        if student is None:
            return jsonify(error="not found"), 404
        payload = clean_payload(request.get_json(silent=True) or {})
        if payload is None:
            return jsonify(error="invalid data"), 400
        clash = Student.query.filter_by(email=payload["email"]).first()
        if clash and clash.id != student.id:
            return jsonify(error="email already exists"), 409
        for key, value in payload.items():
            setattr(student, key, value)
        db.session.commit()
        return jsonify(student.to_dict())

    @app.route("/api/students/<int:student_id>", methods=["DELETE"])
    def api_delete(student_id):
        student = db.session.get(Student, student_id)
        if student is None:
            return jsonify(error="not found"), 404
        db.session.delete(student)
        db.session.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
