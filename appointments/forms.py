from django import forms


class MedicalSpecialtyForm(forms.Form):
    OPTIONS = (
            ("S 1", "S 1"),
            ("S 2", "S 2"),
            ("S 3", "S 3"),
    )
    specialty = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(
        attrs={'class': 'custom-control-checkbox'}), choices=OPTIONS)
