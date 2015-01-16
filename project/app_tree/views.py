from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.renderers import JSONRenderer

from models import TreeNode
from serializers import ElementSerializer, ChildFancySerializer, KeySerializer


def home(request):
    return render(request, 'fancy_index.html')


class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


@csrf_exempt
def element_list(request):
    """
    List all root elements.
    """
    if request.method == 'GET':
        treenodes = TreeNode.objects.filter(parent=None)
        serializer = ElementSerializer(treenodes, many=True)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_detail(request, pk):
    """
    Retrieve an element.
    """
    try:
        treenode = TreeNode.objects.get(pk=pk)
    except TreeNode.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = ElementSerializer(treenode)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_fancy_roots(request):
    """
    List all root elements as FancyTree nodes.
    """

    if request.method == 'GET':
        treenode = TreeNode.objects.root_nodes()
        serializer = ChildFancySerializer(treenode, many=True)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_fancy_children(request, pk):
    """
    List all children of an element as FancyTree nodes.
    """

    if request.method == 'GET':
        treenode = TreeNode.objects.filter(parent=pk)
        serializer = ChildFancySerializer(treenode, many=True)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_fancy_ancestors(request, pk):
    """
    List all ancestors' pks of an element.
    """

    if request.method == 'GET':
        treenode = TreeNode.objects.get(pk=pk)
        ancestors = treenode.get_ancestors(
            ascending=True,
            include_self=True
        ).filter(is_lazy=True)
        serializer = KeySerializer(ancestors, many=True)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_fancy_search(request, query):
    """
    List all ancestors' pk of the first element found.
    """

    if request.method == 'GET':
        r = TreeNode.objects.all()
        for param in query.split():
            p = param.split('=')
            r = r.filter(
                element__attributes__att_type__name=p[0],
                element__attributes__value=p[1].upper()
            )

        if r.exists():
            treenode = r[0]
            ancestors = treenode.get_ancestors(
                ascending=True,
                include_self=True
            ).filter(is_lazy=True)

            serializer = KeySerializer(ancestors, many=True)
            return JSONResponse(serializer.data)
        else:
            return HttpResponse(status=404)

''' Diff:
t = TreeNode.objects.root_nodes()
for d in zip(t[0].get_descendants(), t[1].get_descendants()):
    f1 = [n.element for n in d[0].get_children()]
    f2 = [n.element for n in d[1].get_children()]
    if f1 != f2:
         x+=1
         print f1, f2
         if x==5: break
'''