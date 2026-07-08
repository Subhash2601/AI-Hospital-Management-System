from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ==========================================================
# USER LOGIN
# ==========================================================

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    fullname = db.Column(db.String(100), nullable=False)

    username = db.Column(db.String(50), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False)
    # Admin
    # Doctor
    # Patient
    # Receptionist

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.username}>"

# ==========================================================
# PATIENT
# ==========================================================

class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    age = db.Column(db.Integer)

    gender = db.Column(db.String(20))

    phone = db.Column(db.String(20))
    username = db.Column(db.String(50), unique=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    address = db.Column(db.String(200))

    blood_group = db.Column(db.String(10))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==========================================================
# DOCTOR
# ==========================================================

class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    specialization = db.Column(db.String(100))

    phone = db.Column(db.String(20))
    username = db.Column(db.String(50), unique=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    email = db.Column(db.String(100))

    status = db.Column(db.String(20), default="Available")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==========================================================
# APPOINTMENTS
# ==========================================================

class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"))

    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"))

    appointment_date = db.Column(db.String(30))

    appointment_time = db.Column(db.String(20))

    status = db.Column(
        db.String(20),
        default="Pending"
    )

    patient = db.relationship("Patient")

    doctor = db.relationship("Doctor")

# ==========================================================
# SMART TOKEN SYSTEM
# ==========================================================

class Token(db.Model):
    __tablename__ = "tokens"

    id = db.Column(db.Integer, primary_key=True)

    token_number = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id")
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id")
    )

    department = db.Column(db.String(100))

    priority = db.Column(
        db.String(20),
        default="Normal"
    )

    status = db.Column(
        db.String(20),
        default="Waiting"
    )
    # Waiting
    # Called
    # In Consultation
    # Completed
    # Cancelled

    queue_position = db.Column(db.Integer)

    estimated_wait = db.Column(db.Integer)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    patient = db.relationship("Patient")

    doctor = db.relationship("Doctor")

# ==========================================================
# BILLING
# ==========================================================

class Bill(db.Model):
    __tablename__ = "bills"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False
    )

    consultation_fee = db.Column(
        db.Float,
        default=0
    )

    medicine_fee = db.Column(
        db.Float,
        default=0
    )

    lab_fee = db.Column(
        db.Float,
        default=0
    )

    total = db.Column(
        db.Float,
        default=0
    )

    payment_status = db.Column(
        db.String(20),
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    patient = db.relationship(
        "Patient",
        backref="bills"
    )

    def __repr__(self):
        return f"<Bill {self.id}>"
# ==========================================================
# LAB REPORTS
# ==========================================================

class LabReport(db.Model):

    __tablename__ = "lab_reports"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id")
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id")
    )

    report_name = db.Column(db.String(100))

    report_file = db.Column(db.String(200))

    report_date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    patient = db.relationship("Patient")

    doctor = db.relationship("Doctor")

# ==========================================================
# PRESCRIPTIONS
# ==========================================================

class Prescription(db.Model):
    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id"),
        nullable=False
    )

    diagnosis = db.Column(
        db.String(300),
        nullable=False
    )

    medicines = db.Column(
        db.Text,
        nullable=False
    )

    dosage = db.Column(
        db.String(300)
    )

    advice = db.Column(
        db.Text
    )

    prescription_date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    patient = db.relationship("Patient")
    doctor = db.relationship("Doctor")