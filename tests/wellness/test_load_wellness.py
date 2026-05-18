import sys
import os
import streamlit as st
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.db.db_players import load_players_db
from modules.db.db_records import get_records_db
from modules.reports.wellness_processing import prepare_players, prepare_wellness_dataset

st.session_state["auth"] = {
    "rol": "admin",
    "name": "Javier"
}

df_players = load_players_db()
df_players = prepare_players(df_players)

df_wellness = get_records_db()
df_wellness_clean = prepare_wellness_dataset(df_wellness, df_players)

print("TEST prepare_wellness_dataset")
print("-" * 40)

print("Shape:", df_wellness_clean.shape)
print("\nColumnas:")
print(df_wellness_clean.columns.tolist())

print("\nPrimeras filas:")
pd.set_option("display.max_columns", None)
print(df_wellness_clean.head())

print("\nTipos:")
print(df_wellness_clean.dtypes)