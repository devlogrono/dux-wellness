function setCookie(name, value, days, samesite="Lax") {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + days * 86400000);
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = `${name}=${value || ""}${expires}; path=/; SameSite=${samesite}`;
}

function deleteCookie(name) {
    document.cookie = `${name}=; Max-Age=-99999999; path=/;`;
}

function getCookie(name) {
    const match = document.cookie.match(
        new RegExp("(^| )" + name + "=([^;]+)")
    );
    return match ? match[2] : null;
}

function onRender(event) {
    const data = event.detail.args;
    let result = null;

    if (data.action === "get") {
        result = getCookie(data.name);
        // La llamada a setComponentValue debe ocurrir SOLO cuando se obtiene un valor
        // para que Python pueda usarlo inmediatamente.
        Streamlit.setComponentValue(result); 
    }
    
    // Las operaciones de escritura (set y delete) no necesitan 
    // forzar un rerunn del script.
    if (data.action === "set") {
        setCookie(data.name, data.value, data.days, data.samesite);
    }

    if (data.action === "delete") {
        deleteCookie(data.name);
    }

    // Streamlit.setComponentValue(result); // ¡Eliminar o mover!
}


Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
Streamlit.setComponentReady();
Streamlit.setFrameHeight(0);
