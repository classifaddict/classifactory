from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from rest_framework.renderers import JSONRenderer
from rest_framework.decorators import api_view, permission_classes

from models import TreeNode
from serializers import ElementSerializer, ChildFancyNoTableSerializer, ChildDiffFancySerializer, KeySerializer#, PaginatedKeySerializer
from rest_framework.pagination import PageNumberPagination

def home(request):
    return render(request, 'fancy_index.html')


def mode(request, mode):
    if mode == 'table':
        return render(request, 'fancy_index.html')
    else:
        return render(request, 'fancy_notable_index.html')


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
        serializer = ChildDiffFancySerializer(treenode, many=True)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_fancy_children(request, mode, pk):
    """
    List all children of an element as FancyTree nodes.
    """

    if request.method == 'GET':
        treenode = TreeNode.objects.select_related('element').prefetch_related(
            'element__attributes'
        ).filter(parent=pk)
        if mode == 'table':
            serializer = ChildDiffFancySerializer(treenode, many=True)
        else:
            serializer = ChildFancyNoTableSerializer(treenode, many=True)
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
@api_view(['GET'])
def element_fancy_search(request, query):
    """
    List all ancestors' pk of the first element found.
    """

    queryset = TreeNode.objects.only('id')

    for param in query.split():
        if '!' in param:
            p = param.split('!')
            if len(p) > 2:
                break
            queryset = queryset.filter(
                dataset__doctype__name=p[0],
                dataset__name=p[1]
            )
        elif '@' in param:
            # Search specified element by attribute
            p = param.split('@')
            if len(p) > 2:
                continue
            if p[0] and p[1]:
                if '=' in p[1]:
                    a = p[1].split('=')
                    if len(a) > 2:
                        continue
                    if a[0] and a[1]:
                        # 'e@a=v' Search specified element by attribute name and value
                        queryset = queryset.filter(
                            element__type__name=p[0],
                            element__attributes__type__name=a[0],
                            element__attributes__value=a[1]
                        )
                    elif a[1]:
                        # 'e@=v' Search specified element by attribute value
                        queryset = queryset.filter(
                            element__type__name=p[0],
                            element__attributes__value=a[1]
                        )
                else:
                    # 'e@a' Search specified element by attribute name
                    queryset = queryset.filter(
                        element__type__name=p[0],
                        element__attributes__type__name=p[1],
                    )
            elif p[1]:
                # Search any element by attribute
                if '=' in p[1]:
                    a = p[1].split('=')
                    if len(a) > 2:
                        continue
                    if a[0] and a[1]:
                        # '@a=v' Search any element by attribute name and value
                        queryset = queryset.filter(
                            element__attributes__type__name=a[0],
                            element__attributes__value=a[1]
                        )
                    elif a[1]:
                        # '@=v' Search any element by attribute value
                        queryset = queryset.filter(
                            element__attributes__value=a[1]
                        )
                else:
                    # '@a' Search any element by attribute name
                    queryset = queryset.filter(
                        element__attributes__type__name=p[1]
                    )
            else:
                # '@' Search any element with attribute
                queryset = queryset.filter(
                    element__attributes__isnull=False
                )
        else:
            # if '=' in p[1]:
                # 'e=t' Search element by content
            # else:
            # 'e' Search specified element by name
            queryset = queryset.filter(
                element__type__name=param
            )

    paginator = PageNumberPagination()
    paginator.page_size = 1

    result_page = paginator.paginate_queryset(queryset, request)
    serializer = KeySerializer(result_page, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
def diffs(request, doctype_name, dataset_name):
    queryset = TreeNode.objects.select_related(
        'dataset', 'tree2_diffs'
    ).filter(
        dataset__doctype__name=doctype_name,
        dataset__name=dataset_name,
        tree2_diffs__isnull=False
    )

    paginator = PageNumberPagination()
    paginator.page_size = 1

    result_page = paginator.paginate_queryset(queryset, request)
    serializer = KeySerializer(result_page, many=True)

    return paginator.get_paginated_response(serializer.data)
