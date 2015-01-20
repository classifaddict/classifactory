import os
import zipfile
from hashlib import md5
from string import Template

from lxml import etree
from django.conf import settings

from app_tree.models import Doctype, ElementType, AttributeType
from app_tree.models import Dataset, Element, Attribute, Text, TreeNode

doctypes = {
    'ipc_scheme': {
        'data_path': Template('ITOS/IPC/data/$version/ipcr_scheme_and_figures'),
        'file_basename': Template('ipcr_scheme_$version'),
        'main_elts': ['revisionPeriods', 'ipcEntry'],
        'main_attrs': ['symbol'],
        'skip_attrs': ['edition'],
        'remove_attrs': ['lang', 'ipcLevel', 'priorityOrder'],
        'remove_attrs_val': [],
        'mixed_elts': ['text', 'references', 'entryReference']
    }
}


def store_element(elt, dataset, parent=None):

    # Search for element type with or create a new one
    elt_type, c = ElementType.objects.get_or_create(
        doctype=dataset.doctype,
        name=elt.tag
    )
    if elt.tag in doctypes[dataset.doctype.name]['mixed_elts']:
        elt_type.is_mixed = True
        elt_type.save()
    if elt.tag in doctypes[dataset.doctype.name]['main_elts']:
        elt_type.is_main = True
        elt_type.save()

    # Search for an element with same attributes
    element = Element.objects.filter(elt_type=elt_type)

    attrs = []
    for name, value in elt.items():
        if name not in doctypes[dataset.doctype.name]['remove_attrs']:
            att_type, c = AttributeType.objects.get_or_create(
                doctype=dataset.doctype,
                name=name
            )
            if name in doctypes[dataset.doctype.name]['main_attrs']:
                att_type.is_main = True
                att_type.save()
            if name in doctypes[dataset.doctype.name]['skip_attrs']:
                att_type.skip = True
                att_type.save()

            if value and not (name, value) in doctypes[dataset.doctype.name]['remove_attrs_val']:
                elt_type.attributes.add(att_type)

                a, c = Attribute.objects.get_or_create(
                    att_type=att_type,
                    value=value
                )

                element = element.filter(attributes=a)
                attrs.append(a)

    elt_type.save()

    # Search for an element with same mixed contents
    text = None
    if elt_type.is_mixed:
        contents = etree.tostring(elt).replace(
            '<%s>' % elt.tag, ''
        ).replace(
            '</%s>' % elt.tag, ''
        )
        text, c = Text.objects.get_or_create(
            doctype=dataset.doctype,
            name=md5(contents).hexdigest(),
            contents=contents
        )

        element = element.filter(text=text)

    # If element exists then use it or create a new one
    if element.exists():
        # element_is_new = False
        e = element[0]
    else:
        # element_is_new = True
        e = Element.objects.create(
            elt_type=elt_type,
            text=text
        )
        e.attributes = attrs
        e.save()

    # Attach the element to a treenode
    treenode = TreeNode.objects.create(
        parent=parent,
        dataset=dataset,
        element=e
    )

    if not elt_type.is_mixed:
        for child in elt:
            store_element(child, dataset, parent=treenode)


def load(doctype_name, dataset_version, file_extension='xml'):
    parser = etree.XMLParser(remove_blank_text=True)

    file_basename = doctypes[doctype_name]['file_basename'].substitute(version=dataset_version)

    path_basename = os.path.join(
        settings.DATA_DIR,
        doctypes[doctype_name]['data_path'].substitute(version=dataset_version),
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

    store_element(root, dataset)
