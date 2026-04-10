from __future__ import annotations

import pandas as pd


def compute_team_wellness_kpis(df: pd.DataFrame) -> dict:
    """
    Calcula KPIs globales del equipo a partir del dataset de wellness ya preparado.
    """
    if df is None or df.empty:
        return {
            "energia_media": None,
            "recuperacion_media": None,
            "sueno_medio": None,
            "stress_medio": None,
            "dolor_medio": None,
            "rpe_medio": None,
            "ua_total": None,
            "n_registros": 0,
            "n_jugadoras": 0,
            "pct_dolor_3omas": None,
        }

    dolor_mask = df["dolor"] >= 3 if "dolor" in df.columns else pd.Series(dtype=bool)

    return {
        "energia_media": round(df["energia"].mean(), 2) if "energia" in df.columns else None,
        "recuperacion_media": round(df["recuperacion"].mean(), 2) if "recuperacion" in df.columns else None,
        "sueno_medio": round(df["sueno"].mean(), 2) if "sueno" in df.columns else None,
        "stress_medio": round(df["stress"].mean(), 2) if "stress" in df.columns else None,
        "dolor_medio": round(df["dolor"].mean(), 2) if "dolor" in df.columns else None,
        "rpe_medio": round(df["rpe"].mean(), 2) if "rpe" in df.columns else None,
        "ua_total": round(df["ua"].sum(), 2) if "ua" in df.columns else None,
        "n_registros": int(len(df)),
        "n_jugadoras": int(df["id_jugadora"].nunique()) if "id_jugadora" in df.columns else 0,
        "pct_dolor_3omas": round(dolor_mask.mean() * 100, 2) if "dolor" in df.columns and len(df) > 0 else None,
    }




def build_team_daily_wellness(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "fecha_sesion" not in df.columns:
        return pd.DataFrame()

    out = df.copy()
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce")
    out = out.dropna(subset=["fecha_sesion"])

    cols = ["energia", "recuperacion", "sueno", "stress", "dolor", "rpe", "ua"]
    cols = [c for c in cols if c in out.columns]

    if not cols:
        return pd.DataFrame()

    return (
        out.groupby("fecha_sesion", as_index=False)[cols]
        .mean(numeric_only=True)
        .sort_values("fecha_sesion")
    )


def build_team_weekly_wellness(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "fecha_sesion" not in df.columns:
        return pd.DataFrame()

    out = df.copy()
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce")
    out = out.dropna(subset=["fecha_sesion"])

    out["semana"] = out["fecha_sesion"].dt.to_period("W").astype(str)

    cols = ["energia", "recuperacion", "sueno", "stress", "dolor", "rpe", "ua"]
    cols = [c for c in cols if c in out.columns]

    if not cols:
        return pd.DataFrame()

    return (
        out.groupby("semana", as_index=False)[cols]
        .mean(numeric_only=True)
    )


def build_team_monthly_wellness(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "fecha_sesion" not in df.columns:
        return pd.DataFrame()

    out = df.copy()
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce")
    out = out.dropna(subset=["fecha_sesion"])

    out["mes"] = out["fecha_sesion"].dt.to_period("M").astype(str)

    cols = ["energia", "recuperacion", "sueno", "stress", "dolor", "rpe", "ua"]
    cols = [c for c in cols if c in out.columns]

    if not cols:
        return pd.DataFrame()

    return (
        out.groupby("mes", as_index=False)[cols]
        .mean(numeric_only=True)
    )


def build_wellness_by_tipo_carga(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega wellness medio según tipo de carga.
    """
    if df is None or df.empty or "tipo_carga" not in df.columns:
        return pd.DataFrame()

    cols = ["energia", "recuperacion", "sueno", "stress", "dolor", "rpe", "ua"]
    cols = [c for c in cols if c in df.columns]

    if not cols:
        return pd.DataFrame()

    return (
        df.groupby("tipo_carga", as_index=False)[cols]
        .mean(numeric_only=True)
        .sort_values("energia", ascending=False) if "energia" in cols
        else df.groupby("tipo_carga", as_index=False)[cols].mean(numeric_only=True)
    )


def compute_player_wellness_kpis(df: pd.DataFrame) -> dict:
    """
    Calcula KPIs de wellness para una jugadora ya filtrada.
    """

    if df is None or df.empty:
        return {
            "energia_media": None,
            "recuperacion_media": None,
            "sueno_medio": None,
            "stress_medio": None,
            "dolor_medio": None,
            "dolor_max": None,
            "rpe_medio": None,
            "ua_total": None,
            "n_registros": 0,
            "pct_dolor_3omas": None,
        }

    out = df.copy()

    columnas_numericas = [
        "energia",
        "recuperacion",
        "sueno",
        "stress",
        "dolor",
        "rpe",
        "ua",
    ]
    for col in columnas_numericas:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    dolor_mask = out["dolor"] >= 3 if "dolor" in out.columns else pd.Series(dtype=bool)

    return {
        "energia_media": round(out["energia"].mean(), 2) if "energia" in out.columns else None,
        "recuperacion_media": round(out["recuperacion"].mean(), 2) if "recuperacion" in out.columns else None,
        "sueno_medio": round(out["sueno"].mean(), 2) if "sueno" in out.columns else None,
        "stress_medio": round(out["stress"].mean(), 2) if "stress" in out.columns else None,
        "dolor_medio": round(out["dolor"].mean(), 2) if "dolor" in out.columns else None,
        "dolor_max": round(out["dolor"].max(), 2) if "dolor" in out.columns else None,
        "rpe_medio": round(out["rpe"].mean(), 2) if "rpe" in out.columns else None,
        "ua_total": round(out["ua"].sum(), 2) if "ua" in out.columns else None,
        "n_registros": int(len(out)),
        "pct_dolor_3omas": round(dolor_mask.mean() * 100, 2) if "dolor" in out.columns and len(out) > 0 else None,
    }

def build_player_daily_wellness(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega el wellness diario de una jugadora.
    Espera un DataFrame ya filtrado para una sola jugadora.
    """

    if df is None or df.empty or "fecha_sesion" not in df.columns:
        return pd.DataFrame()

    out = df.copy()
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce")
    out = out.dropna(subset=["fecha_sesion"])

    cols = ["energia", "recuperacion", "sueno", "stress", "dolor", "rpe", "ua"]
    cols = [c for c in cols if c in out.columns]

    if not cols:
        return pd.DataFrame()

    for col in cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return (
        out.groupby("fecha_sesion", as_index=False)[cols]
        .mean(numeric_only=True)
        .sort_values("fecha_sesion")
    )


## individual
def compute_player_wellness_summary(df: pd.DataFrame) -> dict:
    """
    Calcula un resumen ejecutivo de wellness para una jugadora.
    Escala base: 1 = mejor, 5 = peor
    Escala visual: wellness_score_25 invertida, donde 25 = mejor
    """

    if df is None or df.empty:
        return {
            "prom_w_1_5": None,
            "wellness_score_25": None,
            "rpe_prom": None,
            "ua_total": None,
            "dolor_mean": None,
            "dolor_max": None,
            "energia_mean": None,
            "stress_mean": None,
            "riesgo_actual": None,
            "riesgo_label": "Sin datos",
        }

    out = df.copy()

    cols = ["recuperacion", "energia", "sueno", "stress", "dolor", "rpe", "ua"]
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    wellness_cols = ["recuperacion", "energia", "sueno", "stress", "dolor"]
    wellness_cols = [c for c in wellness_cols if c in out.columns]

    prom_w_1_5 = round(out[wellness_cols].mean(axis=1, skipna=True).mean(), 2) if wellness_cols else None
    wellness_score_25 = round((6 - prom_w_1_5) * 5, 1) if prom_w_1_5 is not None and pd.notna(prom_w_1_5) else None

    rpe_prom = round(out["rpe"].mean(), 1) if "rpe" in out.columns else None
    ua_total = round(out["ua"].sum(), 1) if "ua" in out.columns else None
    dolor_mean = round(out["dolor"].mean(), 2) if "dolor" in out.columns else None
    dolor_max = round(out["dolor"].max(), 2) if "dolor" in out.columns else None
    energia_mean = round(out["energia"].mean(), 2) if "energia" in out.columns else None
    stress_mean = round(out["stress"].mean(), 2) if "stress" in out.columns else None

    # Riesgo coherente con tu lógica grupal
    if prom_w_1_5 is None or dolor_mean is None:
        riesgo_actual = None
        riesgo_label = "Sin datos"
    elif prom_w_1_5 > 3 or dolor_mean > 3:
        riesgo_actual = "alto"
        riesgo_label = "🔴 Alto"
    elif prom_w_1_5 >= 2.5 or dolor_mean >= 2.5:
        riesgo_actual = "moderado"
        riesgo_label = "🟠 Moderado"
    else:
        riesgo_actual = "bajo"
        riesgo_label = "🟢 Bajo"

    return {
        "prom_w_1_5": prom_w_1_5,
        "wellness_score_25": wellness_score_25,
        "rpe_prom": rpe_prom,
        "ua_total": ua_total,
        "dolor_mean": dolor_mean,
        "dolor_max": dolor_max,
        "energia_mean": energia_mean,
        "stress_mean": stress_mean,
        "riesgo_actual": riesgo_actual,
        "riesgo_label": riesgo_label,
    }

def _calc_delta(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    prev = values[-2]
    curr = values[-1]
    if prev in [0, None] or pd.isna(prev):
        return 0.0
    return round(((curr - prev) / prev) * 100, 1)


def _calc_trend_player(df: pd.DataFrame, by_col: str, target_col: str, agg: str = "mean") -> list[float]:
    if df.empty or by_col not in df.columns or target_col not in df.columns:
        return []

    if agg == "sum":
        g = df.groupby(by_col)[target_col].sum().reset_index(name="valor")
    else:
        g = df.groupby(by_col)[target_col].mean().reset_index(name="valor")

    return g.sort_values(by_col)["valor"].round(2).tolist()


def compute_player_wellness_cards(
    df: pd.DataFrame,
    periodo: str = "Mes",
) -> dict:
    """
    Calcula métricas para tarjetas-resumen de wellness individual,
    incluyendo valor actual, delta y mini serie para chart_data.

    IMPORTANTE:
    - El dataframe `df` ya debe venir filtrado por jugadora y rango de fechas.
    - El cálculo de wellness se hace a nivel diario para evitar sesgos
      cuando hay distinto número de registros por día.
    """

    if df is None or df.empty:
        return {
            "wellness_val": 0,
            "wellness_delta": 0.0,
            "wellness_chart": [0],
            "rpe_val": 0,
            "rpe_delta": 0.0,
            "rpe_chart": [0],
            "ua_val": 0,
            "ua_delta": 0.0,
            "ua_chart": [0],
            "riesgo_val": "Sin datos",
            "riesgo_delta": 0.0,
            "riesgo_chart": [0],
        }

    out = df.copy()
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce")
    out = out.dropna(subset=["fecha_sesion"]).sort_values("fecha_sesion")

    cols = ["recuperacion", "energia", "sueno", "stress", "dolor", "rpe", "ua"]
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    # -------------------------------------------------
    # 1) AGREGRACIÓN DIARIA
    # -------------------------------------------------
    cols_daily = [c for c in cols if c in out.columns]

    daily = (
        out.groupby("fecha_sesion", as_index=False)[cols_daily]
        .mean(numeric_only=True)
        .sort_values("fecha_sesion")
    )

    # Score de malestar general /25
    wellness_cols = ["recuperacion", "energia", "sueno", "stress", "dolor"]

    if all(c in daily.columns for c in wellness_cols):
        daily["prom_w_1_5"] = daily[wellness_cols].mean(axis=1, skipna=True)
        daily["wellness_score_25"] = (6 - daily["prom_w_1_5"]) * 5
    else:
        daily["wellness_score_25"] = pd.NA

    daily["semana"] = daily["fecha_sesion"].dt.to_period("W").astype(str)
    daily["mes"] = daily["fecha_sesion"].dt.to_period("M").astype(str)

    # -------------------------------------------------
    # 2) CÁLCULO SEGÚN PERIODO
    # -------------------------------------------------
    if periodo in ["Hoy", "Último día"]:
        # Usa el último día disponible del dataframe ya filtrado
        ultimo_dia = daily["fecha_sesion"].max()
        daily_last = daily[daily["fecha_sesion"] == ultimo_dia]

        wellness_val = round(daily_last["wellness_score_25"].mean(), 1) if "wellness_score_25" in daily_last.columns else 0
        wellness_chart = [wellness_val]
        wellness_delta = 0.0

        rpe_val = round(daily_last["rpe"].mean(), 1) if "rpe" in daily_last.columns else 0
        rpe_chart = [rpe_val]
        rpe_delta = 0.0

        ua_val = round(daily_last["ua"].sum(), 1) if "ua" in daily_last.columns else 0
        ua_chart = [ua_val]
        ua_delta = 0.0

    elif periodo == "Semana":
        wellness_chart = _calc_trend_player(daily, "semana", "wellness_score_25", agg="mean")
        wellness_val = round(wellness_chart[-1], 1) if wellness_chart else 0
        wellness_delta = _calc_delta(wellness_chart)

        rpe_chart = _calc_trend_player(daily, "semana", "rpe", agg="mean")
        rpe_val = round(rpe_chart[-1], 1) if rpe_chart else 0
        rpe_delta = _calc_delta(rpe_chart)

        ua_chart = _calc_trend_player(daily, "semana", "ua", agg="sum")
        ua_val = round(ua_chart[-1], 1) if ua_chart else 0
        ua_delta = _calc_delta(ua_chart)

    else:  # Mes
        wellness_chart = _calc_trend_player(daily, "mes", "wellness_score_25", agg="mean")
        wellness_val = round(wellness_chart[-1], 1) if wellness_chart else 0
        wellness_delta = _calc_delta(wellness_chart)

        rpe_chart = _calc_trend_player(daily, "mes", "rpe", agg="mean")
        rpe_val = round(rpe_chart[-1], 1) if rpe_chart else 0
        rpe_delta = _calc_delta(rpe_chart)

        ua_chart = _calc_trend_player(daily, "mes", "ua", agg="sum")
        ua_val = round(ua_chart[-1], 1) if ua_chart else 0
        ua_delta = _calc_delta(ua_chart)

    def _calc_riesgo_wellness(prom_w, dolor):
        if prom_w is None or pd.isna(prom_w) or dolor is None or pd.isna(dolor):
            return 0, "Sin datos"
        elif prom_w > 3 or dolor > 3:
            return 2, "🔴 Alto"
        elif prom_w >= 2.5 or dolor >= 2.5:
            return 1, "🟠 Moderado"
        else:
            return 0, "🟢 Bajo"

        # -------------------------------------------------
    # 3) RIESGO ACTUAL (últimos 4 días)
    # -------------------------------------------------
    if "prom_w_1_5" in daily.columns and "dolor" in daily.columns and not daily.empty:
        daily_sorted = daily.sort_values("fecha_sesion")
        daily_last4 = daily_sorted.tail(4)

        prom_w_1_5_recent = daily_last4["prom_w_1_5"].mean()
        dolor_recent = daily_last4["dolor"].mean()

        riesgo_num, riesgo_val = _calc_riesgo_wellness(
            prom_w_1_5_recent,
            dolor_recent
        )
    else:
        riesgo_num, riesgo_val = 0, "Sin datos"

    riesgo_chart = [riesgo_num]
    riesgo_delta = 0.0

    return {
        "wellness_val": wellness_val,
        "wellness_delta": wellness_delta,
        "wellness_chart": wellness_chart if wellness_chart else [wellness_val],
        "rpe_val": rpe_val,
        "rpe_delta": rpe_delta,
        "rpe_chart": rpe_chart if rpe_chart else [rpe_val],
        "ua_val": ua_val,
        "ua_delta": ua_delta,
        "ua_chart": ua_chart if ua_chart else [ua_val],
        "riesgo_val": riesgo_val,
        "riesgo_delta": riesgo_delta,
        "riesgo_chart": riesgo_chart,
    }