# IoT-based Smart Parking System

A professional, production-level smart parking system using Python, Flask, SQLite, Bootstrap 5, REST API, MVC architecture, AJAX, simulated IoT sensors, authentication, role-based access, analytics, revenue charts, and logging.

## Folder Structure

- `app/` — Main application
  - `models/` — Database models (User, ParkingSlot, Vehicle, Log)
  - `controllers/` — Business logic and REST API endpoints
  - `views/` — View functions for rendering templates
  - `templates/` — HTML templates (Bootstrap 5)
  - `static/` — JS, CSS, Chart.js, AJAX
  - `logs/` — Log files
  - `__init__.py` — Flask app setup
- `config.py` — App configuration
- `run.py` — Entry point

## Features
- Authentication system (Admin/Operator)
- Role-based access control
- Parking analytics and revenue charts (Chart.js)
- REST API for IoT devices
- Real-time updates (AJAX)
- Automatic vehicle entry/exit simulation
- Logging system

## How to Run
1. Install dependencies: `pip install flask flask_sqlalchemy flask_login`
2. Run: `python run.py`
3. Access via browser: `http://localhost:5000`

## File Explanations
- `app/__init__.py`: Initializes Flask, DB, login, logging, loads controllers
- `config.py`: App and DB config
- `models/`: ORM models for users, parking, logs
- `controllers/`: API endpoints and business logic
- `views/`: View functions for pages
- `templates/`: HTML pages (Bootstrap 5)
- `static/`: JS (AJAX, Chart.js), CSS
- `logs/`: Log files
- `run.py`: App entry point

## To Do
- Implement controller/view logic
- Add IoT simulation
- Complete AJAX and Chart.js integration
- Finalize logging and analytics
