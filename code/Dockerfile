FROM python:3.7

RUN mkdir -p /app/code
COPY requirements.txt /app/code/requirements.txt
WORKDIR /app/code
RUN pip install -U pip && pip install -r requirements.txt && python -m nltk.downloader wordnet && python -m nltk.downloader stopwords && python -m nltk.downloader punkt && python -m textblob.download_corpora
