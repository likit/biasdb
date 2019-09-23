import os
from flask import Flask
from .models import *

app = Flask(__name__)

from .views import *
