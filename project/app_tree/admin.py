from django.contrib import admin
from django_mptt_admin.admin import DjangoMpttAdmin
from models import Element, Attribute, Text, Translation, Doctype, TreeNode, Dataset, Diff


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


class TranslationAdmin(admin.ModelAdmin):
    list_display = ('lang', 'contents')

admin.site.register(Translation, TranslationAdmin)


class TextAdmin(admin.ModelAdmin):
    list_display = ('name', 'contents')

admin.site.register(Text, TextAdmin)


class DiffAdmin(admin.ModelAdmin):
    list_display = ('treenode1', 'treenode2', 'elt_type_is_diff', 'texts_is_diff', 'attrs_is_diff', 'struct_is_diff')

admin.site.register(Diff, DiffAdmin)

