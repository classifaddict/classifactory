from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer

from app_scheme.models import Concept
#from app_scheme.serializers import TopConceptSerializer, ConceptSerializer


class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


def _get_definition(concept):
    return '; '.join([d.text for d in concept.definition.all()])


def home(request):
    return render(request, 'index.html')


@csrf_exempt
def topconcepts(request):
    """
    List all topconcepts.
    """
    if request.method == 'GET':
        topconcepts = Concept.objects.filter(depth=1)
        dynatree = {}
        for t in topconcepts:
            dynatree['isFolder'] = True
            dynatree['title'] = _get_definition(t)
            children = []
            for c in t.narrower.all():
                child = {}
                child['isLazy'] = True
                child['isFolder'] = True
                child['key'] = c.id
                child['title'] = _get_definition(c)
                children.append(child)
            dynatree['children'] = children
        return JSONResponse(dynatree)


@csrf_exempt
def concept(request, pk):
    """
    Retrieve an concept.
    """
    try:
        concept = Concept.objects.get(pk=pk)
    except Concept.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        dynatree = []
        if concept.depth not in [2, 5] and concept.definition.count():
            # Not a subsection, guidance heading nor group range without heading
        	dynatree.append({'title': _get_definition(concept), 'addClass': 'ws-wrap', 'noLink': True})
        for c in concept.narrower.all():
            child = {}
            child['isLazy'] = True
            child['key'] = c.id
            child['isFolder'] = True
            if c.depth == 5 and c.definition.count():
                # Guidance heading
                child['title'] = _get_definition(c)
            else:
                child['title'] = c.label

            dynatree.append(child)
        return JSONResponse(dynatree)
