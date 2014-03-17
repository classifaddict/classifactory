from django.db import models
#from django.conf import settings
from mptt.models import MPTTModel, TreeForeignKey

# IPC/SKOS mapping
# 18 chr symbol or range = notation
# pretty symbol or range = prefLabel
# parent (broader)
# children = narrower
# kind = depth
# titles = definition


class Concept(MPTTModel):
    notation = models.CharField(max_length=39, unique=True)
    label = models.CharField(max_length=39)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='narrower')
    depth = models.IntegerField()

    def __unicode__(self):
        return self.notation

    class MPTTMeta:
        order_insertion_by = ['notation']


class Definition(models.Model):
    concept = models.ForeignKey('Concept', related_name='definition')
    lang = models.CharField(max_length=2)
    text = models.TextField()

    def __unicode__(self):
        return self.text


class Reference(models.Model):
    definition = models.ForeignKey('Definition', related_name='references')
    lang = models.CharField(max_length=2)
    text = models.TextField()

    def __unicode__(self):
        return self.text
