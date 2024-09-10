FROM python:3.12-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY chat_bot /app

ENTRYPOINT ["/bin/echo", "python", "chat_bot.py"]