import sys
import os
import re
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, insert, update
import requests

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')

engine = create_engine('postgres+psycopg2://postgres:{}@pg/{}'\
                       .format(POSTGRES_PASSWORD, DB_NAME))
connection = engine.connect()

metadata = MetaData()

Organism = Table('organisms', metadata, autoload=True, autoload_with=engine)


def add_taxonomy():
    gs_pattern = ('\<span class=\"genusspecies\"\>(\w+)\<\/span\>'
                  '\s+\<span class=\'specificepithet\'\>(\w+)\<\/span\>')
    gss_pattern = ('\<span class=\"genusspecies\"\>(\w+)\<\/span\>'
                   '\s+\<span class=\'specificepithet\'\>(\w+)\<\/span\>'
                   '\s+\<span class=\"genusspecies-subspecies\"\>(subsp.)\<\/span\>'
                   '\s+\<span class=\'subspecificepithet\'\>(\w+)\<\/span\>'
                   )
    urls = ['http://www.bacterio.net/-allnamesac.html',
            'http://www.bacterio.net/-allnamesdl.html',
            'http://www.bacterio.net/-allnamesmr.html',
            'http://www.bacterio.net/-allnamessz.html']

    species_set = set()

    for url in urls:
        print('Loading from {}..'.format(url))
        r = requests.get(url)
        html_contents = r.text

        for pat in [gs_pattern, gss_pattern]:
            matches = re.findall(pat, html_contents)
            for m in matches:
                species = ' '.join(m).lower()
                species_set.add(species)

    for n, sp in enumerate(species_set, start=1):
        ins = insert(Organism).values(
            id=n,
            species=sp,
        )
        result = connection.execute(ins)


if __name__ == '__main__':
    add_taxonomy()
