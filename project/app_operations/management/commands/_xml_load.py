import os
import zipfile
from hashlib import md5
from string import Template

from lxml import etree
from django.conf import settings

from app_tree.models import Doctype, ElementType, AttributeType
from app_tree.models import Dataset, Element, Attribute, Text, TreeNode

doctypes_conf = {
    'ipc_scheme': {
        'data_path': Template('ITOS/IPC/data/$version/ipcr_scheme_and_figures'),
        'file_basename': Template('ipcr_scheme_$version'),
        'main_elts': ['revisionPeriods', 'ipcEntry'],
        'remove_elts': ['fr'],
        'main_attrs': ['symbol'],
        'skip_attrs': [], # ['edition'],
        'remove_attrs': ['lang', 'ipcLevel', 'priorityOrder'],
        'remove_attrs_val': [],
        'mixed_elts': ['text', 'references', 'entryReference']
    }
}


def store_element(elt, dataset, dt_conf, parent=None):

    # Get or create element type object
    elt_type, c = ElementType.objects.get_or_create(
        doctype=dataset.doctype,
        name=elt.tag
    )
    # Update element type object from input occurence
    # (will be saved after attributes object are collected too)
    if elt.tag in dt_conf['mixed_elts']:
        elt_type.is_mixed = True
    if elt.tag in dt_conf['main_elts']:
        elt_type.is_main = True

    # Get or create attribute(s) and collect them
    attrs = []
    attributes = [(k, elt.get(k)) for k in sorted(elt.keys()) if elt.get(k) and k not in dt_conf['remove_attrs'] and (k, elt.get(k)) not in dt_conf['remove_attrs_val']]
    for name, value in attributes:
        # Get or create attribute type object
        att_type, c = AttributeType.objects.get_or_create(
            doctype=dataset.doctype,
            name=name
        )

        # Update element type object with attribute type object
        elt_type.attributes.add(att_type)

        # Update attribute type object from input occurence
        if name in dt_conf['main_attrs']:
            att_type.is_main = True
        if name in dt_conf['skip_attrs']:
            att_type.skip = True
        att_type.save()

        # Get or create attribute object
        a, c = Attribute.objects.get_or_create(
            type=att_type,
            value=value
        )

        attrs.append(a)

    elt_type.save()

    # Get or create texts
    text = None
    if elt_type.is_mixed:
        # Serialize descendance as string, removing root element tags
        # and stripping normal and non-breaking spaces
        contents = etree.tostring(elt).replace(
            '<%s>' % elt.tag, ''
        ).replace(
            '</%s>' % elt.tag, ''
        ).strip(u'\xA0 ')

        # Get or create text object
        text, c = Text.objects.get_or_create(
            doctype=dataset.doctype,
            name=md5(contents).hexdigest(),
            contents=contents
        )

    # If element exists then use it or create a new one
    e, created = Element.objects.get_or_create(
        type=elt_type,
        text=text,
        attrs_key=md5(''.join([
            a.type.name + a.value for a in attrs
    ])).hexdigest())

    if created:
        e.attributes = attrs
        e.save()

    # Attach the element to a new treenode
    treenode = TreeNode.objects.create(
        parent=parent,
        dataset=dataset,
        element=e
    )

    if not elt_type.is_mixed:
        for child in elt:
            if elt.tag not in dt_conf['remove_elts']:
                store_element(child, dataset, dt_conf, parent=treenode)


def load(doctype_name, dataset_version, file_extension='xml'):
    dt_conf = doctypes_conf[doctype_name]

    parser = etree.XMLParser(remove_blank_text=True)

    file_basename = dt_conf['file_basename'].substitute(version=dataset_version)

    path_basename = os.path.join(
        settings.DATA_DIR,
        dt_conf['data_path'].substitute(version=dataset_version),
        file_basename
    )

    if file_extension == 'zip':
        zip_file = zipfile.ZipFile(path_basename + '.' + file_extension)
        file_obj = zip_file.open(file_basename + '.xml')
    else:
        file_obj = open(path_basename + '.' + file_extension)

    tree = etree.parse(file_obj, parser)
    root = tree.getroot()

    doctype, c = Doctype.objects.get_or_create(name=doctype_name)

    dataset, c = Dataset.objects.get_or_create(
        doctype=doctype,
        name=dataset_version
    )

    store_element(root, dataset, dt_conf)
