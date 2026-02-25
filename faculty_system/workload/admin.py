from django.contrib import admin
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
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


class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'max_hours')
    search_fields = ('name', 'department')
    change_form_template = 'admin/workload/faculty/change_form.html'

    def get_urls(self):
        urls = super().get_urls()
        opts = self.model._meta
        custom_urls = [
            path(
                '<path:object_id>/assigned-lectures/',
                self.admin_site.admin_view(self.assigned_lectures_view),
                name=f'{opts.app_label}_{opts.model_name}_assigned_lectures',
            ),
        ]
        return custom_urls + urls

    def assigned_lectures_view(self, request, object_id):
        faculty = get_object_or_404(Faculty, pk=object_id)
        lectures = Lecture.objects.filter(faculty=faculty).select_related('subject').order_by('day', 'time_slot', 'division')

        lecture_rows = []
        for lecture in lectures:
            lecture_rows.append({
                'lecture': lecture,
                'change_url': reverse('admin:workload_lecture_change', args=[lecture.pk]),
                'delete_url': reverse('admin:workload_lecture_delete', args=[lecture.pk]),
            })

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'faculty': faculty,
            'title': f'Assigned Lectures - {faculty.name}',
            'lecture_rows': lecture_rows,
            'back_url': reverse('admin:workload_faculty_change', args=[faculty.pk]),
        }
        return render(request, 'admin/workload/faculty/assigned_lectures.html', context)


admin.site.register(Faculty, FacultyAdmin)
admin.site.register(Subject)
admin.site.register(Lecture, LectureAdmin)