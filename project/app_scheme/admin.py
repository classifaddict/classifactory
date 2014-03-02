from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from app_scheme.models import Concept, Definition, Reference


class ConceptAdmin(MPTTModelAdmin):
    list_display = ('notation', 'label')

admin.site.register(Concept, ConceptAdmin)


class DefinitionAdmin(admin.ModelAdmin):
    list_display = ('concept', 'text')

admin.site.register(Definition, DefinitionAdmin)


class ReferenceAdmin(admin.ModelAdmin):
    list_display = ('definition', 'text')

admin.site.register(Reference, ReferenceAdmin)
