import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .models import *

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres+psycopg2://postgres:{}@pg/bactwatchweb'.format(POSTGRES_PASSWORD)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from .views import *
