# Generated manually for MonthEndStatement.pdf_file

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="monthendstatement",
            name="pdf_file",
            field=models.FileField(blank=True, upload_to="statements/"),
        ),
    ]
