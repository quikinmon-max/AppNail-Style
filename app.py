import streamlit as st
from pymongo import MongoClient
import pandas as pd
from datetime import date
import base64
from PIL import Image
import io

# 1. Configuración de Estilo y Página
st.set_page_config(layout="wide", page_title="Nail Manager Pro")

st.markdown("""
    <style>
    .stApp { background-color: #0d0d0d; color: #e0e0e0; }
    h1, h2, h3 { color: #8b0000 !important; font-family: 'Georgia', serif; }
    section[data-testid="stSidebar"] { background-color: #1a1a1a; border-right: 1px solid #4b0082; }
    .stButton>button { background-color: #4b0082; color: white; border: 1px solid #8b0000; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# 2. Conexión a MongoDB Atlas (Usando Secrets)
@st.cache_resource
def init_connection():
    # Esta línea jala la URL que pegaste en los Secrets de Streamlit
    return MongoClient(st.secrets["mongo"]["uri"])

try:
    client = init_connection()
    db = client.estetica_nails
    clientes_col = db.clientes
    trabajos_col = db.trabajos
except Exception as e:
    st.error(f"Error de conexión a la base de datos: {e}")

# 3. Función para procesar imágenes
def imagen_a_base64(imagen_archivo):
    if imagen_archivo:
        img = Image.open(imagen_archivo)
        # Optimizamos el tamaño para no saturar la base de datos gratuita
        img.thumbnail((500, 500))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    return None

# 4. Interfaz de Navegación
opcion = st.sidebar.radio("Menú Principal", ["Buscador de Clientas", "Registrar Nuevo Servicio", "Análisis de Ventas"])

# --- MÓDULO: BUSCADOR ---
if opcion == "Buscador de Clientas":
    st.title("🔎 Consultoría de Historial")
    nombre_busqueda = st.text_input("Ingresa el nombre de la clienta:").strip().lower()
    
    if nombre_busqueda:
        cliente = clientes_col.find_one({"nombre": nombre_busqueda})
        if cliente:
            st.header(f"Expediente: {cliente['nombre'].upper()}")
            # Traer todos los trabajos asociados a esta clienta
            historial = list(trabajos_col.find({"id_cliente": cliente["_id"]}).sort("fecha", -1))
            
            if historial:
                for t in historial:
                    with st.container():
                        col1, col2 = st.columns([1, 2])
                        if t.get("foto"):
                            col1.image(f"data:image/png;base64,{t['foto']}", use_container_width=True)
                        col2.subheader(f"Fecha: {t['fecha']}")
                        col2.write(f"**Técnica:** {t['tecnica']}")
                        col2.write(f"**Costo:** ${t['precio']}")
                        col2.info(f"**Notas:** {t.get('obs', 'Sin observaciones')}")
                    st.divider()
            else:
                st.info("Esta clienta no tiene servicios registrados todavía.")
        else:
            st.warning("No se encontró ninguna clienta con ese nombre.")

# --- MÓDULO: REGISTRO ---
elif opcion == "Registrar Nuevo Servicio":
    st.title("💅 Registro de Cita")
    nombre = st.text_input("Nombre de la clienta:").strip().lower()
    
    if nombre:
        cliente_registrado = clientes_col.find_one({"nombre": nombre})
        
        with st.form("formulario_uñas"):
            st.write("### Detalles del Trabajo")
            # Si es nueva, pedimos el teléfono
            telefono = st.text_input("Teléfono de contacto:") if not cliente_registrado else None
            
            tecnica = st.selectbox("Técnica aplicada", ["Acrílico", "Gelish", "Retoque", "Efecto Espejo", "Diseño Mano Alzada"])
            precio = st.number_input("Precio del servicio", min_value=0.0, step=50.0)
            fecha_servicio = st.date_input("Fecha", date.today())
            foto_diseno = st.file_uploader("Subir foto del resultado", type=["jpg", "png", "jpeg"])
            observaciones = st.text_area("Observaciones (colores, marcas de gel, etc.)")
            
            submit = st.form_submit_button("Guardar Permanentemente")
            
            if submit:
                # 1. Asegurar que la clienta existe en la colección de clientes
                if not cliente_registrado:
                    nuevo_cliente = clientes_col.insert_one({"nombre": nombre, "telefono": telefono})
                    id_cliente = nuevo_cliente.inserted_id
                else:
                    id_cliente = cliente_registrado["_id"]
                
                # 2. Guardar el trabajo relacionado
                trabajos_col.insert_one({
                    "id_cliente": id_cliente,
                    "fecha": str(fecha_servicio),
                    "tecnica": tecnica,
                    "precio": precio,
                    "foto": imagen_a_base64(foto_diseno),
                    "obs": observaciones
                })
                st.success(f"¡Servicio para {nombre} guardado en la nube!")

# --- MÓDULO: TABLERO ---
elif opcion == "Análisis de Ventas":
    st.title("Tablero de Control")
    todos_trabajos = list(trabajos_col.find({}, {"_id": 0, "precio": 1, "tecnica": 1, "fecha": 1}))
    
    if todos_trabajos:
        df = pd.DataFrame(todos_trabajos)
        
        c1, c2 = st.columns(2)
        c1.metric("Ingresos Totales", f"${df['precio'].sum():,.2f}")
        c2.metric("Servicios Realizados", len(df))
        
        st.write("### Popularidad por Técnica")
        st.bar_chart(df['tecnica'].value_counts())
    else:
        st.info("Aún no hay suficientes datos para generar estadísticas.")