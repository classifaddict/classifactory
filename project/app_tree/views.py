from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from models import Element
from serializers import ElementSerializer, ChildFancySerializer


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
        elements = Element.objects.filter(parent=None)
        serializer = ElementSerializer(elements, many=True)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_detail(request, pk):
    """
    Retrieve an element.
    """
    try:
        element = Element.objects.get(pk=pk)
    except Element.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = ElementSerializer(element)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_fancy_roots(request):
    """
    List all root elements as FancyTree nodes.
    """

    if request.method == 'GET':
        element = Element.objects.filter(parent=None)
        serializer = ChildFancySerializer(element, many=True)
        return JSONResponse(serializer.data)


@csrf_exempt
def element_fancy_children(request, pk):
    """
    List all children of an element as FancyTree nodes.
    """

    if request.method == 'GET':
        element = Element.objects.filter(parent=pk)
        serializer = ChildFancySerializer(element, many=True)
        return JSONResponse(serializer.data)
