from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    make_response
)

import os
from werkzeug.utils import secure_filename

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from models import (
    db,
    User,
    Patient,
    Doctor,
    Appointment,
    Token,
    Bill,
    Prescription,
    LabReport
)

from functools import wraps
from datetime import datetime
import io
from reportlab.pdfgen import canvas


# ==========================================================
# Flask Configuration
# ==========================================================

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["SECRET_KEY"] = "hospital123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hospital.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ==========================================================
# Flask Login
# ==========================================================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

login_manager.login_message = "Please login first."


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==========================================================
# Role Required Decorator
# ==========================================================

def role_required(*roles):

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):

            if not current_user.is_authenticated:

                flash("Please login first.", "danger")

                return redirect(url_for("login"))

            if current_user.role not in roles:

                flash("Access Denied!", "danger")

                return redirect(url_for("login"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator
# ==========================================================
# Home
# ==========================================================

@app.route("/")
def home():
    return render_template("home.html")


# ==========================================================
# Login
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # Already Logged In
    if current_user.is_authenticated:

        if current_user.role == "Admin":
            return redirect(url_for("dashboard"))

        elif current_user.role == "Doctor":
            return redirect(url_for("doctor_dashboard"))

        elif current_user.role == "Reception":
            return redirect(url_for("reception_dashboard"))

        elif current_user.role == "Patient":
            return redirect(url_for("patient_dashboard"))

    # Login Process
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            flash(
                f"Welcome {user.fullname}",
                "success"
            )

            if user.role == "Admin":
                return redirect(url_for("dashboard"))

            elif user.role == "Doctor":
                return redirect(url_for("doctor_dashboard"))

            elif user.role == "Reception":
                return redirect(url_for("reception_dashboard"))

            elif user.role == "Patient":
                return redirect(url_for("patient_dashboard"))

        flash(
            "Invalid Username or Password",
            "danger"
        )

    return render_template("login.html")


# ==========================================================
# Logout
# ==========================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "Logged Out Successfully!",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ==========================================================
# Dashboard (Role Based)
# ==========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    # ---------------- Admin ----------------

    if current_user.role == "Admin":

        total_patients = Patient.query.count()

        total_doctors = Doctor.query.count()

        total_appointments = Appointment.query.count()

        total_bills = Bill.query.count()

        total_revenue = db.session.query(
            db.func.sum(Bill.total)
        ).scalar() or 0

        waiting_tokens = Token.query.filter_by(
            status="Waiting"
        ).count()

        completed_tokens = Token.query.filter_by(
            status="Completed"
        ).count()

        return render_template(
            "dashboard.html",
            total_patients=total_patients,
            total_doctors=total_doctors,
            total_appointments=total_appointments,
            total_bills=total_bills,
            total_revenue=total_revenue,
            waiting_tokens=waiting_tokens,
            completed_tokens=completed_tokens
        )

    # ---------------- Doctor ----------------

    elif current_user.role == "Doctor":

        return redirect(url_for("doctor_dashboard"))

    # ---------------- Reception ----------------

    elif current_user.role == "Reception":

        return redirect(url_for("reception_dashboard"))

    # ---------------- Patient ----------------

    elif current_user.role == "Patient":

        return redirect(url_for("patient_dashboard"))

    flash("Access Denied!", "danger")

    return redirect(url_for("logout"))
# ==========================================================
# Doctor Dashboard
# ==========================================================

@app.route("/doctor_dashboard")
@login_required
@role_required("Doctor")
def doctor_dashboard():

    doctor = Doctor.query.filter_by(
        user_id=current_user.id
    ).first()

    if not doctor:
        flash("Doctor record not found.", "danger")
        return redirect(url_for("logout"))

    appointments = Appointment.query.filter_by(
        doctor_id=doctor.id
    ).all()

    waiting_tokens = Token.query.filter_by(
        doctor_id=doctor.id,
        status="Waiting"
    ).all()

    completed_tokens = Token.query.filter_by(
        doctor_id=doctor.id,
        status="Completed"
    ).count()

    return render_template(
        "doctor_dashboard.html",
        doctor=doctor,
        appointments=appointments,
        waiting_tokens=waiting_tokens,
        completed_tokens=completed_tokens,
        patients=Patient.query.count()
    )


# ==========================================================
# Reception Dashboard
# ==========================================================

@app.route("/reception_dashboard")
@login_required
@role_required("Reception")
def reception_dashboard():

    waiting = Token.query.filter_by(
        status="Waiting"
    ).count()

    return render_template(
        "reception_dashboard.html",
        patients=Patient.query.count(),
        doctors=Doctor.query.count(),
        appointments=Appointment.query.count(),
        waiting_tokens=waiting
    )


# ==========================================================
# Patient Dashboard
# ==========================================================

@app.route("/patient_dashboard")
@login_required
@role_required("Patient")
def patient_dashboard():

    patient = Patient.query.filter_by(
        user_id=current_user.id
    ).first()

    if not patient:
        flash("Patient record not found.", "danger")
        return redirect(url_for("logout"))

    appointments = Appointment.query.filter_by(
        patient_id=patient.id
    ).all()

    bills = Bill.query.filter_by(
        patient_id=patient.id
    ).all()

    prescriptions = Prescription.query.filter_by(
        patient_id=patient.id
    ).all()

    reports = LabReport.query.filter_by(
        patient_id=patient.id
    ).all()

    tokens = Token.query.filter_by(
        patient_id=patient.id
    ).all()

    return render_template(
        "patient_dashboard.html",
        patient=patient,
        appointments=appointments,
        bills=bills,
        prescriptions=prescriptions,
        reports=reports,
        tokens=tokens
    )
# ==========================================================
# User Management
# ==========================================================

@app.route("/users", methods=["GET", "POST"])
@login_required
@role_required("Admin")
def users():

    if request.method == "POST":

        fullname = request.form["fullname"].strip()
        username = request.form["username"].strip()
        password = request.form["password"]
        role = request.form["role"]

        # Check Username

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash(
                "Username already exists!",
                "danger"
            )

            return redirect(
                url_for("users")
            )

        # Create User

        new_user = User(

            fullname=fullname,
            username=username,
            password=generate_password_hash(password),
            role=role

        )

        db.session.add(new_user)
        db.session.commit()

        flash(
            "User Added Successfully!",
            "success"
        )

        return redirect(
            url_for("users")
        )

    all_users = User.query.order_by(
        User.id.desc()
    ).all()

    return render_template(
        "users.html",
        users=all_users
    )


# ==========================================================
# Edit User
# ==========================================================

@app.route("/edit_user/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("Admin")
def edit_user(id):

    user = User.query.get_or_404(id)

    if request.method == "POST":

        user.fullname = request.form["fullname"].strip()
        user.username = request.form["username"].strip()
        user.role = request.form["role"]

        password = request.form.get("password")

        if password:

            user.password = generate_password_hash(password)

        db.session.commit()

        flash(
            "User Updated Successfully!",
            "success"
        )

        return redirect(
            url_for("users")
        )

    return render_template(
        "edit_user.html",
        user=user
    )


# ==========================================================
# Delete User
# ==========================================================

@app.route("/delete_user/<int:id>")
@login_required
@role_required("Admin")
def delete_user(id):

    user = User.query.get_or_404(id)

    # Prevent Admin deleting himself

    if user.id == current_user.id:

        flash(
            "You cannot delete your own account.",
            "warning"
        )

        return redirect(
            url_for("users")
        )

    db.session.delete(user)
    db.session.commit()

    flash(
        "User Deleted Successfully!",
        "success"
    )

    return redirect(
        url_for("users")
    )
# ==========================================================
# Patient Management
# ==========================================================
@app.route("/patients", methods=["GET", "POST"])
@login_required
def patients():

    if request.method == "POST":

        username = request.form["username"].strip()

        # Check username already exists
        existing = User.query.filter_by(username=username).first()

        if existing:
            flash("Username already exists!", "danger")
            return redirect(url_for("patients"))

        # Create login account
        user = User(
            fullname=request.form["name"].strip(),
            username=username,
            password=generate_password_hash(request.form["password"]),
            role="Patient"
        )

        db.session.add(user)
        db.session.flush()      # Gets user.id before commit

        # Create patient
        patient = Patient(
            name=request.form["name"].strip(),
            age=int(request.form["age"]),
            gender=request.form["gender"],
            phone=request.form["phone"].strip(),
            username=username,
            user_id=user.id,
            address=request.form.get("address", ""),
            blood_group=request.form.get("blood_group", "")
        )

        db.session.add(patient)
        db.session.commit()

        flash(
            "Patient Added Successfully!",
            "success"
        )

        return redirect(url_for("patients"))

    search = request.args.get("search")

    if search:

        all_patients = Patient.query.filter(
            Patient.name.ilike(f"%{search}%")
        ).order_by(
            Patient.id.desc()
        ).all()

    else:

        all_patients = Patient.query.order_by(
            Patient.id.desc()
        ).all()

    return render_template(
        "patients.html",
        patients=all_patients
    )


# ==========================================================
# Edit Patient
# ==========================================================

@app.route("/edit_patient/<int:id>", methods=["GET", "POST"])
@login_required
def edit_patient(id):

    patient = Patient.query.get_or_404(id)

    if request.method == "POST":

        patient.name = request.form["name"]
        patient.age = int(request.form["age"])
        patient.gender = request.form["gender"]
        patient.phone = request.form["phone"]
        patient.address = request.form.get("address", "")
        patient.blood_group = request.form.get("blood_group", "")

        db.session.commit()

        flash(
            "Patient Updated Successfully!",
            "success"
        )

        return redirect(url_for("patients"))

    return render_template(
        "edit_patient.html",
        patient=patient
    )


# ==========================================================
# Delete Patient
# ==========================================================

@app.route("/delete_patient/<int:id>")
@login_required
def delete_patient(id):

    patient = Patient.query.get_or_404(id)

    appointment_exists = Appointment.query.filter_by(
        patient_id=patient.id
    ).first()

    if appointment_exists:

        flash(
            "Cannot delete patient. Appointments exist.",
            "danger"
        )

        return redirect(url_for("patients"))

    db.session.delete(patient)
    db.session.commit()

    flash(
        "Patient Deleted Successfully!",
        "success"
    )

    return redirect(url_for("patients"))


# ==========================================================
# Patient Details
# ==========================================================

@app.route("/patient/<int:id>")
@login_required
def patient_details(id):

    patient = Patient.query.get_or_404(id)

    appointments = Appointment.query.filter_by(
        patient_id=id
    ).all()

    bills = Bill.query.filter_by(
        patient_id=id
    ).all()

    prescriptions = Prescription.query.filter_by(
        patient_id=id
    ).all()

    reports = LabReport.query.filter_by(
        patient_id=id
    ).all()

    tokens = Token.query.filter_by(
        patient_id=id
    ).order_by(
        Token.id.desc()
    ).all()

    return render_template(
        "patient_dashboard.html",
        patient=patient,
        appointments=appointments,
        bills=bills,
        prescriptions=prescriptions,
        reports=reports,
        tokens=tokens
    )
# ==========================================================
# Doctor Management
# ==========================================================

@app.route("/doctors", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Reception")
def doctors():

    if request.method == "POST":

        username = request.form["username"].strip()

        # Check if username already exists
        existing = User.query.filter_by(username=username).first()

        if existing:
            flash("Username already exists!", "danger")
            return redirect(url_for("doctors"))

        # Create User Login
        user = User(
            fullname=request.form["name"].strip(),
            username=username,
            password=generate_password_hash(request.form["password"]),
            role="Doctor"
        )

        db.session.add(user)
        db.session.flush()      # Gets user.id before commit

        # Create Doctor
        doctor = Doctor(
            name=request.form["name"].strip(),
            specialization=request.form["specialization"].strip(),
            phone=request.form["phone"].strip(),
            username=username,
            user_id=user.id,
            email=request.form.get("email", "").strip(),
            status=request.form.get("status", "Available")
        )

        db.session.add(doctor)
        db.session.commit()

        flash("Doctor Added Successfully!", "success")

        return redirect(url_for("doctors"))

    search = request.args.get("search")

    if search:

        all_doctors = Doctor.query.filter(
            (Doctor.name.ilike(f"%{search}%")) |
            (Doctor.specialization.ilike(f"%{search}%"))
        ).order_by(
            Doctor.id.desc()
        ).all()

    else:

        all_doctors = Doctor.query.order_by(
            Doctor.id.desc()
        ).all()

    return render_template(
        "doctors.html",
        doctors=all_doctors
    )


# ==========================================================
# Edit Doctor
# ==========================================================

@app.route("/edit_doctor/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Reception")
def edit_doctor(id):

    doctor = Doctor.query.get_or_404(id)

    if request.method == "POST":

        doctor.name = request.form["name"].strip()
        doctor.specialization = request.form["specialization"].strip()
        doctor.phone = request.form["phone"].strip()
        doctor.email = request.form.get("email", "").strip()
        doctor.status = request.form.get("status", "Available")

        db.session.commit()

        flash(
            "Doctor Updated Successfully!",
            "success"
        )

        return redirect(url_for("doctors"))

    return render_template(
        "edit_doctor.html",
        doctor=doctor
    )


# ==========================================================
# Delete Doctor
# ==========================================================

@app.route("/delete_doctor/<int:id>")
@login_required
@role_required("Admin")
def delete_doctor(id):

    doctor = Doctor.query.get_or_404(id)

    appointment_exists = Appointment.query.filter_by(
        doctor_id=doctor.id
    ).first()

    if appointment_exists:

        flash(
            "Cannot delete doctor. Appointments exist.",
            "danger"
        )

        return redirect(url_for("doctors"))

    db.session.delete(doctor)
    db.session.commit()

    flash(
        "Doctor Deleted Successfully!",
        "success"
    )

    return redirect(url_for("doctors"))


# ==========================================================
# Doctor Details
# ==========================================================

@app.route("/doctor/<int:id>")
@login_required
def doctor_details(id):

    doctor = Doctor.query.get_or_404(id)

    appointments = Appointment.query.filter_by(
        doctor_id=id
    ).all()

    waiting_tokens = Token.query.filter_by(
        doctor_id=id,
        status="Waiting"
    ).all()

    completed_tokens = Token.query.filter_by(
        doctor_id=id,
        status="Completed"
    ).count()

    return render_template(
        "doctor_dashboard.html",
        doctor=doctor,
        appointments=appointments,
        waiting_tokens=waiting_tokens,
        completed_tokens=completed_tokens
    )
# ==========================================================
# Appointment Management
# ==========================================================

@app.route("/appointments", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Reception")
def appointments():

    if request.method == "POST":

        try:

            patient_id = int(request.form.get("patient", 0))
            doctor_id = int(request.form.get("doctor", 0))

        except (TypeError, ValueError):

            flash("Please select a valid patient and doctor.", "danger")
            return redirect(url_for("appointments"))

        appointment_date = request.form.get("date", "").strip()
        appointment_time = request.form.get("time", "").strip()

        # Validate all fields

        if not patient_id or not doctor_id:
            flash("Please select a patient and doctor.", "danger")
            return redirect(url_for("appointments"))

        if not appointment_date or not appointment_time:
            flash("Please select appointment date and time.", "danger")
            return redirect(url_for("appointments"))

        patient = db.session.get(Patient, patient_id)
        doctor = db.session.get(Doctor, doctor_id)

        if not patient:
            flash("Selected patient was not found.", "danger")
            return redirect(url_for("appointments"))

        if not doctor:
            flash("Selected doctor was not found.", "danger")
            return redirect(url_for("appointments"))

        # Prevent past dates

        try:

            selected_date = datetime.strptime(
                appointment_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash("Invalid appointment date.", "danger")
            return redirect(url_for("appointments"))

        today = datetime.now().date()

        if selected_date < today:

            flash(
                "Appointment date cannot be in the past.",
                "warning"
            )

            return redirect(url_for("appointments"))

        # Prevent duplicate booking

        existing_appointment = Appointment.query.filter_by(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        ).filter(
            Appointment.status != "Cancelled"
        ).first()

        if existing_appointment:

            flash(
                "This appointment is already booked.",
                "warning"
            )

            return redirect(url_for("appointments"))

        # Save appointment

        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status="Pending"
        )

        db.session.add(appointment)

        # Generate smart token

        today_string = today.strftime("%Y-%m-%d")

        today_tokens = Token.query.filter(
            db.func.date(Token.created_at) == today_string
        ).count()

        queue_position = today_tokens + 1

        # Date is included because token_number is unique
        token_date = today.strftime("%Y%m%d")

        token_number = (
            f"T{token_date}-{queue_position:03d}"
        )

        token = Token(
            token_number=token_number,
            patient_id=patient_id,
            doctor_id=doctor_id,
            department=doctor.specialization or "General",
            priority="Normal",
            status="Waiting",
            queue_position=queue_position,
            estimated_wait=today_tokens * 10
        )

        db.session.add(token)

        try:

            db.session.commit()

        except Exception:

            db.session.rollback()

            flash(
                "Unable to book the appointment. Please try again.",
                "danger"
            )

            return redirect(url_for("appointments"))

        flash(
            f"Appointment booked successfully! "
            f"Token number: {token_number}",
            "success"
        )

        return redirect(url_for("appointments"))

    patients = Patient.query.order_by(
        Patient.name.asc()
    ).all()

    doctors = Doctor.query.order_by(
        Doctor.name.asc()
    ).all()

    appointments = Appointment.query.order_by(
        Appointment.id.desc()
    ).all()

    return render_template(
        "appointments.html",
        patients=patients,
        doctors=doctors,
        appointments=appointments
    )


# ==========================================================
# Update Appointment Status
# ==========================================================

@app.route(
    "/appointment/<int:appointment_id>/status/<string:action>",
    methods=["POST"]
)
@login_required
@role_required("Admin", "Reception")
def update_appointment_status(appointment_id, action):

    appointment = db.session.get(
        Appointment,
        appointment_id
    )

    if not appointment:

        flash("Appointment was not found.", "danger")
        return redirect(url_for("appointments"))

    action_status_map = {
        "approve": "Approved",
        "start": "In Consultation",
        "complete": "Completed",
        "cancel": "Cancelled"
    }

    if action not in action_status_map:

        flash("Invalid appointment action.", "danger")
        return redirect(url_for("appointments"))

    current_status = appointment.status or "Pending"
    new_status = action_status_map[action]

    allowed_transitions = {
        "Pending": [
            "Approved",
            "Cancelled"
        ],
        "Approved": [
            "In Consultation",
            "Cancelled"
        ],
        "In Consultation": [
            "Completed",
            "Cancelled"
        ],
        "Completed": [],
        "Cancelled": []
    }

    allowed_next_statuses = allowed_transitions.get(
        current_status,
        []
    )

    if new_status not in allowed_next_statuses:

        flash(
            f"Cannot change appointment from "
            f"{current_status} to {new_status}.",
            "warning"
        )

        return redirect(url_for("appointments"))

    appointment.status = new_status

    # Find the related active token

    token = Token.query.filter(
        Token.patient_id == appointment.patient_id,
        Token.doctor_id == appointment.doctor_id,
        Token.status.notin_(
            ["Completed", "Cancelled"]
        )
    ).order_by(
        Token.id.desc()
    ).first()

    # Keep token status synchronized

    if token:

        if new_status == "Approved":
            token.status = "Waiting"

        elif new_status == "In Consultation":
            token.status = "In Consultation"

        elif new_status == "Completed":
            token.status = "Completed"

        elif new_status == "Cancelled":
            token.status = "Cancelled"

    try:

        db.session.commit()

        flash(
            f"Appointment status changed to {new_status}.",
            "success"
        )

    except Exception:

        db.session.rollback()

        flash(
            "Unable to update appointment status.",
            "danger"
        )

    return redirect(url_for("appointments"))


# ==========================================================
# Delete Appointment
# ==========================================================

@app.route(
    "/delete_appointment/<int:id>",
    methods=["POST"]
)
@login_required
@role_required("Admin", "Reception")
def delete_appointment(id):

    appointment = db.session.get(
        Appointment,
        id
    )

    if not appointment:

        flash("Appointment was not found.", "danger")
        return redirect(url_for("appointments"))

    # Find the latest related active token

    token = Token.query.filter(
        Token.patient_id == appointment.patient_id,
        Token.doctor_id == appointment.doctor_id,
        Token.status.notin_(
            ["Completed", "Cancelled"]
        )
    ).order_by(
        Token.id.desc()
    ).first()

    if token:
        db.session.delete(token)

    db.session.delete(appointment)

    try:

        db.session.commit()

        flash(
            "Appointment deleted successfully.",
            "success"
        )

    except Exception:

        db.session.rollback()

        flash(
            "Unable to delete appointment.",
            "danger"
        )

    return redirect(url_for("appointments"))
# ==========================================================
# Token Management
# ==========================================================

@app.route("/tokens", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Doctor", "Reception")
def tokens():

    if request.method == "POST":

        patient_id = int(request.form["patient_id"])
        doctor_id = int(request.form["doctor_id"])
        priority = request.form["priority"]

        token_count = Token.query.count() + 1

        token = Token(
            token_number=f"T{token_count:03d}",
            patient_id=patient_id,
            doctor_id=doctor_id,
            department="General",
            priority=priority,
            status="Waiting",
            queue_position=token_count,
            estimated_wait=(token_count - 1) * 10
        )

        db.session.add(token)
        db.session.commit()

        flash("Token Generated Successfully!", "success")

        return redirect(url_for("tokens"))

    patients = Patient.query.order_by(Patient.name).all()
    doctors = Doctor.query.order_by(Doctor.name).all()
    all_tokens = Token.query.order_by(Token.queue_position.asc()).all()

    return render_template(
        "tokens.html",
        patients=patients,
        doctors=doctors,
        tokens=all_tokens
    )


# ==========================================================
# Call Token
# ==========================================================

@app.route("/call_token/<int:id>")
@login_required
@role_required("Admin", "Doctor", "Reception")
def call_token(id):

    token = Token.query.get_or_404(id)

    token.status = "Called"

    db.session.commit()

    flash("Token Called Successfully!", "success")

    return redirect(url_for("tokens"))


# ==========================================================
# Complete Token
# ==========================================================

@app.route("/complete_token/<int:id>")
@login_required
@role_required("Admin", "Doctor")
def complete_token(id):

    token = Token.query.get_or_404(id)

    token.status = "Completed"

    db.session.commit()

    flash("Consultation Completed Successfully!", "success")

    return redirect(url_for("tokens"))


# ==========================================================
# Update Token Status
# ==========================================================

@app.route("/update_token/<int:id>/<status>")
@login_required
@role_required("Admin", "Doctor", "Reception")
def update_token(id, status):

    token = Token.query.get_or_404(id)

    token.status = status

    db.session.commit()

    flash("Token Status Updated Successfully!", "success")

    return redirect(url_for("tokens"))


# ==========================================================
# Delete Token
# ==========================================================

@app.route("/delete_token/<int:id>")
@login_required
@role_required("Admin")
def delete_token(id):

    token = Token.query.get_or_404(id)

    db.session.delete(token)

    db.session.commit()

    flash("Token Deleted Successfully!", "success")

    return redirect(url_for("tokens"))

# ==========================================================
# Prescription Management
# ==========================================================

@app.route("/prescriptions", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Doctor")
def prescriptions():

    if request.method == "POST":

        prescription = Prescription(
            patient_id=int(request.form["patient_id"]),
            doctor_id=int(request.form["doctor_id"]),
            diagnosis=request.form["diagnosis"],
            medicines=request.form["medicines"],
            dosage=request.form["dosage"],
            advice=request.form["advice"]
        )

        db.session.add(prescription)
        db.session.commit()

        flash("Prescription Added Successfully!", "success")

        return redirect(url_for("prescriptions"))

    patients = Patient.query.order_by(Patient.name).all()
    doctors = Doctor.query.order_by(Doctor.name).all()

    prescriptions = Prescription.query.order_by(
        Prescription.id.desc()
    ).all()

    return render_template(
        "prescriptions.html",
        patients=patients,
        doctors=doctors,
        prescriptions=prescriptions
    )
# ==========================================================
# Lab Reports
# ==========================================================

@app.route("/lab_reports", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Doctor")
def lab_reports():

    if request.method == "POST":

        patient_id = int(request.form["patient_id"])
        doctor_id = int(request.form["doctor_id"])

        report_name = request.form["report_name"]

        file = request.files["report_file"]

        filename = ""

        if file:

            filename = secure_filename(file.filename)

            file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

        report = LabReport(
            patient_id=patient_id,
            doctor_id=doctor_id,
            report_name=report_name,
            report_file=filename
        )

        db.session.add(report)

        db.session.commit()

        flash("Lab Report Uploaded Successfully!", "success")

        return redirect(url_for("lab_reports"))

    patients = Patient.query.order_by(Patient.name).all()

    doctors = Doctor.query.order_by(Doctor.name).all()

    reports = LabReport.query.order_by(
        LabReport.id.desc()
    ).all()

    return render_template(
        "lab_reports.html",
        patients=patients,
        doctors=doctors,
        reports=reports
    )
# ==========================================================
# My Lab Reports
# ==========================================================

@app.route("/my_lab_reports")
@login_required
@role_required("Patient")
def my_lab_reports():

    patient = Patient.query.filter_by(
        user_id=current_user.id
    ).first()

    if not patient:

        flash("Patient record not found.", "danger")

        return redirect(url_for("patient_dashboard"))

    reports = LabReport.query.filter_by(
        patient_id=patient.id
    ).order_by(
        LabReport.id.desc()
    ).all()

    return render_template(
        "my_lab_reports.html",
        reports=reports
    )

@app.route("/patient_profile", methods=["GET", "POST"])
@login_required
@role_required("Patient")
def patient_profile():

    patient = Patient.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":

        patient.name = request.form["name"]
        patient.age = request.form["age"]
        patient.gender = request.form["gender"]
        patient.phone = request.form["phone"]
        patient.address = request.form["address"]
        patient.blood_group = request.form["blood_group"]

        current_user.fullname = request.form["name"]

        db.session.commit()

        flash("Profile Updated Successfully!", "success")

        return redirect(url_for("patient_profile"))

    return render_template(
        "patient_profile.html",
        patient=patient
    )
# ==========================================================
# My Appointments (Patient)
# ==========================================================

@app.route("/my_appointments")
@login_required
@role_required("Patient")
def my_appointments():

    patient = Patient.query.filter_by(
        user_id=current_user.id
    ).first()

    if not patient:
        flash("Patient record not found.", "danger")
        return redirect(url_for("patient_dashboard"))

    appointments = Appointment.query.filter_by(
        patient_id=patient.id
    ).order_by(
        Appointment.id.desc()
    ).all()

    return render_template(
        "my_appointments.html",
        appointments=appointments
    )


# ==========================================================
# My Bills (Patient)
# ==========================================================

@app.route("/my_bills")
@login_required
@role_required("Patient")
def my_bills():

    patient = Patient.query.filter_by(
        user_id=current_user.id
    ).first()

    if not patient:
        flash("Patient record not found.", "danger")
        return redirect(url_for("patient_dashboard"))

    bills = Bill.query.filter_by(
        patient_id=patient.id
    ).order_by(
        Bill.id.desc()
    ).all()

    return render_template(
        "my_bills.html",
        bills=bills
    )
#----------------------------------------------
#change passsword
# ---------------------------------------------
@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():

    if request.method == "POST":

        old = request.form["old_password"]
        new = request.form["new_password"]
        confirm = request.form["confirm_password"]

        if not check_password_hash(current_user.password, old):
            flash("Old password is incorrect.", "danger")
            return redirect(url_for("change_password"))

        if new != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("change_password"))

        current_user.password = generate_password_hash(new)

        db.session.commit()

        flash("Password Changed Successfully!", "success")

        return redirect(url_for("patient_dashboard"))

    return render_template("change_password.html")

# ==========================================================
# AI Hospital Chatbot
# ==========================================================

@app.route("/chatbot", methods=["GET", "POST"])
@login_required
def chatbot():

    reply = ""

    if request.method == "POST":

        message = request.form["message"].lower()

        if "fever" in message:
            reply = "Fever may be caused by an infection. Drink plenty of water, take rest, and consult a doctor if the fever is high or lasts more than two days."

        elif "cough" in message:
            reply = "A cough can occur due to a cold, allergy, or infection. Stay hydrated and consult a doctor if it persists."

        elif "headache" in message:
            reply = "Headaches can result from stress, dehydration, or illness. Drink water, rest well, and seek medical advice if severe."

        elif "cold" in message:
            reply = "Common cold usually improves with rest, fluids, and proper nutrition."

        elif "stomach" in message:
            reply = "Stomach pain can have many causes. Avoid spicy food and consult a doctor if the pain is severe."

        elif "diabetes" in message:
            reply = "Maintain a healthy diet, exercise regularly, and monitor your blood sugar as advised by your doctor."

        elif "blood pressure" in message or "bp" in message:
            reply = "Monitor your blood pressure regularly, reduce salt intake, and follow your doctor's advice."

        elif "appointment" in message:
            reply = "You can book an appointment using the Appointment section in this Hospital Management System."

        elif "token" in message:
            reply = "You can view your token status from the Smart Token Management section."

        elif "lab" in message:
            reply = "Your lab reports are available under My Lab Reports."

        elif "prescription" in message:
            reply = "Your prescriptions are available in the My Prescriptions section."

        elif "bill" in message:
            reply = "You can check your bills under the My Bills section."

        elif "hello" in message or "hi" in message:
            reply = f"Hello {current_user.fullname}! How can I help you today?"

        else:
            reply = "Sorry, I couldn't understand your question. Please ask about appointments, fever, cough, prescriptions, bills, lab reports, tokens, or other hospital-related topics."

    return render_template(
        "chatbot.html",
        reply=reply
    )
# ==========================================================
# My Prescriptions (Patient)
# ==========================================================

@app.route("/my_prescriptions")
@login_required
@role_required("Patient")
def my_prescriptions():

    patient = Patient.query.filter_by(
        user_id=current_user.id
    ).first()

    if not patient:

        flash("Patient record not found.", "danger")
        return redirect(url_for("patient_dashboard"))

    prescriptions = Prescription.query.filter_by(
        patient_id=patient.id
    ).order_by(
        Prescription.id.desc()
    ).all()

    return render_template(
        "my_prescriptions.html",
        patient=patient,
        prescriptions=prescriptions
    )
# ==========================================================
# Billing Management
# ==========================================================

@app.route("/billing", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Reception")
def billing():

    if request.method == "POST":

        patient_id = int(request.form["patient"])

        consultation_fee = float(
            request.form["consultation"]
        )

        medicine_fee = float(
            request.form["medicine"]
        )

        lab_fee = float(
            request.form.get("lab", 0)
        )

        total = (
            consultation_fee +
            medicine_fee +
            lab_fee
        )

        bill = Bill(
            patient_id=patient_id,
            consultation_fee=consultation_fee,
            medicine_fee=medicine_fee,
            lab_fee=lab_fee,
            total=total,
            payment_status="Pending"
        )

        db.session.add(bill)
        db.session.commit()

        flash(
            "Bill Generated Successfully!",
            "success"
        )

        return redirect(url_for("billing"))

    bills = Bill.query.order_by(
        Bill.id.desc()
    ).all()

    patients = Patient.query.order_by(
        Patient.name
    ).all()

    return render_template(
        "billing.html",
        bills=bills,
        patients=patients
    )


# ==========================================================
# Delete Bill
# ==========================================================

@app.route("/delete_bill/<int:id>")
@login_required
@role_required("Admin", "Reception")
def delete_bill(id):

    bill = Bill.query.get_or_404(id)

    db.session.delete(bill)
    db.session.commit()

    flash(
        "Bill Deleted Successfully!",
        "success"
    )

    return redirect(url_for("billing"))


# ==========================================================
# Print Bill
# ==========================================================

@app.route("/print_bill/<int:id>")
@login_required
def print_bill(id):

    return redirect(
        url_for("bill_pdf", id=id)
    )


# ==========================================================
# Download Bill PDF
# ==========================================================

@app.route("/bill/pdf/<int:id>")
@login_required
def bill_pdf(id):

    bill = Bill.query.get_or_404(id)

    patient = Patient.query.get(
        bill.patient_id
    )

    buffer = io.BytesIO()

    pdf = canvas.Canvas(buffer)

    pdf.setFont(
        "Helvetica-Bold",
        18
    )

    pdf.drawString(
        180,
        800,
        "Hospital Bill"
    )

    pdf.setFont(
        "Helvetica",
        12
    )

    pdf.drawString(
        50,
        760,
        f"Bill ID : {bill.id}"
    )

    pdf.drawString(
        50,
        740,
        f"Patient : {patient.name}"
    )

    pdf.drawString(
        50,
        720,
        f"Consultation Fee : ₹{bill.consultation_fee}"
    )

    pdf.drawString(
        50,
        700,
        f"Medicine Fee : ₹{bill.medicine_fee}"
    )

    pdf.drawString(
        50,
        680,
        f"Lab Fee : ₹{bill.lab_fee}"
    )

    pdf.drawString(
        50,
        660,
        f"Total : ₹{bill.total}"
    )

    pdf.drawString(
        50,
        640,
        f"Payment Status : {bill.payment_status}"
    )

    pdf.save()

    buffer.seek(0)

    return make_response(
        buffer.getvalue(),
        200,
        {
            "Content-Type": "application/pdf",
            "Content-Disposition":
            f"inline; filename=Bill_{bill.id}.pdf"
        }
    )
# ==========================================================
# AI Disease Prediction
# ==========================================================

@app.route("/ai", methods=["GET", "POST"])
@login_required
def ai():

    prediction = None
    confidence = 0
    doctor = ""
    advice = ""

    if request.method == "POST":

        symptoms = request.form.getlist("symptoms")

        symptoms = [s.lower() for s in symptoms]

        # ==================================================
        # Disease Prediction
        # ==================================================

        if "fever" in symptoms and "cough" in symptoms:

            prediction = "Viral Fever"
            confidence = 95
            doctor = "General Physician"
            advice = (
                "Take rest, drink plenty of fluids "
                "and use prescribed medicines."
            )

        elif "headache" in symptoms and "body pain" in symptoms:

            prediction = "Dengue"
            confidence = 91
            doctor = "General Physician"
            advice = (
                "Get a blood test immediately "
                "and stay hydrated."
            )

        elif "chest pain" in symptoms:

            prediction = "Heart Disease"
            confidence = 96
            doctor = "Cardiologist"
            advice = (
                "Immediate medical attention "
                "is required."
            )

        elif "vomiting" in symptoms:

            prediction = "Food Poisoning"
            confidence = 88
            doctor = "General Physician"
            advice = (
                "Drink ORS and consult a doctor."
            )

        elif "sore throat" in symptoms:

            prediction = "Throat Infection"
            confidence = 86
            doctor = "ENT Specialist"
            advice = (
                "Avoid cold drinks and consult "
                "an ENT doctor."
            )

        elif "fever" in symptoms:

            prediction = "Common Fever"
            confidence = 80
            doctor = "General Physician"
            advice = (
                "Take rest and monitor "
                "your temperature."
            )

        else:

            prediction = "No Prediction"
            confidence = 50
            doctor = "General Physician"
            advice = (
                "Please consult a doctor "
                "for proper diagnosis."
            )

    return render_template(
        "ai.html",
        prediction=prediction,
        confidence=confidence,
        doctor=doctor,
        advice=advice
    )
# ==========================================================
# Create Default Users
# ==========================================================

def create_default_users():

    # ----------------------------
    # Admin
    # ----------------------------

    if not User.query.filter_by(username="admin").first():

        admin = User(
            fullname="Administrator",
            username="admin",
            password=generate_password_hash("admin123"),
            role="Admin"
        )

        db.session.add(admin)

    # ----------------------------
    # Doctor
    # ----------------------------

    if not User.query.filter_by(username="doctor").first():

        doctor = User(
            fullname="Doctor",
            username="doctor",
            password=generate_password_hash("doctor123"),
            role="Doctor"
        )

        db.session.add(doctor)

    # ----------------------------
    # Reception
    # ----------------------------

    if not User.query.filter_by(username="reception").first():

        reception = User(
            fullname="Receptionist",
            username="reception",
            password=generate_password_hash("reception123"),
            role="Reception"
        )

        db.session.add(reception)

    # ----------------------------
    # Patient
    # ----------------------------

    if not User.query.filter_by(username="patient").first():

        patient = User(
            fullname="Patient",
            username="patient",
            password=generate_password_hash("patient123"),
            role="Patient"
        )

        db.session.add(patient)

    db.session.commit()


# ==========================================================
# Database Initialization
# ==========================================================

with app.app_context():

    db.create_all()

    create_default_users()

# ===============================
# About Page
# ===============================

@app.route("/about")
def about():
    return render_template("about.html")

# ==========================================================
# Contact Page
# ==========================================================

@app.route("/contact")
def contact():
    return render_template("contact.html")

# ==========================================================
# Run Application
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
