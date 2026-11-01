FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    KAIRIS_LLM_ENABLED=false

WORKDIR /tmp/kairis-build

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home kairis
USER kairis
WORKDIR /home/kairis/app

COPY --chown=kairis:kairis . .
RUN mkdir -p /home/kairis/app/data/input /home/kairis/app/output/metrics /home/kairis/app/output/figures /home/kairis/app/output/reports

EXPOSE 8000
VOLUME ["/home/kairis/app/data/input", "/home/kairis/app/output"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["python", "web_app.py", "--host", "0.0.0.0", "--port", "8000", "--no-open"]
