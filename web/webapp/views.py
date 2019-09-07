import os
import re
import random
from collections import defaultdict
from . import app
from flask import render_template, url_for, jsonify
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, func, and_
import wikipedia
from collections import namedtuple
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer

gram_pattern = re.compile('[Gg]ram[\s,-](positive|negative)')

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
bigram_tbl = Table('bigrams', metadata, autoload=True, autoload_with=engine)

bigram_idf = {}
for bg in connection.execute(select([bigram_tbl])):
    bigram_idf[bg.text] = bg.tfidf


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


@app.route('/api/v1/organisms/')
def api_get_organisms():
    organism_list = get_organism_list()
    return jsonify(organism_list)


def get_organism_list():
    columns = [articles.c.pmid, articles.c.pubyear, articles.c.term,
               organisms.c.species, organisms.c.id]
    s = select(columns).select_from(org_articles.join(articles).join(organisms))
    result = connection.execute(s).fetchall()
    _data = {}
    n = 0
    for row in result:
        pmid, year, terms, spname, spid = row
        s = select([articles]).where(articles.c.pmid == pmid)
        rp = connection.execute(s)
        article = rp.first()
        for term in row[2].split(','):
            n += 1
            if (spid, spname) not in _data:
                item = {
                    'id': n,
                    'spid': spid,
                    'spname': spname.capitalize(),
                    'term': term,
                    'pmid': article['pmid'],
                    'title': article['data']['TI'],
                    'year': year,
                    'authors': ','.join(article['data']['AU']),
                    'journal': article['data']['TA'],
                    'count': 1
                }
                _data[(spid, spname)] = item
            else:
                _data[(spid, spname)]['count'] += 1

    return [item for item in _data.values()]

vectorizer_word = TfidfVectorizer(stop_words='english', ngram_range=(1,1), analyzer='word', min_df=1, max_df=0.8)
all_abstracts = []
for rp in connection.execute(select([articles.c.data['AB'].label('abstract')])):
    all_abstracts.append(rp.abstract or '')

vectorizer_word.fit(all_abstracts)

def calculate_normalized_idf(bigram):
    bividf = bigram_idf[bigram]
    if bividf:
        f, s = bigram.split()
        fidf = vectorizer_word.idf_[vectorizer_word.vocabulary_[f]]
        sidf = vectorizer_word.idf_[vectorizer_word.vocabulary_[s]]
        newscore = fidf * sidf / float(bividf)
    else:
        newscore = 0
    return newscore

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

    abstract_recs = defaultdict(set)

    bact_related_articles = []
    bact_related_article_ids = set()
    for row in connection.execute(
            select([articles.c.id.label('pid'),
                    articles.c.data['AB'].label('abstract'),
                    articles.c.data['TI'].label('title'),
                    articles.c.data['AU'].label('authors'),
                    articles.c.data['TA'].label('journal'),
                    articles.c.pubyear,
                    org_articles.c.article_id,
                    org_articles.c.organism_id,
                    organisms.c.species]).select_from(
                articles.join(org_articles).join(organisms)).where(
                org_articles.c.organism_id == bactid)):
        if row.pid not in bact_related_article_ids:
            bact_related_articles.append(row)
            bact_related_article_ids.add(row.pid)

        for s in connection.execute(select(
                [org_articles, organisms.c.species, organisms.c.id.label('oid')]) \
                .select_from(org_articles.join(organisms)).where(
            org_articles.c.article_id == row.article_id)):
            # if row.organism_id != s.organism_id:
            article_links[s.organism_id].add((row.article_id, s.species, s.oid))
            abstract_recs[s.article_id].add((s.organism_id, s.species))

    important_keyword_items = {}
    for pid, orgs in abstract_recs.items():
        related_bigrams = connection.execute(
            select([bigram_tbl]).select_from(
                bigram_tbl.join(org_articles, org_articles.c.article_id==bigram_tbl.c.article_id)).where(and_(
                bigram_tbl.c.article_id == pid, org_articles.c.organism_id == bactid)
            )).fetchall()
        for bigram in related_bigrams:
            if bigram.tfidf:
                important_keyword_items[bigram.id] = (bigram.id, bigram.text, bigram.tfidf,
                                                      orgs, calculate_normalized_idf(bigram.text))

    important_keyword_items = sorted(important_keyword_items.values(),
                                     key=lambda x: x[-1], reverse=True)[:20]
    # important_keyword_items = sorted(important_keyword_items, key=lambda x: float(x[2]), reverse=True)[:20]
    important_keywords = ((w[1].title(), round(float(w[-1]),2), w[3])
                              for w in important_keyword_items)

    nodes = []
    edges = []
    _nodes = set()
    for kw in important_keyword_items:
        bid, btext, bscore, borgs, nbscore = kw
        bscore = round(float(bscore), 2)
        # keyword nodes
        if bid not in _nodes:
            _nodes.add(bid)
            nodes.append({
                'id': bid,
                'label': btext,
                'color': '#eef442',
                'size': 4,
                'font': {'size': 16, 'background': '#eef442'}
            })
        for org in borgs:
            # pathogen nodes
            if org[0] not in _nodes:
                _nodes.add(org[0])
                nodes.append({
                    'id': org[0],
                    'label': org[1].capitalize(),
                    'shape': 'circularImage',
                    'image': url_for('static', filename='img/bacteria.png'),
                    'color': '#ff6600' if org[0] == bactid else '#42f489',
                    'font': {'background': '#ff6600', 'color': 'white', 'size': 18}
                })
            edges.append({
                'from': org[0],
                'to': bid,
                'title': btext,
                'color': {
                    'color': '#d1560a' if org[0] == bactid else '#04894b',
                    'highlight': '#ffcc00',
                    'opacity': 1.0
                },
            })

    common_links = set(wiki_links.keys()).intersection(set(article_links.keys()))
    species_article_links = defaultdict(set)
    for sp in common_links:
        the_links = article_links[sp]
        for lnk in the_links:
            species_article_links[Species(lnk[2], lnk[1].capitalize())].add(lnk[0])

    try:
        wiki_summary = wikipedia.summary(
                            bacteria.species.capitalize(),
                            sentences=20)
        wiki_page = wikipedia.page(bacteria.species.capitalize())
    except (wikipedia.exceptions.PageError, wikipedia.exceptions.DisambiguationError):
        wiki_summary = 'Wikipedia Summary not Available'
        wiki_page = None
        gram_stain = None
    else:
        try:
            gram_stain = gram_pattern.findall(wiki_summary)[0].lower()
        except IndexError:
            gram_stain = None

    article_timeline = {}
    years = range(2000, datetime.now().year + 1)
    for sid in common_links:
        if sid == bactid:
            continue
        s = select([organisms.c.species, articles.c.pubyear]).select_from(
            articles.join(org_articles).join(organisms)).where(org_articles.c.organism_id == sid)
        for row in connection.execute(s):
            if row.pubyear > 1999:
                if row.species not in article_timeline:
                    article_timeline[row.species] = dict([(y, 0) for y in years])
                article_timeline[row.species][row.pubyear] += 1

    s = select([organisms.c.species, articles.c.pubyear]).select_from(
        articles.join(org_articles).join(organisms)).where(org_articles.c.organism_id == bactid)
    for row in connection.execute(s):
        if row.pubyear > 1999:
            if row.species not in article_timeline:
                article_timeline[row.species] = dict([(y, 0) for y in years])
            article_timeline[row.species][row.pubyear] += 1

    article_timeline_data = []
    article_timeline_list = list(article_timeline)
    if bacteria.species in article_timeline_list:
        article_timeline_list.remove(bacteria.species)
    if len(article_timeline_list) > 4:
        random.shuffle(article_timeline_list)
        sp_choices = article_timeline_list[:4]
    else:
        sp_choices = list(article_timeline)
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
                           years=list(years),
                           important_keywords=important_keywords,
                           bact_related_articles=bact_related_articles,
                           gram_stain=gram_stain,
                           )


@app.route('/about')
def about():
    return render_template('about.html')
