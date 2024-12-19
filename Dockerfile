FROM python:3.12
LABEL authors="mldchan"

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .

STOPSIGNAL SIGKILL

ENTRYPOINT ["python", "main.py"]