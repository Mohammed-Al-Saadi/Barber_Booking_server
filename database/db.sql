
# SQL to create tables if they don't exist
-- Barbers table
CREATE TABLE Barbers (
    barber_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- Categories table
CREATE TABLE Categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL
);

-- Services table
CREATE TABLE Services (
    service_id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    category_id INT REFERENCES Categories(category_id),
    exclusive_to INT REFERENCES Barbers(barber_id)  -- Optional, for exclusive services
    estimated_time INT NOT NULL;

);

-- BarberServices table (many-to-many relationship)
CREATE TABLE BarberServices (
    barber_id INT REFERENCES Barbers(barber_id),
    service_id INT REFERENCES Services(service_id),
    PRIMARY KEY (barber_id, service_id)
);

-- Bookings table
CREATE TABLE Bookings (
    booking_id SERIAL PRIMARY KEY,
    barber_id INT REFERENCES Barbers(barber_id),
    service_id INT REFERENCES Services(service_id),
    customer_name VARCHAR(100),
    appointment_time TIMESTAMP NOT NULL
);


-- BarberSchedules table (stores working hours for each barber)
CREATE TABLE BarberSchedules (
    barber_id INT REFERENCES Barbers(barber_id),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    PRIMARY KEY (barber_id)
);

-- BarberAvailability table (stores the date range each barber is available)
CREATE TABLE BarberAvailability (
    barber_id INT REFERENCES Barbers(barber_id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    PRIMARY KEY (barber_id, start_date, end_date)
);

-- BarberExceptions table (stores exceptions for specific days for each barber)
CREATE TABLE BarberExceptions (
    barber_id INT REFERENCES Barbers(barber_id),
    exception_date DATE NOT NULL,
    custom_start_time TIME,
    custom_end_time TIME,
    is_off BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (barber_id, exception_date)
);
CREATE TABLE BarberBreaks (
    break_id SERIAL PRIMARY KEY,
    barber_id INT REFERENCES Barbers(barber_id),
    break_time TIMESTAMP,
    break_date DATE
);

CREATE TABLE barber_login (
    login_id SERIAL PRIMARY KEY,
    barber_id integer NOT Null,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash BYTEA NOT NULL,
    salt BYTEA NOT NULL
);


INSERT INTO Barbers (name) VALUES ('Karar'), ('Ahmed'), ('Ali'), ('Omar'), ('Zaid');
INSERT INTO Categories (category_name) VALUES ('Leikkaukset'), ('Värjäykset'), ('Parta');
-- Leikkaukset (Haircut) Services
INSERT INTO Services (service_name, category_id) VALUES
('Skin Fade (full haircut)', 1),  -- All barbers
('Parturileikkaus', 1),  -- All barbers
('Mallinmuutosleikkaus', 1),  -- All barbers
('100€ Service 🤯🔥', 1),  -- Exclusive to Karar
('Koneajo', 1),  -- All barbers
('Line up', 1),  -- All barbers
('Lasten hiustenleikkaus', 1),  -- All barbers
('Hiukset+parta', 1),  -- Ahmed and Karar
('Koko paketti', 1);  -- Ahmed and Karar

-- Värjäykset (Hair coloring) Services (Only Karar)
INSERT INTO Services (service_name, category_id, exclusive_to) VALUES
('Värjäykset (Hair color)', 2, 1);  -- Karar is barber_id = 1

-- Parta (Beard) Services (Karar and Ahmed)
INSERT INTO Services (service_name, category_id) VALUES
('Parran muotoilu', 3),
('Amerikkalainen parranajo', 3),
('Viiksien muotoilu', 3),
('Parran siistiminen/koneajo', 3);
-- Leikkaukset (Haircut) Services
INSERT INTO BarberServices (barber_id, service_id) VALUES
(1, 1), (2, 1), (3, 1), (4, 1), (5, 1),  -- Skin Fade (full haircut) for all barbers
(1, 2), (2, 2), (3, 2), (4, 2), (5, 2),  -- Parturileikkaus for all barbers
(1, 3), (2, 3), (3, 3), (4, 3), (5, 3),  -- Mallinmuutosleikkaus for all barbers
(1, 4),  -- 100€ Service 🤯🔥 only for Karar
(1, 5), (2, 5), (3, 5), (4, 5), (5, 5),  -- Koneajo for all barbers
(1, 6), (2, 6), (3, 6), (4, 6), (5, 6),  -- Line up for all barbers
(1, 7), (2, 7), (3, 7), (4, 7), (5, 7),  -- Lasten hiustenleikkaus for all barbers
(1, 8), (2, 8),  -- Hiukset+parta for Ahmed and Karar
(1, 9), (2, 9);  -- Koko paketti for Ahmed and Karar

-- Värjäykset (Hair coloring) Services (only Karar)
INSERT INTO BarberServices (barber_id, service_id) VALUES
(1, 10);  -- Karar

-- Parta (Beard) Services (Karar and Ahmed)
INSERT INTO BarberServices (barber_id, service_id) VALUES
(1, 11), (2, 11),  -- Parran muotoilu
(1, 12), (2, 12),  -- Amerikkalainen parranajo
(1, 13), (2, 13),  -- Viiksien muotoilu
(1, 14), (2, 14);  -- Parran siistiminen/koneajo



"""
            """
            cursor.execute(create_bookings_table)

            # Insert barbers
            insert_barbers = """
            INSERT INTO Barbers (name) VALUES 
            ('Karar'), ('Ahmed'), ('Ali'), ('Omar'), ('Zaid')
            ON CONFLICT DO NOTHING;  -- Avoid inserting duplicates
            """
            cursor.execute(insert_barbers)

            # Insert categories
            insert_categories = """
            INSERT INTO Categories (category_name) VALUES 
            ('Leikkaukset'), ('Värjäykset'), ('Parta')
            ON CONFLICT DO NOTHING;
            """
            cursor.execute(insert_categories)

            # Insert services
            insert_services = """
            INSERT INTO Services (service_name, category_id) VALUES
            ('Skin Fade (full haircut)', 1), 
            ('Parturileikkaus', 1), 
            ('Mallinmuutosleikkaus', 1), 
            ('100€ Service 🤯🔥', 1), 
            ('Koneajo', 1), 
            ('Line up', 1), 
            ('Lasten hiustenleikkaus', 1), 
            ('Hiukset+parta', 1), 
            ('Koko paketti', 1);
            
            INSERT INTO Services (service_name, category_id, exclusive_to) VALUES
            ('Värjäykset (Hair color)', 2, 1);
            
            INSERT INTO Services (service_name, category_id) VALUES
            ('Parran muotoilu', 3),
            ('Amerikkalainen parranajo', 3),
            ('Viiksien muotoilu', 3),
            ('Parran siistiminen/koneajo', 3);
            """
            cursor.execute(insert_services)

            # Insert barber services
            insert_barber_services = """
            INSERT INTO BarberServices (barber_id, service_id) VALUES
            (1, 1), (2, 1), (3, 1), (4, 1), (5, 1),  
            (1, 2), (2, 2), (3, 2), (4, 2), (5, 2),  
            (1, 3), (2, 3), (3, 3), (4, 3), (5, 3),  
            (1, 4), 
            (1, 5), (2, 5), (3, 5), (4, 5), (5, 5),  
            (1, 6), (2, 6), (3, 6), (4, 6), (5, 6),  
            (1, 7), (2, 7), (3, 7), (4, 7), (5, 7),  
            (1, 8), (2, 8),  
            (1, 9), (2, 9);  
            
            INSERT INTO BarberServices (barber_id, service_id) VALUES
            (1, 10);

            INSERT INTO BarberServices (barber_id, service_id) VALUES
            (1, 11), (2, 11),
            (1, 12), (2, 12), 
            (1, 13), (2, 13), 
            (1, 14), (2, 14);
            """
            cursor.execute(insert_barber_services)

            # Commit the transaction
            conn.commit()

            # Close the cursor and release the connection
            cursor.close()
            release_connection(conn)

            print("All tables created and data inserted successfully.")

        except Exception as e:
            # Rollback in case of an error
            conn.rollback()
            release_connection(conn)
            print(f"Error occurred while inserting data: {e}")

    else:
        print("Failed to connect to the database")



# Example usage
barber_schedules = {
    1: ('09:00', '16:00'),  
    2: ('09:00', '16:00'),  
    3: ('11:00', '13:00'),  
    4: ('09:00', '13:00'),  
    5: ('10:00', '15:00'),  
}

barber_dates = {
    1: (datetime(2024, 9, 13), datetime(2024, 9, 13)),
    2: (datetime(2024, 9, 13), datetime(2024, 9, 13)),
    3: (datetime(2024, 9, 15), datetime(2024, 9, 15)),
    4: (datetime(2024, 9, 16), datetime(2024, 9, 18)),
    5: (datetime(2024, 9, 17), datetime(2024, 9, 17)),
}

existing_bookings = {
    1: [('2024-09-13 11:15:00', 45), ('2024-09-13 12:15:00', 60),('2024-09-13 14:15:00', 60),('2024-09-13 13:15:00', 45)],  
    2: [('2024-09-13 1:15:00', 45),('2024-09-13 12:15:00', 60),('2024-09-13 14:15:00', 60),('2024-09-13 13:15:00', 45)],  
    3: [('2024-09-15 11:30:00', 30)],  
}

exceptions = {
    '2024-09-15': {
        1: None,  
        2: ('12:00', '16:00')  
    },
    '2024-09-17': {
        2: ('13:00', '17:00')  
    }
}

# Generate the time slots for a specific barber (or list of barbers)
service_duration = 45




-- Insert prices for each barber and service
INSERT INTO BarberServicePrices (barber_id, service_id, price) VALUES
-- Skin Fade (full haircut) for all barbers
(1, 1, 50.00), (2, 1, 45.00), (3, 1, 40.00), (4, 1, 35.00), (5, 1, 30.00),

-- Parturileikkaus for all barbers
(1, 2, 55.00), (2, 2, 50.00), (3, 2, 45.00), (4, 2, 40.00), (5, 2, 35.00),

-- Mallinmuutosleikkaus for all barbers
(1, 3, 60.00), (2, 3, 55.00), (3, 3, 50.00), (4, 3, 45.00), (5, 3, 40.00),

-- 100€ Service 🤯🔥 only for Karar
(1, 4, 100.00),

-- Koneajo for all barbers
(1, 5, 20.00), (2, 5, 18.00), (3, 5, 15.00), (4, 5, 12.00), (5, 5, 10.00),

-- Line up for all barbers
(1, 6, 15.00), (2, 6, 15.00), (3, 6, 14.00), (4, 6, 13.00), (5, 6, 12.00),

-- Lasten hiustenleikkaus for all barbers
(1, 7, 25.00), (2, 7, 23.00), (3, 7, 20.00), (4, 7, 18.00), (5, 7, 15.00),

-- Hiukset+parta for Ahmed and Karar
(1, 8, 75.00), (2, 8, 70.00),

-- Koko paketti for Ahmed and Karar
(1, 9, 80.00), (2, 9, 75.00),

-- Värjäykset (Hair color) - Only Karar
(1, 10, 200.00),

-- Parta (Beard) Services (Karar and Ahmed)
-- Parran muotoilu
(1, 11, 150.00), (2, 11, 140.00),

-- Amerikkalainen parranajo
(1, 12, 130.00), (2, 12, 125.00),

-- Viiksien muotoilu
(1, 13, 80.00), (2, 13, 75.00),

-- Parran siistiminen/koneajo
(1, 14, 50.00), (2, 14, 45.00);

