# AllerGraph — Food Allergy & Ingredient Intelligence Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.20+-008CC1.svg)](https://neo4j.com/)
[![Tests Passing](https://img.shields.io/badge/tests-40%20passed-brightgreen.svg)]()

> **AllerGraph** is an enterprise-grade, graph-powered food allergy screening and culinary transparency intelligence platform. Built with **FastAPI**, **Neo4j**, **Jinja2**, **Cytoscape.js**, and **Chart.js**, it maps multi-hop supply chains from partner restaurants down to molecular allergens and precautionary cross-contact risks.

---

## Architecture & Graph Schema

### 1. Graph Data Model
```
(Restaurant) ──[:OFFERS]──> (Dish) ──[:CONTAINS]──> (Ingredient) ──[:CONTAINS_ALLERGEN]──> (Allergen)
                              │                                                              ▲
                              └──────────────────[:MAY_CONTAIN]──────────────────────────────┘
                                          (Precautionary cross-contact)

(User) ──[:PERFORMED]──> (ActivityLog)
```

- **`(Restaurant)`**: Culinary establishments with city, address, phone, and cuisine metadata.
- **`(Dish)`**: Menu offerings with categories, pricing, dietary flags (`vegetarian`, `vegan`), and data completeness status (`COMPLETE`, `PARTIAL`, `UNVERIFIED`).
- **`(Ingredient)`**: Distinct food items and components with supplier references and verification status (`VERIFIED`, `IN_REVIEW`, `UNVERIFIED`).
- **`(Allergen)`**: FDA Big-9 and international major allergens (`Peanuts`, `Tree Nuts`, `Milk / Dairy`, `Eggs`, `Wheat / Gluten`, `Soy`, `Fish`, `Shellfish`, `Sesame`).
- **`(User)`**: System accounts with role-based access control (`ADMIN`, `EDITOR`, `VIEWER`).
- **`(ActivityLog)`**: Immutable audit entries tracking mutations across restaurants, dishes, ingredients, allergens, and roles.

---

## Key Features

1. **Graph-Powered Multi-Hop Allergy Checker**:
   - Traverses `(Restaurant)-[:OFFERS]->(Dish)-[:CONTAINS]->(Ingredient)-[:CONTAINS_ALLERGEN]->(Allergen)` as well as precautionary `[:MAY_CONTAIN]` relationships.
   - Dual screening modes: **ANY** (flags any dish with at least one target allergen) vs. **ALL** (flags dishes containing every specified allergen).
   - Distinguishes direct recipe ingredients from supplier cross-contact warnings.
   - Flags dishes with incomplete or unverified ingredient profiles.

2. **Interactive Cytoscape.js Knowledge Graph Explorer**:
   - Force-directed physics layout (`cose`).
   - Node search, category filtering (Restaurants, Dishes, Ingredients, Allergens).
   - Click-to-inspect sidebar showing degree, status, and related neighbors.
   - Dynamic neighborhood expansion (`/api/graph/expand/{id}`).
   - Allergen path tracing highlighting supply chain routes to allergen targets.

3. **Role-Based Access Control (RBAC)**:
   - **`ADMIN`**: Full platform control, user management, role elevation, audit logs, analytical reports, CSV exports.
   - **`EDITOR`**: Menu operations, dish curation, ingredient verification, allergen tagging.
   - **`VIEWER`**: Consumer dashboard, menu browsing, allergy screening, personal profile management.

4. **Security & Data Integrity**:
   - Password hashing with **Argon2id** (`pwdlib[argon2]`).
   - Strict password complexity enforcement (min 8 chars, uppercase, lowercase, digit).
   - Cryptographic session-bound CSRF protection (`itsdangerous`).
   - In-memory IP and account lockout rate limiter (`LoginRateLimiter`).
   - 100% parameterized Cypher queries preventing Cypher injection.
   - Non-destructive idempotent data seeding using `MERGE` and UUIDs.

5. **Analytics & Audit Reporting**:
   - Visual charts powered by **Chart.js** (allergen frequency, restaurant dish distribution, verification breakdowns).
   - Diagnostic reports for unverified ingredients and incomplete menu items.
   - Downloadable CSV data exports.

---

## Linux Setup & Installation Guide

### Prerequisites
- **Linux OS** (Ubuntu 20.04+, Debian 11+, Fedora 38+, Arch Linux, or compatible)
- **Python 3.11+** (Python 3.11, 3.12, or 3.13)
- **Neo4j 5.x** running locally or via Docker (`bolt://localhost:7687`)

### 1. Clone Repository & Navigate
```bash
git clone https://github.com/sabaris18/OSS.git
cd OSS/allergraph
```

### 2. Configure Python Virtual Environment
```bash
# Create virtual environment
python3 -m venv ../venv

# Activate virtual environment
source ../venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration (`.env`)
Create your `.env` file from the provided example:
```bash
cp .env.example .env
```
Edit `.env` with your Neo4j credentials and secret keys:
```ini
APP_NAME=AllerGraph
APP_ENV=development
DEBUG=True
HOST=0.0.0.0
PORT=8000

# Neo4j Database Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=ChangeThis_StrongPassword
NEO4J_DATABASE=neo4j

# Cryptographic Secrets (Generate with `openssl rand -hex 32`)
SESSION_SECRET=b63c78864d4a36f5e71f98d79a29e46950e3ce18be60ba09ef7ef2df9b7642ea
CSRF_SECRET=2dc0fdbbf861d9162986c7cf65ad9c5b2ea4da9e97c11f71df427e0ee2c12290
```

### 4. Initialize Database Schema & Constraints
Run the idempotent schema initializer to create uniqueness constraints and search indexes in Neo4j:
```bash
python scripts/initialize_schema.py
```

### 5. Seed Demonstration Data
Seed 9 standard allergens, 4 curated partner restaurants, 28 ingredients, and 16 dishes:
```bash
python scripts/seed_demo_data.py
```

### 6. Create or Verify Administrator Account
```bash
python scripts/create_admin.py admin@allergraph.local "Admin User" "AllerGraph2026!"
```

### 7. Run the Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Access the application in your browser at:
**[http://localhost:8000](http://localhost:8000)**

---

## Demonstration Credentials

| Role | Email Address | Password | Privileges |
| :--- | :--- | :--- | :--- |
| **ADMIN** | `admin@allergraph.local` | `AllerGraph2026!` | Full Admin, Users, Reports, Logs |
| **EDITOR** | `editor@allergraph.local` | `AllerGraph2026!` | CRUD Dishes, Ingredients, Restaurants |
| **VIEWER** | `viewer@allergraph.local` | `AllerGraph2026!` | Browse Menus, Run Allergy Checker |

---

## Running the Automated Test Suite

The platform includes a comprehensive automated test suite with 40 pytest tests covering security, database repositories, authentication, RBAC, graph APIs, allergy screening, and CRUD operations.

```bash
# Run the entire test suite
pytest tests/ -v

# Run individual test modules
pytest tests/test_security.py -v
pytest tests/test_repositories.py -v
pytest tests/test_auth_routes.py -v
pytest tests/test_rbac_routes.py -v
pytest tests/test_graph_api.py -v
pytest tests/test_allergy_checker.py -v
pytest tests/test_crud_operations.py -v
pytest tests/test_public_routes.py -v
```

---

## Application Route Map

### Public Routes
- `GET /` — Responsive Landing Page with platform overview & search
- `GET /about` — Educational platform mission & methodology
- `GET /contact` — Public inquiry and support submission form
- `GET /privacy` — Data privacy statement & medical safety disclaimer
- `GET /search` — Global full-text search across all entities
- `GET /api/health` — System status & Neo4j connectivity diagnostic

### Authentication & Account
- `GET /login` / `POST /login` — Secure login with rate-limiting & CSRF verification
- `GET /register` / `POST /register` — Self-service viewer registration
- `GET /forgot-password` / `POST /forgot-password` — Password reset request
- `GET /logout` — Session termination
- `GET /profile` — Personal profile view & activity history
- `POST /profile/update-name` — Full name update
- `POST /profile/change-password` — Password rotation with Argon2 re-hashing

### Core Dashboards (Role-Tailored)
- `GET /dashboard` — Dynamic routing based on session role:
  - **ADMIN**: Platform graph KPIs, recent mutations, verification distribution, quick links
  - **EDITOR**: Actionable curation queue, incomplete dishes, unverified ingredients
  - **VIEWER**: Quick allergy screening tool, partner restaurant menu explorer

### Intelligence & Visualization
- `GET /allergy-checker` — Multi-allergen screening engine (GET query params or POST)
- `GET /api/allergy-checker` — JSON screening API for asynchronous integrations
- `GET /graph` — Interactive Cytoscape.js Graph Canvas
- `GET /api/graph/data` — JSON graph payload (nodes and edges)
- `GET /api/graph/expand/{node_id}` — Asynchronous neighborhood expansion API
- `GET /api/graph/paths` — Graph tracing route highlighting paths to allergens

### Data Management (CRUD)
- `GET /restaurants`, `GET /restaurants/new`, `GET /restaurants/{id}`, `GET /restaurants/{id}/edit`
- `GET /dishes`, `GET /dishes/new`, `GET /dishes/{id}`, `GET /dishes/{id}/edit`
- `GET /ingredients`, `GET /ingredients/new`, `GET /ingredients/{id}`, `GET /ingredients/{id}/edit`
- `GET /allergens`, `GET /allergens/new`, `GET /allergens/{id}`, `GET /allergens/{id}/edit`

### Administration & Auditing
- `GET /reports` — Analytical charts (Chart.js), data quality audits
- `GET /reports/export/{type}` — CSV export for audits
- `GET /users` — User management (role changes, active status toggling)
- `GET /activity-logs` — Immutable audit log trail with pagination & CSV export

---

## Safety & Medical Notice

> **IMPORTANT DISCLAIMER**: AllerGraph is an educational and informational platform designed for dietary transparency and academic research. It **does not provide medical advice, diagnosis, or absolute food safety guarantees**. Kitchen preparation environments may experience cross-contact or unrecorded ingredient changes. Individuals with severe or anaphylactic food allergies must always consult restaurant culinary staff and medical professionals directly.

---

## Academic Information

- **Project Title**: AllerGraph — Food Allergy and Ingredient Intelligence Platform
- **Project Type**: Full-Stack Capstone / Mini-Project
- **Backend**: FastAPI (Python 3.11+)
- **Database**: Neo4j Graph Database
- **Frontend**: Jinja2, Vanilla CSS3 Design System, Cytoscape.js, Chart.js, Lucide Icons
- **License**: MIT
