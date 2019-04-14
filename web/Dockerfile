FROM python:3.7

RUN mkdir -p /app/web
COPY requirements.txt /app/web/requirements.txt
WORKDIR /app/web
RUN pip install -r requirements.txt

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "app.main:app"]
