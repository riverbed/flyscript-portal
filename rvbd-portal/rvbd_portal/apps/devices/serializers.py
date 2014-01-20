from rest_framework import serializers
from rvbd_portal.apps.devices.models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device