"""Pruebas sin red: python -m unittest -v"""
import unittest

import llms_txt as l

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://ejemplo.com/</loc></url><url><loc>https://ejemplo.com/blog/uno/</loc></url></urlset>"""
INDICE = """<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://ejemplo.com/post-sitemap.xml</loc></sitemap></sitemapindex>"""


class SitemapTest(unittest.TestCase):
    def test_urlset(self):
        self.assertEqual(l.urls_de_sitemap(SITEMAP), (['https://ejemplo.com/', 'https://ejemplo.com/blog/uno/'], []))

    def test_indice(self):
        self.assertEqual(l.urls_de_sitemap(INDICE), ([], ['https://ejemplo.com/post-sitemap.xml']))

    def test_xml_roto(self):
        self.assertEqual(l.urls_de_sitemap('<no'), ([], []))


class HTMLTest(unittest.TestCase):
    def test_lector(self):
        p = l.LectorHTML()
        p.feed('<html><head><title>Servicios | Mi Marca</title><meta name="description" content="Lo que hago."></head>'
               '<body><h1>Servicios</h1><h1>Otro</h1></body></html>')
        self.assertEqual((p.titulo, p.descripcion, p.h1, p.noindex), ('Servicios | Mi Marca', 'Lo que hago.', 'Servicios', False))

    def test_noindex(self):
        p = l.LectorHTML()
        p.feed('<meta name="robots" content="noindex, follow">')
        self.assertTrue(p.noindex)

    def test_limpiar_titulo(self):
        self.assertEqual(l.limpiar_titulo('Servicios | Mi Marca', 'Mi Marca'), 'Servicios')
        self.assertEqual(l.limpiar_titulo('Guía de SEO local - Blog - Mi Marca', 'Mi Marca'), 'Guía de SEO local - Blog')
        self.assertEqual(l.limpiar_titulo('Sin separador'), 'Sin separador')


class ConstruirTest(unittest.TestCase):
    def test_agrupa_por_seccion(self):
        paginas = [l.Pagina('https://ejemplo.com/', 'Inicio | Marca', 'Portada.', '', True),
                   l.Pagina('https://ejemplo.com/blog/a/', 'Post A | Marca', 'Sobre A.', '', True),
                   l.Pagina('https://ejemplo.com/blog/b/', 'Post B | Marca', '', '', True),
                   l.Pagina('https://ejemplo.com/contacto/', 'Contacto | Marca', 'Escríbeme.', '', True)]
        txt = l.construir('Marca', 'Hacemos cosas.', paginas, 'https://ejemplo.com')
        self.assertTrue(txt.startswith('# Marca\n\n> Hacemos cosas.\n'))
        self.assertIn('## Páginas principales\n\n- [Inicio](https://ejemplo.com/): Portada.', txt)
        self.assertIn('## Blog\n\n- [Post A](https://ejemplo.com/blog/a/): Sobre A.\n- [Post B](https://ejemplo.com/blog/b/)', txt)
        self.assertIn('## Otras páginas\n\n- [Contacto](https://ejemplo.com/contacto/): Escríbeme.', txt)

    def test_corchetes_no_rompen_markdown(self):
        txt = l.linea(l.Pagina('https://e.com/x/', 'Guía [2026]', '', '', True), '')
        self.assertEqual(txt, '- [Guía (2026)](https://e.com/x/)')


if __name__ == '__main__':
    unittest.main()
