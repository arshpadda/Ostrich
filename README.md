# Ostrich Monorepo

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
