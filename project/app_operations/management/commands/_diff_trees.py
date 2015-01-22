from app_tree.models import Doctype, Element, Attribute, Text, TreeNode, Diff


def diff(node1, node2, main_attr=''):
    main_attrs = node1.element.attributes.filter(att_type__is_main=True)
    if main_attrs.exists():
        main_attr = ' ' + ' '.join([a.value for a in main_attrs])

    elt_name = node1.element.elt_type.name
    location = elt_name + main_attr

    diff_obj = Diff(treenode1=node1, treenode2=node2)

    if elt_name != node2.element.elt_type.name:
        print location + ' != ' + node2.element.elt_type.name
        diff_obj.elt_type_is_diff = True
        diff_obj.save()
    else:
        if list(node1.element.attributes.exclude(att_type__skip=True)) != list(node2.element.attributes.exclude(att_type__skip=True)):
            print location + ' attributes differ.'
            diff_obj.attrs_is_diff = True
            diff_obj.save()

        if node1.element.text and node1.element.text.name != node2.element.text.name:
            print location + ' texts differ:'
            print 'Text 1: ' + node1.element.text.contents
            print 'Text 2: ' + node2.element.text.contents
            diff_obj.texts_is_diff = True
            diff_obj.save()

    def value(node):
        return (
            node.element.elt_type,
            node.element.text,
            list(node.element.attributes.exclude(att_type__skip=True))
        )

    def values(node):
        return [
            value(n) for n in node.get_children()
        ]

    if values(node1) != values(node2):
        print location + ' children differ.'
        diff_obj.struct_is_diff = True
        diff_obj.save()

    def create_shadow(node, dataset):
        t = None
        if node.element.elt_type.is_mixed:
            t, c = Text.objects.get_or_create(contents='', name='empty', doctype=node.element.elt_type.doctype)
        e, c = Element.objects.get_or_create(elt_type=node.element.elt_type, text=t)
        return TreeNode(element=e, dataset=dataset, diff_only=True)

    nb1 = node1.get_children().count()
    nb2 = node2.get_children().count()
    i = 0
    imax = nb1 - nb2
    while nb1 > nb2:
        if i == imax: break
        i += 1
        for nodes in zip(node1.get_children(), node2.get_children()):
        	#TODO: something smarter for text node
            if value(nodes[0]) != value(nodes[1]) and not nodes[0].element.elt_type.is_mixed:
                n = create_shadow(nodes[0], nodes[1].dataset)
                n.insert_at(nodes[1], position='left', save=True)
                nb2 += 1
                break

    while nb1 > nb2:
        n = create_shadow(node1.get_children().last(), node2.dataset)
        n.insert_at(node2, position='last-child', save=True)
        nb2 += 1

    for nodes in zip(node1.get_children(), node2.get_children()):
        diff(nodes[0], nodes[1], main_attr)


def diff_trees(doctype_name, dataset_version1, dataset_version2):
    root1 = TreeNode.objects.root_nodes().get(
        dataset__name=dataset_version1,
        dataset__doctype__name=doctype_name
    )

    root2 = TreeNode.objects.root_nodes().get(
        dataset__name=dataset_version2,
        dataset__doctype__name=doctype_name
    )

    diff(root1, root2)