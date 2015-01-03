from django.db import models
from mptt.models import MPTTModel, TreeForeignKey


class Element(MPTTModel):
    name = models.CharField(max_length=128)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children')

    def is_container(self):
        return self.children.count()

    def attributes_html(self):
        if not self.attributes.count():
            return None

        return '<dl>%s</dl>' % ''.join(['<dt>%s</dt><dd>%s</dd>' % (
            a.name,
            a.value
        ) for a in self.attributes.all()])

    def lazy(self):
        if self.is_container():
            return True
        return False

    def __unicode__(self):
        return self.name


class Attribute(models.Model):
    element = models.ForeignKey('Element', related_name='attributes')
    name = models.CharField(max_length=128)
    value = models.CharField(max_length=128)

    def __unicode__(self):
        return self.name


class Data(models.Model):
    element = models.ForeignKey('Element', related_name='data')
    lang = models.CharField(max_length=2)
    texts = models.TextField()
