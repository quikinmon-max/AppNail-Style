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
        resultados = list(clientes_col.find({"nombre": {"$regex": query, "$options": "i"}}))
        
        if resultados:
            for cliente in resultados:
                with st.expander(f"👤 EXPEDIENTE: {cliente['nombre'].upper()}"):
                    # 1. Obtener todos los servicios para el historial (Más nuevo a más viejo)
                    servicios_nuevos = list(trabajos_col.find({"id_cliente": cliente["_id"]}).sort("fecha", -1))
                    
                    # 2. Calcular dinámicamente el servicio más antiguo para la fecha de alta
                    servicio_antiguo = trabajos_col.find_one({"id_cliente": cliente["_id"]}, sort=[("fecha", 1)])
                    fecha_inicio = servicio_antiguo["fecha"] if servicio_antiguo else "Sin servicios"

                    col_p1, col_p2 = st.columns([1, 2])
                    with col_p1:
                        if cliente.get("foto_perfil"):
                            st.image(f"data:image/png;base64,{cliente['foto_perfil']}", use_container_width=True)
                    with col_p2:
                        st.write(f"📞 **Teléfono:** {cliente.get('telefono', 'N/A')}")
                        st.write(f"📅 **Cliente desde (Primer servicio):** {fecha_inicio}")
                    
                    st.markdown("---")
                    st.subheader("Historial de Trabajos")
                    
                    if servicios_nuevos:
                        for s in servicios_nuevos:
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
                    # Quitamos el campo estático de fecha_alta porque ya se calcula con los servicios
                    res_c = clientes_col.insert_one({
                        "nombre": nombre,
                        "telefono": c_tel,
                        "foto_perfil": imagen_a_base64(c_foto)
                    })
                    id_c = res_c.inserted_id
                else:
                    id_c = cliente_existente["_id"]
                
                trabajos_col.insert_one({
                    "id_cliente": id_c,
                    "fecha": str(f_fecha),
                    "tecnica": f_tecnica,
                    "precio": f_precio,
                    "foto": imagen_a_base64(f_foto),
                    "obs": f_obs
                })
                st.success("¡Datos sincronizados con MongoDB Atlas!")

# --- MÓDULO 3: GESTIÓN (Ver y Eliminar por Número) ---
elif opcion == "Gestión de Base de Datos":
    st.title("⚙️ Administración de Clientas")
    
    todos = list(clientes_col.find().sort("nombre", 1))
    
    if todos:
        data_lista = []
        for i, c in enumerate(todos, 1):
            data_lista.append({
                "No.": i,
                "Nombre": c['nombre'].upper(),
                "Teléfono": c.get('telefono', 'N/A'),
                "_id": c['_id']
            })
        
        df_ver = pd.DataFrame(data_lista).drop(columns=['_id'])
        st.table(df_ver)
        
        st.markdown("---")
        st.subheader("🗑️ Eliminar por Número de Registro")
        num_eliminar = st.number_input("Escribe el No. de la clienta a eliminar:", 
                                       min_value=1, 
                                       max_value=len(data_lista), 
                                       step=1)
        
        cliente_ref = data_lista[num_eliminar - 1]
        st.error(f"¿Confirmas que deseas eliminar a **{cliente_ref['Nombre']}**? Se borrará TODO su historial.")
        
        if st.button(f"BORRAR NÚMERO {num_eliminar}"):
            trabajos_col.delete_many({"id_cliente": cliente_ref['_id']})
            clientes_col.delete_one({"_id": cliente_ref['_id']})
            st.success("Registro eliminado. La lista se ha reordenado.")
            st.rerun()
    else:
        st.info("Base de datos vacía.")

# --- MÓDULO 4: ESTADÍSTICAS ---
elif opcion == "Estadísticas":
    st.title("📊 Análisis de Consultoría")
    servicios = list(trabajos_col.find())
    if servicios:
        df = pd.DataFrame(servicios)
        st.metric("Ingresos Totales", f"${df['precio'].sum():,.2f}")
        st.write("### Técnicas más Vendidas")
        st.bar_chart(df['tecnica'].value_counts())
    else:
        st.info("Sin datos suficientes.")