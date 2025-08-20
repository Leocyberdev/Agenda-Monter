
import os
from flask_sqlalchemy import SQLAlchemy

# Criar o diretório se não existir
os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)

db = SQLAlchemy()
