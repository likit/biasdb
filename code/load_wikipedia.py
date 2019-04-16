import os
import wikipedia
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, insert, update
from nltk.tokenize import sent_tokenize

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')

engine = create_engine('postgres+psycopg2://postgres:{}@pg/bactwatch'.format(POSTGRES_PASSWORD))
connection = engine.connect()

metadata = MetaData()

organisms = Table('organisms', metadata, autoload=True, autoload_with=engine)
organism_wikis = Table('organism_wikis', metadata, autoload=True, autoload_with=engine)
organism_articles = Table('organism_article', metadata, autoload=True, autoload_with=engine)


def load_wiki():
    s = select([organism_articles.c.organism_id])
    rp = connection.execute(s)
    for n, rec in enumerate(rp, start=1):
        r = connection.execute(select([organism_wikis]).where(organism_wikis.c.organism_id == rec.organism_id))
        _exist = r.first()
        if _exist:
            print('\talready parsed...')
            continue
        organism = connection.execute(
            select([organisms]).where(organisms.c.id == rec.organism_id)).first()
        print('Parsing wiki for {}'.format(organism.species))
        try:
            page = wikipedia.page(organism.species.capitalize())
        except (wikipedia.exceptions.PageError, wikipedia.exceptions.DisambiguationError):
            print('\tpage not found or keyword is disambiguous..')
        else:
            u = update(organisms).where(organisms.c.id == organism.id).values(
                wikiurl=page.url
            )
            ur = connection.execute(u)
            for link in page.links:
                ss = select([organisms]).where(organisms.c.species == link.lower())
                for species in connection.execute(ss):
                    print('\t\tinserting linked {}'.format(species.species))
                    ins = insert(organism_wikis).values(
                        organism_id=organism.id,
                        link_id=species.id
                    )
                    ri = connection.execute(ins)
        if n % 100 == 0:
            print('{}...'.format(n))

if __name__ == '__main__':
    load_wiki()
