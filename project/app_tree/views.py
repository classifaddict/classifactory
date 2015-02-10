from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from rest_framework.renderers import JSONRenderer

from models import TreeNode
from serializers import ElementSerializer, ChildFancySerializer, KeySerializer, PaginatedKeySerializer


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
        treenode = TreeNode.objects.root_nodes().select_related('element').prefetch_related(
            'element__attributes'
        )
        serializer = ChildFancySerializer(treenode, many=True)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_fancy_children(request, pk):
    """
    List all children of an element as FancyTree nodes.
    """

    if request.method == 'GET':
        treenode = TreeNode.objects.select_related('element').prefetch_related(
            'element__attributes'
        ).filter(parent=pk)
        serializer = ChildFancySerializer(treenode, many=True)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_fancy_ancestors(request, pk):
    """
    List all ancestors' pks of an element.
    """

    if request.method == 'GET':
        treenode = TreeNode.objects.only('id').get(pk=pk)

        # Lazy ancestors (the ones for which element__type__is_main)
        # only are returned
        ancestors = treenode.get_ancestors(
            ascending=True,
            include_self=True
        ).filter(element__type__is_main=True)

        serializer = KeySerializer(ancestors, many=True)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_fancy_search(request, query):
    """
    List all ancestors' pk of the first element found.
    """

    if request.method == 'GET':
        r = TreeNode.objects.only('id')
        for param in query.split():
            p = param.split('=')
            r = r.filter(
                element__attributes__type__name=p[0],
                element__attributes__value=p[1]
            )

        if r.exists():
            # Lazy ancestors (the ones for which element__type__is_main)
            # only are returned
            treenode = r[0]
            ancestors = treenode.get_ancestors(
                ascending=True,
                include_self=True
            ).filter(element__type__is_main=True)

            serializer = KeySerializer(ancestors, many=True)
            return JSONResponse(serializer.data)
        else:
            return HttpResponse(status=404)


def diffs(request, dataset_name):
    queryset = TreeNode.objects.select_related(
        'dataset', 'tree2_diffs'
    ).filter(
        dataset__name=dataset_name,
        tree2_diffs__isnull=False
    )

    paginator = Paginator(queryset, 5)
    page = request.GET.get('page')
    try:
        diffs = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        diffs = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999),
        # deliver last page of results.
        diffs = paginator.page(paginator.num_pages)

    serializer = PaginatedKeySerializer(diffs)

    return JSONResponse(serializer.data)
