import streamlit as st
from pymongo import MongoClient
import pandas as pd
from datetime import date
import base64
from PIL import Image
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Nail Manager - Ficha Técnica")

# Estilo visual Gótico/Elegante
st.markdown("""
    <style>
    .stApp { background-color: #0d0d0d; color: #e0e0e0; }
    h1, h2, h3 { color: #8b0000 !important; font-family: 'Georgia', serif; }
    section[data-testid="stSidebar"] { background-color: #1a1a1a; border-right: 1px solid #4b0082; }
    .stButton>button { background-color: #4b0082; color: white; border: 1px solid #8b0000; width: 100%; }
    .stTextInput>div>div>input { background-color: #1a1a1a; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A MONGODB ATLAS ---
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

try:
    client = init_connection()
    db = client.estetica_nails
    clientes_col = db.clientes
    trabajos_col = db.trabajos
except Exception as e:
    st.error(f"Error de conexión: {e}")

# --- UTILIDADES ---
def imagen_a_base64(imagen_archivo):
    if imagen_archivo:
        img = Image.open(imagen_archivo)
        img.thumbnail((600, 600)) # Optimización de tamaño
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    return None

# --- NAVEGACIÓN ---
opcion = st.sidebar.radio("Navegación", ["Consultar Expediente", "Alta de Servicio / Ficha Técnica", "Estadísticas"])

# --- MÓDULO 1: CONSULTA DE EXPEDIENTE ---
if opcion == "Consultar Expediente":
    st.title("🔎 Consultoría de Clientas")
    nombre_b = st.text_input("Buscar por nombre completo:").strip().lower()
    
    if nombre_b:
        cliente = clientes_col.find_one({"nombre": nombre_b})
        if cliente:
            # Encabezado: Ficha Técnica Fija
            st.markdown("---")
            col_foto, col_datos = st.columns([1, 2])
            
            with col_foto:
                if cliente.get("foto_perfil"):
                    st.image(f"data:image/png;base64,{cliente['foto_perfil']}", use_container_width=True)
                else:
                    st.warning("Sin foto de perfil en ficha técnica.")
            
            with col_datos:
                st.subheader(f"CLIENTA: {cliente['nombre'].upper()}")
                st.write(f"📞 **Teléfono:** {cliente.get('telefono', 'No registrado')}")
                st.write(f"📅 **Miembro desde:** {cliente.get('fecha_alta', 'N/A')}")
            
            st.markdown("---")
            st.subheader("📜 Historial de Servicios Realizados")
            
            # Consultar historial de servicios vinculados
            servicios = list(trabajos_col.find({"id_cliente": cliente["_id"]}).sort("fecha", -1))
            
            if servicios:
                for s in servicios:
                    with st.expander(f"Servicio del {s['fecha']} - {s['tecnica']}"):
                        c1, c2 = st.columns([1, 2])
                        if s.get("foto"):
                            c1.image(f"data:image/png;base64,{s['foto']}", use_container_width=True)
                        c2.write(f"**Precio:** ${s['precio']}")
                        c2.write(f"**Observaciones:** {s.get('obs', 'Sin notas')}")
            else:
                st.info("No hay servicios registrados para esta ficha técnica.")
        else:
            st.error("No se encontró registro. Por favor, crea una Ficha Técnica en el menú de alta.")

# --- MÓDULO 2: ALTA DE SERVICIO Y FICHA TÉCNICA ---
elif opcion == "Alta de Servicio / Ficha Técnica":
    st.title("📝 Registro de Sesión")
    nombre = st.text_input("Nombre de la clienta:").strip().lower()
    
    if nombre:
        cliente_existente = clientes_col.find_one({"nombre": nombre})
        
        with st.form("form_registro"):
            if not cliente_existente:
                st.warning("⚠️ Esta clienta no tiene Ficha Técnica. Se creará una nueva ahora.")
                c_tel = st.text_input("Teléfono (Ficha Técnica):")
                c_foto = st.file_uploader("Foto de Perfil para Ficha Técnica", type=["jpg", "png"])
            else:
                st.success("✅ Ficha Técnica encontrada. Registrando nuevo servicio histórico.")
            
            st.markdown("---")
            st.write("### Datos del Servicio Actual")
            f_tecnica = st.selectbox("Técnica", ["Acrílico", "Gelish", "Retoque", "Efectos", "Mano Alzada"])
            f_precio = st.number_input("Costo del servicio", min_value=0.0, step=10.0)
            f_fecha = st.date_input("Fecha", date.today())
            f_foto = st.file_uploader("Foto del trabajo terminado", type=["jpg", "png"])
            f_obs = st.text_area("Notas del servicio")
            
            if st.form_submit_button("Guardar en MongoDB Atlas"):
                # Paso 1: Si es nueva, crear la ficha técnica
                if not cliente_existente:
                    res_c = clientes_col.insert_one({
                        "nombre": nombre,
                        "telefono": c_tel,
                        "foto_perfil": imagen_a_base64(c_foto),
                        "fecha_alta": str(date.today())
                    })
                    id_c = res_c.inserted_id
                else:
                    id_c = cliente_existente["_id"]
                
                # Paso 2: Guardar el servicio vinculado a esa ficha
                trabajos_col.insert_one({
                    "id_cliente": id_c,
                    "fecha": str(f_fecha),
                    "tecnica": f_tecnica,
                    "precio": f_precio,
                    "foto": imagen_a_base64(f_foto),
                    "obs": f_obs
                })
                st.success("¡Datos guardados! La ficha y el historial están seguros en la nube.")

# --- MÓDULO 3: ESTADÍSTICAS ---
elif opcion == "Estadísticas":
    st.title("📊 Análisis de Consultoría")
    servicios_raw = list(trabajos_col.find({}, {"_id": 0, "precio": 1, "tecnica": 1}))
    if servicios_raw:
        df = pd.DataFrame(servicios_raw)
        st.metric("Ingresos Acumulados", f"${df['precio'].sum():,.2f}")
        st.write("### Servicios más solicitados")
        st.bar_chart(df['tecnica'].value_counts())
    else:
        st.info("No hay datos suficientes para el análisis.")