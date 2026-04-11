from django.shortcuts import render, redirect
from .models import Faculty, Subject, Lecture, TimeSlot, DEFAULT_TIME_SLOTS, DAY_CHOICES
from django.db.models import Sum

# ⭐ LOGIN SYSTEM IMPORTS
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.sessions.models import Session

# ⭐ PDF GENERATION IMPORTS
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from datetime import datetime
import io
import json
import matplotlib.pyplot as plt


# ===============================
# ⭐ Session helpers
# ===============================
def expire_other_sessions(user, current_session_key=None):
    """Expire/delete other sessions belonging to `user` except the current session.

    Iterates over all `Session` objects, decodes them and removes any session whose
    `_auth_user_id` matches `user.pk` and whose key is not `current_session_key`.
    """
    try:
        all_sessions = Session.objects.all()
    except Exception:
        return

    uid_str = str(user.pk)

    for s in all_sessions:
        # skip the current session if provided
        if current_session_key and s.session_key == current_session_key:
            continue

        try:
            data = s.get_decoded()
        except Exception:
            continue

        if data.get('_auth_user_id') == uid_str:
            try:
                s.delete()
            except Exception:
                pass

# ===============================
# ⭐ FACULTY LOGIN VIEW
# ===============================
def faculty_login(request):

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        next_url = request.POST.get('next') or request.GET.get('next') or settings.LOGIN_REDIRECT_URL

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Ensure the session key exists then expire other sessions for this user
            try:
                request.session.save()
            except Exception:
                pass

            current_key = request.session.session_key
            expire_other_sessions(user, current_key)

            return redirect(next_url)
        else:
            return render(request, 'login.html', {
                'error': 'Invalid Username or Password'
            })

    # preserve `next` param if present
    next_param = request.GET.get('next', '')
    return render(request, 'login.html', {'next': next_param})


def faculty_signup(request):
    """Simple signup for faculty accounts. Creates user and logs them in."""
    User = get_user_model()

    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        pw1 = request.POST.get('password1')
        pw2 = request.POST.get('password2')

        # Basic validation
        if not username or not pw1 or not pw2:
            return render(request, 'signup.html', {'error': 'Please provide all required fields.'})

        if pw1 != pw2:
            return render(request, 'signup.html', {'error': 'Passwords do not match.'})

        if len(pw1) < 6:
            return render(request, 'signup.html', {'error': 'Password is too short.'})

        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': 'Username already exists.'})

        user = User.objects.create_user(username=username, password=pw1, first_name=first_name, last_name=last_name)
        user.save()

        # authenticate and login
        user = authenticate(request, username=username, password=pw1)
        if user is not None:
            login(request, user)

            # Ensure the session key exists then expire other sessions for this user
            try:
                request.session.save()
            except Exception:
                pass

            current_key = request.session.session_key
            expire_other_sessions(user, current_key)

            return redirect(settings.LOGIN_REDIRECT_URL)

        return render(request, 'login.html', {'error': 'Account created. Please login.'})

    return render(request, 'signup.html')


# ===============================
# ⭐ LOGOUT VIEW
# ===============================
def faculty_logout(request):
    logout(request)
    return redirect('/login/')


# ===============================
# ⭐ DASHBOARD (LOGIN REQUIRED)
# ===============================
@login_required(login_url='/login/')
def dashboard(request):

    # ===============================
    # ⭐ Selected Division (Default = A)
    # ===============================
    selected_division = request.GET.get('division', 'A')

    # ===============================
    # ⭐ Division wise lectures
    # ===============================
    lectures = Lecture.objects.filter(division=selected_division)

    # ===============================
    # ⭐ Faculty Workload Calculation
    # ===============================
    faculties = Faculty.objects.annotate(
        total_lectures=Sum('lecture__time_slot__duration_hours')
    ).order_by('-total_lectures', 'name')

    # ===============================
    # 🔥 WORKLOAD / OVERLOAD LOGIC (14 lecture hours = normal)
    # ===============================
    MAX_NORMAL_LECTURES = 14
    for f in faculties:
        total_hours = int(f.total_lectures or 0)
        # percentage based on 14 lecture-hours as 100%
        pct = int(round((total_hours / MAX_NORMAL_LECTURES) * 100)) if total_hours else 0

        f.total_lectures = total_hours
        f.load_pct = pct
        if total_hours > MAX_NORMAL_LECTURES:
            f.status = "Overloaded"
        else:
            f.status = "Normal"

    # ===============================
    # ⭐ Weekly Grid Timetable Setup (Image-style layout)
    # ===============================
    days = [day for day, _ in DAY_CHOICES]

    timeslots = list(TimeSlot.objects.order_by('sort_order'))
    if not timeslots:
        for slot_key, display_name, sort_order, duration in DEFAULT_TIME_SLOTS:
            TimeSlot.objects.get_or_create(
                slot_key=slot_key,
                defaults={'display_name': display_name, 'sort_order': sort_order, 'duration_hours': duration}
            )
        timeslots = list(TimeSlot.objects.order_by('sort_order'))

    timetable_rows = []
    for slot in timeslots:
        timetable_rows.append({
            'type': 'lecture',
            'key': slot.slot_key,
            'label': slot.display_name,
        })

        if slot.slot_key == '10-11':
            timetable_rows.append({
                'type': 'short_break',
                'key': 'short_break',
                'label': '11:00 am to 11:15 am',
            })

        if slot.slot_key == '12:15-1:15':
            timetable_rows.append({
                'type': 'lunch_break',
                'key': 'lunch_break',
                'label': '1:15 pm to 2:00 pm',
            })

    timetable = {}
    for row in timetable_rows:
        if row['type'] != 'lecture':
            continue

        timetable[row['key']] = {}
        for day in days:
            lecture = Lecture.objects.filter(
                day=day,
                time_slot__slot_key=row['key'],
                division=selected_division
            ).select_related('faculty', 'subject', 'time_slot').first()
            timetable[row['key']][day] = lecture

    # ===============================
    # ⭐ Chart.js Graph Data
    # ===============================
    faculty_names_json = json.dumps([f.name for f in faculties])
    lecture_counts_json = json.dumps([int(f.total_lectures or 0) for f in faculties])

    # ===============================
    # ⭐ Context Data
    # ===============================
    context = {
        'faculty_count': Faculty.objects.count(),
        'subjects_count': Subject.objects.count(),
        'lectures_count': Lecture.objects.count(),
        'lectures': lectures,
        'faculties': faculties,
        'days': days,
        'timetable_rows': timetable_rows,
        'timetable': timetable,
        'faculty_names_json': faculty_names_json,
        'lecture_counts_json': lecture_counts_json,
        'selected_division': selected_division
    }

    return render(request, 'dashboard.html', context)


# ===============================
# ⭐ HOME WRAPPER (ROOT '/')
#    Redirects unauthenticated users to login, otherwise serves dashboard
# ===============================
def home(request):
    if request.user.is_authenticated:
        return dashboard(request)
    # include next so after successful login user returns to '/'
    return redirect(f"{settings.LOGIN_URL}?next=/")


# ===============================
# ⭐ PDF DOWNLOAD VIEW (LOGIN REQUIRED)
#    Generates and downloads ONLY the weekly timetable grid as PDF
# ===============================
@login_required(login_url='/login/')
def download_timetable_pdf(request):
    """
    Generate and download ONLY the weekly timetable grid as PDF.
    Shows exactly what appears on the dashboard.
    """
    try:
        # Get division filter (default to 'A')
        selected_division = request.GET.get('division', 'A')

        # Create HTTP response with PDF content
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="timetable_{selected_division}_{datetime.now().strftime("%Y%m%d")}.pdf"'

        # Create PDF document (use landscape for better grid visibility)
        doc = SimpleDocTemplate(
            response,
            pagesize=landscape(letter),
            rightMargin=0.4*inch,
            leftMargin=0.4*inch,
            topMargin=0.4*inch,
            bottomMargin=0.4*inch,
        )

        # Build PDF content
        story = []
        styles = getSampleStyleSheet()

        # Simple title style
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=12,
            alignment=1,
            fontName='Helvetica-Bold',
        )

        # Add title only
        story.append(Paragraph(f"Weekly Timetable — Division {selected_division}", title_style))

        # Styles aligned with dashboard timetable content hierarchy
        header_cell_style = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontSize=10,
            leading=12,
            alignment=1,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#111827'),
        )
        time_cell_style = ParagraphStyle(
            'TimeCell',
            parent=styles['Normal'],
            fontSize=9.5,
            leading=11,
            alignment=0,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#111827'),
        )
        lecture_cell_style = ParagraphStyle(
            'LectureCell',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            alignment=1,
            fontName='Helvetica',
            textColor=colors.HexColor('#111827'),
            wordWrap='CJK',
        )
        break_cell_style = ParagraphStyle(
            'BreakCell',
            parent=styles['Normal'],
            fontSize=11,
            leading=13,
            alignment=1,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#111827'),
        )

        # Build same structure as dashboard (day columns, time rows, merged break rows)
        days = [day for day, _ in DAY_CHOICES]
        timeslots = list(TimeSlot.objects.order_by('sort_order'))
        if not timeslots:
            for slot_key, display_name, sort_order, duration in DEFAULT_TIME_SLOTS:
                TimeSlot.objects.get_or_create(
                    slot_key=slot_key,
                    defaults={'display_name': display_name, 'sort_order': sort_order, 'duration_hours': duration}
                )
            timeslots = list(TimeSlot.objects.order_by('sort_order'))

        timetable_rows = []
        for slot in timeslots:
            timetable_rows.append({
                'type': 'lecture',
                'key': slot.slot_key,
                'label': slot.display_name,
            })
            if slot.slot_key == '10-11':
                timetable_rows.append({
                    'type': 'short_break',
                    'label': 'SHORT BREAK',
                })
            if slot.slot_key == '12:15-1:15':
                timetable_rows.append({
                    'type': 'lunch_break',
                    'label': 'LUNCH BREAK',
                })

        division_lectures = Lecture.objects.filter(division=selected_division).select_related('faculty', 'subject', 'time_slot')
        lecture_map = {(lec.time_slot.slot_key, lec.day): lec for lec in division_lectures}

        grid_data = [[Paragraph('DAY / TIME', header_cell_style)] + [Paragraph(day.upper(), header_cell_style) for day in days]]
        break_row_indices = []

        for row in timetable_rows:
            if row['type'] == 'lecture':
                table_row = [Paragraph(row['label'], time_cell_style)]
                for day in days:
                    lec = lecture_map.get((row['key'], day))
                    if lec:
                        subject_name = lec.subject.subject_name if lec.subject else '-'
                        faculty_name = lec.faculty.name if lec.faculty else '-'
                        cell_text = f"<b>{subject_name}</b><br/><font size='8' color='#6b7280'>{faculty_name}</font>"
                    else:
                        cell_text = "-"
                    table_row.append(Paragraph(cell_text, lecture_cell_style))
                grid_data.append(table_row)
            else:
                row_index = len(grid_data)
                break_row_indices.append(row_index)
                grid_data.append([
                    Paragraph('11:00 am to 11:15 am' if row['type'] == 'short_break' else '1:15 pm to 2:00 pm', time_cell_style),
                    Paragraph(row['label'], break_cell_style),
                ] + [''] * (len(days) - 1))

        # Set column widths to keep all text inside cells like dashboard
        first_col_width = 1.45 * inch
        day_col_width = ((landscape(letter)[0] - (0.4 * inch * 2)) - first_col_width) / len(days)
        grid_col_widths = [first_col_width] + [day_col_width] * len(days)

        grid_table = Table(grid_data, colWidths=grid_col_widths)

        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#cfd6df')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.8, colors.HexColor('#1f2937')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]

        for row_index in break_row_indices:
            table_style.extend([
                ('SPAN', (1, row_index), (-1, row_index)),
                ('ALIGN', (1, row_index), (-1, row_index), 'CENTER'),
            ])

        grid_table.setStyle(TableStyle(table_style))
        grid_table.repeatRows = 1
        
        story.append(grid_table)

        # Build PDF
        doc.build(story)

        return response

    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)