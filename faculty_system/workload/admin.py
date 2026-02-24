from django.contrib import admin
from .models import Faculty, Subject, Lecture
from django import forms


admin.site.site_header = "Timetable Coordinator"
admin.site.site_title = "Timetable Coordinator Panel"
admin.site.index_title = "Timetable Coordinator Dashboard"

# ===============================
# Custom Admin for Lecture Form
# ===============================
class LectureAdminForm(forms.ModelForm):
    class Meta:
        model = Lecture
        fields = '__all__'
        widgets = {
            'day': forms.Select(),  # Dropdown for day selection
            'time_slot': forms.Select(),  # Dropdown for time slot
        }


class LectureAdmin(admin.ModelAdmin):
    form = LectureAdminForm
    list_display = ('faculty', 'subject', 'division', 'day', 'time_slot')
    list_filter = ('day', 'time_slot', 'division')
    search_fields = ('faculty__name', 'subject__subject_name')
    ordering = ('day', 'time_slot')


admin.site.register(Faculty)
admin.site.register(Subject)
admin.site.register(Lecture, LectureAdmin)