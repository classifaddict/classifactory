import os
import zipfile
import time
from hashlib import md5
from string import Template

from lxml import etree
from django.conf import settings

from app_tree.models import Doctype, ElementType, AttributeType
from app_tree.models import Dataset, Element, Attribute, Text, TreeNode


def log(msg):
    print '(%s) %s' % (time.strftime('%H:%M:%S'), msg)

doctypes_conf = {
    'ipc_scheme': {
        'data_path': Template('ITOS/IPC/data/$version/ipcr_scheme_and_figures'),
        'file_basename': Template('ipcr_scheme_$version'),
        'main_elts': ['revisionPeriods', 'ipcEntry'],
        'remove_elts': ['fr'],
        'main_attrs': ['symbol', 'kind'],
        'skip_attrs': [], # ['edition'],
        'remove_attrs': ['lang', 'ipcLevel', 'priorityOrder'],
        'remove_attrs_val': [],
        'mixed_elts': ['text', 'references', 'entryReference'],
        'container_elts': [
            'revisionPeriods', 'revisionPeriod', 'ipcEdition', 'en', 'fr',
            'translation', 'staticIpc', 'ipcEntry', 'textBody', 'note', 'index',
            'title', 'noteParagraph', 'text', 'references', 'subnote', 'orphan',
            'indexEntry', 'titlePart', 'entryReference'
        ]
    }
}


class XMLTreeLoader:
    def __init__(self, doctype_name, dataset_version, store, file_extension):
        self.dt_conf = doctypes_conf[doctype_name]

        parser = etree.XMLParser(remove_blank_text=True)

        file_basename = self.dt_conf['file_basename'].substitute(
            version=dataset_version
        )

        path_basename = os.path.join(
            settings.DATA_DIR,
            self.dt_conf['data_path'].substitute(version=dataset_version),
            file_basename
        )

        if file_extension == 'zip':
            zip_file = zipfile.ZipFile(path_basename + '.' + file_extension)
            file_obj = zip_file.open(file_basename + '.xml')
        else:
            file_obj = open(path_basename + '.' + file_extension)

        tree = etree.parse(file_obj, parser)
        self.root = tree.getroot()

        self.doctype, c = Doctype.objects.get_or_create(name=doctype_name)

        self.dataset, c = Dataset.objects.get_or_create(
            doctype=self.doctype,
            name=dataset_version
        )

        self.attr_values = set([(
            a['type__name'], a['value']
        ) for a in Attribute.objects.select_related('attributetype').filter(
            type__doctype=self.doctype
        ).order_by().values(
            'type__name', 'value'
        )])

        self.text_names = set([t['name'] for t in Text.objects.filter(
            doctype=self.doctype).values('name')
        ])

        self.elt_values = set([(
            e['type__name'], e['text__name'], e['attrs_key']
        ) for e in Element.objects.select_related(
            'elementtype', 'text'
        ).filter(type__doctype=self.doctype).values(
            'type__name', 'text__name', 'attrs_key'
        )])

        self.elts = {}

        log('Cleaning up...')
        self.cleanup()

        log('Storing elements, attributes and texts...')
        if store == 'types':
            self.store_treeleaves_and_types()
        else:
            self.store_treeleaves()

        log('Storing treenodes...')
        self.store_treenode(self.root)

    def get_attr_types(self):
        return dict([(
            a['name'], a['id']
        ) for a in AttributeType.objects.filter(
            doctype=self.doctype
        ).order_by().values('id', 'name')])

    def get_attrs(self):
        return dict([(
            (a['type__name'], a['value']), a['id']
        ) for a in Attribute.objects.select_related('attributetype').filter(
            type__doctype=self.doctype
        ).order_by().values(
            'id', 'type__name', 'value'
        )])

    def get_elt_types(self):
        return dict([(e['name'], e['id']) for e in ElementType.objects.filter(
            doctype=self.doctype
        ).order_by().values('id', 'name')])

    def get_elts(self):
        return dict([(
            (e['type__name'], e['text__name'], e['attrs_key']), e['id']
        ) for e in Element.objects.select_related(
            'elementtype', 'text'
        ).filter(type__doctype=self.doctype).values(
            'id', 'type__name', 'text__name', 'attrs_key'
        )])

    def get_texts(self):
        return dict([(e['name'], e['id']) for e in Text.objects.filter(
            doctype=self.doctype
        ).values('id', 'name')])

    def cleanup(self):
        for r in self.dt_conf['remove_elts']:
            for e in self.root.xpath('//' + r):
                e.getparent().remove(e)

        for r in self.dt_conf['remove_attrs']:
            for e in self.root.xpath('//*[@%s]' % r):
                a = e.attrib.pop(r)

    def store_attributes(self, new_attrs_values):
        log('Storing attributes...')
        attr_types = self.get_attr_types()
        Attribute.objects.bulk_create([
            Attribute(
                type_id=attr_types[name],
                value=value
            ) for name, value in new_attrs_values
        ])

    def store_elements(self, new_elts_values):
        log('Storing elements...')
        elt_types = self.get_elt_types()
        texts_ids = self.get_texts()
        attrs_objs = self.get_attrs()

        new_elts = []
        for name, text_name, attrs_key, attrs in new_elts_values:
            new_elts.append(
                Element(
                    type_id=elt_types[name],
                    text_id=texts_ids[text_name],
                    attrs_key=attrs_key,
                    main_attrs=md5(''.join(
                        [n + v for n, v in attrs if n in self.dt_conf[
                            'main_attrs'
                        ]]
                    )).hexdigest()
                )
            )
        Element.objects.bulk_create(new_elts)

        log('Attaching attributes...')
        self.elts = self.get_elts()
        through_model = Element.attributes.through

        attrs_sets = []
        for name, text_name, attrs_key, attrs in new_elts_values:
            e = self.elts[(name, text_name, attrs_key)]
            for a in attrs:
                attrs_sets.append(
                    through_model(
                        attribute_id=attrs_objs[a],
                        element_id=e
                    )
                )
        through_model.objects.bulk_create(attrs_sets)

    def create_text_object(self, e, new_texts):
        if e.tag not in self.dt_conf['mixed_elts']:
            contents = ''
        else:
            # Serialize descendance as string, removing root element tags
            # and stripping normal and non-breaking spaces
            contents = etree.tostring(e, encoding='unicode').replace(
                '<%s>' % e.tag, ''
            ).replace(
                '</%s>' % e.tag, ''
            ).strip(u'\xA0 ')

        text_name = md5(contents.encode('utf-8')).hexdigest()

        if text_name in self.text_names:
            return text_name

        self.text_names.add(text_name)

        # Create text object
        new_texts.append(Text(
            doctype=self.doctype,
            name=text_name,
            contents=contents
        ))
        return text_name

    def collect_elt_values(self, e, text_name, attrs, new_elts_values):
        attrs_key = ''
        if attrs:
            attrs_key = md5(
                ''.join([name + value for name, value in attrs])
            ).hexdigest()

        values = (e.tag, text_name, attrs_key)

        if values not in self.elt_values:
            new_elts_values.append(values + (attrs,))

        self.elt_values.add(values)

        # Store element keys in ElementTree node so that element object
        # that will be created can be retrieved when building tree
        e.set('eltkey4node', '_'.join(values))

    def store_treeleaves(self):
        new_attr_values = []
        new_texts = []
        new_elts_values = []

        for e in self.root.iter(self.dt_conf['container_elts']):

            text_name = self.create_text_object(e, new_texts)

            attrs = [(k, e.get(k)) for k in sorted(e.keys()) if e.get(k)]
            for a in attrs:
                if a in self.attr_values:
                    continue
                new_attr_values.append(a)
                self.attr_values.add(a)

            self.collect_elt_values(e, text_name, attrs, new_elts_values)

        self.store_attributes(new_attr_values)

        # Store texts
        Text.objects.bulk_create(new_texts)

        self.store_elements(new_elts_values)

    def store_element_types(self, new_elt_types, new_elt_types_attrs):
        ElementType.objects.bulk_create(new_elt_types)

        elt_types = self.get_elt_types()
        attr_types = self.get_attr_types()

        through_model = ElementType.attributes.through
        attrs_sets = []
        for name, attrs in new_elt_types_attrs.iteritems():
            e = elt_types[name]
            for a in attrs:
                attrs_sets.append(
                    through_model(
                        attributetype_id=attr_types[a],
                        elementtype_id=e
                    )
                )
        through_model.objects.bulk_create(attrs_sets)

    def store_treeleaves_and_types(self):
        attr_names = set([
            a['name'] for a in AttributeType.objects.filter(
                doctype=self.doctype
            ).order_by().values('name')
        ])

        new_attr_values = set()
        new_attr_types = []

        elt_names = set([
            e['name'] for e in ElementType.objects.filter(
                doctype=self.doctype
            ).order_by().values('name')
        ])

        new_elt_types = []
        new_elt_types_attrs = {}

        new_texts = []
        new_elts_values = []

        for e in self.root.iter(self.dt_conf['container_elts']):

            # Create text object
            text_name = self.create_text_object(e, new_texts)

            if e.tag not in elt_names:
                # Create element type object
                new_elt_types.append(ElementType(
                    doctype=self.doctype,
                    name=e.tag,
                    is_mixed=e.tag in self.dt_conf['mixed_elts'],
                    is_main=e.tag in self.dt_conf['main_elts']
                ))
                elt_names.add(e.tag)

            if e.tag not in new_elt_types_attrs:
                new_elt_types_attrs[e.tag] = set()

            attrs = [(k, e.get(k)) for k in sorted(e.keys()) if e.get(k)]
            for name, value in attrs:
                new_elt_types_attrs[e.tag].add(name)

                if (name, value) in self.attr_values:
                    continue

                self.attr_values.add((name, value))
                new_attr_values.add((name, value))

                if name in attr_names:
                    continue

                # Create attribute type object
                new_attr_types.append(AttributeType(
                    doctype=self.doctype,
                    name=name,
                    is_main=name in self.dt_conf['main_attrs'],
                    skip=name in self.dt_conf['skip_attrs']
                ))
                attr_names.add(name)

            self.collect_elt_values(e, text_name, attrs, new_elts_values)

        # Store attribute types
        AttributeType.objects.bulk_create(new_attr_types)

        self.store_attributes(new_attr_values)

        self.store_element_types(new_elt_types, new_elt_types_attrs)

        # Store texts
        Text.objects.bulk_create(new_texts)

        self.store_elements(new_elts_values)

    def store_treenode(self, elt, parent=None):
        # Attach retrieved leaf element to a new treenode
        # Leaf element is retrieved by keys collected during leaves storage
        treenode = TreeNode.objects.create(
            parent=parent,
            dataset=self.dataset,
            element_id=self.elts[tuple(elt.get('eltkey4node').split('_'))]
        )

        # Process children nodes
        if elt.tag not in self.dt_conf['mixed_elts']:
            for child in elt:
                self.store_treenode(elt=child, parent=treenode)


def load(doctype_name, dataset_version, store=None, file_extension='xml'):
    XMLTreeLoader(doctype_name, dataset_version, store, file_extension)
