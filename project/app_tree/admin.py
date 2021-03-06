from django.contrib import admin
from django_mptt_admin.admin import DjangoMpttAdmin

from models import Dataset, Doctype, ElementType, AttributeType
from models import Element, Attribute, Text, Translation
from models import TreeNode, Diff


class DatasetAdmin(admin.ModelAdmin):
    list_display = ('name', )

admin.site.register(Dataset, DatasetAdmin)


class DoctypeAdmin(admin.ModelAdmin):
    list_display = ('name', )

admin.site.register(Doctype, DoctypeAdmin)


class ElementTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_main', 'is_mixed', 'doctype')

admin.site.register(ElementType, ElementTypeAdmin)


class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_main', 'skip', 'doctype')

admin.site.register(AttributeType, AttributeTypeAdmin)


class TreeNodeAdmin(DjangoMpttAdmin):
    list_display = ('element', 'dataset', 'is_diff_only')
    list_filter = ('is_diff_only', 'dataset')

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
    list_display = ('treenode1', 'treenode2', 'is_type_diff', 'is_texts_diff', 'is_attrs_diff', 'is_del_diff', 'is_ins_diff')

admin.site.register(Diff, DiffAdmin)

