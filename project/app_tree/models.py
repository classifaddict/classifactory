from django.db import models
from mptt.models import MPTTModel, TreeForeignKey


class AbstractType(models.Model):
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True


class Doctype(AbstractType):
    main_attrs = models.CharField(max_length=128)
    main_elts = models.CharField(max_length=512)


class AttributeType(AbstractType):
    doctype = models.ForeignKey('Doctype', related_name='attribute_types')

    def is_main(self):
        if self.name in self.doctype.main_attrs.split():
            return True
        return False

    class Meta:
        unique_together = ('doctype', 'name')
        ordering = ['name']


class ElementType(AbstractType):
    doctype = models.ForeignKey('Doctype', related_name='element_types')
    attributes = models.ManyToManyField('AttributeType', related_name='element_types', null=True, blank=True)
    required_attr = models.ManyToManyField('AttributeType', null=True, blank=True)
    #is_mixed_contents = models.BooleanField(default=False)

    class Meta:
        unique_together = ('doctype', 'name')
        ordering = ['name']


class Dataset(models.Model):
    doctype = models.ForeignKey('Doctype', related_name='datasets')
    name = models.CharField(max_length=8)  # e.g. IPC Version

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('doctype', 'name')


class Attribute(models.Model):
    att_type = models.ForeignKey('AttributeType', related_name='attribute_instances')
    value = models.CharField(max_length=128)

    def is_main(self):
        return self.att_type.is_main()

    def attr_html(self):
        cls = ''
        if self.is_main():
            cls = ' class="main"'
        return '<dt>%s</dt><dd%s>%s</dd>' % (self.att_type.name, cls, self.value)

    def __unicode__(self):
        return self.att_type.name

    class Meta:
        unique_together = ('att_type', 'value')
        ordering = ['att_type__name']


class Translation(models.Model):
    text = models.ForeignKey('Text', related_name='translations')
    lang = models.CharField(max_length=2)
    contents = models.TextField()

    def texts_html(self):
        return self.contents.replace('<', '&lt;')

    def __unicode__(self):
        return self.lang


class Text(models.Model):
    doctype = models.ForeignKey('Doctype', related_name='texts')
    name = models.CharField(max_length=32)
    contents = models.TextField()

    def texts_html(self):
        return self.contents.replace('<', '&lt;')

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('doctype', 'name')


class Element(models.Model):
    elt_type = models.ForeignKey('ElementType', related_name='element_instances')
    attributes = models.ManyToManyField('Attribute', null=True, blank=True)
    text = models.ForeignKey('Text', null=True, blank=True)

    def attributes_html(self):
        if self.attributes.exists():
            return '<dl>%s</dl>' % ''.join(
                [a.attr_html() for a in self.attributes.all()]
            )
        return None

    def __unicode__(self):
        return self.elt_type.name


# class Diff(models.Model):
#     dataset = models.ForeignKey('Dataset', related_name='diffs')
#     treenode = models.ForeignKey('TreeNode', related_name='diffs')
#     is_texts = models.BooleanField(default=False)
#     is_attrs = models.BooleanField(default=False)
#     is_struct = models.BooleanField(default=False)


class TreeNode(MPTTModel):
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children')
    element = models.ForeignKey('Element', related_name='treenodes')
    dataset = models.ForeignKey('Dataset', related_name='treenodes')
    is_lazy = models.BooleanField()

    # @property
    # def is_lazy(self):
    #     if self.element.name in self.element.doctype.main_elts.split():
    #         return True
    #     return False

    def lazy_children(self):
        if self.is_lazy and not self.is_root_node():
            return self.get_children().exclude(parent__element__elt_type=self.element.elt_type)
        return self.get_children()

    def is_container(self):
        if self.is_leaf_node():
            return False
        return True

    def expanded(self):
        if self.is_lazy or self.is_root_node():
            return False
        return True

    def __unicode__(self):
        return self.element.elt_type.name
