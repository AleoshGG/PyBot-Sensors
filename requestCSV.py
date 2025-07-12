import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("URL_POSTGRES"))

# Carga la consulta en un DataFrame
df = pd.read_sql("""
    SELECT period_id, weight, hour_period
    FROM weight_data
    WHERE weight > %s
""", conn, params=(100,))

# Guarda a CSV (sin índice)
df.to_csv('data.csv', index=False)

conn.close()
