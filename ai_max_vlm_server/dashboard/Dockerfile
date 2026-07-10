FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY app.py /app/app.py

EXPOSE 18181
CMD ["python", "/app/app.py"]
