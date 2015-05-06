import os
import time
import zipfile
import time
import copy
from hashlib import md5

from lxml import etree

from django.conf import settings


def log(msg):
    print '({}) {}'.format(time.strftime('%H:%M:%S'), msg)

def DEBUG(msgs):
    print "\n<<<<<\n{}\n>>>>>\n".format('\n'.join(msgs))


class DiffTrees:
    def __init__(self, doctype_name, dataset_version1, dataset_version2, lang, file_release1, file_release2, xml):
        self.dt_conf = settings.DOCTYPES[doctype_name]
        self.xml = xml
        self.lang = lang
        self.diffs = {}

        self.parser = etree.XMLParser(
            remove_blank_text=True,
            ns_clean=True,
            remove_comments=True
        )

        self.NSMAP = {}
        self.NSpfx = ''
        self.NS = ''

        old_root = self._get_tree_root(dataset_version1, file_release1, skip_attrs=self.dt_conf['skip_attrs'])
        self.old_root_ET = etree.ElementTree(old_root)

        new_root = self._get_tree_root(dataset_version2, file_release2, skip_attrs=self.dt_conf['skip_attrs'])
        self.new_root_ET = etree.ElementTree(new_root)

        self.diff(old_root, new_root)

    def tag(self, tagname):
        # Replaces URI prefix by local prefix within qualified tag name
        # e.g. {uri}tag => pfx:tag
        return tagname.replace(self.NS, self.NSpfx)

    def diff_record(self, node, diff_type, old=False):
        if old:
            xpath = self.old_root_ET.getpath(node)
        else:
            xpath = self.new_root_ET.getpath(node)

        if xpath in self.diffs:
            self.diffs[xpath].add(diff_type)
        else:
            self.diffs[xpath] = set([diff_type])

    def _cleanup(self, root, skip_attrs=[]):
        '''
        Remove unwanted (as defined in settings.DOCTYPES)
        nodes and/or attributes
        '''

        for r in self.dt_conf['remove_elts']:
            n = r.split(':')
            name = n[-1]
            for e in root.xpath('//*[local-name() = "%s"]' % name):
                e.getparent().remove(e)

        for r in self.dt_conf['remove_attrs'] + skip_attrs:
            n = r.split(':')
            name = n[-1]
            qname = n[0]
            if len(n) > 1:
                qname = '{%s}%s' % (self.NSMAP[n[0]], n[1])

            for e in root.xpath('//*[@*[local-name() = "%s"]]' % name):
                e.attrib.pop(qname)

    def _get_tree_root(self, dataset_version, file_release, skip_attrs=[]):
        '''
        Returns the root node of a (compressed) XML file.
        '''

        data_path = os.path.join(
            settings.DATA_DIR,
            self.dt_conf['data_path'].substitute(version=dataset_version)
        )

        xml_name = self.dt_conf['xml_name'].substitute(
            version=dataset_version,
            lang=self.lang,
            release=file_release
        )

        if self.xml:
            file_obj = open(os.path.join(data_path, xml_name))
        else:
            zip_name = self.dt_conf['zip_name'].substitute(
                version=dataset_version,
                release=file_release
            )
            zip_file = zipfile.ZipFile(os.path.join(data_path, zip_name))
            file_obj = zip_file.open(xml_name)

        tree = etree.parse(file_obj, self.parser)
        root = tree.getroot()

        if root.prefix is not None:
            self.NSMAP = root.nsmap
            self.NSpfx = root.prefix + ":"
            self.NS = "{%s}" % self.NSMAP[root.prefix]

        if self.tag(root.tag) != self.dt_conf['root']:
            root = root.find('.//' + self.dt_conf['root'], namespaces=self.NSMAP)

        for att in root.keys():
            root.attrib.pop(att)
        self._cleanup(root, skip_attrs)

        return root

    def _get_attrs_str(self, node):
        '''
        Returns a String made of the node attribute
        name/value pairs sorted by name
        '''

        return ' '.join(['='.join([k, node.get(k)]) for k in sorted(node.keys())])

    def _get_node_FP(self, node):
        '''
        Returns a String made of MD5 hex digest of a node canonized subtree
        '''

        return md5(etree.tostring(node, method="c14n")).hexdigest()

    def _get_children_FPs(self, node, root_ET=None, relative=False):
        '''
        Returns a Dict:
        - Key: MD5 fingerprint of a child node subtree
        - Value: absolute or relative xpath of the child node
        '''

        if not relative and root_ET is None:
            log('### ERROR: root node ET must be specified to compute absolute path.')
            return

        if relative:
            root_ET = etree.ElementTree(node)

        return dict([(
            self._get_node_FP(c),
            c
            #root_ET.getpath(c)
        ) for c in node.iterchildren()])

    def _get_children_N2_not_in_N1(self, node1, node2, node1_children_FPs, node2_children_FPs):
        '''
        Returns the List of xpath of node2 children which fingerprints
        are not in the list of node1 children fingerprints.
        '''

        node2_diff_children =  [
            node2_children_FPs[fp] for fp in set(
                node2_children_FPs.keys()
            ).difference(
                node1_children_FPs.keys()
            )
        ]

        return node2_diff_children

    def diff(self, old, new):
        '''
        Compare two elementTree objects, recursively starting from root node.
        '''

        old_FP = self._get_node_FP(old)
        new_FP = self._get_node_FP(new)

        # Check node fingerprints
        if new_FP == old_FP:
            # Nodes are indentical then skip to next pair
            return

        old_path = self.old_root_ET.getpath(old)
        new_path = self.new_root_ET.getpath(new)

        if new.tag != old.tag:
            self.diff_record(new, 'name')

            DEBUG([new_path, old_path])

            # No need to compare descendants if nodes have different contents model
            return

        old_attrs = self._get_attrs_str(old)
        new_attrs = self._get_attrs_str(new)
        if old_attrs != new_attrs:
            self.diff_record(new, 'attrs')

        if old.tag in self.dt_conf['mixed_elts']:
            self.diff_record(new, 'txt')

            DEBUG([
                new_path,
                etree.tostring(old, method="c14n"),
                etree.tostring(new, method="c14n")
            ])

            # No need to compare descendants if nodes have mixed contents
            return

        if old_attrs != new_attrs:
            DEBUG([
                new_path,
                old_attrs,
                new_attrs
            ])
        else:
            print new_path

        relative_path=True

        old_children_FPs = self._get_children_FPs(old, self.old_root_ET, relative_path)
        new_children_FPs = self._get_children_FPs(new, self.new_root_ET, relative_path)

        # Get children deleted from old tree
        del_children = self._get_children_N2_not_in_N1(
            new, old,
            new_children_FPs, old_children_FPs
        )

        # Get children inserted in new tree
        ins_children = self._get_children_N2_not_in_N1(
            old, new,
            old_children_FPs, new_children_FPs
        )

        # Store xpath of different nodes for future comparison
        for i in ins_children:
            self.diff_record(i, 'ins')

        for d in del_children:
            self.diff_record(d, 'del', old=True)

        # remove identical node from future comparison
        for child in old:
            if child not in del_children:
                old.remove(child)

        for child in new:
            if child not in ins_children:
                new.remove(child)

        if len(new) != len(old):
            DEBUG([
                new_path,
                str(len(old)),
                str(len(new))
            ])

        for nodes in zip(old.iterchildren(), new.iterchildren()):
            self.diff(nodes[0], nodes[1])

def diff_trees(doctype_name, dataset_version1, dataset_version2, lang='en', file_release1='', file_release2='', xml=False):
    log('Diffing %s and %s...' % (dataset_version1, dataset_version2))
    DiffTrees(doctype_name, dataset_version1, dataset_version2, lang, file_release1, file_release2, xml)
    log('Done.')
