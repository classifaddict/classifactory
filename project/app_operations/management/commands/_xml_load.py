import os
from lxml import etree
from django.conf import settings
from app_tree.models import Doctype, Element, Attribute, Data

doctypes = {
    'ipcr_scheme': {
        'except_attr': ['lang', 'ipcLevel', 'priorityOrder'],
        'except_attr_val': [('entryType', 'K')],
        'data_elt': ['text', 'references', 'entryReference', 'noteParagraph'],
        'lazy_elt': ['ipcEntry']
    }
}


def store_element(elt, doctype, datas, parent=None):
    lazy = elt.tag in doctypes[doctype.name]['lazy_elt']
    e = Element.objects.create(
        doctype=doctype,
        name=elt.tag,
        parent=parent,
        is_lazy=lazy
    )

    for name, value in elt.items():
        if name not in doctypes[doctype.name]['except_attr']
        and value
        and not (name, value) in doctypes[doctype.name]['except_attr_val']:
            a, c = Attribute.objects.get_or_create(
                doctype=doctype,
                name=name,
                value=value
            )
            e.attributes.add(a)
    e.save()

    if elt.tag in doctypes[doctype.name]['data_elt']:
        datas.append(Data(element=e, lang='en', texts=etree.tostring(elt)))
    else:
        for child in elt:
            store_element(child, doctype, datas, parent=e)


def load(doctype, file_version, file_extension='xml'):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(os.path.join(
        settings.DATA_DIR,
        doctype + '_' + file_version + '.' + file_extension
    ), parser)
    root = tree.getroot()

    doctype, c = Doctype.objects.get_or_create(name=doctype)

    datas = []
    store_element(root, doctype, datas=datas)
    Data.objects.bulk_create(datas)
