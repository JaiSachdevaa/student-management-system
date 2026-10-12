import pytest

from app import create_app, db


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        }
    )
    with app.test_client() as test_client:
        yield test_client
    with app.app_context():
        db.drop_all()


def sample(**overrides):
    data = {
        "name": "Asha Verma",
        "email": "asha@example.com",
        "course": "CSE",
        "year": 2,
    }
    data.update(overrides)
    return data


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Student Management System" in response.data
    assert b"No students yet" in response.data


def test_create_and_list_student(client):
    created = client.post("/api/students", json=sample())
    assert created.status_code == 201
    assert created.get_json()["name"] == "Asha Verma"

    listing = client.get("/api/students")
    assert listing.status_code == 200
    assert len(listing.get_json()) == 1


def test_get_single_student(client):
    student_id = client.post("/api/students", json=sample()).get_json()["id"]
    response = client.get(f"/api/students/{student_id}")
    assert response.status_code == 200
    assert response.get_json()["email"] == "asha@example.com"


def test_get_missing_student(client):
    assert client.get("/api/students/999").status_code == 404


def test_duplicate_email_rejected(client):
    client.post("/api/students", json=sample())
    response = client.post("/api/students", json=sample(name="Someone Else"))
    assert response.status_code == 409


def test_invalid_data_rejected(client):
    assert client.post("/api/students", json=sample(email="bad")).status_code == 400
    assert client.post("/api/students", json=sample(name="")).status_code == 400
    assert client.post("/api/students", json=sample(year=99)).status_code == 400


def test_update_student(client):
    student_id = client.post("/api/students", json=sample()).get_json()["id"]
    response = client.put(
        f"/api/students/{student_id}", json=sample(course="ECE", year=3)
    )
    assert response.status_code == 200
    assert response.get_json()["course"] == "ECE"
    assert response.get_json()["year"] == 3


def test_api_update_errors(client):
    first = client.post("/api/students", json=sample()).get_json()["id"]
    client.post("/api/students", json=sample(name="Other", email="other@example.com"))
    assert client.put("/api/students/999", json=sample()).status_code == 404
    assert (
        client.put(f"/api/students/{first}", json=sample(email="x")).status_code == 400
    )
    clash = client.put(f"/api/students/{first}", json=sample(email="other@example.com"))
    assert clash.status_code == 409


def test_delete_student(client):
    student_id = client.post("/api/students", json=sample()).get_json()["id"]
    assert client.delete(f"/api/students/{student_id}").status_code == 204
    assert client.get(f"/api/students/{student_id}").status_code == 404
    assert client.delete(f"/api/students/{student_id}").status_code == 404


def test_form_add_and_delete(client):
    response = client.post("/add", data=sample(), follow_redirects=True)
    assert response.status_code == 200
    assert b"asha@example.com" in response.data
    assert b"Added Asha Verma" in response.data

    student_id = client.get("/api/students").get_json()[0]["id"]
    response = client.post(f"/delete/{student_id}", follow_redirects=True)
    assert b"asha@example.com" not in response.data
    assert b"Student removed" in response.data


def test_form_rejects_bad_input(client):
    response = client.post("/add", data=sample(email="nope"))
    assert response.status_code == 400
    assert b"Please fill every field correctly." in response.data


def test_form_rejects_duplicate_email(client):
    client.post("/add", data=sample())
    response = client.post("/add", data=sample(name="Copy"))
    assert response.status_code == 409
    assert b"already registered" in response.data


def test_delete_missing_student_shows_message(client):
    response = client.post("/delete/999", follow_redirects=True)
    assert response.status_code == 200
    assert b"Student not found" in response.data


def test_search_filters_results(client):
    client.post("/api/students", json=sample())
    client.post("/api/students", json=sample(name="Bob Stone", email="bob@example.com"))
    response = client.get("/?q=asha")
    assert b"asha@example.com" in response.data
    assert b"bob@example.com" not in response.data


def test_course_and_year_filters(client):
    client.post("/api/students", json=sample(course="CSE", year=1))
    client.post(
        "/api/students",
        json=sample(name="Bob Stone", email="bob@example.com", course="ECE", year=3),
    )
    by_course = client.get("/?course=ECE")
    assert b"bob@example.com" in by_course.data
    assert b"asha@example.com" not in by_course.data
    by_year = client.get("/?year=1")
    assert b"asha@example.com" in by_year.data
    assert b"bob@example.com" not in by_year.data


def test_no_matches_message(client):
    client.post("/api/students", json=sample())
    response = client.get("/?q=zzzz")
    assert b"No students match your filters" in response.data


def test_sorting_by_name(client):
    client.post("/api/students", json=sample(name="Zed Zeta", email="zed@example.com"))
    client.post("/api/students", json=sample(name="Amy Adams", email="amy@example.com"))
    response = client.get("/?sort=name")
    assert response.data.index(b"Amy Adams") < response.data.index(b"Zed Zeta")
    response = client.get("/?sort=bogus")
    assert response.status_code == 200


def test_pagination(client):
    for number in range(10):
        client.post(
            "/api/students",
            json=sample(name=f"Person {number}", email=f"p{number}@example.com"),
        )
    first = client.get("/")
    assert b"Page 1 of 2" in first.data
    assert b"Next" in first.data
    second = client.get("/?page=2")
    assert b"Page 2 of 2" in second.data
    assert b"Previous" in second.data


def test_stats_shown(client):
    client.post("/api/students", json=sample(course="CSE", year=2))
    client.post("/api/students", json=sample(name="B", email="b@example.com", year=4))
    response = client.get("/")
    assert b"Total students" in response.data
    assert b"Students by course" in response.data
    assert b"Year 4" in response.data


def test_edit_page_and_update(client):
    client.post("/api/students", json=sample())
    page = client.get("/edit/1")
    assert page.status_code == 200
    assert b"asha@example.com" in page.data

    updated = client.post(
        "/edit/1", data=sample(course="ECE", year=3), follow_redirects=True
    )
    assert updated.status_code == 200
    assert b"Updated Asha Verma" in updated.data
    assert client.get("/api/students/1").get_json()["course"] == "ECE"


def test_edit_errors(client):
    client.post("/api/students", json=sample())
    client.post("/api/students", json=sample(name="Other", email="other@example.com"))
    invalid = client.post("/edit/1", data=sample(email="nope"))
    assert invalid.status_code == 400
    clash = client.post("/edit/1", data=sample(email="other@example.com"))
    assert clash.status_code == 409
    missing = client.get("/edit/999", follow_redirects=True)
    assert b"Student not found" in missing.data


def test_export_csv(client):
    client.post("/api/students", json=sample())
    response = client.get("/export.csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    lines = response.get_data(as_text=True).strip().splitlines()
    assert lines[0] == "id,name,email,course,year"
    assert "Asha Verma" in lines[1]


def test_export_csv_blocks_formulas(client):
    client.post("/api/students", json=sample(name="=SUM(A1)"))
    text = client.get("/export.csv").get_data(as_text=True)
    assert "'=SUM(A1)" in text


def test_seed_demo_data(client):
    first = client.post("/seed", follow_redirects=True)
    assert b"Added 8 demo students" in first.data
    second = client.post("/seed", follow_redirects=True)
    assert b"Demo students already exist" in second.data
    assert len(client.get("/api/students").get_json()) == 8


def test_api_docs_page(client):
    response = client.get("/api-docs")
    assert response.status_code == 200
    assert b"/api/students" in response.data