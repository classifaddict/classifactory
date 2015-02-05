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
        'main_attrs': ['symbol', 'kind'],
        'skip_attrs': [], # ['edition'],
        'remove_attrs': ['lang', 'ipcLevel', 'priorityOrder'],
        'remove_attrs_val': [],
        'mixed_elts': ['text', 'references', 'entryReference']
    }
}


class XMLTreeLoader:
    def __init__(self, doctype_name, dataset_version, store, file_extension):
        self.dt_conf = doctypes_conf[doctype_name]

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
        self.root = tree.getroot()

        self.doctype, c = Doctype.objects.get_or_create(name=doctype_name)

        self.dataset, c = Dataset.objects.get_or_create(
            doctype=self.doctype,
            name=dataset_version
        )

        self.attr_values = set([(a.type.name, a.value) for a in Attribute.objects.filter(type__doctype=self.doctype)])

        self.text_names = set([t.name for t in Text.objects.filter(doctype=self.doctype)])

        self.elt_values = set([(e.type.name, e.text.name, e.attrs_key) for e in Element.objects.filter(type__doctype=self.doctype)])

        self.elts = {}

        print 'Cleaning up...'
        self.cleanup()
        print 'Store elements, attributes and texts...'
        if store == 'types':
            self.store_treeleaves_and_types()
        else:
            self.store_treeleaves()
        print 'Store treenodes...'
        self.store_treenode(self.root)

    def get_attr_types(self):
        return dict([(a.name, a) for a in AttributeType.objects.filter(doctype=self.doctype).order_by()])

    def get_attrs(self):
        return dict([((a.type.name, a.value), a) for a in Attribute.objects.filter(type__doctype=self.doctype).order_by()])

    def get_elt_types(self):
        return dict([(e.name, e) for e in ElementType.objects.filter(doctype=self.doctype).order_by()])

    def get_elts(self):
        return dict([((e.type.name, e.text.name, e.attrs_key), e) for e in Element.objects.filter(type__doctype=self.doctype)])

    def get_texts(self):
        return dict([(e['name'], e['id']) for e in Text.objects.filter(doctype=self.doctype).values('id', 'name')])

    def cleanup(self):
        for r in self.dt_conf['remove_elts']:
            for e in self.root.xpath('//' + r):
                e.getparent().remove(e)

        for r in self.dt_conf['remove_attrs']:
            for e in self.root.xpath('//*[@%s]' % r):
                a = e.attrib.pop(r)

    def store_attributes(self, new_attrs_values):
        attr_types = self.get_attr_types()
        Attribute.objects.bulk_create([
            Attribute(
                type_id=attr_types[name].id,
                value=value
            ) for name, value in new_attrs_values
        ])

    def store_elements(self, new_elts_values):
        elt_types = self.get_elt_types()
        texts_ids = self.get_texts()
        attrs_objs = self.get_attrs()

        new_elts = []
        for name, text_name, attrs_key, attrs in new_elts_values:
            new_elts.append(
                Element(
                    type_id=elt_types[name].id,
                    text_id=texts_ids[text_name],
                    attrs_key=attrs_key,
                    main_attrs=md5(''.join(
                        [n + v for n, v in attrs if n in self.dt_conf['main_attrs']]
                    )).hexdigest()
                )
            )
        Element.objects.bulk_create(new_elts)

        self.elts = self.get_elts()

        for name, text_name, attrs_key, attrs in new_elts_values:
            e = self.elts[(name, text_name, attrs_key)]
            e.attributes = [attrs_objs[a] for a in attrs]
            e.save()

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

        for e in self.root.iter():
            if set([a.tag for a in e.iterancestors()]).intersection(self.dt_conf['mixed_elts']):
                continue

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

    def store_treeleaves_and_types(self):
        attr_names = set([a.name for a in AttributeType.objects.filter(doctype=self.doctype)])
        new_attr_values = []
        new_attr_types = []

        elt_names = set([e.name for e in ElementType.objects.filter(doctype=self.doctype)])
        new_elt_types = []
        new_elt_types_attrs = {}

        new_texts = []
        new_elts_values = []

        for e in self.root.iter():
            if set([a.tag for a in e.iterancestors()]).intersection(self.dt_conf['mixed_elts']):
                continue

            text_name = self.create_text_object(e, new_texts)

            if e.tag not in elt_names:
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
                new_attr_values.append((name, value))

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

        AttributeType.objects.bulk_create(new_attr_types)

        self.store_attributes(new_attr_values)

        ElementType.objects.bulk_create(new_elt_types)

        elt_types = self.get_elt_types()
        attr_types = self.get_attr_types()
        for name, attrs in new_elt_types_attrs.iteritems():
            e = elt_types[name]
            e.attributes = [attr_types[name] for name in attrs]
            e.save()

        # Store texts
        Text.objects.bulk_create(new_texts)

        self.store_elements(new_elts_values)

    def store_treenode(self, elt, parent=None):
        # Attach retrieved leaf element to a new treenode
        # Leaf element is retrieved by keys collected during leaves storage
        treenode = TreeNode.objects.create(
            parent=parent,
            dataset=self.dataset,
            element=self.elts[tuple(elt.get('eltkey4node').split('_'))]
        )

        # Process children nodes
        if elt.tag not in self.dt_conf['mixed_elts']:
            for child in elt:
                self.store_treenode(elt=child, parent=treenode)


def load(doctype_name, dataset_version, store=None, file_extension='xml'):
    xml = XMLTreeLoader(doctype_name, dataset_version, store, file_extension)
