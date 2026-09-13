import json
import unittest
import xml.etree.ElementTree as ET
from collections import Counter, deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://bg-remover-free.netlify.app'
ARTICLES = (
    'background-remover-api', 'no-upload-background-remover',
    'vs-removebg', 'vs-photoroom', 'bgclear-vs-canva',
    'batch-background-removal-workflow', 'make-background-white',
)
PRIORITY = ('index', 'it', 'fr', 'guide') + ARTICLES


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.canonicals = []
        self.alternates = []
        self.meta = {}
        self.hrefs = []
        self.ids = []
        self.h1_count = 0
        self.schemas = []
        self._schema = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'a' and attrs.get('href'):
            self.hrefs.append(attrs['href'])
        if tag == 'meta':
            self.meta[attrs.get('name') or attrs.get('property')] = attrs.get('content')
        if tag == 'link':
            rel = (attrs.get('rel') or '').lower().split()
            if 'canonical' in rel:
                self.canonicals.append(attrs.get('href'))
            if 'alternate' in rel and attrs.get('hreflang'):
                self.alternates.append((attrs['hreflang'], attrs.get('href')))
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self._schema = []

    def handle_data(self, data):
        if self._schema is not None:
            self._schema.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self._schema is not None:
            self.schemas.append(json.loads(''.join(self._schema)))
            self._schema = None


def read_page(stem):
    return Page((ROOT / (stem + '.html')).read_text(encoding='utf-8'))


def route(path):
    if path.endswith('.html'):
        path = path[:-5]
    if path == '/index':
        return '/'
    return '/bgclear-vs-canva' if path == '/vs-canva' else path


def page_file(path):
    return ROOT / ('index.html' if path == '/' else path.lstrip('/') + '.html')


class SeoTests(unittest.TestCase):
    def test_priority_metadata_and_json(self):
        for stem in PRIORITY:
            with self.subTest(page=stem):
                page = read_page(stem)
                expected = SITE + ('/' if stem == 'index' else '/' + stem)
                self.assertEqual(page.canonicals, [expected])
                self.assertEqual(page.h1_count, 1)
                self.assertTrue(page.meta.get('description'))
                self.assertEqual(page.meta.get('og:url'), expected)
                self.assertTrue(page.meta.get('twitter:card'))
                self.assertTrue(page.schemas)
                self.assertEqual(len(page.ids), len(set(page.ids)))

    def test_localized_hreflang(self):
        for stem in ('it', 'fr'):
            with self.subTest(page=stem):
                page = read_page(stem)
                counts = Counter(language for language, _ in page.alternates)
                self.assertEqual(counts['x-default'], 1)
                self.assertTrue(all(count == 1 for count in counts.values()))
                self.assertIn((stem, SITE + '/' + stem), page.alternates)

    def test_sitemap_unique_existing_canonical_paths(self):
        tree = ET.parse(ROOT / 'sitemap.xml')
        urls = [node.text for node in tree.findall('.//{*}loc')]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertNotIn(SITE + '/vs-canva', urls)
        self.assertIn(SITE + '/bgclear-vs-canva', urls)
        for url in urls:
            with self.subTest(url=url):
                parsed = urlsplit(url)
                self.assertEqual(parsed.netloc, urlsplit(SITE).netloc)
                self.assertFalse(parsed.path.endswith('.html'))
                self.assertTrue(page_file(parsed.path).is_file())

    def test_exact_redirects_and_no_chains(self):
        rules = {}
        for line in (ROOT / '_redirects').read_text(encoding='utf-8').splitlines():
            fields = line.split()
            if not fields or fields[0].startswith('#'):
                continue
            self.assertNotIn(fields[0], rules, 'Duplicate redirect source')
            rules[fields[0]] = fields[1:]
        for source in ('/vs-canva', '/vs-canva.html', '/bgclear-vs-canva.html'):
            self.assertEqual(rules[source], ['/bgclear-vs-canva', '301!'])
        for stem in ('it', 'fr', 'guide', 'vs-removebg'):
            self.assertEqual(rules['/' + stem + '.html'], ['/' + stem, '301!'])
        self.assertNotIn('/404.html', rules)
        for target, status, *rest in rules.values():
            self.assertNotIn(target, rules, 'Redirect target should not redirect again')

    def test_rewritten_article_links_and_assets(self):
        self.assertTrue((ROOT / 'article.css').is_file())
        for stem in ARTICLES:
            page = read_page(stem)
            for href in page.hrefs:
                resolved = urlsplit(urljoin(SITE + '/' + stem, href))
                if resolved.netloc != urlsplit(SITE).netloc:
                    continue
                with self.subTest(page=stem, href=href):
                    self.assertTrue(href.startswith('/'))
                    self.assertFalse(resolved.path.endswith('.html'))
                    self.assertTrue(page_file(resolved.path).is_file())
                    if resolved.fragment:
                        target = Page(page_file(resolved.path).read_text(encoding='utf-8'))
                        self.assertIn(resolved.fragment, target.ids)

    def test_priority_pages_reachable_from_home(self):
        graph = {}
        for file in ROOT.glob('*.html'):
            # Only link parsing is needed here; unrelated legacy schema is not
            # part of this focused regression suite.
            text = file.read_text(encoding='utf-8')
            import re
            text = re.sub(r'<script\b[^>]*>.*?</script\s*>', '', text, flags=re.I | re.S)
            page = Page(text)
            origin = '/' if file.stem == 'index' else '/' + file.stem
            graph[origin] = set()
            for href in page.hrefs:
                parsed = urlsplit(urljoin(SITE + origin, href))
                if parsed.netloc == urlsplit(SITE).netloc:
                    graph[origin].add(route(parsed.path))
        seen = set()
        queue = deque(['/'])
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            queue.extend(graph.get(current, set()) - seen)
        for stem in ARTICLES:
            self.assertIn('/' + stem, seen)

    def test_api_does_not_advertise_unavailable_product(self):
        text = (ROOT / 'background-remover-api.html').read_text(encoding='utf-8')
        self.assertIn('not a hosted API or downloadable server package', text)
        for unsupported in ('aggregateRating', 'api-waitlist', 'api.yourdomain.com', 'PreOrder'):
            self.assertNotIn(unsupported, text)


if __name__ == '__main__':
    unittest.main()
