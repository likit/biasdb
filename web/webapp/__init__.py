import os
from flask import Flask
from .models import *
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

from .views import *
