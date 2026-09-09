import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=""
)

cursor = conn.cursor()

cursor.execute("DROP DATABASE IF EXISTS GreenLog")
print("Database eliminato")

cursor.execute("CREATE DATABASE GreenLog")
print("Database creato")

cursor.execute("USE GreenLog")
print("Entro nel database")

query = [
    """
    CREATE TABLE drivers (
        driver_id INT AUTO_INCREMENT PRIMARY KEY,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        hire_date DATE,
        termination_date DATE,
        license_number VARCHAR(50) UNIQUE,
        license_state VARCHAR(2),
        date_of_birth DATE,
        home_terminal VARCHAR(100),
        employment_status VARCHAR(20),
        cdl_class VARCHAR(10),
        years_experience INT
    );
    """,
    """
    CREATE TABLE customers (
        customer_id INT AUTO_INCREMENT PRIMARY KEY,
        customer_name VARCHAR(150) NOT NULL,
        customer_type VARCHAR(50),
        credit_terms_days INT,
        primary_freight_type VARCHAR(100),
        account_status VARCHAR(20),
        contract_start_date DATE,
        annual_revenue_potential DECIMAL(12, 2)
    );
    """,
    """
    CREATE TABLE routes (
        route_id INT AUTO_INCREMENT PRIMARY KEY,
        origin_city VARCHAR(100) NOT NULL,
        origin_state VARCHAR(2) NOT NULL,
        destination_city VARCHAR(100) NOT NULL,
        destination_state VARCHAR(2) NOT NULL,
        typical_distance_miles DECIMAL(10, 2),
        base_rate_per_mile DECIMAL(6, 2),
        fuel_surcharge_rate DECIMAL(6, 4),
        typical_transit_days INT
    );
    """,
    """
    CREATE TABLE trucks (
        truck_id INT AUTO_INCREMENT PRIMARY KEY,
        unit_number VARCHAR(20) NOT NULL UNIQUE,
        make VARCHAR(50) NOT NULL,
        model_year YEAR NOT NULL,
        vin CHAR(17) NOT NULL UNIQUE,
        acquisition_date DATE NOT NULL,
        acquisition_mileage INT NOT NULL CHECK(acquisition_mileage >= 0),
        fuel_type ENUM('Diesel', 'Gasoline', 'Electric', 'Hybrid', 'LNG', 'CNG') NOT NULL,
        tank_capacity_gallons DECIMAL(6,2) CHECK(tank_capacity_gallons > 0),
        status ENUM('Available', 'In Service', 'Maintenance', 'Out of Service') DEFAULT 'Available',
        home_terminal VARCHAR(100)
    );
    """,
    """
    CREATE TABLE trailers (
        trailer_id INT AUTO_INCREMENT PRIMARY KEY,
        trailer_number VARCHAR(20) NOT NULL UNIQUE,
        trailer_type ENUM('Dry Van', 'Reefer', 'Flatbed', 'Tanker', 'Container', 'Lowboy') NOT NULL,
        length_feet DECIMAL(5,2) CHECK(length_feet > 0),
        model_year YEAR,
        vin CHAR(17) UNIQUE,
        acquisition_date DATE,
        status ENUM('Available', 'Assigned', 'Maintenance', 'Out of Service') DEFAULT 'Available',
        current_location VARCHAR(100)
    );
    """,
    """
    CREATE TABLE facilities (
        facility_id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(100) NOT NULL UNIQUE,
        indirizzo VARCHAR(100) NOT NULL,
        citta VARCHAR(100) not null,
        cap VARCHAR(6) NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS loads (
        load_id INT AUTO_INCREMENT PRIMARY KEY,
        customer_id INT NOT NULL,
        route_id INT NOT NULL,
        origin VARCHAR(100),
        destination VARCHAR(100),
        peso_kg DECIMAL(10, 2),
        data_consegna DATE,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (route_id) REFERENCES routes(route_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS trips (
        trip_id INT AUTO_INCREMENT PRIMARY KEY,
        load_id INT NOT NULL,
        driver_id INT NOT NULL,
        truck_id INT NOT NULL,
        trailer_id INT,
        distanza_km DECIMAL(8, 2),
        durata_min INT,
        consumo_litro DECIMAL(8, 2),
        velocita_media DECIMAL(6, 2),
        orario_partenza DATETIME,
        orario_arrivo DATETIME,
        FOREIGN KEY (load_id) REFERENCES loads(load_id),
        FOREIGN KEY (driver_id) REFERENCES drivers(driver_id),
        FOREIGN KEY (truck_id) REFERENCES trucks(truck_id),
        FOREIGN KEY (trailer_id) REFERENCES trailers(trailer_id)
    );
    """,
    """
    CREATE TABLE maintenance_records (
        maintenance_id INT AUTO_INCREMENT PRIMARY KEY,
        truck_id INT NOT NULL,
        maintenance_date DATE NOT NULL,
        maintenance_type ENUM('Preventive', 'Corrective', 'Inspection', 'Oil Change', 'Tire Replacement', 'Brake Service') NOT NULL,
        odometer_reading INT CHECK(odometer_reading >= 0),
        labor_hours DECIMAL(5,2) CHECK(labor_hours >= 0),
        labor_cost DECIMAL(10,2) CHECK(labor_cost >= 0),
        parts_cost DECIMAL(10,2) CHECK(parts_cost >= 0),
        total_cost DECIMAL(10,2) CHECK(total_cost >= 0),
        facility_location VARCHAR(100),
        downtime_hours DECIMAL(6,2) CHECK(downtime_hours >= 0),
        service_description TEXT,
        CONSTRAINT fk_maintenance_truck
            FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
            ON DELETE CASCADE ON UPDATE CASCADE
    );
    """,
    """
    CREATE TABLE truck_utilization_metrics (
        truck_id INT NOT NULL,
        month DATE NOT NULL,
        trips_completed INT DEFAULT 0 CHECK(trips_completed >= 0),
        total_miles DECIMAL(10,2) CHECK(total_miles >= 0),
        total_revenue DECIMAL(12,2) CHECK(total_revenue >= 0),
        average_mpg DECIMAL(5,2) CHECK(average_mpg >= 0),
        maintenance_events INT DEFAULT 0 CHECK(maintenance_events >= 0),
        maintenance_cost DECIMAL(10,2) CHECK(maintenance_cost >= 0),
        downtime_hours DECIMAL(6,2) CHECK(downtime_hours >= 0),
        utilization_rate DECIMAL(5,2) CHECK(utilization_rate BETWEEN 0 AND 100),
        PRIMARY KEY (truck_id, month),
        CONSTRAINT fk_metrics_truck
            FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
            ON DELETE CASCADE ON UPDATE CASCADE
    );
    """,
    """
    CREATE TABLE fuel_purchases (
        fuel_purchase_id INT AUTO_INCREMENT PRIMARY KEY,
        trip_id INT NOT NULL,
        truck_id INT NOT NULL,
        driver_id INT NOT NULL,
        purchase_date DATETIME,
        location_city VARCHAR(15),
        location_state VARCHAR(10),
        gallons DECIMAL(12,3),
        price_per_gallon DECIMAL(10,4),
        total_cost DECIMAL(15,2),
        fuel_card_number VARCHAR(30),

        CONSTRAINT fk_fuel_trip
            FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_fuel_truck
            FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_fuel_driver
            FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """,
    """
    CREATE TABLE delivery_events (
        event_id INT AUTO_INCREMENT PRIMARY KEY,
        load_id INT NOT NULL,
        trip_id INT NOT NULL,
        facility_id INT NOT NULL,
        event_type VARCHAR(50),
        scheduled_time DATETIME,
        actual_time DATETIME,
        detention_minutes INT DEFAULT 0,
        on_time BOOLEAN,
        location_city VARCHAR(15),
        location_state VARCHAR(10),

        CONSTRAINT fk_event_load
            FOREIGN KEY (load_id) REFERENCES loads(load_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_event_trip
            FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_event_facility
            FOREIGN KEY (facility_id) REFERENCES facilities(facility_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """,
    """
    CREATE TABLE safety_incidents (
        incident_id INT AUTO_INCREMENT PRIMARY KEY,
        trip_id INT NOT NULL,
        truck_id INT NOT NULL,
        driver_id INT NOT NULL,
        incident_date DATETIME,
        incident_type VARCHAR(100),
        location_city VARCHAR(15),
        location_state VARCHAR(10),
        at_fault_flag BOOLEAN,
        injury_flag BOOLEAN,
        description TEXT,
        vehicle_damage_cost DECIMAL(15,2),
        cargo_damage_cost DECIMAL(15,2),
        claim_amount DECIMAL(15,2),
        preventable_flag BOOLEAN,

        CONSTRAINT fk_incident_trip
            FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_incident_truck
            FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_incident_driver
            FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """,
    """
    CREATE TABLE driver_monthly_metrics (
        driver_id INT,
        mese DATE,
        tot_km DECIMAL(10,2),
        tot_trips INT,
        consumo_medio DECIMAL(8,2),
        tot_carburante DECIMAL(10,2),
        punteggio_eco DECIMAL(5,2),
        percentuale_puntualità DECIMAL(5,2),
        PRIMARY KEY (driver_id, mese),
        FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
    );
    """,
    """
    CREATE TABLE digital_twin (
        truck_id INT PRIMARY KEY,
        tot_km DECIMAL(10,2),
        consumo_medio DECIMAL(8,2),
        tot_CO2 DECIMAL(10,2),
        punteggio_eco DECIMAL(5,2),
        percentuale_utilizzo DECIMAL(5,2),
        indice_manutenzione DECIMAL(5,2),
        ultimo_aggiornamento DATETIME,
        FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
    );
    """
]

for q in query:
    cursor.execute(q)
    print("Tabella creata")

print("Database completo!")
conn.commit()
conn.close()