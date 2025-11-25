from django import forms

class OTPForm(forms.Form):
    code = forms.CharField(
        label="Código OTP",
        max_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
