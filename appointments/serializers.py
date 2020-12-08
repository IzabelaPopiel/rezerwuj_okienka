from rest_framework import serializers
from appointments.models import Patient


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ('id',
                  'first_name',
                  'last_name',
                  'pesel',
                  'email',
                  'password')