import os
import sys
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, update
from textblob import TextBlob
from pandas import DataFrame
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfTransformer, TfidfVectorizer

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')

engine = create_engine('postgres+psycopg2://postgres:{}@pg/{}'\
                       .format(POSTGRES_PASSWORD, DB_NAME))
connection = engine.connect()

metadata = MetaData()

article_tbl = Table('articles', metadata, autoload=True, autoload_with=engine)
bigram_tbl = Table('bigrams', metadata, autoload=True, autoload_with=engine)

en_stopwords = stopwords.words('english')

def drop_stopwords(text):
    if text:
        return ' '.join([t.lower() for t in text.split() if t not in en_stopwords])
    else:
        return ''


def calculate():
    result_proxy = connection.execute(select([article_tbl.c.id, article_tbl.c.data['AB']])).fetchall()
    all_articles = DataFrame(result_proxy, columns=['pid', 'abstract'])
    all_articles['cleaned_abstract'] = all_articles['abstract'].apply(drop_stopwords)

    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(2,2), analyzer='word', min_df=1, max_df=0.8)
    vectorizer.fit(all_articles['cleaned_abstract'])
    for k, v in vectorizer.vocabulary_.items():
        bigram = connection.execute(select([bigram_tbl]).where(bigram_tbl.c.text==k)).first()
        if bigram:
            u = update(bigram_tbl).values(
                tfidf=vectorizer.idf_[v]
            ).where(bigram_tbl.c.id==bigram.id)
            rp = connection.execute(u)

if __name__ == '__main__':
    calculate()

