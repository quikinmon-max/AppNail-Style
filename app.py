import streamlit as st
import sqlite3
from datetime import date
import base64
from PIL import Image
import io
import pandas as pd

# Configuracion de la pagina con diseño ancho
st.set_page_config(layout="wide", page_title="Gothic Nail Manager")

# Inyeccion de CSS para estilo gotico (Negro, Rojo Sangre y Morado)
st.markdown("""
    <style>
    .stApp {
        background-color: #0d0d0d;
        color: #e0e0e0;
    }
    h1, h2, h3 {
        color: #8b0000 !important;
        font-family: 'Georgia', serif;
        text-shadow: 2px 2px 4px #000000;
    }
    section[data-testid="stSidebar"] {
        background-color: #1a1a1a;
        border-right: 1px solid #4b0082;
    }
    .stButton>button {
        background-color: #4b0082;
        color: white;
        border-radius: 0px;
        border: 1px solid #8b0000;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #8b0000;
        border: 1px solid #4b0082;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #1a1a1a;
        color: #e0e0e0;
        border: 1px solid #4b0082;
    }
    </style>
    """, unsafe_allow_html=True)

# Procesamiento de imagenes a Base64 para almacenamiento en SQLite
def imagen_a_base64(imagen_archivo):
    if imagen_archivo is not None:
        try:
            img = Image.open(imagen_archivo)
            img.thumbnail((500, 500))
            buffered = io.BytesIO()
            img.save(buffered, format="PNG", optimize=True)
            return base64.b64encode(buffered.getvalue()).decode()
        except:
            return None
    return None

# Inicializacion de tablas en la base de datos control_unas.db
def inicializar_db():
    conn = sqlite3.connect('control_unas.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Clientes (
            id_cliente INTEGER PRIMARY KEY AUTOINCREMENT, 
            nombre TEXT UNIQUE, 
            telefono TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Trabajos (
            id_trabajo INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente INTEGER,
            fecha TEXT,
            tecnica TEXT,
            precio REAL,
            foto_diseno TEXT, 
            observaciones TEXT,
            FOREIGN KEY(id_cliente) REFERENCES Clientes(id_cliente)
        )
    """)
    conn.commit()
    conn.close()

# Funcion centralizada para ejecucion de consultas SQL
def ejecutar_query(query, params=(), fetch=False, fetchall=False, return_id=False):
    conn = sqlite3.connect('control_unas.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    if return_id:
        res = cursor.lastrowid
        conn.commit()
    elif fetchall:
        res = cursor.fetchall()
    elif fetch:
        res = cursor.fetchone()
    else:
        conn.commit()
        res = None
    conn.close()
    return res

inicializar_db()

# Navegacion lateral
st.sidebar.title("Nail Control Noir")
opcion = st.sidebar.radio("Navegacion:", ["Buscar Clienta", "Registrar Trabajo", "Tablero de Analisis"])

# Seccion 1: Busqueda de historial y galeria visual
if opcion == "Buscar Clienta":
    st.title("Expediente de Clientas")
    nom_b = st.text_input("Ingresa el nombre a buscar:").strip().lower()
    
    if nom_b:
        cliente = ejecutar_query("SELECT * FROM Clientes WHERE nombre LIKE ?", (f'%{nom_b}%',), fetch=True)
        if cliente:
            st.header(f"Clienta: {cliente[1].upper()}")
            trabajos = ejecutar_query("SELECT fecha, tecnica, precio, foto_diseno, observaciones FROM Trabajos WHERE id_cliente = ? ORDER BY fecha DESC", (cliente[0],), fetchall=True)
            
            if trabajos:
                for t in trabajos:
                    with st.container():
                        col_img, col_txt = st.columns([1, 2])
                        with col_img:
                            if t[3]:
                                st.image(f"data:image/png;base64,{t[3]}", use_container_width=True)
                        with col_txt:
                            st.subheader(f"Fecha: {t[0]}")
                            st.write(f"Tecnica: {t[1]}")
                            st.write(f"Precio: ${t[2]}")
                            st.info(f"Notas: {t[4]}")
                        st.divider()
            else:
                st.write("No existen registros previos para esta clienta.")
        else:
            st.warning("La clienta no se encuentra en la base de datos.")

# Seccion 2: Registro de nuevas sesiones y clientes
elif opcion == "Registrar Trabajo":
    st.title("Nueva Sesion de Trabajo")
    nombre_input = st.text_input("Nombre de la clienta:").strip().lower()
    
    if nombre_input:
        existe = ejecutar_query("SELECT id_cliente FROM Clientes WHERE nombre = ?", (nombre_input,), fetch=True)
        with st.form("form_registro", clear_on_submit=True):
            if not existe:
                st.info("Nueva clienta detectada en el sistema.")
                tel = st.text_input("Telefono de contacto:")
            else:
                st.success("Clienta reconocida.")
                tel = None

            col1, col2 = st.columns(2)
            with col1:
                tecnica = st.selectbox("Tecnica aplicada", ["Acritico", "Retoque", "Gelish", "Polygel", "Soft Gel", "Retiro"])
                precio = st.number_input("Costo del servicio", min_value=0.0, step=50.0)
            with col2:
                fecha = st.date_input("Fecha", date.today())
                foto = st.file_uploader("Subir evidencia del diseno", type=["jpg", "png", "jpeg"])
            
            obs = st.text_area("Detalles del servicio (colores, decoracion, etc.)")
            
            if st.form_submit_button("Guardar en Historial"):
                if not existe:
                    id_c = ejecutar_query("INSERT INTO Clientes (nombre, telefono) VALUES (?,?)", (nombre_input, tel), return_id=True)
                else:
                    id_c = existe[0]
                
                img_str = imagen_a_base64(foto)
                ejecutar_query("""
                    INSERT INTO Trabajos (id_cliente, fecha, tecnica, precio, foto_diseno, observaciones) 
                    VALUES (?,?,?,?,?,?)
                """, (id_c, str(fecha), tecnica, precio, img_str, obs))
                st.success("El registro ha sido sellado correctamente.")

# Seccion 3: Analisis de datos con Pandas
elif opcion == "Tablero de Analisis":
    st.title("Analisis de Rendimiento")
    datos = ejecutar_query("SELECT fecha, precio, tecnica FROM Trabajos", fetchall=True)
    
    if datos:
        df = pd.DataFrame(datos, columns=['Fecha', 'Precio', 'Tecnica'])
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        
        col_met1, col_met2 = st.columns(2)
        col_met1.metric("Ingresos Totales acumulados", f"${df['Precio'].sum():,.2f}")
        col_met2.metric("Numero Total de Servicios", len(df))
        
        st.subheader("Flujo de Ingresos por Tiempo")
        ventas_fecha = df.groupby('Fecha')['Precio'].sum()
        st.line_chart(ventas_fecha)
        
        st.subheader("Distribucion por Tecnica")
        st.bar_chart(df['Tecnica'].value_counts())
    else:
        st.write("Datos insuficientes para generar graficas de analisis.")