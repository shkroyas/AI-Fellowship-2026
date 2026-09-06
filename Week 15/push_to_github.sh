#!/bin/bash

# Script to commit and push the Week 15 assignment to GitHub

# Set variables
REPO_URL="git@github.com:shkroyas/AI-Fellowship-2026.git"
CLONE_DIR="/tmp/ai-fellowship-repo"
TARGET_DIR="$CLONE_DIR/Week 15"
SOURCE_DIR="/home/royas-shakya/Downloads/Week15"

echo "Cloning repository..."
git clone "$REPO_URL" "$CLONE_DIR"

echo "Creating Week 15 directory..."
mkdir -p "$TARGET_DIR"

echo "Copying files..."
cp -r "$SOURCE_DIR/task1-ai-assistant" "$TARGET_DIR/"
cp -r "$SOURCE_DIR/task2-production" "$TARGET_DIR/"
cp -r "$SOURCE_DIR/architecture" "$TARGET_DIR/"
cp "$SOURCE_DIR/README.md" "$TARGET_DIR/"

echo "Committing to git..."
cd "$CLONE_DIR"
git add "Week 15/"
git commit -m "Add Week 15 AI Assistant Assignment: RAG pipeline, FastAPI backend, Streamlit UI, Docker & AWS deployment"

echo "Pushing to GitHub..."
git push origin main

echo "Done! The code has been pushed to your GitHub repository."
