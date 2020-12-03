from django import forms
from django.core.exceptions import ValidationError

from appointments.models import Patient


class MedicalSpecialtyForm(forms.Form):
    OPTIONS = (
        ("S 1", "S 1"),
        ("S 2", "S 2"),
        ("S 3", "S 3"),
    )
    specialty = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(
        attrs={'class': 'custom-control-checkbox'}), choices=OPTIONS)


class PatientForm(forms.ModelForm):
    password = forms.CharField(max_length=255, min_length=8)
    password_repeat = forms.CharField(label="Repeat password", widget=forms.PasswordInput, max_length=255, min_length=8)

    class Meta:
        model = Patient
        fields = '__all__'
        widgets = {
            'password': forms.PasswordInput(),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        print(email)
        r = Patient.objects.filter(email=email)
        if r.count():
            raise ValidationError("Email already exists")
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        print(first_name)
        if not first_name.istitle():
            raise ValidationError("First name must start with capital letter")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name']
        print(last_name)
        if not last_name.istitle():
            raise ValidationError("Last name must start with capital letter")
        return last_name

    def clean_pesel(self):
        pesel = self.cleaned_data['pesel']
        print(pesel)
        r = Patient.objects.filter(pesel=pesel)
        if r.count():
            raise ValidationError("PESEL already exists")
        return pesel

    def clean_password_repeat(self):
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')
        print(password)
        print(password_repeat)
        if password != password_repeat:
            raise ValidationError("Passwords don't match")
        return password_repeat

    def save(self, commit=True):
        patient = super(PatientForm, self).save(commit=False)

        patient.first_name = self.cleaned_data['first_name']
        patient.last_name = self.cleaned_data['last_name']
        patient.pesel = self.cleaned_data['pesel']
        patient.email = self.cleaned_data['email']
        patient.password = self.cleaned_data['password']

        if commit:
            patient.save()

        return patient
