from django.contrib import admin
from django_mptt_admin.admin import DjangoMpttAdmin
from models import Element, Attribute, Text, Doctype, TreeNode, Dataset


class DoctypeAdmin(admin.ModelAdmin):
    list_display = ('name', )

admin.site.register(Doctype, DoctypeAdmin)


class DatasetAdmin(admin.ModelAdmin):
    list_display = ('name', )

admin.site.register(Dataset, DatasetAdmin)


class TreeNodeAdmin(DjangoMpttAdmin):
    pass

admin.site.register(TreeNode, TreeNodeAdmin)


class ElementAdmin(admin.ModelAdmin):
    pass

admin.site.register(Element, ElementAdmin)


class AttributeAdmin(admin.ModelAdmin):
    list_display = ('value',)

admin.site.register(Attribute, AttributeAdmin)


class TextAdmin(admin.ModelAdmin):
    list_display = ('lang', 'contents')

admin.site.register(Text, TextAdmin)

