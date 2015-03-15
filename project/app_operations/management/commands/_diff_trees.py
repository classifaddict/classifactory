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

        old_root = self.get_tree_root(dataset_version1, file_release1, skip_attrs=self.dt_conf['skip_attrs'])
        self.old_root_ET = etree.ElementTree(old_root)

        new_root = self.get_tree_root(dataset_version2, file_release2, skip_attrs=self.dt_conf['skip_attrs'])
        self.new_root_ET = etree.ElementTree(new_root)

        self.diff(old_root, new_root)

    def _cleanup(self, root, skip_attrs=[]):
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

    def get_tree_root(self, dataset_version, file_release, skip_attrs=[]):
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

    def get_attrs_str(self, node):
        return ' '.join(['='.join([k, node.get(k)]) for k in sorted(node.keys())])

    def _get_children_signs(self, node, root_ET):
        # To get relative path: root_ET = etree.ElementTree(node)
        return dict([(
            md5(etree.tostring(c, method="c14n")).hexdigest(),
            root_ET.getpath(c)
        ) for c in node.iterchildren()])

    def get_diff_children(self, node1, node2, root1_ET, root2_ET):
        children_signs1 = self._get_children_signs(node1, root1_ET)
        children_signs2 = self._get_children_signs(node2, root2_ET)
        return [
            children_signs2[s] for s in set(
                children_signs2.keys()
            ).difference(
                children_signs1.keys()
            )
        ]

    def diff(self, old, new):
        sign1 = md5(etree.tostring(old, method="c14n")).hexdigest()
        sign2 = md5(etree.tostring(new, method="c14n")).hexdigest()
        if sign1 != sign2:
            diff_kinds = set()
            del_children = []
            ins_children = []
            sibling_matches = []

            if old.tag != new.tag:
                diff_kinds['name'] = True
            else:
                attrs1 = self.get_attrs_str(old)
                attrs2 = self.get_attrs_str(new)
                if attrs1 != attrs2:
                    diff_kinds.add('attrs')

                if old.tag in self.dt_conf['mixed_elts']:
                    diff_kinds.add('txt')

                if len(old) > len(new):
                    # Attempt to find children deleted from old tree
                    del_children.extend(
                        self.get_diff_children(
                            new, old,
                            etree.ElementTree(new),
                            etree.ElementTree(old)
                        )
                    )
                    # If possible, clone each deleted node and insert it
                    # in new tree at same location with attr mod=del
                    if len(del_children) != len(old) - len(new):
                        diff_kinds.add('struct')
                        #for n in range(len(old) - len(new)):
                        #    e = etree.SubElement(new, new[-1].tag, {'mod': 'del'})
                    else:
                        for path in sorted(del_children):
                            old_elt = old.getparent().find('.' + path)
                            idx = old.index(old_elt)
                            clone = copy.deepcopy(old_elt)
                            clone.set('mod', 'del')
                            new.insert(idx, clone)

                elif len(old) < len(new):
                    # Attempt to find children inserted in new tree
                    ins_children.extend(
                        self.get_diff_children(
                            old, new,
                            etree.ElementTree(old),
                            etree.ElementTree(new)
                        )
                    )
                    # If possible, set attr mod=ins to each inserted node, 
                    # clone and insert it in old tree at same location
                    if len(ins_children) != len(new) - len(old):
                        diff_kinds.add('struct')
                    else:
                        for path in sorted(ins_children):
                            new_elt = new.getparent().find('.' + path)
                            idx = new.index(new_elt)
                            clone = copy.deepcopy(new_elt)
                            new_elt.set('mod', 'ins')
                            old.insert(idx, clone)

            if old.getparent() is not None:
                for new_test in new.getparent().iterchildren():
                    if sign1 == md5(etree.tostring(new_test, method="c14n")).hexdigest():
                        parent_ET = etree.ElementTree(new.getparent())
                        sibling_matches.append("Found old elsewhere in new parent: " + parent_ET.getpath(new_test))
                        break
                for old_test in old.getparent().iterchildren():
                    if sign2 == md5(etree.tostring(old_test, method="c14n")).hexdigest():
                        parent_ET = etree.ElementTree(old.getparent())
                        sibling_matches.append("Found new elsewhere in old parent: " + parent_ET.getpath(old_test))
                        break
                if sibling_matches:
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
                    if sibling_matches: print '\n'.join(sibling_matches)

                if 'txt' in diff_kinds:
                    print etree.tostring(old, method="c14n")
                    print etree.tostring(new, method="c14n")

                print ">>>>>\n"
            else:
                print self.old_root_ET.getpath(old)
        else:
            return

        if old.tag not in self.dt_conf['mixed_elts']:
            for nodes in zip(old.iterchildren(), new.iterchildren()):
                self.diff(nodes[0], nodes[1])


def diff_trees(doctype_name, dataset_version1, dataset_version2, lang='en', file_release1='', file_release2='', xml=False):
    log('Diffing %s and %s...' % (dataset_version1, dataset_version2))
    DiffTrees(doctype_name, dataset_version1, dataset_version2, lang, file_release1, file_release2, xml)
    log('Done.')