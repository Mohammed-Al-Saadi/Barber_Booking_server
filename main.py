from flask import Flask, jsonify, request
from flask_cors import CORS
from routes.categories_and_services import categories_and_services_bp
from routes.auth import login_bp, signup_bp, protected_bp
from routes.booking import insert_booking_bp
from routes.barber import barbers_and_slots_bp
from routes.barber import set_barber_break_slots_bp
from routes.booking import get_todays_bookings_bp
from routes.barber_breaks import get_barber_breaks_bp, delete_barber_break_bp, add_barber_breaks_bp
from routes.barber_schedule import update_barber_schedule_bp, get_barber_schedule_bp
from routes.barber_exceptions import get_barber_exceptions_bp, insert_barber_exception_bp
from routes.over_all import over_all_bp
from routes.available_slots import available_slots_bp
from routes.update_price import update_price_bp
# Flask app initialization
app = Flask(__name__)
# Enable CORS for all origins and allow credentials
CORS(app, supports_credentials=True, origins=["*"])

app.register_blueprint(categories_and_services_bp)
app.register_blueprint(login_bp)
app.register_blueprint(signup_bp)
app.register_blueprint(protected_bp)
app.register_blueprint(barbers_and_slots_bp)
app.register_blueprint(insert_booking_bp)
app.register_blueprint(set_barber_break_slots_bp)
app.register_blueprint(get_todays_bookings_bp)
app.register_blueprint(delete_barber_break_bp)
app.register_blueprint(get_barber_breaks_bp)
app.register_blueprint(add_barber_breaks_bp)
app.register_blueprint(update_barber_schedule_bp)
app.register_blueprint(get_barber_schedule_bp)
app.register_blueprint(get_barber_exceptions_bp)
app.register_blueprint(insert_barber_exception_bp)
app.register_blueprint(over_all_bp)
app.register_blueprint(available_slots_bp)
app.register_blueprint(update_price_bp)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
