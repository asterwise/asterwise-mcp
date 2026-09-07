FROM python:3.12-slim

# Run as an unprivileged user. Port 8080 needs no privileges and the server
# writes nothing to disk (structured logs go to stdout).
RUN groupadd --system app && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# .dockerignore keeps the venv, tests, docs, keys and env files out of this copy.
COPY --chown=app:app . .

# Upstream API; production overrides nothing here. Set so a hosted build (for
# example on Glama) works out of the box: callers bring their own key per
# request, so no secret is required for API-key mode.
ENV ASTERWISE_API_BASE_URL=https://api.asterwise.com

USER app
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4).status == 200 else 1)"

# --forwarded-allow-ips: the service is only reachable through the platform proxy,
# so X-Forwarded-For is trustworthy and per-IP OAuth rate limiting needs it.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080", "--forwarded-allow-ips", "*"]
