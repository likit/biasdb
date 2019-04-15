import os
from . import app
from flask import render_template
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, func

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')

engine = create_engine('postgresql+psycopg2://postgres:{}@pg/bactwatch'.format(POSTGRES_PASSWORD))
connection = engine.connect()
metadata = MetaData()

org_articles = Table('organism_article', metadata, autoload=True, autoload_with=engine)
articles = Table('articles', metadata, autoload=True, autoload_with=engine)
organisms = Table('organisms', metadata, autoload=True, autoload_with=engine)
org_source = Table('organism_sources', metadata, autoload=True, autoload_with=engine)
sentences = Table('sentences', metadata, autoload=True, autoload_with=engine)


def get_summary():
    columns = [articles.c.pmid, articles.c.pubyear, articles.c.term, organisms.c.species]
    s = select(columns).select_from(org_articles.join(articles).join(organisms))
    result = connection.execute(s).fetchall()
    data = {}
    for row in result:
        species = row[3]
        if species not in data:
            data[species] = {
                row[1]: {
                    'terms': dict([(t, set()) for t in row[2].split(',')])
                }
            }
        else:
            if row[1] not in data[species]:
                data[species][row[1]] = {'terms': dict([(t, set()) for t in row[2].split(',')])}
            for t in row[2].split(','):
                if t not in data[species][row[1]]['terms']:
                    data[species][row[1]]['terms'][t] = set([row[0]])
                else:
                    data[species][row[1]]['terms'][t].add(row[0])
    return data


def get_organism_list():
    columns = [articles.c.pmid, articles.c.pubyear, articles.c.term, organisms.c.species, sentences.c.text]
    s = select(columns).select_from(org_articles.join(sentences).join(articles).join(organisms))
    result = connection.execute(s).fetchall()
    data = []
    n = 0
    for row in result:
        pmid, year, terms, spname, sentence = row
        s = select([articles]).where(articles.c.pmid == pmid)
        rp = connection.execute(s)
        article = rp.first()
        for term in row[2].split(','):
            n += 1
            item = {
                'id': n,
                'spname': spname.capitalize(),
                'term': term,
                'pmid': article['pmid'],
                'title': article['data']['TI'],
                'sentence': sentence,
                'year': year,
                'authors': ','.join(article['data']['AU']),
                'journal': article['data']['TA'],
            }
            data.append(item)
    return data


@app.route('/')
def index():
    data = get_summary()
    organism_list = get_organism_list()
    summary = {
        'VITEK MS': {
            'articles': set(),
            'years': set(),
            'organisms': set(),
        },
        'VITEK 2': {
            'articles': set(),
            'years': set(),
            'organisms': set(),
        },
        'biotyper': {
            'articles': set(),
            'years': set(),
            'organisms': set(),
        }
    }
    for term in summary:
        for spname in data:
            for year in data[spname]:
                if term in data[spname][year]['terms']:
                    summary[term]['articles'].update(data[spname][year]['terms'][term])
                    summary[term]['years'].add(year)
                    summary[term]['organisms'].add(spname)

    s = select([func.count(articles.c.pmid)])
    rp = connection.execute(s)
    articles_count = rp.scalar()
    return render_template('index.html', summary=summary,
                           organism_list=organism_list,
                           articles_count=articles_count)
