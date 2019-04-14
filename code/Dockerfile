FROM python:3.7

RUN mkdir -p /app/code
COPY requirements.txt /app/code/requirements.txt
WORKDIR /app/code
RUN pip install -r requirements.txt
