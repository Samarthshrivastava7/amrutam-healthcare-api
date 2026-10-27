FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt
RUN addgroup --system app && adduser --system --ingroup app app
COPY --chown=app:app . .
USER app
EXPOSE 8000
# Run migrations as an explicit release step, not on every web-worker startup.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
