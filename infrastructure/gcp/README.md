# Google Cloud Platform Deployment

This directory contains the Terraform configuration (`main.tf`) and Kubernetes manifests required to deploy the Ostrich infrastructure to Google Cloud Platform. 

The deployment of the architecture follows a strict 6-phase rollout to ensure networking, state, and security boundaries are properly initialized before compute workloads are provisioned.

---

## The 6 Phases of Deployment

### Phase 1: Foundation & API Enablement
Before any physical resources are provisioned, Terraform enables the necessary Google Cloud APIs on the target project. This includes the Compute Engine API, Kubernetes Engine API, Memorystore Redis API, Service Networking API, and Artifact Registry API. This phase ensures the project is legally and technically capable of hosting the subsequent resources.

### Phase 2: Network Infrastructure
A secure Virtual Private Cloud (VPC) named `ostrich-vpc` is created. Crucially, this phase establishes **Private Services Access**. Terraform allocates an internal IP block (`ostrich-redis-peering-alloc`) and creates a VPC peering connection directly into Google's managed services network. This guarantees that our databases will never be exposed to the public internet.

### Phase 3: Data & State Persistence
With the private network established, the stateful services are provisioned.
- **Memorystore for Redis**: A 1GB Basic tier Redis instance is spun up to handle high-throughput Pub/Sub messaging between the Control Plane and the Sandbox pods. It is attached exclusively to the internal VPC.
- **Cloud SQL & Firebase Data Connect**: The PostgreSQL instance is provisioned to hold permanent user and workspace data, interfaced securely via Firebase.

### Phase 4: Compute Orchestration
**GKE Autopilot** is deployed as the execution arena (`ostrich-cluster`). We use Autopilot to eliminate node management overhead—Google automatically provisions and scales the underlying compute instances based strictly on the pod resource requests we define. Concurrently, the **Artifact Registry** (`ostrich-repo`) is created to securely house our proprietary Docker images.

### Phase 5: Identity & Security Boundaries
Security is woven into the infrastructure using **Workload Identity**. 
Terraform creates a dedicated Google Cloud Service Account (`sandbox-agent-sa`) and grants it `roles/storage.objectAdmin` on the `ostrich-agent-workspaces` Cloud Storage bucket. It then binds this GCP Service Account to a Kubernetes Service Account in the `sandbox-chat` namespace. This cryptographic tie allows our ephemeral sandbox pods to authenticate to Cloud Storage password-lessly, eliminating the need to mount risky JSON keys.

### Phase 6: Application Deployment
With the infrastructure cemented, the actual application code is deployed:
1. **Service Mesh**: Istio is installed on GKE, and the Envoy egress network policies (`sandbox-network-policy.yaml`) are applied to lock down outbound internet access.
2. **AI Gateway**: The LiteLLM proxy is deployed to the `ai-gateway` namespace, acting as the Zero-Trust broker to Google Generative AI.
3. **Control Plane**: The FastAPI backend is packaged and deployed to **Google Cloud Run**, attached to the Serverless VPC Connector so it can speak privately to Redis.

---

## Usage

To execute the deployment, ensure your Google Cloud CLI is authenticated and billing is enabled on your project (`var.project_id`).

```bash
# Initialize the Terraform state
terraform init

# Review the deployment plan
terraform plan

# Execute the 6 phases
terraform apply
```
