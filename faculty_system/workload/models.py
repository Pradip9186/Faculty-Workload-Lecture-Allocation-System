from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify


# ===============================
#  TIME SLOT DEFINITIONS
# ===============================
DEFAULT_TIME_SLOTS = [
    ('9-10', '9:00 am to 10:00 am', 1, 1),
    ('10-11', '10:00 am to 11:00 am', 2, 1),
    ('11:15-12:15', '11:15 am to 12:15 pm', 3, 1),
    ('12:15-1:15', '12:15 pm to 1:15 pm', 4, 1),
    ('2-3', '2:00 pm to 3:00 pm', 5, 1),
    ('2-4', '2:00 pm to 4:00 pm', 6, 2),
    ('3-4', '3:00 pm to 4:00 pm', 7, 1),
]

TIME_CHOICES = [(slot_key, slot_key) for slot_key, _, _, _ in DEFAULT_TIME_SLOTS]
TIME_SLOT_OPTIONS = [(display_name, display_name) for _, display_name, _, _ in DEFAULT_TIME_SLOTS]

# ===============================
#  DAY CHOICES (Monday-Saturday)
# ===============================
DAY_CHOICES = [
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
]

# ===============================
#  DIVISION CHOICES
# ===============================
DIVISION_CHOICES = [
    ('A', 'Division A'),
    ('B', 'Division B'),
    ('C', 'Division C'),
    ('D', 'Division D'),
]


# ===============================
#  Time Slot Model
# ===============================
class TimeSlot(models.Model):
    slot_key = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name='Internal code',
        help_text='Optional system code; leave blank to auto-generate from the time range.',
    )
    display_name = models.CharField(
        max_length=50,
        verbose_name='Time range',
        help_text='Choose the displayed time range, for example: 2:00 pm to 4:00 pm.',
    )
    duration_hours = models.IntegerField(
        default=1,
        verbose_name='Duration (hours)',
        help_text='How many lecture hours this slot represents. Use 2 for a 2-hour practical.',
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name='Display order',
        help_text='Lower numbers appear earlier in the timetable.',
    )

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.slot_key and self.display_name:
            base_slug = slugify(self.display_name)
            candidate = base_slug
            counter = 1
            while TimeSlot.objects.filter(slot_key=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slot_key = candidate
        super().save(*args, **kwargs)


# ===============================
#  Faculty Table
# ===============================
class Faculty(models.Model):
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    max_hours = models.IntegerField()

    def __str__(self):
        return self.name


# ===============================
#  Subject Table
# ===============================
class Subject(models.Model):
    subject_name = models.CharField(max_length=100)
    semester = models.IntegerField()
    credit_hours = models.IntegerField()

    def __str__(self):
        return self.subject_name


# ===============================
#  Lecture Allocation Table
# ===============================
class Lecture(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    division = models.CharField(max_length=2, choices=DIVISION_CHOICES, default='A')

    day = models.CharField(max_length=20, choices=DAY_CHOICES)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT)

    # ===============================
    #  🔥 CLASH VALIDATION (NEW CODE)
    # ===============================
    def clean(self):
        errors = {}
        if not self.faculty_id:
            errors['faculty'] = 'Faculty is required.'
        if not self.subject_id:
            errors['subject'] = 'Subject is required.'
        if not self.division:
            errors['division'] = 'Division is required.'
        if not self.day:
            errors['day'] = 'Day is required.'
        if not self.time_slot_id:
            errors['time_slot'] = 'Time slot is required.'

        if errors:
            raise ValidationError(errors)

        clash = Lecture.objects.filter(
            faculty=self.faculty,
            day=self.day,
            time_slot=self.time_slot
        ).exclude(id=self.id)

        if clash.exists():
            raise ValidationError(
                {'__all__': "❌ Lecture Clash! Faculty already has lecture at this time."}
            )

    def __str__(self):
        return f"{self.faculty} - {self.subject} ({self.division})"