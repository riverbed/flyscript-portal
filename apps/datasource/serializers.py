from rest_framework import serializers
from apps.datasource.models import Table, Column, Job

class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        
class ColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Column

class JobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ('id', 'table', 'criteria', 'handle', 'status', 'message', 'progress', 'remaining')
        read_only_fields = ('id', 'status', 'message', 'progress', 'remaining')

class JobDataField(serializers.Field):
    def field_to_native(self, obj, fieldname):
        return obj.data()
    
class JobSerializer(serializers.ModelSerializer):
    data = JobDataField()
    
    class Meta:
        model = Job
        fields = ('table', 'criteria', 'handle', 'status', 'message', 'progress', 'remaining', 'data')
        read_only_fields = ('status', 'message', 'progress', 'remaining')

