FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
# Debian fixes land in the base image's apt archive before the image is rebuilt; upgrade gets them now.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt /app/requirements.txt
# pip is needed only to install; removing it also removes the stale packages it vendors in pip/_vendor.
RUN pip install --no-cache-dir -r /app/requirements.txt && pip uninstall -y pip
COPY src/ /app/src/
RUN groupadd --system app && useradd --system --gid app app \
 && mkdir -p /data && chown -R app:app /data /app
USER app
ENV SVCDESK_DB=/data/svcdesk.db
EXPOSE 8080
CMD ["uvicorn", "svcdesk.main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8080"]
