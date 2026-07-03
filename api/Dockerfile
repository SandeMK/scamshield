# ScamShield Scoring API — deployable to Google Cloud Run / Render free tier
FROM python:3.11-slim
WORKDIR /app
COPY ml/requirements.txt ml/requirements.txt
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY ml/ ml/
COPY api/ api/
ENV MODEL_PATH=/app/ml/model.joblib
EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
