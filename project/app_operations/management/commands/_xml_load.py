import os
from lxml import etree
from django.conf import settings
from app_tree.models import Doctype, Element, Attribute, Data, TreeNode

doctypes = {
    'ipcr_scheme': {
        'main_attr': ['dataset_version', 'symbol'],
        'except_attr': ['lang', 'ipcLevel', 'priorityOrder'],
        'except_attr_val': [],
        'data_elt': ['text', 'references', 'entryReference', 'noteParagraph'],
        'lazy_elt': ['revisionPeriods', 'ipcEntry']
    }
}


def store_element(elt, doctype, datas, parent=None):

    q = Element.objects.filter(
        doctype=doctype,
        name=elt.tag
    )

    attrs = []
    for name, value in elt.items():
        if name not in doctypes[doctype.name]['except_attr'] \
        and value \
        and not (name, value) in doctypes[doctype.name]['except_attr_val']:
            q = q.filter(attributes__name=name, attributes__value=value)
            a, c = Attribute.objects.get_or_create(
                doctype=doctype,
                name=name,
                value=value
            )
            attrs.append(a)

    texts = ''
    if elt.tag in doctypes[doctype.name]['data_elt']:
        texts = etree.tostring(elt).replace('<' + elt.tag + '>', '').replace('</' + elt.tag + '>', '')
        q = q.filter(data__lang='en', data__texts=texts)

    if q.exists() and parent is not None:
        e = q[0]
    else:
        e = Element.objects.create(
            doctype=doctype,
            name=elt.tag
        )
        e.attributes = attrs
        e.save()

        if texts:
            datas.append(Data(element=e, texts=texts))

    n = TreeNode.objects.create(
        element=e,
        parent=parent,
        is_lazy=elt.tag in doctypes[doctype.name]['lazy_elt']
    )

    if not texts:
        for child in elt:
            store_element(child, doctype, datas, parent=n)

    return e

def load(doctype_name, dataset_version, file_extension='xml'):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(
        os.path.join(
            settings.DATA_DIR,
            doctype_name + '_' + dataset_version + '.' + file_extension
        ),
        parser
    )
    root = tree.getroot()

    doctype, created = Doctype.objects.get_or_create(name=doctype_name)
    if created:
        doctype.main_attr = ' '.join(doctypes[doctype_name]['main_attr'])
        doctype.lazy_nodes = ' '.join(doctypes[doctype_name]['lazy_elt'])
        doctype.save()

    datas = []

    root_obj = store_element(root, doctype, datas)

    a, c = Attribute.objects.get_or_create(
        doctype=doctype,
        name='dataset_version',
        value=dataset_version
    )
    root_obj.attributes.add(a)

    Data.objects.bulk_create(datas)
