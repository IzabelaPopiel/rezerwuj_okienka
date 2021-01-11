from django.core.validators import MaxValueValidator, RegexValidator
from django.db import models


class Alert(models.Model):
    specialty = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    patient = models.CharField(max_length=255, blank=True, null=True)


class MedicalSpecialty(models.Model):
    specialty = models.CharField(max_length=255)


class Doctor(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    medical_Specialty = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    password = models.CharField(max_length=255)


class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    pesel = models.CharField(max_length=11, validators=[RegexValidator(r'^\d{11,11}$')])
    email = models.EmailField(max_length=255)
    password = models.CharField(max_length=255)
    slots = models.JSONField(default=dict, null=True, blank=True)


class Address(models.Model):
    name = models.CharField(max_length=255, blank=True)
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=6, blank=True, validators=[RegexValidator(r'^\d\d-\d\d\d$')])


class Visit(models.Model):
    date = models.DateTimeField()
    doctor = models.CharField(max_length=255, blank=True, null=True) # email doctor
    address = models.CharField(max_length=255, blank=True, null=True) # address name
    patient = models.CharField(max_length=255, blank=True, null=True) # email patient
