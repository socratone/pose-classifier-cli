FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pose_classifier.py .
COPY organize_from_csv.py .

ENTRYPOINT ["python", "pose_classifier.py"]
