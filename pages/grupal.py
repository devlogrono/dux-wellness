import streamlit as st
import src.app_config.config as config

from src.i18n.i18n import t

config.init_config()

from src.ui.ui_components import selection_header
from src.reports.ui_grupal import group_dashboard
from src.db.db_records import get_records_db, load_jugadoras_db, load_competiciones_db

st.header(t("Análisis :red[grupal]"), divider="red")

# Load reference data
jug_df = load_jugadoras_db()
comp_df = load_competiciones_db()
wellness_df = get_records_db()

#st.dataframe(wellness_df, hide_index=True)    

df, jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, wellness_df, modo="reporte_grupal")

#st.dataframe(df, hide_index=True)
group_dashboard(df)
