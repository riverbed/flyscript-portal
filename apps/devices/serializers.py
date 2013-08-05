from rest_framework import serializers
from apps.devices.models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device