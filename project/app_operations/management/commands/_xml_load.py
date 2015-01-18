import os
from hashlib import md5

from lxml import etree
from django.conf import settings

from app_tree.models import Doctype, ElementType, AttributeType
from app_tree.models import Dataset, Element, Attribute, Text, TreeNode

doctypes = {
    'ipcr_scheme': {
        'main_elts': ['revisionPeriods', 'ipcEntry'],
        'main_attrs': ['dataset_version', 'symbol'],
        'except_attr': ['lang', 'ipcLevel', 'priorityOrder'],
        'except_attr_val': [],
        'data_elt': ['text', 'references', 'entryReference']
    }
}


def store_element(elt, dataset, parent=None):

    # Search for an element with same attributes and contents
    # If found then use it or create a new one
    elt_type, c = ElementType.objects.get_or_create(
        doctype=dataset.doctype,
        name=elt.tag
    )

    element = Element.objects.filter(elt_type=elt_type)

    attrs = []
    for name, value in elt.items():
        # value = value.upper()
        if name not in doctypes[dataset.doctype.name]['except_attr'] \
            and value \
            and not (name, value) in doctypes[dataset.doctype.name]['except_attr_val']:

            att_type, c = AttributeType.objects.get_or_create(
                doctype=dataset.doctype,
                name=name
            )

            elt_type.attributes.add(att_type)

            element = element.filter(
                attributes__att_type=att_type,
                attributes__value=value
            )

            a, c = Attribute.objects.get_or_create(
                att_type=att_type,
                value=value
            )
            attrs.append(a)

    elt_type.save()

    texts = None
    texts_name = None
    if elt.tag in doctypes[dataset.doctype.name]['data_elt']:
        texts = etree.tostring(elt).replace(
            '<%s>' % elt.tag, ''
        ).replace(
            '</%s>' % elt.tag, ''
        )
        texts_name = md5(texts).hexdigest()
        element = element.filter(
            text__doctype=dataset.doctype,
            text__name=texts_name
        )

    if element.exists():
        #element_is_new = False
        e = element[0]
    else:
        #element_is_new = True
        e = Element.objects.create(elt_type=elt_type)
        e.attributes = attrs
        if texts:
            t, c = Text.objects.get_or_create(
                doctype=dataset.doctype,
                name=texts_name,
                contents=texts
            )
            e.text = t
        e.save()

    def create_treenode():
        return TreeNode.objects.create(
            parent=parent,
            dataset=dataset,
            element=e,
            is_lazy=elt.tag in dataset.doctype.main_elts.split()
        )

    # Attach the element to a treenode
    treenode = create_treenode()

    # Instead of creating a whole new tree (using create_treenode alone)
    # we could try to merge with an existing one to ease furure diffing:
    ###################################################################
    # if parent is None:
    #     # Get or create the root node and attach the element to it
    #     rootnode = TreeNode.objects.root_nodes().filter(dataset__doctype=dataset.doctype)
    #     if rootnode.exists():
    #         # Merge all trees of the same doctype
    #         treenode = rootnode[0]
    #     else:
    #         # Create a new root node
    #         treenode = create_treenode()
    # elif element_is_new:
    #     treenode = create_treenode()
    # elif texts and not parent.get_children().filter(element=e).exists():
    #     # Verify that a child node does not already contain it
    #     treenode = create_treenode()
    # else:
    #     treenode = create_treenode()

    if texts is None:
        for child in elt:
            store_element(child, dataset, parent=treenode)


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

    doctype, c = Doctype.objects.get_or_create(name=doctype_name)
    doctype.main_attrs = ' '.join(doctypes[doctype_name]['main_attrs'])
    doctype.main_elts = ' '.join(doctypes[doctype_name]['main_elts'])
    doctype.save()

    dataset, c = Dataset.objects.get_or_create(
        doctype=doctype,
        name=dataset_version
    )

    store_element(root, dataset)
