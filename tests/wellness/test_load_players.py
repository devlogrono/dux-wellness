import sys
import os
import streamlit as st
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.db.db_players import load_players_db
from modules.db.db_records import get_records_db

df = load_players_db()

print("TEST load_players_db")
print("-" * 40)

if df is None or df.empty:
    print("DataFrame vacío o None")
else:
    print("Shape:", df.shape)
    print("\nColumnas:")
    print(df.columns.tolist())
    print("\nPrimeras filas:")
    print(df.head())

st.session_state["auth"] = {
    "rol": "admin",
    "name": "Javier"
}

df_wellness = get_records_db()

print("TEST get_records_db")
print("-" * 40)

if df_wellness is None or df.empty:
    print("DataFrame vacío o None")
else:
    print("Shape:", df_wellness.shape)
    print("\nColumnas:")
    print(df_wellness.columns.tolist())
    print("\nPrimeras filas:")
    print(df_wellness.head())
    print("\nTipos:")
    print(df_wellness.dtypes)