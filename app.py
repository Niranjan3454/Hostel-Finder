import re

from flask import Flask, render_template, request, redirect, url_for, session
from config import Config
from models import db, User, Hostel, SavedHostel, Booking, Notification
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config.from_object(Config)

# Required for login sessions
app.secret_key = "hostel_finder_secret_key"

db.init_app(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/db-test")
def db_test():
    try:
        db.session.execute(db.text("SELECT 1"))
        return "MySQL Connected Successfully!"
    except Exception as e:
        return f"MySQL Connection Failed: {e}"


# ---------------- OWNER REGISTRATION ----------------

@app.route("/owner/register", methods=["GET", "POST"])
def owner_register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"].strip()
        password = request.form["password"]

        if not re.fullmatch(r"[6-9][0-9]{9}", phone):
            return "Please enter a valid 10-digit mobile number."

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "This email is already registered."

        hashed_password = generate_password_hash(password)

        owner = User(
            name=name,
            email=email,
            password=hashed_password,
            phone=phone,
            role="OWNER"
        )

        db.session.add(owner)
        db.session.commit()

        return redirect(url_for("owner_login"))

    return render_template("owner_register.html")


# ---------------- OWNER LOGIN ----------------

@app.route("/owner/login", methods=["GET", "POST"])
def owner_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        owner = User.query.filter_by(
            email=email,
            role="OWNER"
        ).first()

        if owner and check_password_hash(owner.password, password):

            session["owner_id"] = owner.user_id
            session["owner_name"] = owner.name

            return redirect(url_for("owner_dashboard"))

        return "Invalid email or password."

    return render_template("owner_login.html")


# ---------------- OWNER DASHBOARD ----------------

@app.route("/owner/dashboard")
def owner_dashboard():

    if "owner_id" not in session:
        return redirect(url_for("owner_login"))

    unread_count = Notification.query.filter_by(
        user_id=session["owner_id"],
        is_read=False
    ).count()

    return render_template(
        "owner_dashboard.html",
        owner_name=session["owner_name"],
        unread_count=unread_count
    )

# ---------------- OWNER BOOKING REQUESTS ----------------

@app.route("/owner/bookings")
def owner_bookings():

    if "owner_id" not in session:
        return redirect(url_for("owner_login"))

    bookings = (
        Booking.query
        .join(Hostel, Booking.hostel_id == Hostel.hostel_id)
        .filter(Hostel.owner_id == session["owner_id"])
        .order_by(Booking.booking_date.desc())
        .all()
    )

    return render_template(
        "owner_bookings.html",
        bookings=bookings
    )

@app.route("/owner/add-hostel", methods=["GET", "POST"])
def add_hostel():

    if "owner_id" not in session:
        return redirect(url_for("owner_login"))

    if request.method == "POST":

        hostel_name = request.form["hostel_name"]
        address = request.form["address"]
        area = request.form["area"]
        city = request.form["city"]
        hostel_type = request.form["hostel_type"]

        rent = request.form["rent"]
        total_beds = request.form["total_beds"]
        available_beds = request.form["available_beds"]

        contact_no = request.form["contact_no"]

        facilities = request.form["facilities"]
        description = request.form["description"]

        # Check vacancy
        if int(available_beds) > int(total_beds):
            return "Available beds cannot be greater than total beds."

        hostel = Hostel(
            owner_id=session["owner_id"],
            hostel_name=hostel_name,
            address=address,
            area=area,
            city=city,
            hostel_type=hostel_type,
            rent=rent,
            total_beds=total_beds,
            available_beds=available_beds,
            contact_no=contact_no,
            facilities=facilities,
            description=description
        )

        db.session.add(hostel)
        db.session.commit()

        return redirect(url_for("owner_dashboard"))

    return render_template("add_hostel.html")

@app.route("/owner/my-hostels")
def my_hostels():

    if "owner_id" not in session:
        return redirect(url_for("owner_login"))

    hostels = Hostel.query.filter_by(
        owner_id=session["owner_id"]
    ).all()

    return render_template(
        "my_hostels.html",
        hostels=hostels
    )
# ---------------- CONFIRM BOOKING ----------------

@app.route("/owner/confirm-booking/<int:booking_id>", methods=["POST"])
def confirm_booking(booking_id):

    if "owner_id" not in session:
        return redirect(url_for("owner_login"))

    booking = Booking.query.get_or_404(booking_id)

    # Check that this booking belongs to owner's hostel
    if not booking.hostel or booking.hostel.owner_id != session["owner_id"]:
        return "Unauthorized access.", 403

    # Only pending bookings can be confirmed
    if booking.booking_status != "PENDING":
        return redirect(url_for("owner_bookings"))

    hostel = booking.hostel

    # Check available beds
    if hostel.available_beds < booking.beds_booked:
        return "Not enough beds available."

    # Reduce available beds
    hostel.available_beds -= booking.beds_booked

    # Confirm booking
    booking.booking_status = "CONFIRMED"

    # Create notification for hosteller
    notification = Notification(
        user_id=booking.hosteller_id,
        message=(
            f"Your booking for {hostel.hostel_name} "
            f"has been confirmed."
        )
    )

    db.session.add(notification)

    db.session.commit()

    return redirect(url_for("owner_bookings"))
# ---------------- OWNER CANCEL BOOKING ----------------

@app.route("/owner/cancel-booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):

    if "owner_id" not in session:
        return redirect(url_for("owner_login"))

    booking = Booking.query.get_or_404(booking_id)

    # Check that booking belongs to owner's hostel
    if not booking.hostel or booking.hostel.owner_id != session["owner_id"]:
        return "Unauthorized access.", 403

    # Already cancelled
    if booking.booking_status == "CANCELLED":
        return redirect(url_for("owner_bookings"))

    # Confirmed booking cannot be cancelled
    if booking.booking_status == "CONFIRMED":
        return "Confirmed booking cannot be cancelled."

    # Only pending booking can be cancelled
    if booking.booking_status != "PENDING":
        return redirect(url_for("owner_bookings"))

    hostel = booking.hostel

    # Cancel pending booking
    booking.booking_status = "CANCELLED"

    # Create notification for hosteller
    notification = Notification(
        user_id=booking.hosteller_id,
        message=(
            f"Your booking for {hostel.hostel_name} "
            f"has been cancelled by the owner."
        )
    )

    db.session.add(notification)

    db.session.commit()

    return redirect(url_for("owner_bookings"))

@app.route("/search")
def search_hostels():

    location = request.args.get("location", "").strip()
    budget = request.args.get("budget", "").strip()
    hostel_type = request.args.get("type", "").strip()

    query = Hostel.query

    # Location filter
    if location:
        search_text = f"%{location}%"

        query = query.filter(
            db.or_(
                Hostel.hostel_name.ilike(search_text),
                Hostel.area.ilike(search_text),
                Hostel.city.ilike(search_text)
            )
        )

    # Budget filter
    if budget:

        try:
            max_rent = float(budget)

            query = query.filter(
                Hostel.rent <= max_rent
            )

        except ValueError:
            pass

    # Hostel type filter
    if hostel_type:

        query = query.filter(
            Hostel.hostel_type == hostel_type
        )

    hostels = query.order_by(
        Hostel.created_at.desc()
    ).all()

    return render_template(
        "search_hostels.html",
        hostels=hostels
    )
@app.route("/register", methods=["GET", "POST"])
def hosteller_register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"].strip()
        password = request.form["password"]

        if not re.fullmatch(r"[6-9][0-9]{9}", phone):
            return "Please enter a valid 10-digit mobile number."

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            return "This email is already registered."

        hashed_password = generate_password_hash(password)

        hosteller = User(
            name=name,
            email=email,
            password=hashed_password,
            phone=phone,
            role="HOSTELLER"
        )

        db.session.add(hosteller)
        db.session.commit()

        return redirect(url_for("hosteller_login"))

    return render_template("hosteller_register.html")
@app.route("/hostel/<int:hostel_id>")
def hostel_details(hostel_id):

    hostel = Hostel.query.get_or_404(hostel_id)

    return render_template(
        "hostel_details.html",
        hostel=hostel
    )
# ---------------- SAVE HOSTEL ----------------

@app.route("/save-hostel/<int:hostel_id>", methods=["POST"])
def save_hostel(hostel_id):

    if "hosteller_id" not in session:
        return redirect(url_for("hosteller_login"))

    existing = SavedHostel.query.filter_by(
        hosteller_id=session["hosteller_id"],
        hostel_id=hostel_id
    ).first()

    if existing:
        return "Hostel already saved."

    saved_hostel = SavedHostel(
        hosteller_id=session["hosteller_id"],
        hostel_id=hostel_id
    )

    db.session.add(saved_hostel)
    db.session.commit()

    return redirect(
        url_for(
            "hostel_details",
            hostel_id=hostel_id
        )
    )


# ---------------- BOOK HOSTEL ----------------

@app.route("/book-hostel/<int:hostel_id>", methods=["POST"])
def book_hostel(hostel_id):

    # Check hosteller login
    if "hosteller_id" not in session:
        return redirect(url_for("hosteller_login"))

    # Get hostel
    hostel = Hostel.query.get_or_404(hostel_id)

    # Get number of beds
    try:
        beds_booked = int(request.form["beds_booked"])
    except (ValueError, TypeError):
        return "Invalid number of beds."

    # Validate number of beds
    if beds_booked <= 0:
        return "Number of beds must be at least 1."

    # Check available beds
    if beds_booked > hostel.available_beds:
        return "Not enough beds available."

    # -----------------------------------------
    # CHECK EXISTING ACTIVE BOOKING
    # -----------------------------------------

    existing_booking = Booking.query.filter(
        Booking.hosteller_id == session["hosteller_id"],
        Booking.hostel_id == hostel_id,
        Booking.booking_status.in_(["PENDING", "CONFIRMED"])
    ).first()

    # Prevent duplicate booking
    if existing_booking:

        if existing_booking.booking_status == "PENDING":
            return "You already have a pending booking for this hostel."

        if existing_booking.booking_status == "CONFIRMED":
            return "You already have a confirmed booking for this hostel."

    # -----------------------------------------
    # CREATE NEW BOOKING
    # -----------------------------------------

    booking = Booking(
        hosteller_id=session["hosteller_id"],
        hostel_id=hostel.hostel_id,
        beds_booked=beds_booked,
        booking_status="PENDING"
    )

    # Save booking
    db.session.add(booking)

    # ---------------- NOTIFY OWNER ----------------

    notification = Notification(
        user_id=hostel.owner_id,
        message=(
            f"🔔 New booking request received for "
            f"{hostel.hostel_name}. "
            f"{beds_booked} bed(s) requested."
        )
    )

    db.session.add(notification)

    # Save booking + notification
    db.session.commit()

    # Redirect to hostel details
    return redirect(
        url_for(
            "hostel_details",
            hostel_id=hostel_id
        )
    )
# ---------------- HOSTELLER NOTIFICATIONS ----------------

# ---------------- HOSTELLER NOTIFICATIONS ----------------

@app.route("/hosteller/notifications")
def hosteller_notifications():

    if "hosteller_id" not in session:
        return redirect(url_for("hosteller_login"))

    notifications = (
        Notification.query
        .filter_by(user_id=session["hosteller_id"])
        .order_by(Notification.created_at.desc())
        .all()
    )

    return render_template(
        "notifications.html",
        notifications=notifications
    )

    # ---------------- OWNER NOTIFICATIONS ----------------

# ---------------- OWNER NOTIFICATIONS ----------------

@app.route("/owner/notifications")
def owner_notifications():

    if "owner_id" not in session:
        return redirect(url_for("owner_login"))

    notifications = (
        Notification.query
        .filter_by(user_id=session["owner_id"])
        .order_by(Notification.created_at.desc())
        .all()
    )

    return render_template(
        "owner_notifications.html",
        notifications=notifications
    )

# ---------------- READ OWNER NOTIFICATION ----------------

@app.route("/owner/notifications/read/<int:notification_id>")
def read_owner_notification(notification_id):

    if "owner_id" not in session:
        return redirect(url_for("owner_login"))

    notification = Notification.query.get_or_404(notification_id)

    # Make sure notification belongs to logged-in owner
    if notification.user_id != session["owner_id"]:
        return "Unauthorized access.", 403

    # Mark as read
    notification.is_read = True

    db.session.commit()

    return redirect(url_for("owner_notifications"))

# ---------------- READ HOSTELLER NOTIFICATION ----------------

@app.route("/hosteller/notifications/read/<int:notification_id>")
def read_hosteller_notification(notification_id):

    if "hosteller_id" not in session:
        return redirect(url_for("hosteller_login"))

    notification = Notification.query.get_or_404(notification_id)

    # Make sure notification belongs to logged-in hosteller
    if notification.user_id != session["hosteller_id"]:
        return "Unauthorized access.", 403

    # Mark as read
    notification.is_read = True

    db.session.commit()

    return redirect(url_for("hosteller_notifications"))

# ---------------- MY BOOKINGS ----------------

@app.route("/hosteller/my-bookings")
def my_bookings():

    if "hosteller_id" not in session:
        return redirect(url_for("hosteller_login"))

    bookings = Booking.query.filter_by(
        hosteller_id=session["hosteller_id"]
    ).order_by(
        Booking.booking_date.desc()
    ).all()

    return render_template(
        "my_bookings.html",
        bookings=bookings
    )
# ---------------- CANCEL BOOKING ----------------

# ---------------- HOSTELLER CANCEL BOOKING ----------------

@app.route("/hosteller/cancel-booking/<int:booking_id>", methods=["POST"])
def hosteller_cancel_booking(booking_id):

    # Check hosteller login
    if "hosteller_id" not in session:
        return redirect(url_for("hosteller_login"))

    # Get booking
    booking = Booking.query.get_or_404(booking_id)

    # Make sure booking belongs to logged-in hosteller
    if booking.hosteller_id != session["hosteller_id"]:
        return "Unauthorized access.", 403

    # Already cancelled
    if booking.booking_status == "CANCELLED":
        return redirect(url_for("my_bookings"))

    # Confirmed booking cannot be cancelled
    if booking.booking_status == "CONFIRMED":
        return "Confirmed booking cannot be cancelled."

    # Only PENDING booking can be cancelled
    if booking.booking_status != "PENDING":
        return redirect(url_for("my_bookings"))

    # Cancel the pending booking
    booking.booking_status = "CANCELLED"

    # Save changes
    db.session.commit()

    return redirect(url_for("my_bookings"))

# ---------------- SAVED HOSTELS ----------------

@app.route("/hosteller/saved-hostels")
def saved_hostels():

    if "hosteller_id" not in session:
        return redirect(url_for("hosteller_login"))

    saved = SavedHostel.query.filter_by(
        hosteller_id=session["hosteller_id"]
    ).all()

    hostels = []

    for item in saved:
        hostel = Hostel.query.get(item.hostel_id)

        if hostel:
            hostels.append(hostel)

    return render_template(
        "saved_hostels.html",
        hostels=hostels
    )

# ---------------- REMOVE SAVED HOSTEL ----------------

@app.route("/remove-saved-hostel/<int:hostel_id>", methods=["POST"])
def remove_saved_hostel(hostel_id):

    if "hosteller_id" not in session:
        return redirect(url_for("hosteller_login"))

    saved = SavedHostel.query.filter_by(
        hosteller_id=session["hosteller_id"],
        hostel_id=hostel_id
    ).first()

    if saved:
        db.session.delete(saved)
        db.session.commit()

    return redirect(url_for("saved_hostels"))

@app.route("/owner/edit-hostel/<int:hostel_id>", methods=["GET", "POST"])
def edit_hostel(hostel_id):

    if "owner_id" not in session:
        return redirect(url_for("owner_login"))

    hostel = Hostel.query.filter_by(
        hostel_id=hostel_id,
        owner_id=session["owner_id"]
    ).first_or_404()

    if request.method == "POST":

        hostel.hostel_name = request.form["hostel_name"]
        hostel.address = request.form["address"]
        hostel.area = request.form["area"]
        hostel.city = request.form["city"]
        hostel.hostel_type = request.form["hostel_type"]

        hostel.rent = request.form["rent"]

        hostel.total_beds = int(request.form["total_beds"])
        hostel.available_beds = int(request.form["available_beds"])

        hostel.contact_no = request.form["contact_no"]

        hostel.facilities = request.form["facilities"]
        hostel.description = request.form["description"]

        if hostel.available_beds > hostel.total_beds:
            return "Available beds cannot be greater than total beds."

        db.session.commit()

        return redirect(url_for("my_hostels"))

    return render_template(
        "edit_hostel.html",
        hostel=hostel
    )

@app.route("/owner/delete-hostel/<int:hostel_id>")
def delete_hostel(hostel_id):

    if "owner_id" not in session:
        return redirect(url_for("owner_login"))

    hostel = Hostel.query.filter_by(
        hostel_id=hostel_id,
        owner_id=session["owner_id"]
    ).first_or_404()

    db.session.delete(hostel)
    db.session.commit()

    return redirect(url_for("my_hostels"))


# ---------------- OWNER LOGOUT ----------------

@app.route("/owner/logout")
def owner_logout():

    session.clear()

    return redirect(url_for("owner_login"))

# ---------------- HOSTELLER LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def hosteller_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        hosteller = User.query.filter_by(
            email=email,
            role="HOSTELLER"
        ).first()

        if hosteller and check_password_hash(
            hosteller.password,
            password
        ):

            session["hosteller_id"] = hosteller.user_id
            session["hosteller_name"] = hosteller.name

            return redirect(
                url_for("hosteller_dashboard")
            )

        return "Invalid email or password."

    return render_template("hosteller_login.html")

# ---------------- HOSTELLER DASHBOARD ----------------

@app.route("/hosteller/dashboard")
def hosteller_dashboard():

    if "hosteller_id" not in session:
        return redirect(url_for("hosteller_login"))

    return render_template(
        "hosteller_dashboard.html",
        hosteller_name=session["hosteller_name"]
    )

# ---------------- HOSTELLER LOGOUT ----------------

@app.route("/logout")
def hosteller_logout():

    session.pop("hosteller_id", None)
    session.pop("hosteller_name", None)

    return redirect(url_for("hosteller_login"))


if __name__ == "__main__":
    app.run(debug=True)