from django import forms

from blog.models import Revision, Post
from films.models import Film


class PostAddForm(forms.ModelForm):
    # Post fields
    film = forms.ModelChoiceField(queryset=Film.objects.all(), required=False)
    slug = forms.SlugField(
        required=False,
        help_text='Optional. If not provided, it will be created based on the title.',
    )

    # Revision fields
    title = forms.CharField(max_length=512)
    topic = forms.CharField(
        max_length=128,
        help_text=f'Category of the announcement in the post; '
        f'e.g. <cite>New Open Movie Announcement</cite>.',
    )
    description = forms.CharField(
        max_length=512,
        required=False,
        help_text='An optional short description displayed on the blog card.',
    )
    content = forms.TextInput()
    thumbnail = forms.ImageField()
    is_published = forms.BooleanField(required=False)

    class Meta:
        model = Revision
        fields = (
            'film',
            'slug',
            'is_published',
            'title',
            'topic',
            'description',
            'content',
            'thumbnail',
        )

    def create_post(self) -> Post:
        """
        Creates the revision's related Post instance without saving it to the database.

        The form does not contain all the required fields, so it cannot be saved yet.
        """
        post_fields = ('film', 'slug')
        post_data = {
            field: value for field, value in self.cleaned_data.items() if field in post_fields
        }
        return Post(**post_data)

    def clean(self):
        cleaned_data = super().clean()
        film = cleaned_data.get('film')


class PostChangeForm(forms.ModelForm):
    """
    Used to create a new post revision; the thumbnail field is made optional.

    It is not possible to set an initial value in a FileField, but we don't want to force
    the user to have to manually upload the thumbnail if it does not change.
    """

    thumbnail = forms.ImageField(required=False)

    class Meta:
        model = Revision
        fields = ('title', 'topic', 'description', 'content', 'thumbnail', 'header', 'is_published')
