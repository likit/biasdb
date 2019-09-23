FROM python:3.7

RUN mkdir -p /app/web
COPY requirements.txt /app/web/requirements.txt
WORKDIR /app/web
RUN pip install -r requirements.txt && python -m nltk.downloader wordnet && python -m nltk.downloader stopwords && python -m textblob.download_corpora

CMD ["gunicorn", "--workers", "3", "-k", "gevent", "--worker-connections", "200", "--bind", "0.0.0.0:5000", "webapp:app"]
