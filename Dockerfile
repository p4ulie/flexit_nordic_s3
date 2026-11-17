FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY flexit_nordic/ ./flexit_nordic/
USER 65534
# ponytail: bytecode writes would fail on the read-only root filesystem, so skip them.
ENV FLEXIT_EXPORTER_PORT=9877 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 9877
CMD ["python", "-m", "flexit_nordic.exporter"]
