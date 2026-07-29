from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_ratingsubmission'),
    ]

    operations = [
        migrations.CreateModel(
            name='VariationCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
            options={
                'verbose_name_plural': 'Variation Categories',
            },
        ),
        migrations.RunSQL(
            "INSERT INTO store_variationcategory (name) VALUES ('color'), ('size');",
            reverse_sql="DELETE FROM store_variationcategory WHERE name IN ('color', 'size');",
        ),
        migrations.AddField(
            model_name='variation',
            name='variation_category_fk',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='store.variationcategory',
            ),
        ),
        migrations.RunSQL(
            """
            UPDATE store_variation
            SET variation_category_fk_id = (
                SELECT id FROM store_variationcategory
                WHERE name = store_variation.variation_category
            );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RemoveField(
            model_name='variation',
            name='variation_category',
        ),
        migrations.RenameField(
            model_name='variation',
            old_name='variation_category_fk',
            new_name='variation_category',
        ),
        migrations.AlterField(
            model_name='variation',
            name='variation_category',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='store.variationcategory',
            ),
        ),
    ]
