from app_tree.models import Doctype, Element, Attribute, Text, TreeNode, Diff


def value(node):
    return (
        node.element.type,
        node.element.text,
        node.element.main_attrs
    )


def children_values(node):
    return [
        value(n) for n in node.get_children()
    ]


def create_shadow(node, dataset):
    t = None
    if node.element.type.is_mixed:
        t, c = Text.objects.get_or_create(
            contents='',
            name='empty',
            doctype=node.element.type.doctype
        )
    e, c = Element.objects.get_or_create(
        type=node.element.type,
        text=t,
        attrs_key=node.element.attrs_key,
        main_attrs=node.element.main_attrs
    )
    return TreeNode(
        element=e, dataset=dataset, is_diff_only=True
    )


def diff(node1, node2, main_attr=''):
    main_attrs = node1.element.attributes.filter(type__is_main=True)
    if main_attrs.exists():
        main_attr = ' ' + ' '.join([a.value for a in main_attrs])

    elt_name = node1.element.type.name
    location = elt_name + main_attr

    try:
        diff_obj = Diff.objects.get(treenode1=node1, treenode2=node2)
    except:
        diff_obj = Diff(treenode1=node1, treenode2=node2)

    if elt_name != node2.element.type.name:
        print location + ' != ' + node2.element.type.name
        if not node1.is_root_node():
            diff_obj.is_type_diff = True
            diff_obj.save()
        return
        # No need to go on if both elements are not of same type

    if node1.element.main_attrs != node2.element.main_attrs:
        print location + ' main attributes differ.'
        if not node1.is_root_node():
            diff_obj.is_attrs_diff = True
            diff_obj.save()
        return
        # No need to go on if both elements are not of same kind

    if diff_obj.is_del_diff:
        print location + ' has been deleted.'
        return
        # No need to go on if node has been deleted

    if node1.element.text and node1.element.text.name != node2.element.text.name:
        print location + ' texts differ:'
        print 'Text 1: ' + node1.element.text.contents
        print 'Text 2: ' + node2.element.text.contents
        diff_obj.is_texts_diff = True
        diff_obj.save()

    if children_values(node1) != children_values(node2):
        print location + ' children differ.'

    nb1 = node1.get_children().count()
    nb2 = node2.get_children().count()
    i = 0
    imax = nb1 - nb2
    while nb1 > nb2:
        # Try to insert shadow node(s) in 2nd tree to obtain same size
        if i == imax: break
        i += 1
        for nodes in zip(node1.get_children(), node2.get_children()):
            if nodes[0].element.type.is_mixed:
                #TODO: something smarter for text node
                continue
            if value(nodes[0]) != value(nodes[1]):
                n = create_shadow(nodes[0], nodes[1].dataset)
                n.insert_at(nodes[1], position='left', save=True)
                diff_obj, c = Diff.objects.get_or_create(
                	treenode1=nodes[0],
                	treenode2=n
                )
                diff_obj.is_del_diff = True
                diff_obj.save()
                nb2 += 1
                break

    node1_last_child = node1.get_children().last()
    while nb1 > nb2:
    	# Add shadow node(s) in 2nd tree to obtain same size
        n = create_shadow(node1_last_child, node2.dataset)
        n.insert_at(node2, position='last-child', save=True)
        diff_obj, c = Diff.objects.get_or_create(
            treenode1=node1_last_child,
            treenode2=n
        )
        diff_obj.is_del_diff = True
        diff_obj.save()
        nb2 += 1

    i = 0
    imax = nb2 - nb1
    while nb2 > nb1:
        if i == imax: break
        i += 1
        for nodes in zip(node1.get_children(), node2.get_children()):
            if nodes[0].element.type.is_mixed:
                #TODO: something smarter for text node
                continue
            if value(nodes[0]) != value(nodes[1]):
                diff_obj, c = Diff.objects.get_or_create(
                    treenode1=nodes[0],
                    treenode2=nodes[1]
                )
                if c:
                    diff_obj.is_ins_diff = True
                    diff_obj.save()
                    nb1 += 1

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