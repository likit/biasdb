from sqlalchemy import create_engine
from sqlalchemy import Table, Column, MetaData, Integer, String, ForeignKey, DateTime, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import JSON

'''Medline field reference: https://www.nlm.nih.gov/bsd/mms/medlineelements.html#dp

'''

engine = create_engine('postgres+psycopg2://likit@localhost/bactwatch')

metadata = MetaData()

articles = Table('articles', metadata,
                 Column('id', Integer(), primary_key=True),
                 Column('pmid', String(), unique=True, index=True),
                 Column('pubyear', Integer(), nullable=False),
                 Column('data', JSON()),
                 Column('term', String()),
                 Column('processed', DateTime())
                 )


organisms = Table('organisms', metadata,
                  Column('taxid', Integer(), primary_key=True),
                  Column('species', String(), index=True),
                  Column('parentid', Integer()),
                  )

organism_article = Table('organism_article', metadata,
                         Column('id', Integer(), primary_key=True),
                         Column('article_id', ForeignKey('articles.id')),
                         Column('organism_taxid', ForeignKey('organisms.taxid'))
                         )


if __name__ == '__main__':
    metadata.create_all(engine)
