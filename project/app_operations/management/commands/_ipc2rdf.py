import os
from lxml import etree
from django.conf import settings
from rdflib import URIRef, Literal, BNode, Namespace, Graph
from rdflib.namespace import RDF, SKOS
from _ipc_load import IpcEntry

class IpcSkosScheme:

    def get_tree(self):
        if self.tree is None:
            self.tree = etree.parse(os.path.join(settings.DATA_DIR, 'ipcr_scheme_%s.xml' % self.version))

    def get_entry(self, entry):
        return IpcEntry(entry, self.tree)

    def init_graph(self):
        self.graph = Graph()
        self.graph.bind('skos', SKOS)

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

    def save_graph(self):
        fp = open(os.path.join(settings.DATA_DIR, 'ipc_%s.rdf' % self.version), 'w')
        fp.write(self.graph.serialize(format='pretty-xml'))
        fp.close()


def make_rdf(version):
    scheme = IpcSkosScheme(version)
    scheme.build_graph()
    scheme.save_graph()


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
