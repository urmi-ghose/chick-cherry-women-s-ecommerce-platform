from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0015_footersettings_header_email_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SliderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], default='image', max_length=10)),
                ('image', models.ImageField(blank=True, null=True, upload_to='slider/')),
                ('video', models.FileField(blank=True, null=True, upload_to='slider/')),
                ('caption', models.CharField(blank=True, max_length=200)),
                ('duration', models.PositiveIntegerField(default=4000, help_text='Duration in ms for images (ignored for videos)')),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
    ]
