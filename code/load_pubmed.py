import sys
import os
from Bio import Entrez
from Bio import Medline
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, insert, update

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')

engine = create_engine('postgres+psycopg2://postgres:{}@pg/{}'\
                       .format(POSTGRES_PASSWORD, DB_NAME))
connection = engine.connect()

metadata = MetaData()

Articles = Table('articles', metadata, autoload=True, autoload_with=engine)

'''Medline field reference: https://www.nlm.nih.gov/bsd/mms/medlineelements.html#dp

'''

Entrez.email = 'likit.pre@mahidol.edu'


def load_article(term):
    if not term:
        return

    handle = Entrez.egquery(term=term)
    for record in Entrez.read(handle)['eGQueryResult']:
        if record['DbName'] == 'pubmed':
            total_articles = record['Count']

    handle = Entrez.esearch(db='pubmed', term=term, retmode='xml', retmax=total_articles)
    records = Entrez.read(handle)
    print('The total number of articles is {}.'.format(records['Count']))
    id_list = records['IdList']
    print(len(records['IdList']))
    new_id_list = []

    if id_list:
        for pmid in id_list:
            s = select([Articles]).where(Articles.c.pmid == pmid)
            if connection.execute(s).first():
                print(u'PMID={} exsists..updating the search term.'.format(pmid))
                u = update(Articles).where(Articles.c.pmid == pmid)
                u = u.values(term=Articles.c.term + ',{}'.format(term))
                connection.execute(u)
                continue
            else:
                new_id_list.append(pmid)

        print(len(new_id_list))

        handle = Entrez.efetch(db='pubmed', id=new_id_list,
                               rettype='medline', retmode='text', retmax=len(new_id_list))
        for rec in Medline.parse(handle):
            if not rec.get('PMID', None):
                continue
            try:
                pubyear = int(rec.get('DP', 'No pub date')[:4])
            except ValueError:
                print('\tPMID={} has no pubdate'.format(rec['PMID']))
                continue

            ins = insert(Articles).values(
                pmid=rec['PMID'],
                data=rec,
                pubyear=pubyear,
                term=term
            )
            result = connection.execute(ins)
            print(
                u'TITLE={0} PMID={2} inserted with PK={1}'.format(rec['TI'], result.inserted_primary_key, rec['PMID']))


if __name__ == '__main__':
    term = sys.argv[1]
    print(term)
    load_article(term)
