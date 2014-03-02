from app_scheme.models import Concept
from rest_framework import serializers


class TopConceptSerializer(serializers.ModelSerializer):

    class Meta:
        model = Concept
        fields = ('definition', 'narrower')


class ConceptSerializer(serializers.ModelSerializer):

    class Meta:
        model = Concept
        fields = ('narrower',)
