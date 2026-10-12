# Student Management System

![CI-CD](https://github.com/JaiSachdevaa/student-management-system/actions/workflows/ci-cd.yml/badge.svg)

A web app for managing student records, packaged with Docker and delivered through an automated CI/CD pipeline. Every push is formatted, linted, tested, built into a container, health checked and deployed.



## Features

- Add, edit and delete students with validation and duplicate email checks
- Search by name, email or course
- Filter by course and year, and sort by newest, oldest, name, course or year
- Pagination, 8 students per page
- Dashboard cards and bar charts: total students, courses, top course, average year, students by course and by year
- CSV export of the current filtered list, protected against spreadsheet formula injection
- One click demo data loader
- Dark mode and a responsive layout that works on phones
- REST API with a built-in docs page at `/api-docs`
- Health endpoint at `/health` used by Docker and the pipeline

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Flask, Flask-SQLAlchemy |
| Database | SQLite by default, PostgreSQL supported through `DATABASE_URL` |
| Frontend | Jinja2 templates, HTML, CSS, a little JavaScript |
| Production server | gunicorn |
| Containers | Docker |
| CI/CD | GitHub Actions, GitHub Container Registry, Render |
| Testing | pytest, pytest-cov |
| Code quality | black, flake8 |

## Project structure

```
student-management-system/
├── .github/workflows/ci-cd.yml   CI/CD pipeline
├── templates/
│   ├── base.html                 shared layout, styles, dark mode
│   ├── index.html                dashboard
│   ├── edit.html                 edit student page
│   └── api.html                  API documentation page
├── tests/test_app.py             26 automated tests
├── app.py                        Flask application
├── Dockerfile                    container recipe
├── .dockerignore
├── requirements.txt              runtime dependencies
├── requirements-dev.txt          test and lint dependencies
└── setup.cfg                     flake8 and pytest settings
```

## Run locally

Windows PowerShell:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
python app.py
```

Mac or Linux:

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
python app.py
```

Open http://localhost:8000

## Run with Docker

Build the image:

```
docker build -t sms:latest .
```

Start the container. The volume keeps the database when the container is stopped or deleted:

```
docker run -d --name sms -p 8000:8000 -v sms-data:/app/instance sms:latest
```

Open http://localhost:8000

Useful commands:

| Command | What it does |
|---|---|
| `docker ps` | Show running containers and their health |
| `docker logs sms` | Show the app logs |
| `docker stop sms` | Stop the container |
| `docker start sms` | Start it again, data is kept |
| `docker rm -f sms` | Delete the container, the volume stays |

### How the Dockerfile works

- Starts from `python:3.12-slim`, a small official Python image
- Installs dependencies before copying the code, so Docker reuses the cached layer and rebuilds are fast
- Creates and uses a non-root user for safety
- Defines a `HEALTHCHECK` that calls `/health` every 30 seconds
- Starts the app with gunicorn instead of Flask's development server

## Run the tests

```
pytest --cov=app
```

The pipeline requires at least 80 percent coverage. The current suite has 26 tests and about 98 percent coverage.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/students` | List all students |
| POST | `/api/students` | Create a student |
| GET | `/api/students/<id>` | Get one student |
| PUT | `/api/students/<id>` | Update a student |
| DELETE | `/api/students/<id>` | Delete a student |
| GET | `/export.csv` | Download students as CSV |

Example request body:

```json
{
  "name": "Asha Verma",
  "email": "asha@example.com",
  "course": "CSE",
  "year": 2
}
```

Status codes: 201 created, 400 invalid data, 404 not found, 409 email already exists.

## CI/CD pipeline

The workflow in `.github/workflows/ci-cd.yml` runs on every pull request and every push to `main`.

| Job | What it does |
|---|---|
| test | Installs dependencies, checks formatting with black, lints with flake8, runs the tests with a coverage gate |
| docker | Builds the image, starts it and calls `/health` as a smoke test, then publishes it to GitHub Container Registry on pushes to `main` |
| deploy | Triggers a Render deploy through a deploy hook, then polls `/health` on the live site |

If any step fails, the pipeline stops and nothing is deployed.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `PORT` | Port the app listens on | `8000` |
| `DATABASE_URL` | Database connection string | `sqlite:///students.db` |
| `SECRET_KEY` | Secret used to sign sessions and flash messages | demo value, set your own in production |


## Limitations and future work

- No login system yet, so anyone with the URL can edit data
- SQLite data on free hosting resets when the service restarts, so a managed PostgreSQL database is the next step
- Single container with no load balancing or auto scaling
- Possible next steps: authentication, HTTPS only access, monitoring, Kubernetes

## Author

Built by Jai ([@JaiSachdevaa](https://github.com/JaiSachdevaa)).
