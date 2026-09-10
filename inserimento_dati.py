from pulizia_csv import (
    load_drivers_csv,
    load_customers_csv,
    load_routes_csv,
    load_trucks_csv,
    load_trailers_csv,
    load_facilities_csv,
    load_loads_csv,
    load_trips_csv,
    load_maintenance_records_csv,
    load_truck_utilization_metrics_csv,
    load_fuel_purchases_csv,
    load_delivery_events_csv,
    load_safety_incidents_csv,
    load_driver_monthly_metrics_csv,
)

import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()  # legge il file .env e popola os.environ

conn = mysql.connector.connect(
    host=os.environ["DB_HOST"],
    user=os.environ["DB_USER"],
    root=os.environ["DB_ROOT"],
    password=os.environ["DB_PASSWORD"],
    database=os.environ["DB_NAME"]
)
cursor = conn.cursor()
# tabelle senza dipendenze (nessuna FK verso altre tabelle di questo elenco)
n = load_drivers_csv("drivers.csv", cursor)
print(f"drivers: {n} righe")

n = load_customers_csv("customers.csv", cursor)
print(f"customers: {n} righe")

n = load_routes_csv("routes.csv", cursor)
print(f"routes: {n} righe")

n = load_trucks_csv("trucks.csv", cursor)
print(f"trucks: {n} righe")

n = load_trailers_csv("trailers.csv", cursor)
print(f"trailers: {n} righe")

n = load_facilities_csv("facilities.csv", cursor)
print(f"facilities: {n} righe")

# dipende da customers, routes
n = load_loads_csv("loads.csv", cursor)
print(f"loads: {n} righe")

# dipende da loads, drivers, trucks, trailers
n = load_trips_csv("trips.csv", cursor)
print(f"trips: {n} righe")

# dipende da trucks
n = load_maintenance_records_csv("maintenance_records.csv", cursor)
print(f"maintenance_records: {n} righe")

n = load_truck_utilization_metrics_csv("truck_utilization_metrics.csv", cursor)
print(f"truck_utilization_metrics: {n} righe")

# dipende da trips, trucks, drivers
n = load_fuel_purchases_csv("fuel_purchases.csv", cursor)
print(f"fuel_purchases: {n} righe")

# dipende da loads, trips, facilities
n = load_delivery_events_csv("delivery_events.csv", cursor)
print(f"delivery_events: {n} righe")

# dipende da trips, trucks, drivers
n = load_safety_incidents_csv("safety_incidents.csv", cursor)
print(f"safety_incidents: {n} righe")

# dipende da drivers
n = load_driver_monthly_metrics_csv("driver_monthly_metrics.csv", cursor)
print(f"driver_monthly_metrics: {n} righe")

conn.commit()
cursor.close()
conn.close()


