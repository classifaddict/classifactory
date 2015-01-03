from django.contrib import admin
from django_mptt_admin.admin import DjangoMpttAdmin
from models import Element, Attribute, Data


class ElementAdmin(DjangoMpttAdmin):
    pass

admin.site.register(Element, ElementAdmin)


class AttributeAdmin(admin.ModelAdmin):
    pass

admin.site.register(Attribute, AttributeAdmin)


class DataAdmin(admin.ModelAdmin):
    pass

admin.site.register(Data, DataAdmin)

