import os
from lxml import etree
from django.conf import settings
from app_tree.models import Element, Attribute, Data


except_attr = ['lang', 'ipcLevel', 'priorityOrder']
except_attr_val = [('entryType', 'K')]
data_elt = ['text', 'references', 'entryReference', 'noteParagraph']

def store_element(elt, attrs, datas, parent=None):
    e = Element.objects.create(name=elt.tag, parent=parent)

    attrs.extend([
        Attribute(
            element=e,
            name=name,
            value=value
        ) for name, value in sorted(
            elt.items()
        ) if name not in except_attr and value and not (
            name, value
        ) in except_attr_val
    ])

    if elt.tag in data_elt:
        datas.append(Data(element=e, lang='en', texts=etree.tostring(elt)))
    else:
        for child in elt:
            store_element(child, attrs, datas, parent=e)


def load(filename):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(os.path.join(settings.DATA_DIR, filename), parser)
    root = tree.getroot()

    attrs = []
    datas = []
    store_element(root, attrs=attrs, datas=datas)
    Attribute.objects.bulk_create(attrs)
    Data.objects.bulk_create(datas)
