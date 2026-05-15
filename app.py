import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import base64
from PIL import Image
import io

# Configuracion de la pagina
st.set_page_config(layout="wide", page_title="Gothic Nail Manager Cloud")

# Estilo Gotico
st.markdown("""
    <style>
    .stApp { background-color: #0d0d0d; color: #e0e0e0; }
    h1, h2, h3 { color: #8b0000 !important; font-family: 'Georgia', serif; }
    section[data-testid="stSidebar"] { background-color: #1a1a1a; border-right: 1px solid #4b0082; }
    .stButton>button { background-color: #4b0082; color: white; border: 1px solid #8b0000; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# Conexion a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Funciones de Imagen
def imagen_a_base64(imagen_archivo):
    if imagen_archivo is not None:
        try:
            img = Image.open(imagen_archivo)
            img.thumbnail((400, 400))
            buffered = io.BytesIO()
            img.save(buffered, format="PNG", optimize=True)
            return base64.b64encode(buffered.getvalue()).decode()
        except:
            return ""
    return ""

# Navegacion
st.sidebar.title("Nail Control Cloud")
opcion = st.sidebar.radio("Navegacion:", ["Buscar Clienta", "Registrar Trabajo", "Tablero de Analisis"])

# 1. BUSCAR Y VER HISTORIAL
if opcion == "Buscar Clienta":
    st.title("Expediente Digital")
    nom_b = st.text_input("Nombre de la clienta:").strip().lower()
    
    if nom_b:
        df_clientes = conn.read(worksheet="Clientes")
        cliente = df_clientes[df_clientes['nombre'].str.contains(nom_b, case=False, na=False)]
        
        if not cliente.empty:
            id_c = cliente.iloc[0]['id_cliente']
            st.header(f"Clienta: {cliente.iloc[0]['nombre'].upper()}")
            
            df_trabajos = conn.read(worksheet="Trabajos")
            trabajos = df_trabajos[df_trabajos['id_cliente'] == id_c]
            
            if not trabajos.empty:
                for _, t in trabajos.iterrows():
                    with st.container():
                        col_img, col_txt = st.columns([1, 2])
                        with col_img:
                            if t['foto_diseno']:
                                st.image(f"data:image/png;base64,{t['foto_diseno']}", use_container_width=True)
                        with col_txt:
                            st.subheader(f"Fecha: {t['fecha']}")
                            st.write(f"Tecnica: {t['tecnica']} | Precio: ${t['precio']}")
                            st.info(f"Notas: {t['observaciones']}")
                        st.divider()
            else:
                st.write("No hay trabajos registrados.")
        else:
            st.warning("No encontrada.")

# 2. REGISTRAR TRABAJO
elif opcion == "Registrar Trabajo":
    st.title("Nueva Sesion")
    nombre_input = st.text_input("Nombre:").strip().lower()
    
    if nombre_input:
        df_clientes = conn.read(worksheet="Clientes")
        existe = df_clientes[df_clientes['nombre'] == nombre_input]
        
        with st.form("registro"):
            tel = st.text_input("Telefono:") if existe.empty else None
            tecnica = st.selectbox("Tecnica", ["Acrilico", "Retoque", "Gelish", "Polygel", "Soft Gel", "Tip"])
            precio = st.number_input("Precio", min_value=0.0)
            fecha = st.date_input("Fecha", date.today())
            foto = st.file_uploader("Foto del diseno", type=["jpg", "png"])
            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("Guardar"):
                # Si es nueva, agregar a Clientes
                if existe.empty:
                    new_id = len(df_clientes) + 1
                    new_cliente = pd.DataFrame([{"id_cliente": new_id, "nombre": nombre_input, "telefono": tel}])
                    df_clientes = pd.concat([df_clientes, new_cliente], ignore_index=True)
                    conn.update(worksheet="Clientes", data=df_clientes)
                else:
                    new_id = existe.iloc[0]['id_cliente']
                
                # Agregar a Trabajos
                df_trabajos = conn.read(worksheet="Trabajos")
                img_str = imagen_a_base64(foto)
                new_trabajo = pd.DataFrame([{
                    "id_trabajo": len(df_trabajos) + 1,
                    "id_cliente": new_id,
                    "fecha": str(fecha),
                    "tecnica": tecnica,
                    "precio": precio,
                    "foto_diseno": img_str,
                    "observaciones": obs
                }])
                df_trabajos = pd.concat([df_trabajos, new_trabajo], ignore_index=True)
                conn.update(worksheet="Trabajos", data=df_trabajos)
                st.success("Guardado en la nube.")

# 3. TABLERO DE ANALISIS
elif opcion == "Tablero de Analisis":
    st.title("Analisis de Datos UAQ")
    df = conn.read(worksheet="Trabajos")
    if not df.empty:
        st.metric("Ingresos Totales", f"${df['precio'].sum():,.2f}")
        st.bar_chart(df['tecnica'].value_counts())
    else:
        st.write("Sin datos.")