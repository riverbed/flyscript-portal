from rest_framework import serializers
from rvbd_portal.apps.report.models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ('id', 'title', 'slug')
