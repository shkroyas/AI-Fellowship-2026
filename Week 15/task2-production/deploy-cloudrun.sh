#!/bin/bash
# Simple script to deploy the AI Assistant to Google Cloud Run

PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No Google Cloud project configured."
    exit 1
fi

echo "🚀 Deploying to Google Cloud Run in project: $PROJECT_ID"

# Extract Google API Key from local .env
cd task1-ai-assistant 2>/dev/null || true
source .env 2>/dev/null || true
cd ../task2-production 2>/dev/null || true
source .env 2>/dev/null || true

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "❌ Error: GOOGLE_API_KEY not found in .env files."
    exit 1
fi

cd ..

# ----- 1. DEPLOY BACKEND -----
echo "==> 🏗️ Building Backend Image..."
# We use temporary rename because gcloud builds submit doesn't accept a path to a specific Dockerfile without config
mv task2-production/Dockerfile.backend Dockerfile
gcloud builds submit --tag gcr.io/$PROJECT_ID/ai-assistant-backend .
mv Dockerfile task2-production/Dockerfile.backend

echo "==> ☁️ Deploying Backend to Cloud Run..."
BACKEND_URL=$(gcloud run deploy ai-assistant-backend \
  --image gcr.io/$PROJECT_ID/ai-assistant-backend \
  --port 8000 \
  --memory 2Gi \
  --allow-unauthenticated \
  --set-env-vars="LLM_PROVIDER=gemini,GEMINI_MODEL=gemini-3.6-flash,GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
  --format="value(status.url)" \
  --region asia-south1)

echo "✅ Backend deployed at: $BACKEND_URL"

# ----- 2. DEPLOY FRONTEND -----
echo "==> 🏗️ Building Frontend Image..."
mv task2-production/Dockerfile.frontend Dockerfile
gcloud builds submit --tag gcr.io/$PROJECT_ID/ai-assistant-frontend .
mv Dockerfile task2-production/Dockerfile.frontend

echo "==> ☁️ Deploying Frontend to Cloud Run..."
FRONTEND_URL=$(gcloud run deploy ai-assistant-frontend \
  --image gcr.io/$PROJECT_ID/ai-assistant-frontend \
  --port 8501 \
  --allow-unauthenticated \
  --set-env-vars="BACKEND_URL=$BACKEND_URL" \
  --format="value(status.url)" \
  --region asia-south1)

echo "✅ Frontend deployed at: $FRONTEND_URL"

# ----- 3. UPDATE BACKEND CORS -----
echo "==> 🔒 Updating Backend CORS to restrict to Frontend URL..."
gcloud run services update ai-assistant-backend \
  --update-env-vars="FRONTEND_URL=$FRONTEND_URL" \
  --region asia-south1

echo "🎉 Deployment Complete! You can access your app at $FRONTEND_URL"
