import os
from collections import defaultdict
from . import app
from flask import render_template, url_for
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, func
import wikipedia
from collections import namedtuple
from datetime import datetime
import random

Species = namedtuple('Species', ['id', 'spname'])

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')

engine = create_engine('postgresql+psycopg2://postgres:{}@pg/bactwatch'.format(POSTGRES_PASSWORD))
connection = engine.connect()
metadata = MetaData()

org_articles = Table('organism_article', metadata, autoload=True, autoload_with=engine)
articles = Table('articles', metadata, autoload=True, autoload_with=engine)
organisms = Table('organisms', metadata, autoload=True, autoload_with=engine)
org_source = Table('organism_sources', metadata, autoload=True, autoload_with=engine)
sentences = Table('sentences', metadata, autoload=True, autoload_with=engine)
organism_wikis = Table('organism_wikis', metadata, autoload=True, autoload_with=engine)


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
    columns = [articles.c.pmid, articles.c.pubyear, articles.c.term,
               organisms.c.species, organisms.c.id, sentences.c.text]
    s = select(columns).select_from(org_articles.join(sentences).join(articles).join(organisms))
    result = connection.execute(s).fetchall()
    data = []
    n = 0
    for row in result:
        pmid, year, terms, spname, spid, sentence = row
        s = select([articles]).where(articles.c.pmid == pmid)
        rp = connection.execute(s)
        article = rp.first()
        for term in row[2].split(','):
            n += 1
            item = {
                'id': n,
                'spid': spid,
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


@app.route('/bacteria/profile/<int:bactid>')
def show_profile(bactid=None):
    bacteria = connection.execute(select([organisms]).where(organisms.c.id == bactid)).first()
    in_out_bound_links = 0
    wiki_links = defaultdict(int)
    for link in connection.execute(
            select([
                organisms.c.species,
                organisms.c.id,
                organism_wikis.c.link_id
            ]).select_from(
                organism_wikis.join(
                    organisms, organisms.c.id == organism_wikis.c.organism_id
                )).where(organism_wikis.c.organism_id == bactid)):
        wiki_links[link.link_id] += 1
        in_out_bound_links += 1

    for link in connection.execute(
            select([
                organisms.c.species,
                organisms.c.id,
                organism_wikis.c.organism_id
            ]).select_from(
                organism_wikis.join(
                    organisms, organisms.c.id == organism_wikis.c.organism_id
                )).where(organism_wikis.c.link_id == bactid)):
        wiki_links[link.organism_id] += 1
        in_out_bound_links += 1

    article_links = defaultdict(set)
    species_article_links = defaultdict(set)

    for row in connection.execute(select([org_articles]).where(org_articles.c.organism_id == bactid)):
        for s in connection.execute(select([org_articles]).where(org_articles.c.article_id == row.article_id)):
            if row.organism_id != s.organism_id:
                article_links[s.organism_id].add(row.article_id)

    nodes = [{
            'id': bactid,
            'label': bacteria.species.capitalize(),
            'shape': 'circularImage',
            'image': url_for('static', filename='img/bacteria.png'),
            'color': '#ff6600',
         }
    ]
    edges = []
    common_links = set(wiki_links.keys()).intersection(set(article_links.keys()))
    for sp in common_links:
        r = connection.execute(select([organisms]).where(organisms.c.id == sp)).first()
        num_articles = len(article_links.get(r.id, []))
        species_article_links[Species(r.id, r.species.capitalize())] = article_links[r.id]
        opacity = 0.8
        node = {
            'id': r.id,
            'value': num_articles,
            'label': r.species.capitalize(),
            'shape': 'circularImage',
            'image': url_for('static', filename='img/bacteria.png'),
            'color': '#ffcc00',
        }
        nodes.append(node)
        edge = {
            'from': r.id,
            'to': bactid,
            'value': num_articles,
            'title': '{} articles'.format(num_articles),
            'color': {'color': '#0855c9', 'highlight': '#ffcc00', 'opacity': opacity},
        }
        edges.append(edge)

    try:
        wiki_summary = wikipedia.summary(bacteria.species.capitalize(), sentences=6)
        wiki_page = wikipedia.page(bacteria.species.capitalize())
    except (wikipedia.exceptions.PageError, wikipedia.exceptions.DisambiguationError):
        wiki_summary = 'Wikipedia Summary not Available'
        wiki_page = None

    article_timeline = {}
    years = range(2000, datetime.now().year + 1)
    for sid in common_links:
        s = select([organisms.c.species, articles.c.pubyear]).select_from(
            articles.join(org_articles).join(organisms)).where(org_articles.c.organism_id == sid)
        for row in connection.execute(s):
            if row.pubyear > 1999:
                if row.species not in article_timeline:
                    article_timeline[row.species] = dict([(y,0) for y in years])
                article_timeline[row.species][row.pubyear] += 1

    s = select([organisms.c.species, articles.c.pubyear]).select_from(
        articles.join(org_articles).join(organisms)).where(org_articles.c.organism_id == bactid)
    for row in connection.execute(s):
        if row.pubyear > 1999:
            if row.species not in article_timeline:
                article_timeline[row.species] = dict([(y,0) for y in years])
            article_timeline[row.species][row.pubyear] += 1

    article_timeline_data = []
    sp_choices = random.choices(list(article_timeline), k=4)
    sp_choices.append(bacteria.species)
    colors = [
        'rgb(254, 178, 54)',
        'rgb(107, 91, 149)',
        'rgb(214, 65, 97)',
        'rgb(255, 123, 37)',
        'rgb(3, 79, 132)',
    ]

    for n, spname in enumerate(sp_choices):
        article_timeline_data.append({
            'label': spname.capitalize(),
            'data': [article_timeline[spname][y] for y in years],
            'backgroundColor': colors[n],
            'borderColor': colors[n],
            'fill': False
        })

    return render_template('profile.html', bacteria=bacteria, nodes=nodes, edges=edges,
                           spname=bacteria.species.capitalize(),
                           wiki_summary=wiki_summary,
                           wiki_page=wiki_page,
                           species_article_links=species_article_links,
                           article_timeline_data=article_timeline_data,
                           years=list(years)
                           )
