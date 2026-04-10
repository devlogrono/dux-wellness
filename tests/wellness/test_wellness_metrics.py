import sys
import os
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.db.db_players import load_players_db
from modules.db.db_records import get_records_db
from modules.reports.wellness_processing import prepare_players, prepare_wellness_dataset
from modules.reports.wellness_metrics import (
    compute_team_wellness_kpis,
    build_team_daily_wellness,
    build_team_weekly_wellness,
    build_team_monthly_wellness,
    build_wellness_by_tipo_carga,
)

st.session_state["auth"] = {"rol": "admin", "name": "Javier"}

df_players = prepare_players(load_players_db())
df_wellness = prepare_wellness_dataset(get_records_db(), df_players)

print(compute_team_wellness_kpis(df_wellness))
print(build_team_daily_wellness(df_wellness).head())
print(build_team_weekly_wellness(df_wellness).head())
print(build_team_monthly_wellness(df_wellness).head())
print(build_wellness_by_tipo_carga(df_wellness).head())