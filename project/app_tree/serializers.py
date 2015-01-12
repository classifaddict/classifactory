from rest_framework import serializers
from models import Element, Attribute, Data


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
        model = Element
        fields = ('id',)


class ElementSerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True)
    children = ChildSerializer(many=True)
    data = DataSerializer(many=True)


    class Meta:
        model = Element
        fields = ('id', 'name', 'attributes', 'data', 'children')


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class HtmlDataSerializer(serializers.Serializer):
    lang = serializers.CharField()
    texts = serializers.CharField(source='texts_html')


class ChildFancySerializer(serializers.Serializer):
    key = serializers.CharField(source='pk')
    title = serializers.CharField(source='name')
    folder = serializers.BooleanField(source='is_container')
    attrs = serializers.CharField(source='attributes_html')
    data = HtmlDataSerializer(many=True)
    lazy = serializers.BooleanField(source='is_lazy')
    expanded = serializers.BooleanField()
    children = RecursiveField(source='lazy_children', required=False, many=True)

class KeySerializer(serializers.Serializer):
    key = serializers.CharField(source='pk')

