from rest_framework import serializers, pagination
from models import Attribute, Text, TreeNode


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ('name', 'value')


class TextSerializer(serializers.ModelSerializer):
    class Meta:
        model = Text
        fields = ('lang', 'contents')


class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreeNode
        fields = ('id',)


class ElementSerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True)
    children = ChildSerializer(many=True)
    text = TextSerializer(many=True)

    class Meta:
        model = TreeNode
        fields = ('id', 'element.elt_type.name', 'element.attributes', 'element.text', 'children')


class HtmlDataSerializer(serializers.Serializer):
    text = serializers.CharField(source='texts_html')


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class KeySerializer(serializers.Serializer):
    key = serializers.CharField(source='pk')


# class PaginatedKeySerializer(pagination.PaginationSerializer):
#     class Meta:
#         object_serializer_class = KeySerializer


class ChildFancySerializer(KeySerializer):
    # FancyTree specific values
    title = serializers.CharField(source='element.type.name')
    folder = serializers.BooleanField(source='is_container')
    lazy = serializers.BooleanField(source='element.type.is_main')
    expanded = serializers.BooleanField()
    children = RecursiveField(source='lazy_children', required=False, many=True)

    # Subsequent FancyTreeTable columns values

    attrs = serializers.CharField(source='element.attributes_html')
    text = serializers.CharField(source='element.text.texts_html')


class ChildDiffFancySerializer(ChildFancySerializer):
    text_diff = serializers.CharField()
    attrs_diff = serializers.CharField()
    diff_kind = serializers.CharField()


class ChildFancyNoTableSerializer(ChildDiffFancySerializer):
    title = serializers.CharField(source='element.values')
