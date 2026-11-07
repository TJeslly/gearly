"""Descarga los dos archivos de Amazon Reviews 2023 (McAuley Lab) que usa Gearly.

Uso:  python scripts/descargar_datos.py CARPETA_DATOS
La carpeta debe estar FUERA del repositorio: los datos crudos no se suben a git.
Revisa las condiciones de uso del conjunto antes de redistribuir cualquier archivo.
"""
import sys
import urllib.request
from pathlib import Path

BASE = 'https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/'
ARCHIVOS = {
    'Sports_and_Outdoors.csv': 'benchmark/5core/rating_only/Sports_and_Outdoors.csv',
    'meta_Sports_and_Outdoors.jsonl': 'raw/meta_categories/meta_Sports_and_Outdoors.jsonl',
}


def descargar(url, destino: Path):
    tmp = destino.with_suffix(destino.suffix + '.parcial')
    with urllib.request.urlopen(url) as r, open(tmp, 'wb') as f:
        total = int(r.headers.get('Content-Length') or 0)
        hecho = 0
        while bloque := r.read(1 << 20):
            f.write(bloque)
            hecho += len(bloque)
            if total:
                print(f'\r  {destino.name}: {hecho / 1e6:,.0f} / {total / 1e6:,.0f} MB', end='', flush=True)
    tmp.rename(destino)
    print()


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    carpeta = Path(sys.argv[1]).resolve()
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, ruta in ARCHIVOS.items():
        destino = carpeta / nombre
        if destino.exists():
            print(f'  {nombre}: ya existe, se omite')
            continue
        descargar(BASE + ruta, destino)
    print('Listo. Siguiente paso: python scripts/preparar_datos.py', carpeta)


if __name__ == '__main__':
    main()
