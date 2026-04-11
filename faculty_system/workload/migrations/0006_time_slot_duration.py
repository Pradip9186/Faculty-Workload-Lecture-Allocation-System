from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workload', '0005_time_slot_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='timeslot',
            name='duration_hours',
            field=models.IntegerField(default=1, verbose_name='Duration (hours)', help_text='How many lecture hours this slot represents. Use 2 for a 2-hour practical.'),
            preserve_default=False,
        ),
    ]
