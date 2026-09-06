#!/bin/bash
# Simple helper script to automate AWS ECR pushing

if [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$AWS_REGION" ]; then
    echo "Please set AWS_ACCOUNT_ID and AWS_REGION environment variables."
    exit 1
fi

echo "Authenticating to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "Building images..."
docker-compose -f ../../docker-compose.yml build

echo "Tagging backend..."
docker tag ai-assistant-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-assistant-backend:latest

echo "Tagging frontend..."
docker tag ai-assistant-frontend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-assistant-frontend:latest

echo "Pushing backend..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-assistant-backend:latest

echo "Pushing frontend..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-assistant-frontend:latest

echo "Done! Images are ready in ECR."
