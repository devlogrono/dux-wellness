import pandas as pd


def prepare_players(df_players: pd.DataFrame, plantel_objetivo: str = "1FF") -> pd.DataFrame:
    """
    Prepara la tabla de jugadoras para análisis:
    - filtra por plantel
    - convierte fecha_nacimiento a datetime
    - crea edad
    """
    df = df_players.copy()

    if "plantel" in df.columns:
        df = df[df["plantel"] == plantel_objetivo].copy()

    if "fecha_nacimiento" in df.columns:
        df["fecha_nacimiento"] = pd.to_datetime(df["fecha_nacimiento"], errors="coerce")

        hoy = pd.Timestamp.today().normalize()
        df["edad"] = ((hoy - df["fecha_nacimiento"]).dt.days / 365.25).round(1)

    return df


def prepare_wellness_dataset(
    df_wellness: pd.DataFrame,
    df_players: pd.DataFrame,
    fecha_inicio: str = "2026-01-01"
) -> pd.DataFrame:
    """
    Prepara el dataset analítico de wellness a partir de:
    - df_wellness: salida base de get_records_db()
    - df_players: tabla de jugadoras ya preparada con prepare_players()

    NOTA:
    get_records_db() ya devuelve resueltos:
    - nombre_jugadora
    - tipo_carga
    - rehabilitación_readaptación
    - condicion
    - zona_segmento
    - zonas_anatomicas_dolor (como lista de nombres)
    - fecha_hora_registro en datetime
    """

    df = df_wellness.copy()
    df_players = df_players.copy()

    # =========================
    # FECHA DE SESIÓN A DATETIME
    # =========================
    # get_records_db() la deja como date; aquí la convertimos a datetime
    # para facilitar filtros, agrupaciones y análisis temporal.
    if "fecha_sesion" in df.columns:
        df["fecha_sesion"] = pd.to_datetime(df["fecha_sesion"], errors="coerce")

    # =========================
    # FILTRO TEMPORAL
    # =========================
    if "fecha_sesion" in df.columns:
        df = df[df["fecha_sesion"] >= pd.Timestamp(fecha_inicio)].copy()

    # =========================
    # PREPARAR TABLA DE JUGADORAS
    # =========================
    columnas_players = [
        "id_jugadora",
        "posicion",
        "fecha_nacimiento",
        "edad",
        "dorsal",
        "nacionalidad",
        "altura",
        "peso",
    ]
    columnas_players = [c for c in columnas_players if c in df_players.columns]

    df_players_small = df_players[columnas_players].copy()

    if "id_jugadora" in df_players_small.columns:
        df_players_small = df_players_small.drop_duplicates(subset="id_jugadora")

    # =========================
    # MERGE CON JUGADORAS
    # =========================
    if "id_jugadora" in df.columns and "id_jugadora" in df_players_small.columns:
        df = df.merge(
            df_players_small,
            on="id_jugadora",
            how="left"
        )

    # =========================
    # TIPADO NUMÉRICO
    # =========================
    columnas_numericas = [
        "recuperacion",
        "energia",
        "sueno",
        "stress",
        "dolor",
        "minutos_sesion",
        "rpe",
        "ua",
        "edad",
        "altura",
        "peso",
        "dorsal",
    ]
    for col in columnas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


    # =========================
    # REORDENAR COLUMNAS
    # =========================
    columnas_ordenadas = [
        "id",
        "id_jugadora",
        "nombre_jugadora",
        "plantel",
        "posicion",
        "edad",
        "dorsal",
        "nacionalidad",
        "altura",
        "peso",
        "fecha_nacimiento",
        "fecha_sesion",
        "fecha_hora_registro",
        "tipo",
        "turno",
        "periodizacion_tactica",
        "tipo_carga",
        "rehabilitación_readaptación",
        "condicion",
        "recuperacion",
        "energia",
        "sueno",
        "stress",
        "dolor",
        "zona_segmento",
        "zonas_anatomicas_dolor",
        "lateralidad_dolor",
        "minutos_sesion",
        "rpe",
        "ua",
        "en_periodo",
        "observacion",
        "usuario",
    ]

    columnas_finales = [c for c in columnas_ordenadas if c in df.columns]
    columnas_restantes = [c for c in df.columns if c not in columnas_finales]

    df = df[columnas_finales + columnas_restantes].copy()

    return df