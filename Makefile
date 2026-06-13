# Makefile for Ostrich deployment and local management

# Load environment variables from .env file if it exists
-include .env

# Deployment Variables
PROJECT_ID ?= ostr-499118
REGION ?= us-central1
SERVICE_NAME ?= ostrich-controlplane

# Database Variables
INSTANCE_NAME ?= my-postgres-instance
DB_USER ?= postgres
DB_PASSWORD ?= postgres
DB_NAME ?= ostrich

# Construct the Cloud SQL connection string and socket name
CLOUDSQL_CONNECTION_NAME = $(PROJECT_ID):$(REGION):$(INSTANCE_NAME)
DATABASE_URL = "postgres://$(DB_USER):$(DB_PASSWORD)@/$(DB_NAME)?host=/cloudsql/$(CLOUDSQL_CONNECTION_NAME)"

.PHONY: deploy help

help:
	@echo "Available commands:"
	@echo "  make deploy  - Deploys the controlplane to GCP Cloud Run"

deploy:
	@echo "Deploying $(SERVICE_NAME) to Cloud Run in $(PROJECT_ID)..."
	gcloud run deploy $(SERVICE_NAME) \
		--source ./package \
		--region $(REGION) \
		--project $(PROJECT_ID) \
		--port 8000 \
		--add-cloudsql-instances="$(CLOUDSQL_CONNECTION_NAME)" \
		--set-env-vars="DATABASE_URL=$(DATABASE_URL)"
