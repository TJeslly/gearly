import os, sys, tempfile
from pathlib import Path
AQUI = Path(__file__).parent
os.environ['GEARLY_DATOS'] = str(AQUI / 'datos_prueba')  # catálogo ficticio solo para pruebas
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'prueba.db')
os.environ['ADMIN_CLAVE'] = 'clave-prueba'
sys.path.insert(0, str(AQUI.parent))
