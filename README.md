# Sample FastAPI App

This project contains a simple FastAPI application with JSON logs written to standard output.

The same image can be deployed multiple times with different environment variables so logs can be separated by service in Grafana.

## Endpoints

- `GET /` returns a welcome message.
- `GET /health` returns a basic health response.
- `GET /items/{item_id}` returns a sample item payload.
- `GET /metrics` exposes Prometheus metrics for scraping.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Optional environment variables:

- `SERVICE_NAME` defaults to `sample-fastapi-app`
- `SERVICE_VERSION` defaults to `1.0.0`
- `ENVIRONMENT` defaults to `local`
- `LOG_LEVEL` defaults to `INFO`

Example:

```bash
$env:SERVICE_NAME="orders-api"
$env:SERVICE_VERSION="1.0.0"
$env:ENVIRONMENT="dev"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

To simulate a second service with the same codebase, start another instance with a different `SERVICE_NAME` and port.

## Logging

Logs are emitted in JSON format to stdout and include fields such as:

- `timestamp`
- `level`
- `logger`
- `message`
- `service_name`
- `service_version`
- `environment`
- `request_id`
- `path`
- `method`
- `status_code`
- `duration_ms`

You can control the log level with the `LOG_LEVEL` environment variable.

Example log output:

```json
{"timestamp":"2026-04-20T10:15:30.000000+00:00","level":"INFO","logger":"orders-api","message":"request_completed","service_name":"orders-api","service_version":"1.0.0","environment":"dev","request_id":"c3c0e28f-3f5b-4b6a-93b9-782946f9d6d4","path":"/health","method":"GET","status_code":200,"duration_ms":1.42}
```

## Container image

Build the image locally:

```bash
docker build -t sample-fastapi-app:latest .
```

Run the container:

```bash
docker run --rm -p 8000:8000 -e SERVICE_NAME=orders-api -e ENVIRONMENT=dev sample-fastapi-app:latest
```

Run a second instance with a different identity:

```bash
docker run --rm -p 8001:8000 -e SERVICE_NAME=inventory-api -e ENVIRONMENT=dev sample-fastapi-app:latest
```

This gives you two separately identifiable services from the same codebase, which is usually enough to separate logs and dashboards later in Kubernetes and Grafana.