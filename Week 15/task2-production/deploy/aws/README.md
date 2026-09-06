# AWS Deployment Guide for AI Assistant

This guide explains how to deploy the production AI Assistant to AWS using ECS (Elastic Container Service) with AWS Fargate.

## Architecture

```
Internet → Application Load Balancer → ECS Fargate (Frontend Tasks)
                                    → ECS Fargate (Backend Tasks)
```

## Prerequisites

1. AWS CLI installed and configured (`aws configure`)
2. Docker installed locally
3. AWS IAM permissions for ECS, ECR, and IAM roles

## Step 1: Push Images to ECR

First, create ECR repositories for your backend and frontend images:

```bash
# Set your AWS account ID and region
export AWS_ACCOUNT_ID="your-account-id"
export AWS_REGION="us-east-1"

# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Create repositories
aws ecr create-repository --repository-name ai-assistant-backend
aws ecr create-repository --repository-name ai-assistant-frontend

# Build images
docker-compose -f docker-compose.yml build

# Tag images
docker tag ai-assistant-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-assistant-backend:latest
docker tag ai-assistant-frontend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-assistant-frontend:latest

# Push images
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-assistant-backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-assistant-frontend:latest
```

## Step 2: Set up AWS Parameter Store

Store your sensitive API keys securely in AWS Systems Manager Parameter Store:

```bash
aws ssm put-parameter --name "/ai-assistant/prod/google-api-key" --value "your-key" --type "SecureString"
aws ssm put-parameter --name "/ai-assistant/prod/openai-api-key" --value "your-key" --type "SecureString"
```

## Step 3: Create ECS Task Definitions

Create a `backend-task.json` file:

```json
{
  "family": "ai-assistant-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-assistant-backend:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "LLM_PROVIDER", "value": "gemini"},
        {"name": "ENVIRONMENT", "value": "production"}
      ],
      "secrets": [
        {"name": "GOOGLE_API_KEY", "valueFrom": "/ai-assistant/prod/google-api-key"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-assistant",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "backend"
        }
      }
    }
  ]
}
```

Create a `frontend-task.json` file:

```json
{
  "family": "ai-assistant-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-assistant-frontend:latest",
      "portMappings": [{"containerPort": 8501}],
      "environment": [
        {"name": "BACKEND_URL", "value": "http://INTERNAL_ALB_DNS:8000"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-assistant",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "frontend"
        }
      }
    }
  ]
}
```

Register the tasks:
```bash
aws ecs register-task-definition --cli-input-json file://backend-task.json
aws ecs register-task-definition --cli-input-json file://frontend-task.json
```

## Step 4: Create ECS Cluster and Services

1. Create a cluster:
```bash
aws ecs create-cluster --cluster-name ai-assistant-cluster
```

2. Create an Application Load Balancer (ALB) and target groups for both frontend and backend.
3. Configure Security Groups to allow port 80/443 on the ALB and ports 8000/8501 from the ALB to the ECS tasks.
4. Create the services:

```bash
aws ecs create-service \
    --cluster ai-assistant-cluster \
    --service-name backend-service \
    --task-definition ai-assistant-backend \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[SUBNET_ID],securityGroups=[SG_ID]}" \
    --load-balancers "targetGroupArn=TG_ARN,containerName=backend,containerPort=8000"

aws ecs create-service \
    --cluster ai-assistant-cluster \
    --service-name frontend-service \
    --task-definition ai-assistant-frontend \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[SUBNET_ID],securityGroups=[SG_ID]}" \
    --load-balancers "targetGroupArn=TG_ARN,containerName=frontend,containerPort=8501"
```

## Persistence for Vector Database

For production, instead of local file storage for ChromaDB:
1. Mount an EFS (Elastic File System) volume to the backend ECS task
2. Or use a managed vector database service like Pinecone, AWS OpenSearch Serverless, or hosted Chroma.
