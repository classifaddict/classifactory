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


def _get_titles_flat(concept, lang):
    return '; '.join([d.text for d in concept.definition.filter(lang=lang)])


def _get_definition_flat(concept, lang):
    definitions = []
    for d in concept.definition.filter(lang=lang):
        definition = d.text
        if d.references.count():
            definition += ' (' + '; '.join([r.text for r in d.references.filter(lang=lang)]) + ')'
        definitions.append(definition)
    return '; '.join(definitions)


def _get_definition(concept, lang):
    definitions = []
    for d in concept.definition.filter(lang=lang):
        definition = {
            'title': d.text,
            'addClass': 'ws-wrap',
            'noLink': True,
            'expand': True
        }
        if d.references.count():
            definition['children'] = []
            for r in d.references.filter(lang=lang):
                definition['children'].append({
                    'title': r.text,
                    'addClass': 'ws-wrap',
                    'noLink': True
                })
        definitions.append(definition)
    return definitions


def home(request):
    return render(request, 'index.html')


@csrf_exempt
def topconcepts(request):
    """
    List all topconcepts.
    """
    if request.method == 'GET':
        lang = request.GET['lang']
        topconcepts = Concept.objects.filter(depth=1)
        dynatree = {}
        for t in topconcepts:
            dynatree['isFolder'] = True
            dynatree['title'] = _get_titles_flat(t, lang)
            children = []
            for c in t.narrower.all():
                children.append({
                    'isLazy': True,
                    'isFolder': True,
                    'key': c.id,
                    'title': _get_titles_flat(c, lang)
                })
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
        lang = request.GET['lang']
        dynatree = []
        if concept.depth not in [2, 5] and concept.definition.count():
            # Not a subsection, guidance heading nor group range without heading
            #dynatree.append({'title': _get_titles_flat(concept), 'addClass': 'ws-wrap', 'noLink': True})
            #dynatree.append({'title': _get_definition_flat(concept), 'addClass': 'ws-wrap', 'noLink': True})
            dynatree.extend(_get_definition(concept, lang))
        for c in concept.narrower.all():
            if c.depth == 5 and not c.definition.count():
                # Avoid group range without heading
                for cc in c.narrower.all():
                    dynatree.append({
                        'key': cc.id,
                        'isLazy': True,
                        'isFolder': True,
                        'title': cc.label
                    })
            else:
                child = {
                    'key': c.id,
                    'isLazy': True,
                    'isFolder': True
                }
                if c.depth == 5:
                    # Guidance heading
                    child['title'] = _get_titles_flat(c, lang)
                    child['addClass'] = 'ws-wrap'
                    child['noLink'] = True
                else:
                    child['title'] = c.label #+ ' ' + _get_titles_flat(c)
                dynatree.append(child)
        return JSONResponse(dynatree)
