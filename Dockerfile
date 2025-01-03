FROM python:3.12
LABEL authors="mldchan"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

STOPSIGNAL SIGKILL

ENTRYPOINT ["python", "main.py"]