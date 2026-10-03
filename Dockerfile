FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

ARG UID=1000
ARG GID=1000
# Se crea el home (/home/app, propiedad de app): gunicorn guarda ahí su socket de control
# ($HOME/.gunicorn/gunicorn.ctl).
RUN groupadd --gid "${GID}" app \
    && useradd --uid "${UID}" --gid app --create-home --shell /usr/sbin/nologin app

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY src/ /app/
# El código queda de root (solo lectura para la app); solo staticfiles es escribible.
RUN chmod 0755 /usr/local/bin/entrypoint.sh \
    && mkdir -p /app/staticfiles \
    && chown app:app /app/staticfiles

USER app
EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
