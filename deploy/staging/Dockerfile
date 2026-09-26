FROM python:3.12-slim
WORKDIR /app
COPY service/requirements.txt /app/service/requirements.txt
RUN pip install --no-cache-dir -r /app/service/requirements.txt
COPY . /app
RUN useradd --create-home orama
USER orama
CMD ["uvicorn", "service.app:app_from_env", "--factory", "--host", "0.0.0.0", "--port", "8766", "--proxy-headers", "--forwarded-allow-ips", "*"]
