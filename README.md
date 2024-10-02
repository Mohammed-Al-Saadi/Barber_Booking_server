# Barber Booking System API

## Overview

This is a Flask-based API for managing barber bookings, providing functionalities for user registration, login, appointment booking, and managing barber schedules and breaks.

## API Endpoints

### User Registration

- **`POST /signup`**
  - **Description**: Create a user account.
  - **Request Body**:
    ```json
    {
      "barber_id": 1,
      "username": "example_user",
      "password": "secure_password"
    }
    ```
  - **Responses**:
    - `201 Created`: User created successfully.
    - `409 Conflict`: Barber ID or username already exists.

### User Login

- **`POST /login`**
  - **Description**: Log in a user and obtain a JWT token.
  - **Request Body**:
    ```json
    {
      "username": "example_user",
      "password": "secure_password"
    }
    ```
  - **Responses**:
    - `200 OK`: Login successful, returns JWT token.
    - `401 Unauthorized`: Invalid credentials.
    - `404 Not Found`: Username does not exist.

### Protected Route

- **`GET /protected`**
  - **Description**: Secured endpoint requiring a valid JWT token.
  - **Authorization**: Bearer token in the Authorization header.
  - **Responses**:
    - `200 OK`: Returns barber ID and expiration date.
    - `401 Unauthorized`: Token is missing, expired, or invalid.

### Get Available Barbers and Slots

- **`POST /get_barbers_and_slots`**
  - **Description**: Fetch available barbers and their time slots based on service.
  - **Request Body**:
    ```json
    {
      "category_name": "Haircuts",
      "service_name": "Classic Cut"
    }
    ```
  - **Responses**:
    - `200 OK`: Returns available barbers and time slots.
    - `400 Bad Request`: Missing category or service name.
    - `404 Not Found`: No barbers found for the given service.
    - `500 Internal Server Error`: Database error.

### Get Categories and Services

- **`GET /get_categories_and_services`**
  - **Description**: Retrieve a list of categories and services.
  - **Responses**:
    - `200 OK`: Returns categories and services.
    - `500 Internal Server Error`: Error during fetching.

### Create Booking

- **`POST /bookings`**
  - **Description**: Create a new booking.
  - **Request Body**:
    ```json
    {
      "barber_id": 1,
      "service_id": 2,
      "customer_name": "John Doe",
      "appointment_time": "2024-09-21T15:00:00",
      "email": "john.doe@example.com",
      "phone": "1234567890",
      "price": 50.0,
      "extra_charge": 5.0
    }
    ```
  - **Responses**:
    - `201 Created`: Booking created successfully.
    - `409 Conflict`: Time slot unavailable.
    - `500 Internal Server Error`: Any other error.

### Set Barber Break Slots

- **`POST /set_barber_break_slots`**
  - **Description**: Set break times for a barber.
  - **Request Body**:
    ```json
    {
      "barber_id": 1,
      "break_date": "2024-09-21",
      "break_slots": ["10:00", "11:00", "15:00"]
    }
    ```
  - **Responses**:
    - `201 Created`: Break slots added successfully.
    - `409 Conflict`: Break times overlap with existing bookings.
    - `500 Internal Server Error`: Any other error.

## Installation

pip3 install -r req.txt --break-system-packages

### Prerequisites

- Python 3.x
- PostgreSQL
- pip (Python package installer)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/barber-booking-system.git
   cd barber-booking-system
   ```
