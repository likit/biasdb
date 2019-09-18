import os
import sys
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, insert
from textblob import TextBlob
from pandas import DataFrame
from collections import defaultdict
from nltk.corpus import stopwords

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')

engine = create_engine('postgres+psycopg2://postgres:{}@pg/{}'\
                       .format(POSTGRES_PASSWORD, DB_NAME))
connection = engine.connect()

metadata = MetaData()

article_tbl = Table('articles', metadata, autoload=True, autoload_with=engine)
bigram_tbl = Table('bigrams', metadata, autoload=True, autoload_with=engine)
organism_tbl = Table('organisms', metadata, autoload=True, autoload_with=engine)

en_stopwords = stopwords.words('english')

def drop_stopwords(text):
    if text:
        return ' '.join([t.lower() for t in text.split() if t not in en_stopwords])
    else:
        return ''


def create_bigrams(ngram=2):
    organisms = connection.execute(select([organism_tbl]))
    spnames = set([org.species for org in organisms])
    bigrams = defaultdict(list)
    print('Loading articles and generating bigrams..')
    result_proxy = connection.execute(select([article_tbl.c.id, article_tbl.c.data['AB']])).fetchall()
    all_articles = DataFrame(result_proxy, columns=['pid', 'abstract'])
    all_articles['cleaned_abstract'] = all_articles['abstract'].apply(drop_stopwords)

    for i in range(len(all_articles)):
        row = all_articles.loc[i]
        for np in TextBlob(row.cleaned_abstract).noun_phrases:
            for bg in TextBlob(np).ngrams(ngram):
                bigram = ' '.join(bg).lower()
                if bigram not in spnames:
                    bigrams[bigram].append(row.pid)
        if i % 100 == 0:
            print('...{}'.format(i))

    print('Saving bigrams..')
    for n, bg in enumerate(bigrams, start=1):
        for pid in bigrams[bg]:
            ins = insert(bigram_tbl).values(
                article_id=pid.item(),
                text=bg,
            )
            rp = connection.execute(ins)
        if n % 1000 == 0:
            print('...{}'.format(n))


if __name__ == '__main__':
    try:
        ngram = int(sys.argv[1])
    except IndexError:
        ngram = 2
    create_bigrams(ngram)
