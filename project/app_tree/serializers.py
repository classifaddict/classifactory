from rest_framework import serializers
from models import Element, Attribute, Data, TreeNode


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ('name', 'value')


class DataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Data
        fields = ('lang', 'texts')


class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreeNode
        fields = ('id',)


class ElementSerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True)
    children = ChildSerializer(many=True)
    data = DataSerializer(many=True)


    class Meta:
        model = TreeNode
        fields = ('id', 'element.name', 'element.attributes', 'element.data', 'children')


class HtmlDataSerializer(serializers.Serializer):
    lang = serializers.CharField()
    texts = serializers.CharField(source='texts_html')


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class KeySerializer(serializers.Serializer):
    key = serializers.CharField(source='pk')


class ChildFancySerializer(KeySerializer):
    title = serializers.CharField(source='element.name')
    folder = serializers.BooleanField(source='is_container')
    attrs = serializers.CharField(source='element.attributes_html')
    data = HtmlDataSerializer(source='element.data', many=True)
    lazy = serializers.BooleanField(source='is_lazy')
    expanded = serializers.BooleanField()
    children = RecursiveField(source='lazy_children', required=False, many=True)
