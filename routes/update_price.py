''

from flask import Blueprint, jsonify, request
from database.update_booking_price.update_booking_price import update_booking_price

update_price_bp = Blueprint('update_price_bp', __name__)

@update_price_bp.route('/update_price', methods=['POST'])
def update_price():
    """
    Route to update the price of a booking.
    
    Expected JSON body:
    {
        "booking_id": <int>,
        "new_price": <float>
    }
    
    Returns:
    - JSON response with success status and message.
    """
    try:
        # Get the JSON data from the request
        data = request.get_json()

        # Extract booking_id and new_price from the request body
        booking_id = data.get('booking_id')
        new_price = data.get('new_price')

        if not booking_id or new_price is None:
            return jsonify(success=False, message="Missing booking_id or new_price"), 400

        # Call the update_booking_price function to update the price
        success, message = update_booking_price(booking_id, new_price)

        # Return a success or error message based on the result
        if success:
            return jsonify(success=True, message=message), 200
        else:
            return jsonify(success=False, message=message), 400

    except Exception as e:
        return jsonify(success=False, message=f"An error occurred: {str(e)}"), 500
    

