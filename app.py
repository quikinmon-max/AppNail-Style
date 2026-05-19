import streamlit as st
from pymongo import MongoClient
import pandas as pd
from datetime import date
import base64
from PIL import Image
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Nail Manager - Gestión Pro")

st.markdown("""
    <style>
    .stApp { background-color: #0d0d0d; color: #e0e0e0; }
    h1, h2, h3 { color: #8b0000 !important; font-family: 'Georgia', serif; }
    section[data-testid="stSidebar"] { background-color: #1a1a1a; border-right: 1px solid #4b0082; }
    .stButton>button { background-color: #4b0082; color: white; border: 1px solid #8b0000; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A MONGODB ---
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client.estetica_nails
clientes_col = db.clientes
trabajos_col = db.trabajos

def imagen_a_base64(imagen_archivo):
    if imagen_archivo:
        img = Image.open(imagen_archivo)
        img.thumbnail((500, 500))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    return None

# --- NAVEGACIÓN ---
opcion = st.sidebar.radio("Menú", ["Buscador Flexible", "Alta de Servicio", "Gestión de Clientas", "Estadísticas"])

# --- 1. BUSCADOR FLEXIBLE (Coincidencias parciales) ---
if opcion == "Buscador Flexible":
    st.title("🔎 Consultoría de Historial")
    query = st.text_input("Escribe parte del nombre:").strip().lower()
    
    if query:
        # Búsqueda usando expresiones regulares (regex) para coincidencias parciales
        resultados = list(clientes_col.find({"nombre": {"$regex": query, "$options": "i"}}))
        
        if resultados:
            for cliente in resultados:
                with st.expander(f"👤 {cliente['nombre'].upper()}"):
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        if cliente.get("foto_perfil"):
                            st.image(f"data:image/png;base64,{cliente['foto_perfil']}", use_container_width=True)
                    with c2:
                        st.write(f"📞 Teléfono: {cliente.get('telefono', 'N/A')}")
                        st.write(f"📅 Alta: {cliente.get('fecha_alta', 'N/A')}")
                    
                    st.markdown("---")
                    servicios = list(trabajos_col.find({"id_cliente": cliente["_id"]}).sort("fecha", -1))
                    for s in servicios:
                        col_s1, col_s2 = st.columns([1, 4])
                        if s.get("foto"): col_s1.image(f"data:image/png;base64,{s['foto']}", width=100)
                        col_s2.write(f"**{s['fecha']}** - {s['tecnica']} (${s['precio']})")
        else:
            st.warning("No se encontraron coincidencias.")

# --- 2. ALTA DE SERVICIO ---
elif opcion == "Alta de Servicio":
    st.title("📝 Registro de Sesión")
    nombre = st.text_input("Nombre de la clienta:").strip().lower()
    
    if nombre:
        cliente_existente = clientes_col.find_one({"nombre": nombre})
        with st.form("form_alta"):
            if not cliente_existente:
                st.info("Nueva clienta: Creando Ficha Técnica")
                tel = st.text_input("Teléfono:")
                foto_p = st.file_uploader("Foto de Perfil", type=["jpg", "png"])
            
            st.write("### Datos del Trabajo")
            tec = st.selectbox("Técnica", ["Acrílico", "Gelish", "Retoque", "Efectos"])
            pre = st.number_input("Precio", min_value=0.0)
            fec = st.date_input("Fecha", date.today())
            foto_t = st.file_uploader("Foto del Trabajo", type=["jpg", "png"])
            obs = st.text_area("Notas")
            
            if st.form_submit_button("Guardar"):
                if not cliente_existente:
                    res = clientes_col.insert_one({"nombre": nombre, "telefono": tel, "foto_perfil": imagen_a_base64(foto_p), "fecha_alta": str(date.today())})
                    id_c = res.inserted_id
                else:
                    id_c = cliente_existente["_id"]
                
                trabajos_col.insert_one({"id_cliente": id_c, "fecha": str(fec), "tecnica": tec, "precio": pre, "foto": imagen_a_base64(foto_t), "obs": obs})
                st.success("Guardado con éxito.")

# --- 3. GESTIÓN DE CLIENTAS (Ver, Editar, Eliminar) ---
elif opcion == "Gestión de Clientas":
    st.title("⚙️ Administración de Base de Datos")
    
    todos = list(clientes_col.find().sort("nombre", 1))
    
    if todos:
        # Creamos una lista para mostrar con numeración dinámica (el 1, 2, 3...)
        data_lista = []
        for i, c in enumerate(todos, 1):
            data_lista.append({
                "No.": i,
                "Nombre": c['nombre'].upper(),
                "Teléfono": c.get('telefono', 'N/A'),
                "ID": c['_id']
            })
        
        df_ver = pd.DataFrame(data_lista).drop(columns=['ID'])
        st.table(df_ver)
        
        st.markdown("---")
        st.subheader("🗑️ Eliminar o Editar Registro")
        
        # Selección por nombre para evitar errores
        seleccion = st.selectbox("Selecciona una clienta para gestionar:", [c['Nombre'] for c in data_lista])
        cliente_ref = next(item for item in data_lista if item["Nombre"] == seleccion)
        
        col_btn1, col_btn2 = st.columns(2)
        
        if col_btn1.button(f"Eliminar a {seleccion}"):
            # Borrar trabajos asociados primero
            trabajos_col.delete_many({"id_cliente": cliente_ref['ID']})
            # Borrar ficha técnica
            clientes_col.delete_one({"_id": cliente_ref['ID']})
            st.error(f"Se ha eliminado a {seleccion} y todo su historial.")
            st.rerun()

# --- 4. ESTADÍSTICAS ---
elif opcion == "Estadísticas":
    st.title("📊 Análisis de Negocio")
    servicios = list(trabajos_col.find())
    if servicios:
        df = pd.DataFrame(servicios)
        st.metric("Total de Ventas", f"${df['precio'].sum():,.2f}")
        st.bar_chart(df['tecnica'].value_counts())