from datetime import datetime, time, timedelta

from database.get_existing_breaks_for_barber.get_existing_breaks_for_barber import get_existing_breaks_for_barber

def generate_barber_specific_slots_with_bookings(
    barber_schedules, barber_dates, existing_bookings, barber_ids=None, 
    gap_minutes: int = 15, exceptions: dict = None, service_duration_minutes: int = None
):
    # Normalize barber_ids to a list if it's a single int
    if isinstance(barber_ids, int):
        barber_ids = [barber_ids]
    elif barber_ids is None:
        barber_ids = list(barber_schedules.keys())
    
    slots_by_barber = {barber_id: {} for barber_id in barber_ids}

    for barber_id in barber_ids:
        # Get the default start and end times for this barber
        default_start_time, default_end_time = barber_schedules.get(barber_id, ('00:00', '00:00'))
        
        # Get the start and end dates specific to this barber
        start_date, end_date = barber_dates.get(barber_id, (None, None))
        
        # If start_date or end_date is not provided, set default values
        if start_date is None:
            start_date = datetime.now().date()  
        if end_date is None:
            end_date = start_date + timedelta(days=10)  

        current_date = start_date

        while current_date <= end_date:
            # Skip Sundays (weekday() == 6 for Sunday)
            if current_date.weekday() == 6:
                current_date += timedelta(days=1)
                continue

            current_date_str = current_date.strftime('%Y-%m-%d')

            # Handle exceptions (custom hours or exclusion) for specific days
            if exceptions and current_date_str in exceptions and barber_id in exceptions[current_date_str]:
                custom_times = exceptions[current_date_str][barber_id]
                if custom_times is None:
                    current_date += timedelta(days=1)
                    continue
                else:
                    start_hour, start_minute = map(int, custom_times[0].split(':'))
                    end_hour, end_minute = map(int, custom_times[1].split(':'))
            else:
                start_hour, start_minute = map(int, default_start_time.split(':'))
                end_hour, end_minute = map(int, default_end_time.split(':'))

            # Create datetime objects for start and end times
            start_time = datetime.combine(current_date, time(start_hour, start_minute))
            end_time = datetime.combine(current_date, time(end_hour, end_minute))
            slots = []

            # Fetch bookings for this barber on this date
            barber_bookings = existing_bookings.get(barber_id, [])
            barber_bookings_today = [(datetime.strptime(booking_time, '%Y-%m-%d %H:%M:%S'), service_duration) 
                                     for booking_time, service_duration in barber_bookings 
                                     if datetime.strptime(booking_time, '%Y-%m-%d %H:%M:%S').date() == current_date]

            # Sort the bookings by appointment time
            barber_bookings_today.sort(key=lambda x: x[0])

            # Get the current time
            current_datetime = datetime.now()

            # Fetch barber's break times for this date
            break_times = get_existing_breaks_for_barber(barber_id, current_date)

            # Generate slots while checking for bookings and breaks
            for booking_time, booking_duration in barber_bookings_today:
                if isinstance(booking_duration, timedelta):
                    booking_duration = int(booking_duration.total_seconds() / 60)

                while start_time + timedelta(minutes=service_duration_minutes) <= booking_time:
                    # Skip expired slots if it's the current day
                    if current_date == current_datetime.date() and start_time < current_datetime:
                        start_time += timedelta(minutes=gap_minutes)
                        continue
                    
                    # Format start_time as 'HH:MM' to compare with breaks
                    formatted_start_time = start_time.strftime('%H:%M')

                    # Only append the slot if it doesn't match a break time
                    if formatted_start_time not in break_times:
                        slots.append((start_time, start_time + timedelta(minutes=service_duration_minutes)))
                    
                    start_time += timedelta(minutes=gap_minutes)

                start_time = booking_time + timedelta(minutes=booking_duration)

            # Generate remaining slots after the last booking
            while start_time + timedelta(minutes=service_duration_minutes) <= end_time:
                # Skip expired slots if it's the current day
                if current_date == current_datetime.date() and start_time < current_datetime:
                    start_time += timedelta(minutes=gap_minutes)
                    continue

                # Format start_time as 'HH:MM' to compare with breaks
                formatted_start_time = start_time.strftime('%H:%M')

                # Only add the slot if it fits within operating hours and is not a break time
                if formatted_start_time not in break_times:
                    slots.append((start_time, start_time + timedelta(minutes=service_duration_minutes)))
                
                start_time += timedelta(minutes=gap_minutes)

            slots_by_barber[barber_id][current_date_str] = slots
            current_date += timedelta(days=1)

    return slots_by_barber
