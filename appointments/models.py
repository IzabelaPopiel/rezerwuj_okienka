from django.core.validators import MaxValueValidator, RegexValidator
from django.db import models
from django import forms


class MedicalSpecialty(models.Model):
    specialty = models.CharField(max_length=255)


class Doctor(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    medical_Specialty = models.ManyToManyField(MedicalSpecialty)


class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    pesel = models.CharField(max_length=11, validators=[RegexValidator(r'^\d{11,11}$')])
    email = models.EmailField(max_length=255)
    password = models.CharField(max_length=255)


class Address(models.Model):
    name = models.CharField(max_length=255)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    postcode = models.CharField(max_length=10)


class Visit(models.Model):
    date = models.DateTimeField()
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    location = models.ForeignKey(Address, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
