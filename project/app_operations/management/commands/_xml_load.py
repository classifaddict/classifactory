import os
import zipfile
import time
from hashlib import md5
from string import Template

from lxml import etree
from django.conf import settings
from django.db import  transaction

from app_tree.models import Doctype, ElementType, AttributeType
from app_tree.models import Dataset, Element, Attribute, Text, TreeNode

from app_operations.decorators import with_connection_usable


def log(msg):
    print '(%s) %s' % (time.strftime('%H:%M:%S'), msg)

doctypes_conf = {
    'ipc_scheme': {
        'data_path': Template('ITOS/IPC/data/$version/ipcr_scheme_and_figures'),
        'zip_name': Template('ipcr_scheme_$version$release.zip'),
        'xml_name': Template('ipcr_scheme_$version$release.xml'),
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
    },
    'nice_indications': {
        'data_path': Template('ITOS/NICE/data/$version/indications'),
        'zip_name': Template('$version-indications-$release.zip'),
        'xml_name': Template('$version-$lang-indications-$release.xml'),
        'main_elts': ['nice:Indications', 'nice:GoodOrService'],
        'remove_elts': [],
        'main_attrs': ['basicNumber', 'dateInForce'],
        'skip_attrs': [],
        'remove_attrs': ['xsi:schemaLocation'],
        'remove_attrs_val': [],
        'mixed_elts': [
            'nice:Label', 'nice:SortExpression',
            'nice:AlternateSortExpression'
        ],
        'container_elts': [
            'nice:Indications', 'nice:GoodOrService', 'nice:Indication',
            'nice:SynonymIndication', 'nice:Label',
            'nice:SortExpression', 'nice:AlternateSortExpression'
        ]
    },
    'nice_classes': {
        'data_path': Template('ITOS/NICE/data/$version/class_headings_and_explanatory_notes'),
        'zip_name': Template('$version-class_headings_and_explanatory_notes-$release.zip'),
        'xml_name': Template('$version-$lang-class_headings_and_explanatory_notes-$release.xml'),
        'main_elts': ['nice:ClassHeadingsExplanatoryNotes', 'nice:Class'],
        'remove_elts': [],
        'main_attrs': ['classNumber', 'dateInForce'],
        'skip_attrs': [],
        'remove_attrs': ['xsi:schemaLocation'],
        'remove_attrs_val': [],
        'mixed_elts': [
            'nice:HeadingItem', 'nice:Introduction',
            'nice:Include', 'nice:Exclude'
        ],
        'container_elts': [
            'nice:ClassHeadingsExplanatoryNotes', 'nice:Class', 'nice:ClassHeading',
            'nice:ExplanatoryNote', 'nice:IncludesInParticular',
            'nice:ExcludesInParticular', 'nice:HeadingItem',
            'nice:Introduction', 'nice:Include', 'nice:Exclude'
        ]
    }
}


class XMLTreeLoader:
    def __init__(self, doctype_name, dataset_version, lang, file_release, no_types, xml):
        self.dt_conf = doctypes_conf[doctype_name]

        data_path = os.path.join(
            settings.DATA_DIR,
            self.dt_conf['data_path'].substitute(version=dataset_version)
        )

        xml_name = self.dt_conf['xml_name'].substitute(
            version=dataset_version,
            lang=lang,
            release=file_release
        )

        if xml:
            file_obj = open(os.path.join(data_path, xml_name))
        else:
            zip_name = self.dt_conf['zip_name'].substitute(
                version=dataset_version,
                release=file_release
            )
            zip_file = zipfile.ZipFile(os.path.join(data_path, zip_name))
            file_obj = zip_file.open(xml_name)

        parser = etree.XMLParser(
            remove_blank_text=True,
            ns_clean=True,
            remove_comments=True
        )

        tree = etree.parse(file_obj, parser)
        self.root = tree.getroot()

        # Get namespace(s) info
        self.NSMAP = self.root.nsmap
        self.NSpfx = ''
        self.NS = ''
        if self.root.prefix is not None:
            self.NSpfx = self.root.prefix + ":"
            self.NS = "{%s}" % self.NSMAP[self.root.prefix]

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
        if no_types:
            self.store_treeleaves()
        else:
            self.store_treeleaves_and_types()

        with transaction.atomic():
            with TreeNode.objects.delay_mptt_updates():
                log('Storing treenodes...')
                self.store_treenode(self.root)

        log('Done.')

    def tag(self, tagname):
        # Replaces URI prefix by local prefix within qualified tag name
        # e.g. {uri}tag => pfx:tag
        return tagname.replace(self.NS, self.NSpfx)

    def tags(self, tagname_list):
        # Replaces local prefix by URI prefix within qualified tag names list
        return [n.replace(self.NSpfx, self.NS) for n in tagname_list]

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
            n = r.split(':')
            name = n[-1]
            for e in self.root.xpath('//*[local-name() = "%s"]' % name):
                e.getparent().remove(e)

        for r in self.dt_conf['remove_attrs']:
            n = r.split(':')
            name = n[-1]
            qname = n[0]
            if len(n) > 1:
                qname = '{%s}%s' % (self.NSMAP[n[0]], n[1])

            for e in self.root.xpath('//*[@*[local-name() = "%s"]]' % name):
                e.attrib.pop(qname)

    @with_connection_usable
    def store_attributes(self, new_attrs_values):
        log('Storing attributes...')
        attr_types = self.get_attr_types()
        Attribute.objects.bulk_create([
            Attribute(
                type_id=attr_types[name],
                value=value
            ) for name, value in new_attrs_values
        ])

    @with_connection_usable
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

    def create_text_object(self, e, tag, new_texts):
        if tag not in self.dt_conf['mixed_elts']:
            contents = ''
        else:
            # Serialize descendance as string, removing root element tags
            # and stripping normal and non-breaking spaces
            contents = etree.tostring(e, with_tail=False, encoding='unicode')
            for k, v in e.nsmap.iteritems():
                contents = contents.replace(' xmlns:%s="%s"' % (k, v), '')
            contents = contents.replace(
                '<%s>' % tag, ''
            ).replace(
                '</%s>' % tag, ''
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

    def collect_elt_values(self, e, tag, text_name, attrs, new_elts_values):
        attrs_key = ''
        if attrs:
            attrs_key = md5(
                ''.join([name + value for name, value in attrs])
            ).hexdigest()

        values = (tag, text_name, attrs_key)

        if values not in self.elt_values:
            new_elts_values.append(values + (attrs,))

        self.elt_values.add(values)

        # Store element keys in ElementTree node so that element object
        # that will be created can be retrieved when building tree
        e.set('eltkey4node', '_'.join(values))

    @with_connection_usable
    def store_treeleaves(self):
        new_attr_values = []
        new_texts = []
        new_elts_values = []

        for e in self.root.iter(self.tags(self.dt_conf['container_elts'])):
            tag = self.tag(e.tag)

            text_name = self.create_text_object(e, tag, new_texts)

            attrs = [(k, e.get(k)) for k in sorted(e.keys()) if e.get(k)]
            for a in attrs:
                if a in self.attr_values:
                    continue
                new_attr_values.append(a)
                self.attr_values.add(a)

            self.collect_elt_values(e, tag, text_name, attrs, new_elts_values)

        self.store_attributes(new_attr_values)

        # Store texts
        Text.objects.bulk_create(new_texts)

        self.store_elements(new_elts_values)

    @with_connection_usable
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

    @with_connection_usable
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

        for e in self.root.iter(self.tags(self.dt_conf['container_elts'])):
            tag = self.tag(e.tag)

            # Create text object
            text_name = self.create_text_object(e, tag, new_texts)

            if tag not in elt_names:
                # Create element type object
                new_elt_types.append(ElementType(
                    doctype=self.doctype,
                    name=tag,
                    is_mixed=tag in self.dt_conf['mixed_elts'],
                    is_main=tag in self.dt_conf['main_elts']
                ))
                elt_names.add(tag)

            if tag not in new_elt_types_attrs:
                new_elt_types_attrs[tag] = set()

            attrs = [(k, e.get(k)) for k in sorted(e.keys()) if e.get(k)]
            for name, value in attrs:
                new_elt_types_attrs[tag].add(name)

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

            self.collect_elt_values(e, tag, text_name, attrs, new_elts_values)

        # Store attribute types
        AttributeType.objects.bulk_create(new_attr_types)

        self.store_attributes(new_attr_values)

        self.store_element_types(new_elt_types, new_elt_types_attrs)

        # Store texts
        Text.objects.bulk_create(new_texts)

        self.store_elements(new_elts_values)

    @with_connection_usable
    def store_treenode(self, elt, parent=None):
        # Attach retrieved leaf element to a new treenode
        # Leaf element is retrieved by keys collected during leaves storage
        treenode = TreeNode(
            parent=parent,
            dataset=self.dataset,
            element_id=self.elts[tuple(elt.get('eltkey4node').split('_'))]
        )
        treenode.save()

        # Process children nodes
        if self.tag(elt.tag) not in self.dt_conf['mixed_elts']:
            for child in elt:
                self.store_treenode(elt=child, parent=treenode)


def load(doctype_name, dataset_version, lang='en', file_release='', no_types=False, xml=False):
    XMLTreeLoader(doctype_name, dataset_version, lang, file_release, no_types, xml)
