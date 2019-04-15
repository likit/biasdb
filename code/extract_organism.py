import os
import re
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, insert
from nltk.tokenize import sent_tokenize

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')

engine = create_engine('postgres+psycopg2://postgres:{}@pg/bactwatch'.format(POSTGRES_PASSWORD))
connection = engine.connect()

metadata = MetaData()

OrgArticle = Table('organism_article', metadata, autoload=True, autoload_with=engine)
Article = Table('articles', metadata, autoload=True, autoload_with=engine)
Organism = Table('organisms', metadata, autoload=True, autoload_with=engine)
OrgSource = Table('organism_sources', metadata, autoload=True, autoload_with=engine)
Sentence = Table('sentences', metadata, autoload=True, autoload_with=engine)


def extract_organism():
    s = select([Article])
    for n, ar in enumerate(connection.execute(s), start=1):
        abstract = ar['data'].get('TI', '') + '\n' + ar['data'].get('AB', '')
        patterns = ['([A-Z]\w+)\s(\w+)\s(subsp\.?|subspecies)\s(\S+)', '([A-Z]\w+)\s(\w+)']
        for sent in sent_tokenize(abstract):
            ins = insert(Sentence).values(
                article_id=ar.id,
                text=sent,
            )
            result = connection.execute(ins)
            sent_id = result.inserted_primary_key[0]
            for p in patterns:
                _sent = re.sub('\sand\s|\sor\s|\swith\s', ' | ',
                           sent)  # replace some words with a pipe to prevent regex matching across multiple names
                sps = re.findall(p, _sent)
                for tx in sps:
                    print(' '.join(tx))
                    s = select([Organism]).where(Organism.c.species == '{}'.format(' '.join([t.lower() for t in tx])))
                    rp = connection.execute(s)
                    org = rp.first()
                    if org:
                        print('\tfound {} from ({})'.format(org.species, ' '.join(tx)))

                        ins = insert(OrgArticle).values(
                            article_id=ar.id,
                            organism_id=org.id,
                            sentence_id=sent_id,
                        )
                        result = connection.execute(ins)


if __name__ == '__main__':
    extract_organism()
