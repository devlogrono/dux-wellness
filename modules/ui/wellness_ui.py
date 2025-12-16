import time
import streamlit as st
from modules.db.db_records import search_existing_record, upsert_record_db
from modules.schema import new_base_record
from modules.ui.check_in_ui import checkin_form
from modules.ui.check_out_ui import checkout_form
from modules.i18n.i18n import t
from modules.ui.ui_components import preview_record

def wellness_form(jugadora, tipo, turno):
    """
    Lógica completa y segura para crear, validar y guardar Wellness/RPE.
    Versión corregida para evitar reruns globales y conflictos entre usuarios.
    """

    # ---------------------------------------
    # 1. Validación inicial
    # ---------------------------------------
    if not jugadora:
        st.info(t("Selecciona una jugadora para continuar."))
        return
    
    # ---------------------------------------
    # 2. Crear record base
    # ---------------------------------------
    record = new_base_record(
        id_jugadora=str(jugadora["id_jugadora"]),
        username=st.session_state["auth"]["name"].lower(),
        tipo="checkin" if tipo == "Check-in" else "checkout",
    )
    #preview_record(record)
    record["turno"] = turno or ""

    # ID seguro por navegador
    session_id = st.session_state["client_session_id"]
    redirect_key = f"redirect_{session_id}"

    # ---------------------------------------
    # ---------------------------------------
    form_key = f"form_wellness_{session_id}"

    #with st.form(key=form_key, border=False):

    # ---- Check-in ----
    if tipo == "Check-in":
        record, is_valid, validation_msg = checkin_form(record, jugadora["genero"])

    # ---- Check-out ----
    else:
        record, is_valid, validation_msg = checkout_form(record)

        # ---- Botón seguro ----
        #submitted = st.form_submit_button(t("Guardar"))

    # ---------------------------------------
    # 5. Procesamiento del guardado
    # ---------------------------------------
    if st.button(f":material/save: {t('Guardar')}", key="btn_reg_wellness", disabled=not is_valid):
        #preview_record(record)

        # ---------------------------------------
        # 3. Revisar si ya existe Check-in hoy
        # ---------------------------------------
        # existing_today = search_existing_record(record)
        # if existing_today:
        #     st.error(t("Existe un registro de check-in previo para esta jugadora, fecha y turno."))
        #     st.stop()
        
        # if not existing_today:
        #     st.error(t("No existe un registro de check-in previo para esta jugadora, fecha y turno."))
        #     st.stop()

        # # Validación previa
        # if not is_valid and validation_msg:
        #     st.error(validation_msg)
        #     return

        modo = "checkin" if tipo == "Check-in" else "checkout"
        success = upsert_record_db(record, modo)

        if success:
            st.success(t("Registro guardado correctamente."))
            st.session_state[redirect_key] = True
            st.session_state["submitted"] = True
        else:
            st.error(t("Error al guardar el registro."))
            return

    # ---------------------------------------
    # 6. Vista de previsualización (solo developers)
    # ---------------------------------------
    if st.session_state["auth"]["rol"].lower() == "developer":
        st.divider()
        if st.checkbox(t("Previsualización")):
            preview_record(record)

    # ---------------------------------------
    # 7. Redirección segura SOLO para este navegador
    # ---------------------------------------
    if st.session_state.get(redirect_key):
        del st.session_state[redirect_key]
        st.session_state["target_page"] = "registro"
        #time.sleep(5)  # Pequeña pausa para evitar conflictos
        st.switch_page("pages/switch.py")
        #st.rerun()

def resolver_jugadora_final(jugadora_header, jug_df_filtrado, jug_df):
    """
    Resuelve la jugadora final a usar en el formulario de wellness,
    manteniendo consistencia entre reruns y evitando selección incorrecta
    cuando la jugadora desaparece de la lista.

    Lógica:
    - new_id: jugadora seleccionada actualmente en el header
    - prev_id: jugadora previamente bloqueada en session_state
    - Si prev_id desaparece → reset + rerun
    - Si prev_id existe y new_id cambia → cambio manual → actualizar
    - Si prev_id no existe aún → asignar new_id
    """

    # ID actual entregado por el header
    new_id = str(jugadora_header["id_jugadora"]) if jugadora_header else None

    # IDs válidos en el filtrado actual
    current_ids = jug_df_filtrado["id_jugadora"].astype(str).tolist()

    # ID bloqueado previamente
    prev_id = st.session_state.get("last_selected_player_id")

    # ------------------------------
    # 1. Primera asignación
    # ------------------------------
    if prev_id is None:
        if new_id is not None:
            st.session_state["last_selected_player_id"] = new_id

    else:
        # ------------------------------
        # 2. Si cambia la jugadora del header
        # ------------------------------
        if new_id != prev_id:

            # Si la jugadora anterior ya no existe → reset + rerun
            if prev_id not in current_ids:
                st.session_state["last_selected_player_id"] = None
                st.warning("La jugadora seleccionada ya no se encontraba disponible.")
                st.rerun()
            # Cambio manual → actualizar bloqueada
            st.session_state["last_selected_player_id"] = new_id

    # ------------------------------
    # 3. Jugadora final bloqueada
    # ------------------------------
    locked_id = st.session_state.get("last_selected_player_id")

    # Si por alguna razón está limpia
    if locked_id is None:
        st.rerun()

    # Buscar jugadora final exacta
    jugadora_rows = jug_df[jug_df["id_jugadora"].astype(str) == locked_id]

    if jugadora_rows.empty:
        st.session_state["last_selected_player_id"] = None
        st.rerun()

    # Devolver jugadora final en dict
    return jugadora_rows.iloc[0].to_dict()
