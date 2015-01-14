from django.contrib import admin
from django_mptt_admin.admin import DjangoMpttAdmin
from models import Element, Attribute, Data, Doctype, TreeNode


class DoctypeAdmin(admin.ModelAdmin):
    list_display = ('name', )

admin.site.register(Doctype, DoctypeAdmin)


class TreeNodeAdmin(DjangoMpttAdmin):
    pass

admin.site.register(TreeNode, TreeNodeAdmin)


class ElementAdmin(admin.ModelAdmin):
    list_display = ('doctype', 'name')

admin.site.register(Element, ElementAdmin)


class AttributeAdmin(admin.ModelAdmin):
    list_display = ('doctype', 'name', 'value')

admin.site.register(Attribute, AttributeAdmin)


class DataAdmin(admin.ModelAdmin):
    list_display = ('element', 'lang', 'texts')

admin.site.register(Data, DataAdmin)

