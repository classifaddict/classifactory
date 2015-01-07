import os
from lxml import etree
from django.conf import settings
from app_tree.models import Element, Attribute, Data


def store_element(elt, parent=None):
    e = Element.objects.create(name=elt.tag, parent=parent)
    e.save()

    for name, value in sorted(elt.items()):
        if value:
            a = Attribute.objects.create(element=e, name=name, value=value)
            a.save()

    if elt.tag in ['text', 'references', 'entryReference', 'noteParagraph']:
        d = Data.objects.create(element=e, lang='en', texts=etree.tostring(elt))
        d.save()
    else:
        for child in elt:
            store_element(child, parent=e)


def load(filename):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(os.path.join(settings.DATA_DIR, filename), parser)
    root = tree.getroot()
    store_element(root)
