FROM python:3.12-alpine
WORKDIR /opt/spyi
RUN pip install --no-cache-dir 'openpyxl==3.1.5'
COPY spyi_server.py spyi_sync_server.py market_store.py ha_server.py SPYI_Dashboard.html ./
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
CMD ["python", "ha_server.py"]
