FROM python:3.11

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --use-pep517 --prefer-binary -r requirements.txt


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
