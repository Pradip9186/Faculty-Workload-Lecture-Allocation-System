from django.shortcuts import render, redirect
from .models import Faculty, Subject, Lecture
from django.db.models import Count

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
        total_lectures=Count('lecture')
    )

    # ===============================
    # 🔥 WORKLOAD / OVERLOAD LOGIC (14 lectures = normal)
    # ===============================
    MAX_NORMAL_LECTURES = 14
    for f in faculties:
        # percentage based on 14 lectures as 100%
        try:
            pct = int(round((f.total_lectures / MAX_NORMAL_LECTURES) * 100))
        except Exception:
            pct = 0

        f.load_pct = pct
        if f.total_lectures > MAX_NORMAL_LECTURES:
            f.status = "Overloaded"
        else:
            f.status = "Normal"

    # ===============================
    # ⭐ Weekly Grid Timetable Setup
    # ===============================
    days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
    slots = ['9-10','10-11','11:15-12:15','12:15-1:15','3-4']

    timetable = {}

    for day in days:
        timetable[day] = {}
        for slot in slots:
            lecture = Lecture.objects.filter(
                day=day,
                time_slot=slot,
                division=selected_division
            ).first()

            timetable[day][slot] = lecture

    # ===============================
    # ⭐ Chart.js Graph Data
    # ===============================
    faculty_names = []
    lecture_counts = []

    for f in faculties:
        faculty_names.append(f.name)
        lecture_counts.append(f.total_lectures)

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
        'slots': slots,
        'timetable': timetable,
        'faculty_names': faculty_names,
        'lecture_counts': lecture_counts,
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

        # Small paragraph style for table cells
        cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9, leading=10)

        # Build weekly grid timetable
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        slots = ['9-10', '10-11', '11:15-12:15', '12:15-1:15', '3-4']

        # Create grid data
        grid_header = [Paragraph('Time Slot', cell_style)] + [Paragraph(d, cell_style) for d in days]
        grid_data = [grid_header]

        for slot in slots:
            row = [Paragraph(slot, cell_style)]
            for day in days:
                lec = Lecture.objects.filter(
                    day=day, 
                    time_slot=slot, 
                    division=selected_division
                ).select_related('faculty', 'subject').first()
                
                if lec:
                    faculty_name = lec.faculty.name if lec.faculty else '-'
                    subject_name = lec.subject.subject_name if lec.subject else '-'
                    cell_text = f"<b>{faculty_name}</b><br/><font size=8>{subject_name}</font>"
                    cell = Paragraph(cell_text, cell_style)
                else:
                    cell = Paragraph('', cell_style)
                row.append(cell)
            grid_data.append(row)

        # Set column widths - landscape gives more space
        grid_col_widths = [1.0*inch] + [1.5*inch] * len(days)
        grid_table = Table(grid_data, colWidths=grid_col_widths)
        
        # Style the grid table: keep it simple / ERP-like (no colored headers)
        grid_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            # Header text should be blue to match dashboard PDF requirement
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            # use a subtle row background only for readability
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ffffff')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('LEFTPADDING', (1, 1), (-1, -1), 6),
            ('RIGHTPADDING', (1, 1), (-1, -1), 6),
            ('TOPPADDING', (1, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (1, 1), (-1, -1), 6),
        ]))
        grid_table.repeatRows = 1
        
        story.append(grid_table)

        # Build PDF
        doc.build(story)

        return response

    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)