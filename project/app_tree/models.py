from lxml.html.diff import htmldiff
from django.db import models
from django.db.models import Q
from mptt.models import MPTTModel, TreeForeignKey


class AbstractType(models.Model):
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True


class Doctype(AbstractType):
    pass


class AttributeType(AbstractType):
    doctype = models.ForeignKey('Doctype', related_name='attribute_types')
    is_main = models.BooleanField(default=False)
    skip = models.BooleanField(default=False)

    class Meta:
        unique_together = ('doctype', 'name')
        index_together = [['doctype', 'name']]
        ordering = ['name']


class ElementType(AbstractType):
    doctype = models.ForeignKey('Doctype', related_name='element_types')
    attributes = models.ManyToManyField('AttributeType', related_name='element_types', blank=True)
    required_attr = models.ManyToManyField('AttributeType', blank=True)
    is_main = models.BooleanField(default=False)
    is_mixed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('doctype', 'name')
        index_together = [['doctype', 'name']]
        ordering = ['name']


class Dataset(models.Model):
    doctype = models.ForeignKey('Doctype', related_name='datasets')
    name = models.CharField(max_length=8)  # e.g. IPC Version

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('doctype', 'name')
        index_together = [['doctype', 'name']]


class Attribute(models.Model):
    type = models.ForeignKey('AttributeType', related_name='attribute_instances')
    value = models.CharField(max_length=128)

    def attr_html(self):
        cls = ''
        if self.type.is_main:
            cls = ' class="main"'
        return '<dt>%s</dt><dd%s>%s</dd>' % (self.type.name, cls, self.value)

    def __unicode__(self):
        return self.type.name

    class Meta:
        unique_together = ('type', 'value')
        index_together = [['type', 'value']]
        ordering = ['type__name']


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
        index_together = [['doctype', 'name']]


class Element(models.Model):
    type = models.ForeignKey('ElementType', related_name='element_instances')
    text = models.ForeignKey('Text', null=True, blank=True)
    attrs_key = models.CharField(max_length=32, blank=True)
    main_attrs = models.CharField(max_length=32, blank=True)
    attributes = models.ManyToManyField('Attribute', blank=True)

    def attributes_html(self):
        if self.attributes.exists():
            return '<dl>%s</dl>' % ''.join(
                [a.attr_html() for a in self.attributes.all()]
            )
        return ''

    def values(self):
        texts = ''
        if self.text is not None and self.text.texts_html() != '':
            texts = ': ' + self.text.texts_html()
        return self.type.name + self.attributes_html() + texts

    def __unicode__(self):
        return self.type.name

    class Meta:
        unique_together = ('type', 'text', 'attrs_key')
        index_together = [['type', 'text', 'attrs_key']]


class Diff(models.Model):
    treenode1 = models.ForeignKey('TreeNode', related_name='tree1_diffs')
    treenode2 = models.ForeignKey('TreeNode', related_name='tree2_diffs')
    is_type_diff = models.BooleanField(default=False)
    is_texts_diff = models.BooleanField(default=False)
    is_attrs_diff = models.BooleanField(default=False)
    is_del_diff = models.BooleanField(default=False)
    is_ins_diff = models.BooleanField(default=False)

    class Meta:
        unique_together = ('treenode1', 'treenode2')
        index_together = [['treenode1', 'treenode2']]
        ordering = ['treenode2']


class TreeNode(MPTTModel):
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children')
    fingerprint = models.CharField(max_length=32)
    element = models.ForeignKey('Element', related_name='treenodes')
    dataset = models.ForeignKey('Dataset', related_name='treenodes')
    is_diff_only = models.BooleanField(default=False)

    def lazy_children(self):
        children = self.get_children().select_related(
            'element'
        ).prefetch_related(
            'element__attributes'
        )
        if not self.element.type.is_main:
            # Return all children because current node is not lazy
            return children
        # Return children which element type is different than parent one
        return children.exclude(parent__element__type=self.element.type)

    def is_container(self):
        if self.is_leaf_node():
            return False
        return True

    def expanded(self):
        if self.element.type.is_main or self.is_root_node():
            return False
        return True

    def text_diff(self):
        diffs = self.tree2_diffs.filter(is_texts_diff=True)
        if diffs.exists():
            diff = diffs.first()
            return htmldiff(
                diff.treenode1.element.text.texts_html(),
                diff.treenode2.element.text.texts_html()
            )
        return None

    def attrs_diff(self):
        diffs = self.tree2_diffs.filter(is_attrs_diff=True)
        if diffs.exists():
            diff = diffs.first()
            return htmldiff(
                diff.treenode1.element.attributes_html(),
                diff.treenode2.element.attributes_html()
            )
        return None

    def diff_kind(self):
        diffs = self.tree2_diffs.filter(
            Q(is_texts_diff=True) | Q(is_attrs_diff=True) | Q(is_type_diff=True)
        )
        if diffs.exists():
            return 'mod'

        diffs = self.tree2_diffs.filter(is_del_diff=True)
        if diffs.exists():
            return 'del'

        diffs = self.tree2_diffs.filter(is_ins_diff=True)
        if diffs.exists():
            return 'ins'

        return None

    def __unicode__(self):
        return self.element.type.name
