from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# =========================
# USER MODEL
# =========================

class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    phone = db.Column(
        db.String(15)
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )

    hostels = db.relationship(
        "Hostel",
        backref="owner",
        lazy=True
    )


# =========================
# HOSTEL MODEL
# =========================

class Hostel(db.Model):
    __tablename__ = "hostels"

    hostel_id = db.Column(
        db.Integer,
        primary_key=True
    )

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    hostel_name = db.Column(
        db.String(150),
        nullable=False
    )

    address = db.Column(
        db.String(255),
        nullable=False
    )

    area = db.Column(
        db.String(100),
        nullable=False
    )

    city = db.Column(
        db.String(100),
        nullable=False
    )

    hostel_type = db.Column(
        db.String(50),
        nullable=False
    )

    rent = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    total_beds = db.Column(
        db.Integer,
        nullable=False
    )

    available_beds = db.Column(
        db.Integer,
        nullable=False
    )

    contact_no = db.Column(
        db.String(15),
        nullable=False
    )

    facilities = db.Column(
        db.Text
    )

    description = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )


# =========================
# SAVED HOSTEL MODEL
# =========================

class SavedHostel(db.Model):
    __tablename__ = "saved_hostels"

    saved_id = db.Column(
        db.Integer,
        primary_key=True
    )

    hosteller_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    hostel_id = db.Column(
        db.Integer,
        db.ForeignKey("hostels.hostel_id"),
        nullable=False
    )

    saved_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )


# =========================
# BOOKING MODEL
# =========================

class Booking(db.Model):
    __tablename__ = "bookings"

    booking_id = db.Column(
        db.Integer,
        primary_key=True
    )

    hosteller_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    hostel_id = db.Column(
        db.Integer,
        db.ForeignKey("hostels.hostel_id"),
        nullable=False
    )

    beds_booked = db.Column(
        db.Integer,
        nullable=False
    )

    booking_status = db.Column(
        db.Enum(
            "PENDING",
            "CONFIRMED",
            "CANCELLED"
        ),
        default="PENDING"
    )

    booking_date = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )
    hostel = db.relationship(
        "Hostel",
        backref="bookings"
    )
    hosteller = db.relationship(
        "User",
        foreign_keys=[hosteller_id],
        backref="bookings"
    )
    # =========================
# NOTIFICATION MODEL
# =========================

class Notification(db.Model):
    __tablename__ = "notifications"

    notification_id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    message = db.Column(
        db.String(255),
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )

    user = db.relationship(
        "User",
        backref="notifications"
    )