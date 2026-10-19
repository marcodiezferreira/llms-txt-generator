# llms-txt-generator

> **EN** · Generate the `llms.txt` file of any website from its sitemap: reads every page (title, meta description, H1), groups them by section and writes a ready-to-upload Markdown file following [llmstxt.org](https://llmstxt.org). Single Python file, zero dependencies. Docs below in Spanish.

**Crea el `llms.txt` de tu web en un minuto, a partir de su sitemap.**

`llms.txt` es un fichero en Markdown que se sube a la raíz de la web (`https://tu-web.com/llms.txt`) y resume quién eres y cuáles son tus páginas clave. Está pensado para que ChatGPT, Gemini, Perplexity y el resto de asistentes con IA entiendan tu web sin rastrearla entera. El formato está propuesto en [llmstxt.org](https://llmstxt.org).

Escribirlo a mano es tedioso y se queda viejo en cuanto publicas algo. Este script lo genera desde tu sitemap.

Sin instalar nada: solo Python 3.10 o superior.

## Uso

```bash
python llms_txt.py https://tu-web.com -o llms.txt
```

Con tu nombre y un resumen propio:

```bash
python llms_txt.py https://tu-web.com -o llms.txt --nombre "Tu Marca" --resumen "Qué haces y para quién, en una o dos frases."
```

Para webs grandes o con secciones que no interesan:

```bash
python llms_txt.py https://tu-web.com -o llms.txt --max 120 --excluir /etiqueta/ --excluir /portfolio-antiguo/
```

## Qué genera

```markdown
# Tu Marca

> Qué haces y para quién, en una o dos frases.

## Páginas principales

- [Inicio](https://tu-web.com/): descripción de la portada.

## Blog

- [Guía de SEO local](https://tu-web.com/blog/seo-local/): cómo conseguir que te encuentren en tu zona.
- [Automatizar el correo](https://tu-web.com/blog/automatizar-correo/): un flujo práctico paso a paso.

## Otras páginas

- [Contacto](https://tu-web.com/contacto/): cómo hablar conmigo.
```

## Cómo funciona

1. Busca el sitemap en `robots.txt` y, si no lo declara, en `/sitemap.xml` y `/sitemap_index.xml`. Sigue los índices de sitemaps (WordPress, Yoast, Rank Math…).
2. Lee cada página en paralelo y saca el título, la meta descripción y el H1. Salta las páginas con `noindex`.
3. Quita el nombre de la web del final de los títulos («Servicios | Tu Marca» pasa a «Servicios»).
4. Agrupa por la primera parte de la ruta (`/blog/`, `/servicios/`…) y deja las páginas sueltas al final.
5. Excluye por defecto lo que no aporta: etiquetas, autores, paginación, carrito, avisos legales, administración…

El resultado es un buen punto de partida: revísalo, añade lo que falte (precios, datos de contacto, lo que no está en la web) y súbelo a la raíz.

## Pruebas

```bash
python -m unittest -v
```

## Relacionado

- [ai-seo-audit](https://github.com/marcodiezferreira/ai-seo-audit): comprueba si tu web está preparada para los buscadores con IA, también si tiene `llms.txt`.

## Autor

Hecho por [Marco Díez](https://marcodiez.es): marketing digital y desarrollo.
¿Quieres que prepare tu web para los buscadores con IA? [Escríbeme](https://marcodiez.es/contacto/).

Licencia MIT.
