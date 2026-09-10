import pandas as pd

# --- costanti di conversione -------------------------------------------------
MILES_TO_KM = 1.60934
FEET_TO_M = 0.3048
LBS_TO_KG = 0.453592
GALLONS_TO_LITERS = 3.78541          # gallone USA
USD_TO_EUR = 0.92                    # tasso fisso indicativo: aggiornalo se serve
MPG_TO_L_100KM = 235.214583          # 100 * GALLONS_TO_LITERS / MILES_TO_KM


def _to_none(df: pd.DataFrame) -> pd.DataFrame:
    """Converte NaT/NaN/<NA> in None esplicito, per il connector MySQL."""
    return df.astype(object).where(pd.notnull(df), None)


def _bool(series: pd.Series) -> pd.Series:
    """Converte stringhe 'True'/'False' in booleani Python."""
    return series.map({"True": True, "False": False})


# --- drivers -------------------------------------------------------------
def load_drivers_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    df["hire_date"] = pd.to_datetime(df["hire_date"], errors="coerce").dt.date
    df["termination_date"] = pd.to_datetime(df["termination_date"], errors="coerce").dt.date
    df["date_of_birth"] = pd.to_datetime(df["date_of_birth"], errors="coerce").dt.date
    df["years_experience"] = pd.to_numeric(df["years_experience"], errors="coerce").astype("Int64")

    df = _to_none(df)
    data = list(df.itertuples(index=False, name=None))

    query = """
        INSERT INTO drivers
        (driver_id, first_name, last_name, hire_date, termination_date,
         license_number, license_state, date_of_birth, home_terminal,
         employment_status, cdl_class, years_experience)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- customers -------------------------------------------------------------
def load_customers_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    df["credit_terms_days"] = pd.to_numeric(df["credit_terms_days"], errors="coerce").astype("Int64")
    df["contract_start_date"] = pd.to_datetime(df["contract_start_date"], errors="coerce").dt.date
    df["annual_revenue_potential"] = (
        pd.to_numeric(df["annual_revenue_potential"], errors="coerce") * USD_TO_EUR
    ).round(2)

    df = _to_none(df)
    data = list(df.itertuples(index=False, name=None))

    query = """
        INSERT INTO customers
        (customer_id, customer_name, customer_type, credit_terms_days,
         primary_freight_type, account_status, contract_start_date,
         annual_revenue_potential_eur)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- routes -------------------------------------------------------------
def load_routes_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    dist_miles = pd.to_numeric(df["typical_distance_miles"], errors="coerce")
    rate_mile = pd.to_numeric(df["base_rate_per_mile"], errors="coerce")

    df["typical_distance_miles"] = (dist_miles * MILES_TO_KM).round(2)
    df["base_rate_per_mile"] = ((rate_mile / MILES_TO_KM) * USD_TO_EUR).round(4)
    df["fuel_surcharge_rate"] = pd.to_numeric(df["fuel_surcharge_rate"], errors="coerce").round(4)
    df["typical_transit_days"] = pd.to_numeric(df["typical_transit_days"], errors="coerce").astype("Int64")

    df = _to_none(df)
    data = list(df.itertuples(index=False, name=None))

    query = """
        INSERT INTO routes
        (route_id, origin_city, origin_state, destination_city, destination_state,
         typical_distance_km, base_rate_per_km_eur, fuel_surcharge_rate, typical_transit_days)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- trucks -------------------------------------------------------------
def load_trucks_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    df["model_year"] = pd.to_numeric(df["model_year"], errors="coerce").astype("Int64")
    df["acquisition_date"] = pd.to_datetime(df["acquisition_date"], errors="coerce").dt.date
    df["acquisition_mileage"] = (
        pd.to_numeric(df["acquisition_mileage"], errors="coerce") * MILES_TO_KM
    ).round(2)
    df["tank_capacity_gallons"] = (
        pd.to_numeric(df["tank_capacity_gallons"], errors="coerce") * GALLONS_TO_LITERS
    ).round(2)

    df = _to_none(df)
    data = list(df.itertuples(index=False, name=None))

    query = """
        INSERT INTO trucks
        (truck_id, unit_number, make, model_year, vin, acquisition_date,
         acquisition_km, fuel_type, tank_capacity_litri, status, home_terminal)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- trailers -------------------------------------------------------------
def load_trailers_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    df["length_feet"] = (pd.to_numeric(df["length_feet"], errors="coerce") * FEET_TO_M).round(2)
    df["model_year"] = pd.to_numeric(df["model_year"], errors="coerce").astype("Int64")
    df["acquisition_date"] = pd.to_datetime(df["acquisition_date"], errors="coerce").dt.date

    df = _to_none(df)
    data = list(df.itertuples(index=False, name=None))

    query = """
        INSERT INTO trailers
        (trailer_id, trailer_number, trailer_type, length_metri, model_year,
         vin, acquisition_date, status, current_location)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- facilities -------------------------------------------------------------
def load_facilities_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["dock_doors"] = pd.to_numeric(df["dock_doors"], errors="coerce").astype("Int64")

    df = _to_none(df)
    data = list(df.itertuples(index=False, name=None))

    query = """
        INSERT INTO facilities
        (facility_id, nome, tipo, citta, stato, latitudine, longitudine,
         numero_banchine, orario_operativo)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- loads -------------------------------------------------------------
def load_loads_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    out = pd.DataFrame({
        "load_id": df["load_id"],
        "customer_id": df["customer_id"],
        "route_id": df["route_id"],
        "data_consegna": pd.to_datetime(df["load_date"], errors="coerce").dt.date,
        "tipo_carico": df["load_type"],
        "peso_kg": (pd.to_numeric(df["weight_lbs"], errors="coerce") * LBS_TO_KG).round(2),
        "pezzi": pd.to_numeric(df["pieces"], errors="coerce").astype("Int64"),
        "ricavo_eur": (pd.to_numeric(df["revenue"], errors="coerce") * USD_TO_EUR).round(2),
        "supplemento_carburante_eur": (pd.to_numeric(df["fuel_surcharge"], errors="coerce") * USD_TO_EUR).round(2),
        "oneri_accessori_eur": (pd.to_numeric(df["accessorial_charges"], errors="coerce") * USD_TO_EUR).round(2),
        "stato_carico": df["load_status"],
        "tipo_prenotazione": df["booking_type"],
    })

    out = _to_none(out)
    data = list(out.itertuples(index=False, name=None))

    query = """
        INSERT INTO loads
        (load_id, customer_id, route_id, data_consegna,
         tipo_carico, peso_kg, pezzi, ricavo_eur, supplemento_carburante_eur,
         oneri_accessori_eur, stato_carico, tipo_prenotazione)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- trips -------------------------------------------------------------
def load_trips_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    distanza_km = (pd.to_numeric(df["actual_distance_miles"], errors="coerce") * MILES_TO_KM).round(2)
    durata_h = pd.to_numeric(df["actual_duration_hours"], errors="coerce")
    consumo_litro = (pd.to_numeric(df["fuel_gallons_used"], errors="coerce") * GALLONS_TO_LITERS).round(3)

    # velocità/consumo calcolati dai valori già convertiti, evitando 0/0
    durata_h_safe = durata_h.replace(0, pd.NA)
    distanza_km_safe = distanza_km.replace(0, pd.NA)

    out = pd.DataFrame({
        "trip_id": df["trip_id"],
        "load_id": df["load_id"],
        "driver_id": df["driver_id"],
        "truck_id": df["truck_id"],
        "trailer_id": df["trailer_id"],
        "data_partenza": pd.to_datetime(df["dispatch_date"], errors="coerce").dt.date,
        "distanza_km": distanza_km,
        "durata_min": (durata_h * 60).round(0).astype("Int64"),
        "consumo_litro": consumo_litro,
        "consumo_l_100km": (consumo_litro / distanza_km_safe * 100).round(2),
        "velocita_media_kmh": (distanza_km / durata_h_safe).round(2),
        "tempo_inattivita_min": (pd.to_numeric(df["idle_time_hours"], errors="coerce") * 60).round(0).astype("Int64"),
        "stato_viaggio": df["trip_status"],
    })

    out = _to_none(out)
    data = list(out.itertuples(index=False, name=None))

    query = """
        INSERT INTO trips
        (trip_id, load_id, driver_id, truck_id, trailer_id, data_partenza,
         distanza_km, durata_min, consumo_litro, consumo_l_100km,
         velocita_media_kmh, tempo_inattivita_min, stato_viaggio)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- maintenance_records -------------------------------------------------
def load_maintenance_records_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    df["maintenance_date"] = pd.to_datetime(df["maintenance_date"], errors="coerce").dt.date
    df["odometer_reading"] = (pd.to_numeric(df["odometer_reading"], errors="coerce") * MILES_TO_KM).round(2)
    df["labor_hours"] = pd.to_numeric(df["labor_hours"], errors="coerce").round(2)
    df["labor_cost"] = (pd.to_numeric(df["labor_cost"], errors="coerce") * USD_TO_EUR).round(2)
    df["parts_cost"] = (pd.to_numeric(df["parts_cost"], errors="coerce") * USD_TO_EUR).round(2)
    df["total_cost"] = (pd.to_numeric(df["total_cost"], errors="coerce") * USD_TO_EUR).round(2)
    df["downtime_hours"] = pd.to_numeric(df["downtime_hours"], errors="coerce").round(2)

    df = _to_none(df)
    data = list(df.itertuples(index=False, name=None))

    query = """
        INSERT INTO maintenance_records
        (maintenance_id, truck_id, maintenance_date, maintenance_type, odometro_km,
         labor_hours, labor_cost_eur, parts_cost_eur, total_cost_eur,
         facility_location, downtime_hours, service_description)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- truck_utilization_metrics -------------------------------------------
def load_truck_utilization_metrics_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    df["month"] = pd.to_datetime(df["month"], errors="coerce").dt.date
    df["trips_completed"] = pd.to_numeric(df["trips_completed"], errors="coerce").astype("Int64")
    df["total_miles"] = (pd.to_numeric(df["total_miles"], errors="coerce") * MILES_TO_KM).round(2)
    df["total_revenue"] = (pd.to_numeric(df["total_revenue"], errors="coerce") * USD_TO_EUR).round(2)
    df["average_mpg"] = (MPG_TO_L_100KM / pd.to_numeric(df["average_mpg"], errors="coerce")).round(2)
    df["maintenance_events"] = pd.to_numeric(df["maintenance_events"], errors="coerce").astype("Int64")
    df["maintenance_cost"] = (pd.to_numeric(df["maintenance_cost"], errors="coerce") * USD_TO_EUR).round(2)
    df["downtime_hours"] = pd.to_numeric(df["downtime_hours"], errors="coerce").round(2)
    df["utilization_rate"] = (pd.to_numeric(df["utilization_rate"], errors="coerce") * 100).round(2)

    df = _to_none(df)
    data = list(df.itertuples(index=False, name=None))

    query = """
        INSERT INTO truck_utilization_metrics
        (truck_id, month, trips_completed, total_km, total_revenue_eur,
         average_l_100km, maintenance_events, maintenance_cost_eur,
         downtime_hours, utilization_rate_pct)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- fuel_purchases -------------------------------------------------------
def load_fuel_purchases_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
    df["gallons"] = (pd.to_numeric(df["gallons"], errors="coerce") * GALLONS_TO_LITERS).round(3)
    price_gallon = pd.to_numeric(df["price_per_gallon"], errors="coerce")
    df["price_per_gallon"] = ((price_gallon / GALLONS_TO_LITERS) * USD_TO_EUR).round(4)
    df["total_cost"] = (pd.to_numeric(df["total_cost"], errors="coerce") * USD_TO_EUR).round(2)

    df = _to_none(df)
    data = list(df.itertuples(index=False, name=None))

    query = """
        INSERT INTO fuel_purchases
        (fuel_purchase_id, trip_id, truck_id, driver_id, purchase_date,
         location_city, location_state, litri, prezzo_litro_eur,
         costo_totale_eur, fuel_card_number)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- delivery_events -------------------------------------------------------
def load_delivery_events_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    out = pd.DataFrame({
        "event_id": df["event_id"],
        "load_id": df["load_id"],
        "trip_id": df["trip_id"],
        "facility_id": df["facility_id"],
        "event_type": df["event_type"],
        "scheduled_time": pd.to_datetime(df["scheduled_datetime"], errors="coerce"),
        "actual_time": pd.to_datetime(df["actual_datetime"], errors="coerce"),
        "detention_minutes": pd.to_numeric(df["detention_minutes"], errors="coerce").astype("Int64"),
        "on_time": _bool(df["on_time_flag"]),
        "location_city": df["location_city"],
        "location_state": df["location_state"],
    })

    out = _to_none(out)
    data = list(out.itertuples(index=False, name=None))

    query = """
        INSERT INTO delivery_events
        (event_id, load_id, trip_id, facility_id, event_type, scheduled_time,
         actual_time, detention_minutes, on_time, location_city, location_state)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- safety_incidents -------------------------------------------------------
def load_safety_incidents_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    out = pd.DataFrame({
        "incident_id": df["incident_id"],
        "trip_id": df["trip_id"],
        "truck_id": df["truck_id"],
        "driver_id": df["driver_id"],
        "incident_date": pd.to_datetime(df["incident_date"], errors="coerce"),
        "incident_type": df["incident_type"],
        "location_city": df["location_city"],
        "location_state": df["location_state"],
        "at_fault_flag": _bool(df["at_fault_flag"]),
        "injury_flag": _bool(df["injury_flag"]),
        "description": df["description"],
        "vehicle_damage_cost_eur": (pd.to_numeric(df["vehicle_damage_cost"], errors="coerce") * USD_TO_EUR).round(2),
        "cargo_damage_cost_eur": (pd.to_numeric(df["cargo_damage_cost"], errors="coerce") * USD_TO_EUR).round(2),
        "claim_amount_eur": (pd.to_numeric(df["claim_amount"], errors="coerce") * USD_TO_EUR).round(2),
        "preventable_flag": _bool(df["preventable_flag"]),
    })

    out = _to_none(out)
    data = list(out.itertuples(index=False, name=None))

    query = """
        INSERT INTO safety_incidents
        (incident_id, trip_id, truck_id, driver_id, incident_date, incident_type,
         location_city, location_state, at_fault_flag, injury_flag, description,
         vehicle_damage_cost_eur, cargo_damage_cost_eur, claim_amount_eur, preventable_flag)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount


# --- driver_monthly_metrics -------------------------------------------------
def load_driver_monthly_metrics_csv(csv_path: str, cursor) -> int:
    df = pd.read_csv(csv_path, dtype=str)

    out = pd.DataFrame({
        "driver_id": df["driver_id"],
        "mese": pd.to_datetime(df["month"], errors="coerce").dt.date,
        "tot_km": (pd.to_numeric(df["total_miles"], errors="coerce") * MILES_TO_KM).round(2),
        "tot_trips": pd.to_numeric(df["trips_completed"], errors="coerce").astype("Int64"),
        "consumo_medio_l_100km": (MPG_TO_L_100KM / pd.to_numeric(df["average_mpg"], errors="coerce")).round(2),
        "tot_carburante_litri": (pd.to_numeric(df["total_fuel_gallons"], errors="coerce") * GALLONS_TO_LITERS).round(2),
        "total_revenue_eur": (pd.to_numeric(df["total_revenue"], errors="coerce") * USD_TO_EUR).round(2),
        "percentuale_puntualita": (pd.to_numeric(df["on_time_delivery_rate"], errors="coerce") * 100).round(2),
        "tempo_inattivita_medio_h": pd.to_numeric(df["average_idle_hours"], errors="coerce").round(2),
    })

    out = _to_none(out)
    data = list(out.itertuples(index=False, name=None))

    query = """
        INSERT INTO driver_monthly_metrics
        (driver_id, mese, tot_km, tot_trips, consumo_medio_l_100km,
         tot_carburante_litri, total_revenue_eur, percentuale_puntualita,
         tempo_inattivita_medio_h)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(query, data)
    return cursor.rowcount