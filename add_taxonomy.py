import sys
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, insert, update
from ete3 import NCBITaxa

engine = create_engine('postgres+psycopg2://likit@localhost/bactwatch')
connection = engine.connect()

metadata = MetaData()

Organism = Table('organisms', metadata, autoload=True, autoload_with=engine)


def add_taxonomy(parentid):
    ncbi = NCBITaxa()
    descendants = ncbi.get_descendant_taxa(parentid)
    for tid, taxa in ncbi.get_taxid_translator(descendants).items():
        print('Adding ID={} {}...'.format(tid, taxa))
        ins = insert(Organism).values(
            taxid=tid,
            species=taxa,
            parentid=parentid,
        )
        result = connection.execute(ins)


if __name__ == '__main__':
    parentid = sys.argv[1]
    if parentid.isdigit():
        add_taxonomy(int(parentid))
    else:
        print('Parent ID must be specified as an integer.')
