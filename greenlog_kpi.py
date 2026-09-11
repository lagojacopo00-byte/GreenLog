"""
GreenLog - KPI flotta
======================
Crea (o aggiorna) le view MySQL corrispondenti ai KPI della dashboard,
e fornisce funzioni pronte per interrogarle come DataFrame pandas.
Pensato per essere importato dalla dashboard interattiva (Streamlit/Dash/ecc.)
nel prossimo step del progetto.

Setup:
    pip install mysql-connector-python pandas python-dotenv
    crea un file .env nella stessa cartella (vedi .env.example)
"""

import os

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "ssl_disabled": False,  # Aiven richiede SSL
}


def get_connection():
    """Apre una nuova connessione al database MySQL (Aiven)."""
    return mysql.connector.connect(**DB_CONFIG)


# ---------------------------------------------------------------------------
# DEFINIZIONE DELLE VIEW
# Ogni view corrisponde a uno dei KPI della dashboard (vedi spiegazione
# della logica di ognuna nella chat / nel README del progetto).
# ---------------------------------------------------------------------------

VIEWS = {
    # 1. Mezzi che consumano più del previsto (confronto con la media della marca)
    "vw_consumo_previsto": """
        CREATE OR REPLACE VIEW vw_consumo_previsto AS
        SELECT
            t.truck_id, t.make,
            tr.consumo_reale,
            peer.consumo_medio_marca AS previsto,
            ROUND(tr.consumo_reale - peer.consumo_medio_marca, 2) AS scostamento_assoluto,
            ROUND((tr.consumo_reale - peer.consumo_medio_marca) / peer.consumo_medio_marca * 100, 1) AS scostamento_pct
        FROM trucks t
        JOIN (
            SELECT truck_id, SUM(consumo_litro) / SUM(distanza_km) * 100 AS consumo_reale
            FROM trips
            WHERE distanza_km > 0
            GROUP BY truck_id
        ) tr ON tr.truck_id = t.truck_id
        JOIN (
            SELECT t2.make, SUM(tr2.consumo_litro) / SUM(tr2.distanza_km) * 100 AS consumo_medio_marca
            FROM trucks t2
            JOIN trips tr2 ON tr2.truck_id = t2.truck_id
            WHERE tr2.distanza_km > 0
            GROUP BY t2.make
        ) peer ON peer.make = t.make
    """,
    # 2. Dove perdiamo efficienza (utilizzo e fermo mezzi)
    "vw_efficienza_flotta": """
        CREATE OR REPLACE VIEW vw_efficienza_flotta AS
        SELECT
            truck_id,
            ROUND(AVG(utilization_rate_pct), 1) AS utilizzo_medio_pct,
            SUM(downtime_hours) AS ore_fermo_totali,
            SUM(maintenance_cost_eur) AS costo_manutenzione_totale
        FROM truck_utilization_metrics
        GROUP BY truck_id
    """,
    # 3. Quali interventi genererebbero il maggior risparmio (costo/km per mezzo)
    "vw_priorita_interventi": """
        CREATE OR REPLACE VIEW vw_priorita_interventi AS
        SELECT
            t.truck_id, t.make, t.status,
            COALESCE(f.costo_carburante, 0) AS costo_carburante,
            COALESCE(m.costo_manutenzione, 0) AS costo_manutenzione,
            COALESCE(tk.km_totali, 0) AS km_totali,
            ROUND(
                (COALESCE(f.costo_carburante, 0) + COALESCE(m.costo_manutenzione, 0))
                / NULLIF(tk.km_totali, 0), 3
            ) AS costo_per_km
        FROM trucks t
        LEFT JOIN (
            SELECT truck_id, SUM(costo_totale_eur) AS costo_carburante
            FROM fuel_purchases GROUP BY truck_id
        ) f ON f.truck_id = t.truck_id
        LEFT JOIN (
            SELECT truck_id, SUM(total_cost_eur) AS costo_manutenzione
            FROM maintenance_records GROUP BY truck_id
        ) m ON m.truck_id = t.truck_id
        LEFT JOIN (
            SELECT truck_id, SUM(distanza_km) AS km_totali
            FROM trips GROUP BY truck_id
        ) tk ON tk.truck_id = t.truck_id
    """,
    # Extra - stato attuale della flotta (quanti mezzi attivi / in manutenzione / inattivi)
    "vw_stato_flotta": """
        CREATE OR REPLACE VIEW vw_stato_flotta AS
        SELECT
            status,
            COUNT(*) AS numero_mezzi,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM trucks), 1) AS pct_flotta
        FROM trucks
        GROUP BY status
    """,
    # 4. Quanto risparmieremmo (litri / euro / CO2) ottimizzando i mezzi sopra la media marca
    "vw_risparmio_potenziale": """
        CREATE OR REPLACE VIEW vw_risparmio_potenziale AS
        WITH consumo_mezzi AS (
            SELECT
                t.truck_id, t.make,
                SUM(tr.consumo_litro) AS litri_totali,
                SUM(tr.distanza_km) AS km_totali,
                SUM(tr.consumo_litro) / NULLIF(SUM(tr.distanza_km), 0) * 100 AS consumo_reale
            FROM trucks t
            JOIN trips tr ON tr.truck_id = t.truck_id
            GROUP BY t.truck_id, t.make
        ),
        benchmark_marca AS (
            SELECT make, AVG(consumo_reale) AS consumo_medio_marca
            FROM consumo_mezzi
            GROUP BY make
        ),
        prezzo_medio AS (
            SELECT AVG(prezzo_litro_eur) AS p FROM fuel_purchases
        )
        SELECT
            ROUND(SUM(GREATEST(cm.consumo_reale - bm.consumo_medio_marca, 0) / 100 * cm.km_totali), 0) AS litri_risparmiabili,
            ROUND(SUM(GREATEST(cm.consumo_reale - bm.consumo_medio_marca, 0) / 100 * cm.km_totali) * (SELECT p FROM prezzo_medio), 0) AS risparmio_eur_stimato,
            ROUND(SUM(GREATEST(cm.consumo_reale - bm.consumo_medio_marca, 0) / 100 * cm.km_totali) * 2.68, 0) AS co2_risparmiabile_kg
        FROM consumo_mezzi cm
        JOIN benchmark_marca bm ON bm.make = cm.make
    """,
    # 6. Puntualità delle consegne per facility
    "vw_puntualita_consegne": """
        CREATE OR REPLACE VIEW vw_puntualita_consegne AS
        SELECT
            facility_id,
            ROUND(AVG(on_time) * 100, 1) AS pct_puntualita,
            ROUND(AVG(detention_minutes), 1) AS minuti_attesa_medi,
            COUNT(*) AS eventi
        FROM delivery_events
        GROUP BY facility_id
    """,
    # 7. Redditività per cliente (ricavo vs potenziale)
    "vw_redditivita_cliente": """
        CREATE OR REPLACE VIEW vw_redditivita_cliente AS
        SELECT
            c.customer_id, c.customer_name,
            c.annual_revenue_potential_eur AS potenziale_annuo,
            SUM(l.ricavo_eur) AS ricavo_effettivo,
            ROUND(SUM(l.ricavo_eur) / NULLIF(c.annual_revenue_potential_eur, 0) * 100, 1) AS pct_del_potenziale,
            COUNT(l.load_id) AS numero_carichi
        FROM customers c
        LEFT JOIN loads l ON l.customer_id = c.customer_id
        GROUP BY c.customer_id, c.customer_name, c.annual_revenue_potential_eur
    """,
}


# NB: il KPI 5 (baseline prima/dopo un intervento) non è una view fissa perché
# richiede due parametri scelti di volta in volta (truck_id + data) -> resta
# una funzione parametrica, vedi get_baseline_confronto() più sotto.


def create_views() -> None:
    """Crea (o aggiorna, se già esistono) tutte le view nel database."""
    conn = get_connection()
    cur = conn.cursor()
    for nome, sql in VIEWS.items():
        cur.execute(sql)
        print(f"View creata/aggiornata: {nome}")
    conn.commit()
    cur.close()
    conn.close()


def query_view(view_name: str) -> pd.DataFrame:
    """Legge una view e la ritorna come DataFrame pandas."""
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {view_name}", conn)
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Funzioni pronte per ogni KPI - da richiamare dalla dashboard
# ---------------------------------------------------------------------------

def get_consumo_previsto() -> pd.DataFrame:
    """KPI 1 - Quali mezzi consumano più del previsto."""
    return query_view("vw_consumo_previsto")


def get_efficienza_flotta() -> pd.DataFrame:
    """KPI 2 - Dove perdiamo efficienza."""
    return query_view("vw_efficienza_flotta")


def get_priorita_interventi(solo_attivi: bool = True) -> pd.DataFrame:
    """
    KPI 3 - Quali interventi genererebbero il maggior risparmio.

    solo_attivi=True (default) esclude i mezzi non operativi (Maintenance/Inactive),
    che non hanno viaggi e quindi costo_per_km = NaN. Metti False per vederli tutti.
    """
    df = query_view("vw_priorita_interventi")
    if solo_attivi:
        df = df[df["status"] == "Active"]
    return df


def get_stato_flotta() -> pd.DataFrame:
    """Extra - quanti mezzi sono Active / Maintenance / Inactive in questo momento."""
    return query_view("vw_stato_flotta")


def get_risparmio_potenziale() -> pd.DataFrame:
    """KPI 4 - Quanto potremmo ridurre costi ed emissioni ottimizzando la flotta."""
    return query_view("vw_risparmio_potenziale")


def get_puntualita_consegne() -> pd.DataFrame:
    """KPI 6 - Puntualità delle consegne."""
    return query_view("vw_puntualita_consegne")


def get_redditivita_cliente() -> pd.DataFrame:
    """KPI 7 - Redditività per cliente."""
    return query_view("vw_redditivita_cliente")


def get_baseline_confronto(truck_id: str, data_intervento: str) -> pd.DataFrame:
    """
    KPI 5 - Come misuriamo oggettivamente i benefici di un investimento.
    Confronta le metriche di un mezzo prima/dopo una data di intervento.

    truck_id: es. 'TRK00001'
    data_intervento: formato 'YYYY-MM-DD' (es. la data presa da maintenance_records)
    """
    query = """
        SELECT
            CASE WHEN month < %s THEN 'prima' ELSE 'dopo' END AS periodo,
            ROUND(AVG(average_l_100km), 2) AS consumo_medio,
            ROUND(AVG(utilization_rate_pct), 1) AS utilizzo_medio,
            SUM(downtime_hours) AS ore_fermo_totali
        FROM truck_utilization_metrics
        WHERE truck_id = %s
        GROUP BY periodo
    """
    conn = get_connection()
    df = pd.read_sql(query, conn, params=(data_intervento, truck_id))
    conn.close()
    return df


if __name__ == "__main__":
    create_views()

    print("\n--- 1. Consumo previsto ---")
    print(get_consumo_previsto().head())

    print("\n--- 2. Efficienza flotta ---")
    print(get_efficienza_flotta().head())

    print("\n--- Stato flotta ---")
    print(get_stato_flotta())

    print("\n--- 3. Priorità interventi (solo mezzi attivi) ---")
    print(get_priorita_interventi().head())

    print("\n--- 4. Risparmio potenziale ---")
    print(get_risparmio_potenziale())

    print("\n--- 6. Puntualità consegne ---")
    print(get_puntualita_consegne().head())

    print("\n--- 7. Redditività cliente ---")
    print(get_redditivita_cliente().head())