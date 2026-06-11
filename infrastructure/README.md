# Cloud Infrastructure

This directory houses the Infrastructure as Code (IaC) configurations for deploying the Ostrich platform.

We support deployments to both **Google Cloud Platform (GCP)** and **Amazon Web Services (AWS)** using Terraform.

## Directory Layout

```text
infrastructure/
├── README.md        # This documentation
├── aws/             # AWS-specific Terraform configurations
│   └── main.tf      # AWS entry point
└── gcp/             # GCP-specific Terraform configurations
    └── main.tf      # GCP entry point
```

## Getting Started

### Prerequisites

- [Terraform](https://www.terraform.io/) (v1.5.0+) installed locally.
- Access credentials configured for the target cloud provider.

### Initializing and Applying Configuration

To deploy using either GCP or AWS:

1. Navigate to the cloud provider's directory:
   ```bash
   cd gcp
   # or
   cd aws
   ```

2. Initialize Terraform:
   ```bash
   terraform init
   ```

3. Plan the changes:
   ```bash
   terraform plan
   ```

4. Apply the changes:
   ```bash
   terraform apply
   ```
