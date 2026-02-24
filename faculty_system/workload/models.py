from django.db import models
from django.core.exceptions import ValidationError


# ===============================
#  TIME SLOT CHOICES (Best Practice)
# ===============================
TIME_CHOICES = [
    ('9-10','9-10'),
    ('10-11','10-11'),
    ('11:15-12:15','11:15-12:15'),
    ('12:15-1:15','12:15-1:15'),
    ('3-4','3-4'),
]

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
    time_slot = models.CharField(max_length=20, choices=TIME_CHOICES)

    # ===============================
    #  🔥 CLASH VALIDATION (NEW CODE)
    # ===============================
    def clean(self):
        clash = Lecture.objects.filter(
            faculty=self.faculty,
            day=self.day,
            time_slot=self.time_slot
        ).exclude(id=self.id)

        if clash.exists():
            raise ValidationError(
                "❌ Lecture Clash! Faculty already has lecture at this time."
            )

    def __str__(self):
        return f"{self.faculty} - {self.subject} ({self.division})"