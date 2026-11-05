from django import forms


class CheckoutForm(forms.Form):
    name = forms.CharField(label="আপনার নাম", max_length=100)
    phone = forms.CharField(label="ফোন নম্বর", max_length=20)
    address = forms.CharField(
        label="ডেলিভারির ঠিকানা",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
