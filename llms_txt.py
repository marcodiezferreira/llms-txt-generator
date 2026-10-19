#!/usr/bin/env python3
"""llms-txt-generator: crea el llms.txt de una web a partir de su sitemap.

llms.txt es un fichero Markdown en la raíz de la web (https://tu-web.com/llms.txt) que resume quién eres y cuáles son
tus páginas clave, pensado para que los asistentes y buscadores con IA entiendan tu web sin rastrearla entera.
Formato propuesto en https://llmstxt.org: título, resumen en cita, datos y secciones con enlaces.

Este script:
  1. encuentra el sitemap (robots.txt o /sitemap.xml; también índices de sitemaps),
  2. lee cada página (título, meta descripción, H1),
  3. las agrupa por sección según la ruta (/blog/, /servicios/…),
  4. escribe el llms.txt listo para subir.

Uso:
  python llms_txt.py https://tu-web.com
  python llms_txt.py https://tu-web.com -o llms.txt --nombre "Tu Marca" --resumen "Qué haces en una frase"
  python llms_txt.py https://tu-web.com --max 80 --excluir /etiqueta/ --excluir /autor/
Solo biblioteca estándar de Python 3.10+.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass
from html.parser import HTMLParser

AGENTE = 'llms-txt-generator/1.0 (+https://github.com/marcodiezferreira/llms-txt-generator)'
NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
# Rutas que casi nunca aportan a un llms.txt.
EXCLUIR_POR_DEFECTO = ['/wp-admin', '/wp-json', '/feed', '/tag/', '/etiqueta/', '/author/', '/autor/', '/page/', '/carrito',
                       '/cart', '/checkout', '/mi-cuenta', '/my-account', '/aviso-legal', '/privacidad', '/cookies', '/legal']
NOMBRES_SECCION = {'blog': 'Blog', 'noticias': 'Noticias', 'servicios': 'Servicios', 'proyectos': 'Proyectos', 'productos': 'Productos',
                   'tienda': 'Tienda', 'docs': 'Documentación', 'casos': 'Casos', 'recursos': 'Recursos', 'sobre-mi': 'Sobre mí',
                   'sobre-nosotros': 'Sobre nosotros', 'contacto': 'Contacto'}


@dataclass
class Pagina:
    url: str
    titulo: str = ''
    descripcion: str = ''
    h1: str = ''
    ok: bool = False


# ---------------------------------------------------------------------------------------------- red
def pedir(url: str, timeout: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={'User-Agent': AGENTE, 'Accept-Language': 'es,en;q=0.8'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(2_000_000).decode(r.headers.get_content_charset() or 'utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, ''


# ---------------------------------------------------------------------------------------------- sitemap
def urls_de_sitemap(xml: str) -> tuple[list[str], list[str]]:
    """Devuelve (páginas, sub-sitemaps) de un sitemap o de un índice de sitemaps."""
    try:
        raiz = ET.fromstring(xml.strip().encode('utf-8'))
    except ET.ParseError:
        return [], []
    locs = [(e.text or '').strip() for e in raiz.iter(f'{NS}loc')] or [(e.text or '').strip() for e in raiz.iter('loc')]
    if raiz.tag.endswith('sitemapindex'):
        return [], [u for u in locs if u]
    return [u for u in locs if u], []


def descubrir_sitemaps(raiz: str) -> list[str]:
    estado, robots = pedir(raiz + '/robots.txt')
    encontrados = re.findall(r'(?im)^\s*sitemap:\s*(\S+)', robots) if estado == 200 else []
    return encontrados or [raiz + '/sitemap.xml', raiz + '/sitemap_index.xml']


def leer_sitemaps(raiz: str, limite_sitemaps: int = 50) -> list[str]:
    pendientes, vistos, paginas = descubrir_sitemaps(raiz), set(), []
    while pendientes and len(vistos) < limite_sitemaps:
        s = pendientes.pop(0)
        if s in vistos:
            continue
        vistos.add(s)
        estado, xml = pedir(s)
        if estado != 200:
            continue
        p, subs = urls_de_sitemap(xml)
        paginas += p
        pendientes += subs
    return list(OrderedDict.fromkeys(paginas))


# ---------------------------------------------------------------------------------------------- páginas
class LectorHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titulo, self.descripcion, self.h1, self.og_titulo, self.og_desc, self.noindex = '', '', '', '', '', False
        self._en, self._buffer = None, ''

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or '') for k, v in attrs}
        if tag == 'meta':
            nombre = (a.get('name') or a.get('property') or '').lower()
            if nombre == 'description':
                self.descripcion = a.get('content', '').strip()
            elif nombre == 'og:title':
                self.og_titulo = a.get('content', '').strip()
            elif nombre == 'og:description':
                self.og_desc = a.get('content', '').strip()
            elif nombre == 'robots' and 'noindex' in a.get('content', '').lower():
                self.noindex = True
        if tag in ('title', 'h1') and not (tag == 'h1' and self.h1):
            self._en, self._buffer = tag, ''

    def handle_data(self, data):
        if self._en:
            self._buffer += data

    def handle_endtag(self, tag):
        if self._en == tag:
            texto = re.sub(r'\s+', ' ', self._buffer).strip()
            if tag == 'title':
                self.titulo = texto
            else:
                self.h1 = texto
            self._en = None


def limpiar_titulo(titulo: str, nombre: str = '') -> str:
    """Quita el nombre de la web del final del título («Servicios | Mi Marca» → «Servicios»)."""
    partes = re.split(r'\s+[|·–—-]\s+', titulo)
    if len(partes) > 1 and (not nombre or nombre.lower() in partes[-1].lower() or len(partes[-1]) < 40):
        return ' - '.join(partes[:-1]).strip() or titulo
    return titulo


def leer_pagina(url: str) -> Pagina:
    estado, html = pedir(url)
    if estado != 200:
        return Pagina(url)
    p = LectorHTML()
    p.feed(html)
    if p.noindex:
        return Pagina(url)
    return Pagina(url, p.og_titulo or p.titulo, p.descripcion or p.og_desc, p.h1, True)


# ---------------------------------------------------------------------------------------------- llms.txt
def seccion_de(url: str) -> str:
    ruta = urllib.parse.urlparse(url).path.strip('/')
    return ruta.split('/')[0] if ruta else ''


def nombre_seccion(slug: str) -> str:
    return NOMBRES_SECCION.get(slug, slug.replace('-', ' ').capitalize()) if slug else 'Páginas principales'


def construir(nombre: str, resumen: str, paginas: list[Pagina], raiz: str) -> str:
    grupos: OrderedDict[str, list[Pagina]] = OrderedDict()
    for p in paginas:
        grupos.setdefault(seccion_de(p.url), []).append(p)
    # Primero las páginas sueltas de la raíz (inicio, sobre mí…), después las secciones con más páginas.
    orden = sorted(grupos, key=lambda s: (s != '', -len(grupos[s]) if len(grupos[s]) > 1 else 0, s))
    sueltas = [s for s in orden if s and len(grupos[s]) == 1]
    lineas = [f'# {nombre}', '', f'> {resumen}', '']
    for s in [x for x in orden if x == '' or len(grupos[x]) > 1]:
        lineas += [f'## {nombre_seccion(s)}', '']
        lineas += [linea(p, nombre) for p in grupos[s]] + ['']
    if sueltas:
        lineas += ['## Otras páginas', '']
        lineas += [linea(grupos[s][0], nombre) for s in sueltas] + ['']
    return '\n'.join(lineas).rstrip() + '\n'


def linea(p: Pagina, nombre: str) -> str:
    titulo = limpiar_titulo(p.titulo or p.h1 or p.url, nombre).replace('[', '(').replace(']', ')')
    desc = re.sub(r'\s+', ' ', p.descripcion).strip()
    return f'- [{titulo}]({p.url})' + (f': {desc}' if desc else '')


def generar(url: str, nombre: str = '', resumen: str = '', maximo: int = 60, excluir: list[str] | None = None,
            hilos: int = 6, avisar=print) -> str:
    if not re.match(r'^https?://', url):
        url = 'https://' + url
    partes = urllib.parse.urlparse(url)
    raiz = f'{partes.scheme}://{partes.netloc}'
    filtros = EXCLUIR_POR_DEFECTO + (excluir or [])
    urls = [u for u in leer_sitemaps(raiz) if urllib.parse.urlparse(u).netloc == partes.netloc and not any(f in u for f in filtros)]
    if not urls:
        urls = [raiz + '/']
        avisar('No he encontrado sitemap: uso solo la portada.')
    if len(urls) > maximo:
        avisar(f'El sitemap tiene {len(urls)} páginas: uso las {maximo} primeras (cámbialo con --max).')
        urls = urls[:maximo]
    with cf.ThreadPoolExecutor(max_workers=hilos) as ex:
        paginas = [p for p in ex.map(leer_pagina, urls) if p.ok]
    portada = next((p for p in paginas if urllib.parse.urlparse(p.url).path in ('', '/')), None) or leer_pagina(raiz + '/')
    if not nombre:
        nombre = limpiar_titulo(portada.titulo or partes.netloc)
    resumen = resumen or portada.descripcion or f'Web de {nombre}.'
    avisar(f'{len(paginas)} páginas leídas.')
    return construir(nombre, resumen, paginas, raiz)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Crea el llms.txt de una web a partir de su sitemap.')
    ap.add_argument('url')
    ap.add_argument('-o', '--salida', help='fichero de salida (por defecto, se imprime)')
    ap.add_argument('--nombre', default='', help='nombre de la web o la marca (por defecto, el título de la portada)')
    ap.add_argument('--resumen', default='', help='una o dos frases sobre qué haces (por defecto, la descripción de la portada)')
    ap.add_argument('--max', type=int, default=60, help='máximo de páginas a leer (60)')
    ap.add_argument('--excluir', action='append', default=[], help='excluir URLs que contengan este texto (se puede repetir)')
    a = ap.parse_args(argv)
    texto = generar(a.url, a.nombre, a.resumen, a.max, a.excluir, avisar=lambda m: print(m, file=sys.stderr))
    if a.salida:
        with open(a.salida, 'w', encoding='utf-8', newline='\n') as f:
            f.write(texto)
        print(f'Escrito {a.salida}', file=sys.stderr)
    else:
        print(texto, end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
