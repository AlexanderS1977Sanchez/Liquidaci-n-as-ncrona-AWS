# 🌾 AgroLink Andes: Serverless Asynchronous Payment Settlement Platform

An enterprise-grade, event-driven serverless architecture designed for high-throughput, fault-tolerant, and strictly idempotent asynchronous payment processing for agricultural producers in the Andean region.

![AWS Serverless](https://img.shields.io/badge/AWS-Serverless-orange?logo=amazon-aws&logoColor=white)
![Terraform IaC](https://img.shields.io/badge/Terraform-1.x-purple?logo=terraform&logoColor=white)
![Node.js Runtime](https://img.shields.io/badge/Node.js-18.x-green?logo=nodedotjs&logoColor=white)
![DynamoDB NoSQL](https://img.shields.io/badge/DynamoDB-On--Demand-blue?logo=amazondynamodb&logoColor=white)
![Build Status](https://img.shields.io/badge/Infrastructure-Passing-brightgreen)

---

## 📌 Table of Contents
- [Architecture Overview](#-architecture-overview)
- [Key Features & Design Patterns](#-key-features--design-patterns)
- [Tech Stack & IaC](#-tech-stack--iac)
- [Repository Structure](#-repository-structure)
- [Load Testing & Benchmark (1,000 Requests)](#-load-testing--benchmark-1000-requests)
- [Cost Analysis & Financial Estimation](#-cost-analysis--financial-estimation)
- [Getting Started](#-getting-started)
- [Author & License](#-author--license)

---

## 📐 Architecture Overview

```
                    ┌────────────────────────────────────────────────────────────────────────┐
                    │                      AWS Cloud Region (us-east-1)                      │
                    │                                                                        │
┌──────────────┐    │   ┌─────────────────┐       ┌─────────────────┐      ┌──────────────┐  │
│  API Client  │───>│──>│   API Gateway   │──────>│ Lambda Producer │─────>│  SQS Buffer  │  │
│  (REST API)  │<───│───│  (HTTP API v2)  │<──────│  (Ingestion)    │      │ (Main Queue) │  │
└──────────────┘    │   └─────────────────┘ 202   └─────────────────┘      └──────┬───────┘  │
   Payload          │                    Accepted                                 │          │
   Validation       │                                                             │ Event    │
                    │                                                             ▼ Source   │
                    │   ┌─────────────────┐       ┌─────────────────┐      ┌──────────────┐  │
                    │   │ DynamoDB Table  │<──────│ Lambda Consumer │<─────│ Lambda Poll  │  │
                    │   │  (Liquidaciones)│ Put   │ (Business Logic)│      │ Trigger      │  │
                    │   └─────────────────┘       └────────┬────────┘      └──────────────┘  │
                    │                                      │ Max Retries > 3                 │
                    │                                      ▼                                 │
                    │                             ┌─────────────────┐      ┌──────────────┐  │
                    │                             │    SQS DLQ      │─────>│  CloudWatch  │  │
                    │                             │  (Dead Letter)  │      │  DLQ Alarm   │  │
                    │                             └─────────────────┘      └──────────────┘  │
                    └────────────────────────────────────────────────────────────────────────┘
```

The system decouples immediate HTTP API ingestion from backend accounting calculations and persistent database storage:

1. **API Gateway (HTTP v2):** Exposes public REST endpoints with sub-300ms SLA.
2. **Lambda Producer:** Performs fast-path JSON payload validation, generates timestamps, and enqueues messages to SQS, returning an immediate `202 Accepted` response.
3. **Amazon SQS (Main Buffer):** Absorbs high-concurrency spikes during harvest peak hours, preventing downstream service degradation.
4. **Lambda Consumer:** Batch-processes events, computes net values, and writes to DynamoDB with conditional logic.
5. **Amazon SQS (DLQ) & CloudWatch Alarm:** Captures malformed or poisoned payloads after 3 failed retries (`maxReceiveCount = 3`), triggering proactive operational alerts.

---

## ✨ Key Features & Design Patterns

* **Asynchronous Decoupling:** Ingestion response times are isolated from physical database writes.
* **Strict Financial Idempotency:** Utilizes DynamoDB conditional expressions (`attribute_not_exists(id_liquidacion)`) to prevent duplicate payouts resulting from network retries.
* **Fault Tolerance & Poison-Pill Sanitation:** Dead Letter Queue (DLQ) integration isolates failing events without blocking valid message pipelines.
* **Least Privilege IAM:** Custom roles per Lambda function with zero wildcards (`*`) across execution permissions.

---

## 🛠️ Tech Stack & IaC

* **Cloud Provider:** Amazon Web Services (AWS)
* **Infrastructure as Code:** Terraform >= 1.3.0
* **Compute:** AWS Lambda (Node.js 18.x runtime)
* **API Ingestion:** Amazon API Gateway (HTTP API v2)
* **Messaging:** Amazon SQS (Standard Queue + Dead Letter Queue)
* **Database:** Amazon DynamoDB (On-Demand Capacity Mode)
* **Monitoring:** Amazon CloudWatch (Structured JSON Logs + Alarm)
* **Load Testing:** Python 3.10+ (`httpx` + `asyncio`)

---

## 📂 Repository Structure

```
.
├── frontend/                 # Web interface for payload dispatching
│   └── index.html
├── src/                      # Lambda function source code
│   ├── consumer_lambda/      # SQS consumer, financial logic & DynamoDB write
│   │   ├── index.js
│   │   └── package.json
│   └── producer_lambda/      # API ingestion & SQS payload enqueue
│       ├── index.js
│       └── package.json
├── terraform/                # Infrastructure as Code declaration
│   ├── backend.tf            # Remote state configuration (S3 + DynamoDB locking)
│   ├── iam.tf                # Granular Least-Privilege IAM roles
│   ├── main.tf               # Core AWS resources declaration
│   ├── outputs.tf            # Deployed resource ARNs & endpoints
│   └── terraform.tfvars      # Environment parameters
├── test_stress.py            # Asynchronous multi-scenario load testing script
└── README.md
```

---

## 🧪 Load Testing & Benchmark (1,000 Requests)

A controlled asynchronous load test was conducted using `httpx` and `asyncio` to validate concurrency, DLQ isolation, and idempotency mechanisms across **1,000 mixed request payloads**.

### Test Suite Payload Composition
* **900 Valid Requests (90%):** Standard settlement payments with unique IDs.
* **50 Negative Value Requests (5%):** Invalid payloads (`cantidad_kg: -400`) engineered to fail validation and populate the DLQ after 3 retries.
* **50 Duplicate Requests (5%):** Re-submitted IDs engineered to trigger `ConditionalCheckFailedException` in DynamoDB.

```bash
# Execute 1,000 requests load test
python test_stress.py
```

### Benchmark Results Summary

| Metric | Measured Value | Operational Assessment |
| :--- | :--- | :--- |
| **Total Test Volume** | 1,000 requests | Executed with concurrency control (`Semaphore = 50`) |
| **API Acceptance Rate** | 100% (1,000 / 1,000) | All incoming calls received `202 Accepted` |
| **Ingestion Duration** | ~20 - 35 seconds | Smooth execution without local socket exhaustion |
| **SQS DLQ Derivation** | 50 messages | Negative payloads successfully isolated to DLQ |
| **Idempotency Handling** | 50 duplicate blocks | Handled gracefully without duplicate database writes |
| **CloudWatch Alarm** | Conmuted to `ALARM` | Operational alert triggered upon DLQ depth $\ge 1$ |

---

## 💡 Cost Analysis & Financial Estimation

Calculated using the official **AWS Pricing Calculator** (`us-east-1` region) based on monthly operational volume:

| Service | Configured Metric | Monthly Consumption | Estimated Cost (USD) |
| :--- | :--- | :--- | :--- |
| **API Gateway** | HTTP API Requests | 50,000 calls / month | $0.00 USD (Free Tier) |
| **AWS Lambda** | Compute Duration (256 MB) | 100,000 invocations | $0.00 USD (Free Tier) |
| **Amazon SQS** | API Actions | 150,000 requests | $0.00 USD (Free Tier) |
| **Amazon DynamoDB** | On-Demand Reads/Writes | 50k PutItem / 50k Reads | $0.07 USD |
| **Amazon CloudWatch**| Logs (0.2 GB) + 1 Alarm | Continuous monitoring | $0.20 USD |
| **TOTAL** | **Full Serverless Architecture** | **Monthly Estimate** | **~$0.27 USD / month** |

---

## 🚀 Getting Started

### Prerequisites
* [AWS CLI v2](https://aws.amazon.com/cli/) configured with valid credentials.
* [Terraform v1.x](https://www.terraform.io/) installed.
* [Python 3.10+](https://www.python.org/) for executing load tests.

### Deployment Steps
1. **Clone the repository:**
   ```bash
   git clone https://github.com/AlexanderS1977Sanchez/Liquidaci-n-as-ncrona-AWS.git
   cd AgroLink-Andes
   ```
2. **Install Backend Lambda Dependencies (Node.js)**
Navigate to each Lambda function folder and install its respective AWS SDK modules:
    ```bash
   # Para la Lambda Producer
   cd src/producer_lambda
   npm init -y
   npm install @aws-sdk/client-sqs

   # Para la Lambda Consumer
   cd ../consumer_lambda
   npm init -y
   npm install @aws-sdk/client-dynamodb @aws-sdk/lib-dynamodb
    ```

3. **Initialize & Apply Infrastructure:**
   ```bash
   1. aws sso login 
   2. Enter AWS credentials
      $env:AWS_ACCESS_KEY_ID=""                    
      $env:AWS_SECRET_ACCESS_KEY=""
      $env:AWS_SESSION_TOKEN=""
      $env:AWS_DEFAULT_REGION="us-east-1"
   3. aws sts get-caller-identity 
   4. terraform init   
   5. terraform plan -lock=false
   6. terraform apply    
   ```

4. **Run Load Test Suite:**
   ```bash
   cd ..
   pip install httpx
   python test_stress.py
   ```

---

## 👨‍💻 Author & License

* **Developer:** Jorge Alexander Sánchez Collaguazo
* **Institution:** Universidad Central del Ecuador — Information Systems Engineering
* **License:** MIT License