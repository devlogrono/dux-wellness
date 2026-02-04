
import streamlit as st
import modules.app_config.config as config

from modules.i18n.i18n import t

config.init_config()

from modules.ui.ui_components import selection_header
from modules.reports.ui_grupal import group_dashboard, metricas_grupal
from modules.db.db_records import get_records_db
from modules.db.db_players import load_players_db
from modules.db.db_competitions import load_competitions_db

st.header(t("Análisis :red[grupal]"), divider="red")

# Load reference data
jug_df = load_players_db()
comp_df = load_competitions_db()
wellness_df = get_records_db()

df, jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, wellness_df, modo="reporte_grupal")

metricas_grupal(df, jugadora, turno, start, end)
#st.dataframe(df, hide_index=True)
group_dashboard(df)
