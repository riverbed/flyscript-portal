from rest_framework import serializers
from apps.report.models import Report, Widget


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ('id', 'title', 'slug', 'criteria')
