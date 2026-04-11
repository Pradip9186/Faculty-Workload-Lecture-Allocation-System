from django.db import migrations, models
import django.db.models.deletion


DEFAULT_TIME_SLOTS = [
    ('9-10', '9:00 am to 10:00 am', 1),
    ('10-11', '10:00 am to 11:00 am', 2),
    ('11:15-12:15', '11:15 am to 12:15 pm', 3),
    ('12:15-1:15', '12:15 pm to 1:15 pm', 4),
    ('2-3', '2:00 pm to 3:00 pm', 5),
    ('3-4', '3:00 pm to 4:00 pm', 6),
]


def create_timeslots_and_migrate(apps, schema_editor):
    TimeSlot = apps.get_model('workload', 'TimeSlot')
    Lecture = apps.get_model('workload', 'Lecture')

    slot_map = {}
    for slot_key, display_name, sort_order in DEFAULT_TIME_SLOTS:
        slot, _ = TimeSlot.objects.get_or_create(
            slot_key=slot_key,
            defaults={'display_name': display_name, 'sort_order': sort_order}
        )
        slot_map[slot_key] = slot

    for lecture in Lecture.objects.all():
        slot = slot_map.get(lecture.time_slot)
        if slot:
            lecture.time_slot_tmp_id = slot.id
            lecture.save(update_fields=['time_slot_tmp_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('workload', '0004_create_demo_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slot_key', models.CharField(max_length=20, unique=True)),
                ('display_name', models.CharField(max_length=50)),
                ('sort_order', models.IntegerField(default=0)),
            ],
            options={
                'ordering': ['sort_order'],
            },
        ),
        migrations.AddField(
            model_name='lecture',
            name='time_slot_tmp',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='workload.timeslot'),
        ),
        migrations.RunPython(create_timeslots_and_migrate, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='lecture',
            name='time_slot',
        ),
        migrations.RenameField(
            model_name='lecture',
            old_name='time_slot_tmp',
            new_name='time_slot',
        ),
    ]
