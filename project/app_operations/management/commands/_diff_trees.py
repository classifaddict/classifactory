from app_tree.models import Doctype, Element, Attribute, Text, TreeNode, Diff


def diff(node1, node2, main_attrs, main_att_val=''):
    elt_name = node1.element.elt_type.name
    elt_attr_names = set([a.att_type.name for a in node1.element.attributes.all()])
    elt_attr_names.intersection_update(main_attrs)
    if elt_attr_names:
        main_att_val = node1.element.attributes.get(att_type__name=elt_attr_names.pop()).value

    diff_obj = Diff(treenode1=node1, treenode2=node2)
    if node1.element != node2.element:
        if elt_name != node2.element.elt_type.name:
            print elt_name + ' != ' + node2.element.elt_type.name
            diff_obj.elt_type_is_diff = True
            diff_obj.save()
        else:
            if list(node1.element.attributes.all()) != list(node2.element.attributes.all()):
                print elt_name + ' ' + main_att_val + ' attributes differ.'
                diff_obj.attrs_is_diff = True
                diff_obj.save()

            if node1.element.text.name != node2.element.text.name:
                print elt_name + ' ' + main_att_val + ' texts differ:'
                print 'Text 1: ' + node1.element.text.contents
                print 'Text 2: ' + node2.element.text.contents
                diff_obj.texts_is_diff = True
                diff_obj.save()

    elts_children1 = [n.element for n in node1.get_children()]
    elts_children2 = [n.element for n in node2.get_children()]
    if elts_children1 != elts_children2:
        print elt_name + ' ' + main_att_val + ' children differ.'
        diff_obj.struct_is_diff = True
        diff_obj.save()

    for nodes in zip(node1.get_children(), node2.get_children()):
        diff(nodes[0], nodes[1], main_attrs, main_att_val)

    count1 = node1.get_children().count()
    count2 = node2.get_children().count()
    if count1 > count2:
        print elt_name + ' ' + main_att_val + ' (tree #1) ' + ' has ' + str(count1 - count2) + ' node(s) more.'
    elif count2 > count1:
        print elt_name + ' ' + main_att_val + ' (tree #2) ' + ' has ' + str(count2 - count1) + ' node(s) more.'


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

    main_attrs = set(root1.dataset.doctype.main_attrs.split())

    diff(root1, root2, main_attrs)