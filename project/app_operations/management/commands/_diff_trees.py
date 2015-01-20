from app_tree.models import Doctype, Element, Attribute, Text, TreeNode, Diff


def diff(node1, node2, main_attr=''):
    elt_name = node1.element.elt_type.name

    main_attrs = node1.element.attributes.filter(att_type__is_main=True)
    if main_attrs.exists():
    	main_attr = ' ' + ' '.join([a.value for a in main_attrs])
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

    elts_children1 = [(n.element.text, list(n.element.attributes.exclude(att_type__skip=True))) for n in node1.get_children()]
    elts_children2 = [(n.element.text, list(n.element.attributes.exclude(att_type__skip=True))) for n in node2.get_children()]
    if elts_children1 != elts_children2:
        print location + ' children differ.'
        diff_obj.struct_is_diff = True
        diff_obj.save()

    for nodes in zip(node1.get_children(), node2.get_children()):
        diff(nodes[0], nodes[1], main_attr)

    count1 = node1.get_children().count()
    count2 = node2.get_children().count()
    if count1 > count2:
        print location + ' (tree #1) ' + ' has ' + str(count1 - count2) + ' node(s) more.'
    elif count2 > count1:
        print location + ' (tree #2) ' + ' has ' + str(count2 - count1) + ' node(s) more.'


    # s1 = set(node1.get_children())
    # s2 = set(node2.get_children())
    # symdiff = s1.symmetric_difference(s2)
    # print symdiff


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