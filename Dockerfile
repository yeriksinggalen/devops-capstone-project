FROM python:3.9-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --no-cache-dir \
    -r requirements.txt

COPY . /app

RUN chgrp -R 0 /app && chmod -R g=u /app

USER 1001:0

EXPOSE 8080

CMD ["sh", "-c", "exec gunicorn --workers 1 --bind 0.0.0.0:${PORT} --log-level info service:app"]
