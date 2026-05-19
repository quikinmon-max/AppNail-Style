import streamlit as st
from pymongo import MongoClient
import pandas as pd
from datetime import date
import base64
from PIL import Image
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Nail Manager Pro - CRM")

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
        img.thumbnail((600, 600)) 
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    return None

# --- NAVEGACIÓN ---
opcion = st.sidebar.radio("Menú Principal", 
                         ["Buscador de Clientas", 
                          "Alta de Servicio / Ficha Técnica", 
                          "Gestión de Base de Datos", 
                          "Estadísticas"])

# --- MÓDULO 1: BUSCADOR FLEXIBLE ---
if opcion == "Buscador de Clientas":
    st.title("🔎 Consultoría de Historial")
    query = st.text_input("Ingresa el nombre o parte de él:").strip()
    
    if query:
        # Búsqueda flexible usando Regex
        resultados = list(clientes_col.find({"nombre": {"$regex": query, "$options": "i"}}))
        
        if resultados:
            for cliente in resultados:
                with st.expander(f"👤 EXPEDIENTE: {cliente['nombre'].upper()}"):
                    col_p1, col_p2 = st.columns([1, 2])
                    with col_p1:
                        if cliente.get("foto_perfil"):
                            st.image(f"data:image/png;base64,{cliente['foto_perfil']}", use_container_width=True)
                    with col_p2:
                        st.write(f"📞 **Teléfono:** {cliente.get('telefono', 'N/A')}")
                        st.write(f"📅 **Cliente desde:** {cliente.get('fecha_alta', 'N/A')}")
                    
                    st.markdown("---")
                    st.subheader("Historial de Trabajos")
                    servicios = list(trabajos_col.find({"id_cliente": cliente["_id"]}).sort("fecha", -1))
                    
                    if servicios:
                        for s in servicios:
                            c1, c2 = st.columns([1, 3])
                            if s.get("foto"):
                                c1.image(f"data:image/png;base64,{s['foto']}", use_container_width=True)
                            c2.write(f"**Fecha:** {s['fecha']} | **Técnica:** {s['tecnica']}")
                            c2.write(f"**Costo:** ${s['precio']}")
                            c2.info(f"**Obs:** {s.get('obs', 'Sin notas')}")
                    else:
                        st.info("No hay servicios registrados.")
        else:
            st.warning("No se encontraron coincidencias.")

# --- MÓDULO 2: ALTA Y FICHA TÉCNICA ---
elif opcion == "Alta de Servicio / Ficha Técnica":
    st.title("📝 Registro de Sesión")
    nombre = st.text_input("Nombre de la clienta:").strip().lower()
    
    if nombre:
        cliente_existente = clientes_col.find_one({"nombre": nombre})
        
        with st.form("form_registro"):
            if not cliente_existente:
                st.warning("⚠️ Nueva Clienta detectada. Creando Ficha Técnica...")
                c_tel = st.text_input("Teléfono:")
                c_foto = st.file_uploader("Foto de Perfil (Fija)", type=["jpg", "png"])
            else:
                st.success(f"✅ Ficha Técnica activa para {nombre.upper()}")
            
            st.markdown("---")
            st.write("### Detalles del Trabajo de Hoy")
            f_tecnica = st.selectbox("Técnica", ["Acrílico", "Gelish", "Retoque", "Efectos", "Mano Alzada"])
            f_precio = st.number_input("Costo", min_value=0.0, step=10.0)
            f_fecha = st.date_input("Fecha", date.today())
            f_foto = st.file_uploader("Foto del diseño", type=["jpg", "png"])
            f_obs = st.text_area("Observaciones")
            
            if st.form_submit_button("Guardar en la Nube"):
                if not cliente_existente:
                    res_c = clientes_col.insert_one({
                        "nombre": nombre,
                        "telefono": c_tel,
                        "foto_perfil": imagen_a_base64(c_foto),
                        "fecha_alta": str(date.today())
                    })
                    id_c = res_c.inserted_