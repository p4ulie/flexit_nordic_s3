FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY flexit.py exporter.py ./
USER 65534
ENV FLEXIT_HOST=10.3.252.2 FLEXIT_DEVICE_ID=2 FLEXIT_EXPORTER_PORT=9877 PYTHONUNBUFFERED=1
EXPOSE 9877
CMD ["python", "exporter.py"]
