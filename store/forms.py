from django import forms
from .models import ReviewRating

class ReviewForm(forms.ModelForm):
    subject = forms.CharField(required=False, max_length=100)
    review = forms.CharField(required=False, max_length=500, widget=forms.Textarea)

    class Meta:
        model = ReviewRating
        fields = ['subject', 'review', 'rating', 'image']

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if not rating or rating < 1:
            raise forms.ValidationError('Please select a star rating.')
        return rating
