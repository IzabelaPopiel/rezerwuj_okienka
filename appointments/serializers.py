from rest_framework import serializers
from appointments.models import Patient, Visit


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ('id',
                  'first_name',
                  'last_name',
                  'pesel',
                  'email',
                  'password')

class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit

        fields = ('name',
                  'street',
                  'city',
                  'postcode',
                  'date'
                  )