# check=skip=InvalidDefaultArgInFrom
ARG PYTHON_BASE_IMAGE
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /app/app.py
COPY index.html /app/index.html

EXPOSE 18181
CMD ["python", "/app/app.py"]
