from rest_framework import serializers
from appointments.models import Patient, Visit, Doctor, Address, Alert


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ('id',
                  'specialty',
                  'city',
                  'patient')


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ('id',
                  'first_name',
                  'last_name',
                  'pesel',
                  'email',
                  'password',
                  'slots')


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ('id',
                  'first_name',
                  'last_name',
                  'email',
                  'password',
                  'medical_Specialty')


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('id',
                  'name',
                  'street',
                  'city',
                  'postcode')


class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = ('id',
                  'doctor',
                  'address',
                  'patient',
                  'date')
