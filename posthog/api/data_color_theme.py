from rest_framework import serializers, viewsets
from rest_framework.response import Response
from django.db.models import Q

from posthog.api.routing import TeamAndOrgViewSetMixin
from posthog.models import DataColorTheme


class DataColorThemeSerializer(serializers.ModelSerializer):
    is_global = serializers.SerializerMethodField()

    class Meta:
        model = DataColorTheme
        fields = ["id", "name", "colors", "is_global"]

    def create(self, validated_data: dict, *args, **kwargs) -> DataColorTheme:
        validated_data["team_id"] = self.context["team_id"]
        return super().create(validated_data, *args, **kwargs)

    def get_is_global(self, obj):
        return obj.team_id is None


class DataColorThemeViewSet(TeamAndOrgViewSetMixin, viewsets.ModelViewSet):
    scope_object = "INTERNAL"
    queryset = DataColorTheme.objects.all()
    serializer_class = DataColorThemeSerializer

    # override the team scope queryset to also include global themes
    def dangerously_get_queryset(self):
        query_condition = Q(team_id=self.team_id) | Q(team_id=None)

        return DataColorTheme.objects.filter(query_condition)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
