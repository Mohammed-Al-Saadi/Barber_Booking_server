# Barber Booking System API

## Overview

The **Barber Booking System API** is a robust, Flask-based solution for managing barbershop appointments, user registrations, logins, barber schedules, and breaks. This API supports core functionalities such as booking appointments, retrieving available barbers and time slots, setting break times for barbers, and managing user authentication via JWT tokens.

**Key Features:**

- **Dynamic Slot Management**: When a user books an appointment, the selected time slot is immediately removed from the available slots, ensuring real-time updates and preventing double bookings.
- **Extended Booking Management**: Barbers have the ability to extend existing bookings, provided there is sufficient time before the next scheduled appointment. This allows for flexibility in handling appointments that may require additional time.
- **Availability Checks**: The system automatically checks for available time slots before extending a booking or scheduling a new one, ensuring that barbers can manage their schedules efficiently without conflicts.

The API is designed for scalability, allowing barbershop owners to manage multiple barbers with customizable availability and services.

- **Service-specific Barbers**: Not all barbers perform the same services. Each service can be assigned to specific barbers, ensuring customers can only book a barber qualified to perform the selected service.

- **Admin Management**: Admins can easily add or remove barbers from specific services, adjust their working hours, and set break times through the admin panel.

- **Customizable Schedules**: Barbers can define their working hours, set break times, and mark unavailable slots.

- **Comprehensive Barber Calendar**: The system provides a calendar view that shows all barbers’ schedules, including booked appointments, breaks, and exception days. Barbers can manage their calendars by adding breaks, days off, or adjusting their working hours for specific days.

- **Break and Exception Day Management**: Barbers can add breaks throughout their working day and mark exception days when they are unavailable (such as days off or special working hours). The system reflects these changes in real-time, ensuring customers only see available slots during booking.

### Calendar Features

- **All Barber Schedules**: The calendar shows a comprehensive view of all barbers' schedules, including booked appointments, breaks, and exception days, allowing both the admin and barbers to have a full overview of availability.

## Table of Contents

- [API Endpoints](#api-endpoints)
  - [User Registration](#user-registration)
  - [User Login](#user-login)
  - [Protected Route](#protected-route)
  - [Get Available Barbers and Slots](#get-available-barbers-and-slots)
  - [Get Categories and Services](#get-categories-and-services)
  - [Create Booking](#create-booking)
  - [Set Barber Break Slots](#set-barber-break-slots)

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

- **`GET /protected`**
  - **Description**: Secured endpoint requiring a valid JWT token.
  - **Responses**:
    - `200 OK`: Returns barber ID and expiration date.
    - `401 Unauthorized`: Token is missing, expired, or invalid.

### Categories and Services

- **`GET /categories_and_services`**
  - **Description**: Fetch all available categories and services.
  - **Responses**:
    - `200 OK`: Returns all categories and services.

### Barbers and Slots

- **`POST /get_barbers_and_slots`**
  - **Description**: Get available barbers and their time slots for a particular service.
  - **Request Body**:
    ```json
    {
      "category_name": "Haircuts",
      "service_name": "Classic Cut"
    }
    ```
  - **Responses**:
    - `200 OK`: Returns available barbers and slots.
    - `400 Bad Request`: Missing category or service name.

### Bookings

- **`POST /bookings`**

  - **Description**: Create a new booking for a specified barber and service.
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

- **`GET /get_todays_bookings`**
  - **Description**: Retrieve all bookings for the current day.
  - **Responses**:
    - `200 OK`: Returns today's bookings.

### Barber Breaks

- **`POST /set_barber_break_slots`**

  - **Description**: Set break slots for a specific barber.
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

- **`GET /get_barber_breaks`**

  - **Description**: Retrieve all breaks for a specific barber.
  - **Request Body**:
    ```json
    {
      "barber_id": 1
    }
    ```
  - **Responses**:
    - `200 OK`: Returns barber's breaks.

- **`DELETE /delete_barber_break`**

  - **Description**: Delete a specific break for a barber.
  - **Request Body**:
    ```json
    {
      "barber_id": 1,
      "break_time": "15:00"
    }
    ```
  - **Responses**:
    - `200 OK`: Break deleted successfully.

- **`POST /add_barber_breaks`**
  - **Description**: Add multiple break slots for a barber.
  - **Request Body**:
    ```json
    {
      "barber_id": 1,
      "break_slots": ["12:00", "13:00"]
    }
    ```
  - **Responses**:
    - `201 Created`: Breaks added successfully.

### Barber Schedule

- **`PUT /update_barber_schedule`**

  - **Description**: Update the schedule of a barber.
  - **Request Body**:
    ```json
    {
      "barber_id": 1,
      "schedule": {
        "start_time": "09:00",
        "end_time": "18:00"
      }
    }
    ```
  - **Responses**:
    - `200 OK`: Schedule updated successfully.

- **`GET /get_barber_schedule`**
  - **Description**: Retrieve the schedule of a barber.
  - **Request Body**:
    ```json
    {
      "barber_id": 1
    }
    ```
  - **Responses**:
    - `200 OK`: Returns barber's schedule.

### Barber Exceptions

- **`GET /get_barber_exceptions`**

  - **Description**: Retrieve the list of exceptions (e.g., days off) for a specific barber.
  - **Responses**:
    - `200 OK`: Returns the exception dates.

- **`POST /insert_barber_exception`**
  - **Description**: Add an exception date for a barber (e.g., day off).
  - **Request Body**:
    ```json
    {
      "barber_id": 1,
      "exception_date": "2024-09-21"
    }
    ```
  - **Responses**:
    - `201 Created`: Exception date added successfully.

### Overall Barber Management

- **`GET /over_all`**
  - **Description**: Retrieve an overview of all barbers and their current schedules.
  - **Responses**:
    - `200 OK`: Returns an overview of all barbers.

### Available Slots

- **`GET /available_slots`**
  - **Description**: Get all available time slots for a specific barber.
  - **Request Body**:
    ```json
    {
      "barber_id": 1
    }
    ```
  - **Responses**:
    - `200 OK`: Returns available slots for the barber.

### Pricing

- **`PUT /update_price`**
  - **Description**: Update the price of a service for a specific barber.
  - **Request Body**:
    ```json
    {
      "barber_id": 1,
      "service_id": 2,
      "price": 55.0
    }
    ```
  - **Responses**:
    - `200 OK`: Price updated successfully.

## Installation

Follow these steps to install and set up the API:

### Prerequisites

- **Python 3.x**
- **PostgreSQL**
- **pip (Python package installer)**

### Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/barber-booking-system.git
   cd barber-booking-system
   ```
