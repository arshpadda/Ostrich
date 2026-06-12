# Ostrich Monorepo
![alt text](image.png)
Welcome to the **Ostrich** monorepo. This repository contains the application packages and the cloud infrastructure deployment setup.

## Repository Structure

```text
Ostrich/
├── .gitignore             # Git ignore patterns (Python, Terraform, etc.)
├── GEMINI.MD              # Gemini API integration and AI agent guidelines
├── README.md              # Root documentation
├── package/               # Application codebase
│   ├── pyproject.toml     # Package configuration & dependencies
│   ├── src/               # Application source code
│   │   ├── __init__.py
│   │   └── main.py
│   └── tests/             # Package test suite
├── infrastructure/        # Infrastructure as Code (IaC)
│   ├── README.md          # Infrastructure overview
│   ├── aws/               # AWS infrastructure deployment placeholders
│   │   └── main.tf
│   └── gcp/               # GCP infrastructure deployment placeholders
│       └── main.tf
└── system_design/         # High-level system design documents and diagrams
    └── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended)
- [Terraform](https://www.terraform.io/) (for infrastructure management)

### Local Application Setup

To install and run the application locally:

```bash
cd package
# Sync and create virtual environment
uv sync

# Run the application
uv run python -m src.main
```

### Infrastructure Management

Refer to the documentation in [infrastructure/README.md](infrastructure/README.md) for details on provisioning cloud resources via Terraform.

## API Documentation

The control plane exposes the following API endpoints. All `/users` endpoints require a valid **Firebase ID Token** passed via the `Authorization: Bearer <TOKEN>` header.

### Health Check
- `GET /health`: Verify that the service is running.

### Users (Authentication Required)
- `POST /users/`: Create a new PostgreSQL user profile. The email address will be safely extracted from the Firebase ID Token and linked via the token's `uid`.
- `GET /users/me`: Retrieve the profile of the currently authenticated user.
- `GET /users/{user_id}`: Retrieve a specific user profile. Users can only fetch their own records.
- `PUT /users/{user_id}`: Update a user profile (e.g., `first_name`, `last_name`). Users can only update their own records.
- `DELETE /users/{user_id}`: Delete a user profile. Users can only delete their own records.

**Note:** You can explore and test the interactive API documentation by running the app and navigating to `http://localhost:8000/docs` (Swagger UI).
