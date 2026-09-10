"""
Creazione e popolamento della collection "digital_twin" su MongoDB Atlas
=========================================================================

A differenza della tabella `digital_twin` creata in MySQL (creazione_db_v3.py),
qui sfruttiamo il modello a documenti di MongoDB: ogni camion ha UN documento
che contiene sia le metriche aggregate (equivalenti alle colonne della tabella
SQL) sia lo STORICO incorporato (embedded) di utilizzo mensile e manutenzioni.

In MySQL, per ricostruire lo storico di un camion servono JOIN su piu' tabelle
(truck_utilization_metrics, maintenance_records...). In MongoDB, una singola
query (find_one) restituisce il "gemello digitale" completo del camion, con
tutta la sua storia incorporata. E' proprio questo il vantaggio del modello
NoSQL in un caso d'uso come il "digital twin".

Fonte dati: i CSV originali del Dataset.zip (trucks, trips, maintenance_records,
truck_utilization_metrics). Le metriche sono ricalcolate qui con Pandas, non
copiate dalla tabella MySQL: questo script puo' quindi girare in autonomia,
indipendentemente da popola_database.py.

Prerequisiti:
    pip install pymongo pandas python-dotenv

Configurazione connessione:
    Imposta la variabile d'ambiente MONGO_URI (consigliato, vedi .env.example)
    oppure sostituisci direttamente MONGO_URI_DEFAULT qui sotto SOLO in locale,
    MAI committare credenziali reali su GitHub (nemmeno per un progetto scolastico).
"""

import os
from datetime import datetime, timezone

import pandas as pd
from pymongo import MongoClient, UpdateOne

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv e' opzionale: se non c'e', si usa solo os.environ
from pymongo import MongoClient
from pprint import pprint

client = MongoClient(os.environ["MONGO_URI"])



# --------------------------------------------------------------------------
# CONFIGURAZIONE
# --------------------------------------------------------------------------

CARTELLA_DATASET = "Dataset"  # cartella dove hai estratto Dataset.zip

MONGO_URI_DEFAULT = "INSERISCI_QUI_LA_TUA_CONNECTION_STRING"
MONGO_URI = os.environ.get("MONGO_URI", MONGO_URI_DEFAULT)

NOME_DATABASE = "GreenLog"
NOME_COLLECTION = "digital_twin"

# Fattori di conversione (dataset originale in unita' imperiali/USD)
MIGLIA_TO_KM = 1.60934
GALLONI_TO_LITRI = 3.78541
FATTORE_CO2_DIESEL_KG_PER_LITRO = 2.68  # kg di CO2 per litro di gasolio (fattore standard EU)
TASSO_CAMBIO_USD_EUR = 1.0  # cambia questo valore se nel tuo popola_database.py usi un tasso diverso


# --------------------------------------------------------------------------
# CARICAMENTO DATI
# --------------------------------------------------------------------------

def carica_dati(cartella):
    trucks = pd.read_csv(os.path.join(cartella, "trucks.csv"))
    trips = pd.read_csv(os.path.join(cartella, "trips.csv"))
    maintenance = pd.read_csv(os.path.join(cartella, "maintenance_records.csv"), parse_dates=["maintenance_date"])
    utilization = pd.read_csv(os.path.join(cartella, "truck_utilization_metrics.csv"), parse_dates=["month"])
    print(f"Caricati: {len(trucks)} trucks, {len(trips)} trips, "
          f"{len(maintenance)} interventi manutenzione, {len(utilization)} righe utilizzo mensile")
    return trucks, trips, maintenance, utilization


# --------------------------------------------------------------------------
# CALCOLO METRICHE AGGREGATE PER CAMION
# --------------------------------------------------------------------------

def calcola_metriche_aggregate(trucks, trips, maintenance, utilization):
    # alcuni trip non hanno truck_id valorizzato: li escludiamo dall'aggregazione
    trips_validi = trips.dropna(subset=["truck_id"])

    agg_viaggi = trips_validi.groupby("truck_id").agg(
        tot_miglia=("actual_distance_miles", "sum"),
        tot_galloni=("fuel_gallons_used", "sum"),
        numero_viaggi_totali=("trip_id", "count"),
    ).reset_index()
    agg_viaggi["tot_km"] = agg_viaggi["tot_miglia"] * MIGLIA_TO_KM
    agg_viaggi["tot_litri"] = agg_viaggi["tot_galloni"] * GALLONI_TO_LITRI
    agg_viaggi["consumo_medio_l_100km"] = (
        agg_viaggi["tot_litri"] / agg_viaggi["tot_km"] * 100
    )
    agg_viaggi["tot_CO2_kg"] = agg_viaggi["tot_litri"] * FATTORE_CO2_DIESEL_KG_PER_LITRO

    agg_manutenzione = maintenance.groupby("truck_id").agg(
        costo_manutenzione_tot_eur=("total_cost", "sum"),
        ore_fermo_tot=("downtime_hours", "sum"),
        numero_interventi=("maintenance_id", "count"),
    ).reset_index()
    agg_manutenzione["costo_manutenzione_tot_eur"] *= TASSO_CAMBIO_USD_EUR

    agg_utilizzo = utilization.groupby("truck_id").agg(
        percentuale_utilizzo_media=("utilization_rate", "mean"),
    ).reset_index()

    df = (
        trucks[["truck_id"]]
        .merge(agg_viaggi, on="truck_id", how="left")
        .merge(agg_manutenzione, on="truck_id", how="left")
        .merge(agg_utilizzo, on="truck_id", how="left")
    )

    # punteggio_eco (0-100, piu' alto = piu' efficiente): normalizzazione
    # min-max del consumo medio sull'intera flotta (consumo piu' basso -> punteggio piu' alto)
    c_min, c_max = df["consumo_medio_l_100km"].min(), df["consumo_medio_l_100km"].max()
    df["punteggio_eco"] = (
        100 * (1 - (df["consumo_medio_l_100km"] - c_min) / (c_max - c_min))
    ).round(2)

    # indice_manutenzione (0-100, piu' alto = meno problemi): normalizzazione
    # min-max del costo di manutenzione per km percorso
    df["costo_manutenzione_per_km"] = df["costo_manutenzione_tot_eur"] / df["tot_km"]
    m_min, m_max = df["costo_manutenzione_per_km"].min(), df["costo_manutenzione_per_km"].max()
    df["indice_manutenzione"] = (
        100 * (1 - (df["costo_manutenzione_per_km"] - m_min) / (m_max - m_min))
    ).round(2)

    # percentuale_utilizzo: i camion senza record mensili (status Maintenance/Inactive)
    # restano NaN -> diventeranno null nel documento Mongo
    df["percentuale_utilizzo"] = (df["percentuale_utilizzo_media"] * 100).round(2)

    df["tot_km"] = df["tot_km"].round(2)
    df["consumo_medio_l_100km"] = df["consumo_medio_l_100km"].round(2)
    df["tot_CO2_kg"] = df["tot_CO2_kg"].round(2)

    return df


# --------------------------------------------------------------------------
# COSTRUZIONE DOCUMENTI (con storico incorporato)
# --------------------------------------------------------------------------

def _valore_o_none(v):
    """Converte NaN/NaT in None cosi' Mongo salva un null invece di 'NaN' (non valido in JSON)."""
    if pd.isna(v):
        return None
    return v


def costruisci_documenti(trucks, metriche, maintenance, utilization):
    documenti = []
    adesso = datetime.now(timezone.utc)

    for _, riga_truck in trucks.iterrows():
        truck_id = riga_truck["truck_id"]
        riga_metriche = metriche.loc[metriche["truck_id"] == truck_id]
        m = riga_metriche.iloc[0] if not riga_metriche.empty else None

        # storico manutenzioni del camion, dal piu' recente al piu' vecchio
        storico_manutenzioni = []
        for _, r in maintenance[maintenance["truck_id"] == truck_id].sort_values(
            "maintenance_date", ascending=False
        ).iterrows():
            storico_manutenzioni.append({
                "maintenance_id": r["maintenance_id"],
                "data": r["maintenance_date"],
                "tipo": r["maintenance_type"],
                "odometro_km": round(r["odometer_reading"] * MIGLIA_TO_KM, 2),
                "ore_fermo": _valore_o_none(r["downtime_hours"]),
                "costo_totale_eur": round(r["total_cost"] * TASSO_CAMBIO_USD_EUR, 2),
                "descrizione": r["service_description"],
            })

        # storico utilizzo mensile del camion, in ordine cronologico
        storico_utilizzo = []
        for _, r in utilization[utilization["truck_id"] == truck_id].sort_values("month").iterrows():
            storico_utilizzo.append({
                "mese": r["month"],
                "viaggi_completati": int(r["trips_completed"]),
                "km_totali": round(r["total_miles"] * MIGLIA_TO_KM, 2),
                "ricavo_totale_eur": round(r["total_revenue"] * TASSO_CAMBIO_USD_EUR, 2),
                "consumo_medio_mpg": _valore_o_none(r["average_mpg"]),
                "eventi_manutenzione": int(r["maintenance_events"]),
                "costo_manutenzione_eur": round(r["maintenance_cost"] * TASSO_CAMBIO_USD_EUR, 2),
                "ore_fermo": _valore_o_none(r["downtime_hours"]),
                "percentuale_utilizzo": round(r["utilization_rate"] * 100, 2),
            })

        documento = {
            "_id": truck_id,
            "truck_id": truck_id,
            "anagrafica": {
                "unit_number": riga_truck["unit_number"],
                "make": riga_truck["make"],
                "model_year": int(riga_truck["model_year"]),
                "vin": riga_truck["vin"],
                "fuel_type": riga_truck["fuel_type"],
                "status": riga_truck["status"],
                "home_terminal": riga_truck["home_terminal"],
            },
            "metriche_aggregate": {
                "tot_km": _valore_o_none(m["tot_km"]) if m is not None else None,
                "consumo_medio_l_100km": _valore_o_none(m["consumo_medio_l_100km"]) if m is not None else None,
                "tot_CO2_kg": _valore_o_none(m["tot_CO2_kg"]) if m is not None else None,
                "punteggio_eco": _valore_o_none(m["punteggio_eco"]) if m is not None else None,
                "percentuale_utilizzo": _valore_o_none(m["percentuale_utilizzo"]) if m is not None else None,
                "indice_manutenzione": _valore_o_none(m["indice_manutenzione"]) if m is not None else None,
                "numero_viaggi_totali": int(m["numero_viaggi_totali"]) if m is not None and not pd.isna(m["numero_viaggi_totali"]) else 0,
                "ultimo_aggiornamento": adesso,
            },
            "storico_utilizzo_mensile": storico_utilizzo,
            "storico_manutenzioni": storico_manutenzioni,
        }
        documenti.append(documento)

    return documenti


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------

def main():
    if MONGO_URI == MONGO_URI_DEFAULT:
        raise SystemExit(
            "Devi impostare la connection string di MongoDB Atlas.\n"
            "Consigliato: crea un file .env con MONGO_URI=mongodb+srv://... "
            "(vedi .env.example), oppure esporta la variabile d'ambiente MONGO_URI."
        )

    trucks, trips, maintenance, utilization = carica_dati(CARTELLA_DATASET)

    print("Calcolo metriche aggregate per camion...")
    metriche = calcola_metriche_aggregate(trucks, trips, maintenance, utilization)

    print("Costruzione documenti digital twin (con storico incorporato)...")
    documenti = costruisci_documenti(trucks, metriche, maintenance, utilization)

    print(f"Connessione a MongoDB Atlas (database '{NOME_DATABASE}')...")
    client = MongoClient(MONGO_URI)
    # verifica subito che la connessione funzioni, invece di scoprirlo al primo insert
    client.admin.command("ping")
    print("Connesso a MongoDB Atlas")

    db = client[NOME_DATABASE]
    collection = db[NOME_COLLECTION]

    print(f"Svuoto la collection '{NOME_COLLECTION}' (se esiste)...")
    collection.drop()

    print(f"Inserisco {len(documenti)} documenti...")
    collection.insert_many(documenti)

    collection.create_index("anagrafica.status")

    print(f"Fatto: {collection.count_documents({})} digital twin creati in '{NOME_DATABASE}.{NOME_COLLECTION}'")
    client.close()


if __name__ == "__main__":
    main()
