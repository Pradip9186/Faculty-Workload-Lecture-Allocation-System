from django.db import migrations


def create_demo_user(apps, schema_editor):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    demo_accounts = [
        ('faculty1', 'faculty123', 'Faculty', 'One'),
        ('coordinator', 'mca2025', 'Time', 'Admin'),
    ]

    for username, password, first_name, last_name in demo_accounts:
        if not User.objects.filter(username=username).exists():
            User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name)


def remove_demo_user(apps, schema_editor):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    User.objects.filter(username='faculty1').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('workload', '0003_alter_lecture_day'),
    ]

    operations = [
        migrations.RunPython(create_demo_user, remove_demo_user),
    ]
