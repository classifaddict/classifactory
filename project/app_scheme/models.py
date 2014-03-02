from django.db import models
from django.conf import settings
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
        return self.label

    class MPTTMeta:
        order_insertion_by = ['notation']


class Definition(models.Model):
    concept = models.ForeignKey('Concept', null=True, blank=True, related_name='definition')
    text = models.TextField()
    
    def __unicode__(self):
        return self.text


class Reference(models.Model):
    definition = models.ForeignKey('Definition', null=True, blank=True, related_name='references')
    text = models.TextField()
    
    def __unicode__(self):
        return self.text