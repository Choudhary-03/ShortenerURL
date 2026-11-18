FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Install dependencies first so this layer is cached until requirements change
COPY requirements/ requirements/
RUN pip install -r requirements/production.txt

COPY . .

# Fix Windows line endings in the entrypoint, collect static files, set ownership
RUN sed -i 's/\r$//' deployment/entrypoint.sh \
    && chmod +x deployment/entrypoint.sh \
    && python manage.py collectstatic --noinput \
    && chown -R app:app /app

USER app
EXPOSE 8000

ENTRYPOINT ["/app/deployment/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--no-control-socket"]
