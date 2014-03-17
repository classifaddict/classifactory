import os

from lxml import etree

from rdflib import URIRef, Literal, BNode, Namespace, Graph
from rdflib.namespace import RDF, SKOS

from django.conf import settings

from app_scheme.models import Concept, Definition, Reference


class IpcEntry:
    def __init__(self, entry, tree):
        self.entry = entry
        self.tree = tree
        self.kind = entry.get('kind')
        self.id = None
        self.label = None
        self.titles = None
        self.children = None
        self.depth = settings.DEPTHS.index(self.kind) + 1

        if self.kind in ['t', 'g']:
            # Assign range based id to SubSections and Guidance Headings 
            self.id = '%s-%s' % (
                entry.get('symbol'),
                entry.get('endSymbol', 'last')
            )
            self.label = self.decode_symbol(entry.get('symbol'))
            if entry.get('endSymbol') is not None:
                self.label += ' - ' + self.decode_symbol(entry.get('endSymbol'))
        else:
            self.id = entry.get('symbol')
            self.label = self.decode_symbol(self.id)

        self.get_titles()
        self.get_children()

    def decode_group(self, symbol):
        f = float('.'.join([symbol[4:8], symbol[8:]]))
        if len(str(f).split('.')[1]) == 1:
            f = '%.2F' % f
        else:
            f = str(f)
        return f.replace('.', '/')

    def decode_symbol(self, symbol):
        if len(symbol) < 5:
            return symbol
        return '%s %s' % (symbol[:4], self.decode_group(symbol))

    def get_ref(self, symbol):
        return '<a href="#%s">%s</a>' % (symbol, self.decode_symbol(symbol))

    def get_texts(self, text):
        texts = ''

        if text.tag == 'mref':
            texts += '%s - %s' % (self.get_ref(text.get('ref')), self.get_ref(text.get('endRef')))
        elif text.tag == "sref":
            texts += self.get_ref(text.get('ref'))
        elif text.tag == "emdash":
            texts += '-'
        elif text.tag not in ['entryReference', 'text']:
            print etree.tostring(text)

        if text.text is not None:
            texts += text.text

        for t in text:
            texts += self.get_texts(t)

        if text.tail is not None:
            texts += text.tail.rstrip()

        return texts

    def get_titles(self):
        titleparts = self.entry.xpath('./textBody/title/titlePart')
        if len(titleparts):
            self.titles = []
            for tp in titleparts:
                title = [self.get_texts(tp[0])]
                if len(tp) > 1:
                    title.append([self.get_texts(ref) for ref in tp[1:]])
                else:
                    title.append([])
                self.titles.append(title)

    def get_xml_titles(self):
        title_list = ''
        for lang, titles in self.items.iteritems():
            title = '<span class="h%d" xml:lang="%s">' % (self.depth, lang)
            subtitles = []
            for title in titles:
                subtitle = '<span class="title">%s</span>' % title[0]
                if len(title[1]):
                    subtitle += '<span class="refs"> ('
                    subtitle += '; '.join(title[1])
                    subtitle += ')</span>'
                subtitles.append(subtitle)
            title += '; '.join(subtitles)
            title += '</span>'
            title_list += title
        return title_list

    def _build_ranges(self, rangekind, children):
        r = None
        prev_symbol = None
        for c in children:
            if c.get('kind') == rangekind:
                if r is not None and r.get('endSymbol') is None:
                    r.set('endSymbol', prev_symbol)
                r = c
            elif r is None:
                r = etree.Element('ipcEntry', kind=rangekind, symbol=c.get('symbol'))
                self.entry.append(r)
                r.append(c)
            else:
                r.append(c)
                if c.get('symbol') == r.get('endSymbol'):
                    r = None
            prev_symbol = c.get('symbol')

    def get_children(self):
        #if parent.get("symbol") == 'A01N0061020000': import pdb; pdb.set_trace()
        #TODO: process 'n'
        if self.kind == 's':
            self._build_ranges('t', self.entry.xpath('./ipcEntry[@kind="c" or @kind="t"]'))
            self.children = self.entry.xpath('./ipcEntry[@kind="t"]')

        elif self.kind == 'u':
            self._build_ranges('g', self.entry.xpath('./ipcEntry[@kind="m" or @kind="g"]'))
            self.children = self.entry.xpath('./ipcEntry[@kind="g"]')

        else:
            self.children = self.entry.xpath('./ipcEntry[@kind!="t" and @kind!="n" and @kind!="g" and @kind!="i"]')


def db_load_concept(entry, lang, parent=None):
        cObj, created = Concept.objects.get_or_create(
            notation=entry.id,
            label=entry.label,
            depth=entry.depth,
        )
        cObj.save()

        if created and parent is not None:
            cObj.parent = parent

        if entry.titles is not None:
            for title in entry.titles:
                dObj = Definition(
                    concept=cObj,
                    text=title[0],
                    lang=lang
                )
                dObj.save()
                for ref in title[1]:
                    rObj = Reference(
                        definition=dObj,
                        text=ref,
                        lang=lang
                    )
                    rObj.save()
                dObj.save()
        cObj.save()
        return cObj


class IpcScheme:
    def __init__(self, version):
        self.version = version
        self.tree = None
        self.graph = None
        self.sections = None

    def get_tree(self):
        if self.tree is None:
            self.tree = etree.parse(os.path.join(settings.DATA_DIR, 'ipcr_scheme_%s.xml' % self.version))
            #import ipdb; ipdb.set_trace()

    def init_graph(self):
        self.graph = Graph()
        self.graph.bind('skos', SKOS)

    def get_entry(self, entry):
        return IpcEntry(entry, self.tree)

    def add_concept(self, entry):
        concept = URIRef('#%s' % entry.id)
        self.graph.add((concept, RDF.type, SKOS.Concept))
        self.graph.add((concept, SKOS.notation, Literal(entry.id)))
        self.graph.add((concept, SKOS.prefLabel, Literal(entry.label)))
        self.graph.add((concept, SKOS.depth, Literal(str(entry.depth))))

        if entry.titles is not None:
            self.graph.add((concept, SKOS.definition, Literal(entry.titles, datatype=RDF.XMLLiteral)))

        return concept

    def recurse_collections(self, entry, broader):
        if len(entry.children):
            collection = self.add_collection(entry.id, broader)
            for child in entry.children:
                e = self.get_entry(child)
                concept = self.add_concept(e)
                self.graph.add((collection, SKOS.member, concept))
                self.recurse_collections(e, concept)

    def add_collection(self, parent_id, broader):
        collection = URIRef('#entries/%s' % parent_id)
        self.graph.add((collection, RDF.type, SKOS.Collection))
        self.graph.add((collection, SKOS.broader, broader))
        self.graph.add((broader, SKOS.narrower, collection))

        return collection

    def build_graph(self):
        self.init_graph()

        scheme = URIRef('#scheme')
        self.graph.add((scheme, RDF.type, SKOS.ConceptScheme))

        self.get_tree()
        sections = self.tree.xpath('//en')[0][0]
        for section in sections:
            s = self.get_entry(section)
            concept = self.add_concept(s)
            self.graph.add((scheme, SKOS.hasTopConcept, concept))
            self.recurse_collections(s, concept)

    def recurse_entries(self, entry, lang, parent):
        if len(entry.children):
            for child in entry.children:
                e = self.get_entry(child)
                cObj = db_load_concept(e, lang, parent)
                self.recurse_entries(e, lang, cObj)

    def db_load(self):
        self.get_tree()
        for lang in ['en', 'fr']:
            sections = self.tree.xpath('//' + lang)[0][0]
            for section in sections:
                entry = self.get_entry(section)
                sObj = db_load_concept(entry, lang)
                self.recurse_entries(entry, lang, sObj)

    def save_graph(self):
        fp = open(os.path.join(settings.DATA_DIR, 'ipc_%s.rdf' % self.version), 'w')
        fp.write(self.graph.serialize(format='pretty-xml'))
        fp.close()


def make_rdf(version):
    scheme = IpcScheme(version)
    scheme.build_graph()
    scheme.save_graph()


def load(version):
    scheme = IpcScheme(version)
    scheme.db_load()


def main():
    make_rdf('20140101')

    # CAUTION: To perform SPARQL query following namespace must be in RDF/XML file
    #xmlns:ipc="http://www.wipo.int/ipc/"
    #xmlns:xhtml="http://www.w3.org/1999/xhtml"
    import sys; sys.exit(0)
    ipc = Graph()
    ipc.bind('skos', SKOS)

    ipc.parse('ipc_20140101.rdf')
    #q = "SELECT ?entry WHERE {?entry skos:notation 'A01N'}"
    q = "SELECT ?definition WHERE {?concept a skos:Concept . ?concept skos:definition ?definition}"
    r = ipc.query(q)
    for row in r:
        print row[0]
    print len(r)

if __name__ == '__main__':
    main()
