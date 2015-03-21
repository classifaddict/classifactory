import os
import time
import zipfile
import time
import copy
from hashlib import md5

from lxml import etree

from django.conf import settings


def log(msg):
    print '(%s) %s' % (time.strftime('%H:%M:%S'), msg)


class DiffTrees:
    def __init__(self, doctype_name, dataset_version1, dataset_version2, lang, file_release1, file_release2, xml):
        self.dt_conf = settings.DOCTYPES[doctype_name]
        self.xml = xml
        self.lang = lang

        self.parser = etree.XMLParser(
            remove_blank_text=True,
            ns_clean=True,
            remove_comments=True
        )

        old_root = self._get_tree_root(dataset_version1, file_release1, skip_attrs=self.dt_conf['skip_attrs'])
        self.old_root_ET = etree.ElementTree(old_root)

        new_root = self._get_tree_root(dataset_version2, file_release2, skip_attrs=self.dt_conf['skip_attrs'])
        self.new_root_ET = etree.ElementTree(new_root)

        self.diff(old_root, new_root)

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
            root_ET.getpath(c)
        ) for c in node.iterchildren()])

    def _align_N1_to_N2(self, mod, node1, node2, root1_ET=None, root2_ET=None, relative=False):
        '''
        Returns the List of xpath of node2 children which fingerprints
        are not in the list of node1 children fingerprints.

        Tries also to align number of children in node1 with node2
        by cloning node2 children that are not in node1 and then
        by inserting them in node1 at the same position.
        '''

        # Get List xpath of node2 children which fingerprints
        # are not in the list of node1 children fingerprints
        node1_children_FPs = self._get_children_FPs(node1, root1_ET, relative)
        node2_children_FPs = self._get_children_FPs(node2, root2_ET, relative)

        node2_added_children =  [
            node2_children_FPs[fp] for fp in set(
                node2_children_FPs.keys()
            ).difference(
                node1_children_FPs.keys()
            )
        ]

        # If possible, clone each node2 child missing in node1
        # and insert it in node1 at same location
        if len(node2_added_children) == len(node2) - len(node1):
            parent = node2.getparent()
            for path in sorted(node2_added_children):
                node2_child = parent.find('.' + path)
                idx = node2.index(node2_child)
                node2_child.set('mod', mod)
                node1.insert(idx, copy.deepcopy(node2_child))
        #else:
            #for n in range(len(node2) - len(node1)):
            #    e = etree.SubElement(node1, node1[-1].tag, {'mod': 'del'})

        return node2_added_children

    def _get_xpath_N2_matching_N1(self, node1, node2_FP):
        '''
        Returns xpath String of node1 sibling which fingerprint
        is same as node1 fingerprint,
        or None if node1 is root or no indentical sibling is found.
        '''

        parent = node1.getparent()
        if parent is None:
            return None

        parent_ET = etree.ElementTree(parent)

        for sibling in parent.iterchildren():
            if node2_FP == self._get_node_FP(sibling):
                return parent_ET.getpath(sibling)

        return None

    def diff(self, old, new):
        '''
        Compare two elementTree objects, recursively starting from root node.
        '''

        old_FP = self._get_node_FP(old)
        new_FP = self._get_node_FP(new)

        # Check node fingerprints
        if new_FP == old_FP:
            # Node need to compare descendants if node are indentical
            return

        diff_kinds = set()
        del_children = None
        ins_children = None

        if new.tag != old.tag:
            diff_kinds['name'] = True
        else:
            attrs1 = self._get_attrs_str(old)
            attrs2 = self._get_attrs_str(new)
            if attrs1 != attrs2:
                diff_kinds.add('attrs')

            if old.tag in self.dt_conf['mixed_elts']:
                diff_kinds.add('txt')

            relative_path=True

            if len(old) > len(new):
                # Search children deleted from old tree and try to align trees
                del_children = self._align_N1_to_N2(
                    'del',
                    new, old,
                    self.new_root_ET, self.old_root_ET,
                    relative_path
                )

            elif len(old) < len(new):
                # Search children inserted in new tree and try to align trees
                ins_children = self._align_N1_to_N2(
                    'ins',
                    old, new,
                    self.old_root_ET, self.new_root_ET,
                    relative_path
                )

        old_sibling_matches = self._get_xpath_N2_matching_N1(new, old_FP)
        new_sibling_matches = self._get_xpath_N2_matching_N1(old, new_FP)

        if del_children or ins_children or old_sibling_matches or new_sibling_matches:
            diff_kinds.add('struct')

        if diff_kinds:
            print "\n<<<<<"
            print self.old_root_ET.getpath(old)
            print self.new_root_ET.getpath(new)

            if 'name' in diff_kinds:
                print new.tag

            if 'attrs' in diff_kinds:
                print attrs1
                print attrs2

            if 'struct' in diff_kinds:
                if len(old) != len(new):
                    print len(old)
                    print len(new)
                if del_children: print 'DEL from old:\n' + '\n'.join(sorted(del_children))
                if ins_children: print 'INS in new:\n' + '\n'.join(sorted(ins_children))
                if old_sibling_matches:
                    print 'Found old elsewhere in new parent: ' + old_sibling_matches
                if new_sibling_matches:
                    print 'Found new elsewhere in old parent: ' + new_sibling_matches

            if 'txt' in diff_kinds:
                print etree.tostring(old, method="c14n")
                print etree.tostring(new, method="c14n")

            print ">>>>>\n"
        else:
            print self.old_root_ET.getpath(old)

        if old.tag not in self.dt_conf['mixed_elts']:
            for nodes in zip(old.iterchildren(), new.iterchildren()):
                self.diff(nodes[0], nodes[1])


def diff_trees(doctype_name, dataset_version1, dataset_version2, lang='en', file_release1='', file_release2='', xml=False):
    log('Diffing %s and %s...' % (dataset_version1, dataset_version2))
    DiffTrees(doctype_name, dataset_version1, dataset_version2, lang, file_release1, file_release2, xml)
    log('Done.')