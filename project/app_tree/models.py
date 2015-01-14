from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.html import escape

class Doctype(models.Model):
    name = models.CharField(max_length=128, unique=True)
    main_attr = models.CharField(max_length=128)
    lazy_nodes = models.CharField(max_length=512)

    def __unicode__(self):
        return self.name


class Attribute(models.Model):
    doctype = models.ForeignKey('Doctype', related_name='attributes')
    name = models.CharField(max_length=128)
    value = models.CharField(max_length=128)

    def is_main(self):
        if self.name in self.doctype.main_attr.split():
            return True
        return False

    def attr_html(self):
        cls = ''
        if self.is_main():
            cls = ' class="main"'
        return '<dt>%s</dt><dd%s>%s</dd>' % (self.name, cls, self.value)

    class Meta:
        unique_together = ('doctype', 'name', 'value')
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Element(models.Model):
    doctype = models.ForeignKey('Doctype', related_name='elements')
    name = models.CharField(max_length=128)
    attributes = models.ManyToManyField(Attribute, null=True, blank=True)
    dataset_version = models.CharField(max_length=8)

    def attributes_html(self):
        if not self.attributes.count():
            return None
        return '<dl>%s</dl>' % ''.join([a.attr_html() for a in self.attributes.all()])

    def __unicode__(self):
        return self.name


class TreeNode(MPTTModel):
    element = models.ForeignKey('Element', related_name='elements')
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children')
    is_lazy = models.BooleanField()

    # @property
    # def is_lazy(self):
    #     if self.element.name in self.element.doctype.lazy_nodes.split():
    #         return True
    #     return False

    def lazy_children(self):
        if self.is_lazy:
            return self.get_children().exclude(parent__element__name=self.element.name)
        return self.get_children()

    def is_container(self):
        if self.is_leaf_node():
            return False
        return True

    def expanded(self):
        if self.is_lazy or self.is_root_node() :
            return False
        return True

    def __unicode__(self):
        return self.element.name


class Data(models.Model):
    element = models.ForeignKey('Element', related_name='data')
    lang = models.CharField(max_length=2, default='en')
    texts = models.TextField()

    def texts_html(self):
        return escape(self.texts)


    class Meta:
        unique_together = ('element', 'lang')
