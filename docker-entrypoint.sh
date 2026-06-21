#!/bin/bash
set -e

echo "Starting AI Learning Companion..."

cd /workspace

# Start FastAPI backend
uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to be ready
echo "Waiting for backend to start..."
sleep 5

# Start Streamlit frontend
streamlit run app/app.py --server.port 5000 --server.address 0.0.0.0 &
STREAMLIT_PID=$!

# Wait for both processes
wait $FASTAPI_PID $STREAMLIT_PID
