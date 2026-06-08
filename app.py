import streamlit as st
from pymongo import MongoClient
from bson.objectid import ObjectId
import pandas as pd
from datetime import date
import base64
from PIL import Image
import io
import hashlib

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Portal SaaS: Gestión de Estéticas ✂️", page_icon="👑")
st.set_page_config(layout="wide", page_title="Nail Manager Pro - SaaS")

# --- CONEXIÓN A MONGODB ATLAS ---
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

try:
    client = init_connection()
    db = client.estetica_nails
    clientes_col = db.clientes
    trabajos_col = db.trabajos
    usuarios_col = db.usuarios 
except Exception as e:
    st.error(f"Error de conexión: {e}")

# --- UTILIDADES ---
def imagen_a_base64(imagen_archivo, size=(1000, 1000)):
    if imagen_archivo:
        img = Image.open(imagen_archivo)
        img.thumbnail(size) 
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    return None

def encriptar_pass(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- CONTROL DE SESIONES ---
if 'usuario_id' not in st.session_state:
    st.session_state['usuario_id'] = None
    st.session_state['nombre_negocio'] = None
    st.session_state['logo'] = None
    st.session_state['fondo'] = None

# ==========================================
# PANTALLA DE ACCESO (LOG OUT STATE)
# ==========================================
if st.session_state['usuario_id'] is None:
    st.markdown("""
        <style>
        .stApp { background-color: #0d0d0d; color: #e0e0e0; }
        .stButton>button { background-color: #4b0082; color: white; width: 100%; }
        </style>
        """, unsafe_allow_html=True)

    st.title("🔐 Portal de Administración")
    st.write("Bienvenido al centro de gestión inteligente para salones de belleza y estéticas.")
    
    tab_login, tab_registro = st.tabs(["👤 Iniciar Sesión", "🏢 Registrar Mi Negocio"])
    
    with tab_login:
        with st.form("form_login"):
            usuario_login = st.text_input("Usuario").strip().lower()
            pass_login = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar al Sistema"):
                user_db = usuarios_col.find_one({
                    "usuario": usuario_login, 
                    "password": encriptar_pass(pass_login)
                })
                if user_db:
                    st.session_state['usuario_id'] = str(user_db["_id"])
                    st.session_state['nombre_negocio'] = user_db["negocio"]
                    st.session_state['logo'] = user_db.get("logo", None)
                    st.session_state['fondo'] = user_db.get("fondo", "#0d0d0d")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
                    
    with tab_registro:
        st.write("Crea una cuenta para tu estética.")
        with st.form("form_registro_negocio"):
            nuevo_negocio = st.text_input("Nombre de la Estética/Salón")
            nuevo_usuario = st.text_input("Crea un Usuario (sin espacios)").strip().lower()
            nueva_pass = st.text_input("Crea una Contraseña", type="password")
            
            if st.form_submit_button("Crear Cuenta"):
                if usuarios_col.find_one({"usuario": nuevo_usuario}):
                    st.error("Ese usuario ya está en uso. Elige otro.")
                elif nuevo_negocio and nuevo_usuario and nueva_pass:
                    usuarios_col.insert_one({
                        "negocio": nuevo_negocio,
                        "usuario": nuevo_usuario,
                        "password": encriptar_pass(nueva_pass),
                        "logo": None,
                        "fondo": "#0d0d0d"
                    })
                    st.success("¡Cuenta creada! Ya puedes iniciar sesión en la pestaña anterior.")
                else:
                    st.warning("Llena los campos obligatorios.")

# ==========================================
# APLICACIÓN PRINCIPAL (LOG IN STATE)
# ==========================================
else:
    id_negocio = st.session_state['usuario_id']
    
    # 1. Inyectar Personalización (White-Label) Dinámica con Filtro Oscuro
    fondo_val = st.session_state.get('fondo', '#0d0d0d')
    
    if fondo_val and not fondo_val.startswith("#"):
        # Filtro oscuro (linear-gradient) y ajuste de imagen (cover)
        css_fondo = f"""
            background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('data:image/png;base64,{fondo_val}');
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        """
    else:
        color = fondo_val if fondo_val else "#0d0d0d"
        css_fondo = f"background-color: {color};"
    
    st.markdown(f"""
        <style>
        .stApp {{ {css_fondo} color: #e0e0e0; }}
        h1, h2, h3 {{ font-family: 'Georgia', serif; text-shadow: 1px 1px 2px black; }}
        section[data-testid="stSidebar"] {{ background-color: rgba(26, 26, 26, 0.9); border-right: 1px solid #4b0082; }}
        .stButton>button {{ background-color: #4b0082; color: white; border: 1px solid #8b0000; width: 100%; }}
        .stTextInput>div>div>input {{ background-color: rgba(26, 26, 26, 0.8); color: white; }}
        /* Contenedores oscuros y opacos para asegurar lectura perfecta */
        div[data-testid="stForm"], div[data-testid="stExpander"] {{ 
            background-color: rgba(15, 15, 15, 0.85); 
            border-radius: 10px; 
            padding: 15px; 
            border: 1px solid #4b0082; 
            box-shadow: 0px 4px 10px rgba(0,0,0,0.5); 
        }}
        </style>
        """, unsafe_allow_html=True)

    # 2. Menú Lateral Personalizado
    st.sidebar.title(f"👑 {st.session_state['nombre_negocio']}")
    if st.session_state.get('logo'):
        st.sidebar.image(f"data:image/png;base64,{st.session_state['logo']}", use_container_width=True)
    else:
        st.sidebar.markdown(f"### 🏢 {st.session_state['nombre_negocio']}")
        
    if st.sidebar.button("Cerrar Sesión"):
        for key in ['usuario_id', 'nombre_negocio', 'logo', 'fondo']:
            st.session_state[key] = None
        st.rerun()
        
    st.sidebar.markdown("---")
    opcion = st.sidebar.radio("Navegación", 
                             ["Buscador por Nombre", 
                              "Alta de Servicio / Ficha", 
                              "Gestión de Clientas", 
                              "Estadísticas Financieras",
                              "🎨 Personalizar Estética"])

    # --- MÓDULO 1: BUSCADOR FLEXIBLE ---
    if opcion == "Buscador por Nombre":
        st.title("🔎 Consultoría de Historial")
        query = st.text_input("Ingresa el nombre o fragmento a buscar:").strip()
        if query:
            resultados = list(clientes_col.find({"id_negocio": id_negocio, "nombre": {"$regex": query, "$options": "i"}}))
            if resultados:
                for cliente in resultados:
                    with st.expander(f"👤 EXPEDIENTE: {cliente['nombre'].upper()}"):
                        servicios_nuevos = list(trabajos_col.find({"id_cliente": cliente["_id"]}).sort("fecha", -1))
                        servicio_antiguo = trabajos_col.find_one({"id_cliente": cliente["_id"]}, sort=[("fecha", 1)])
                        fecha_inicio = servicio_antiguo["fecha"] if servicio_antiguo else "Sin historial"

                        col_p1, col_p2 = st.columns([1, 2])
                        with col_p1:
                            if cliente.get("foto_perfil"):
                                st.image(f"data:image/png;base64,{cliente['foto_perfil']}", use_container_width=True)
                        with col_p2:
                            st.write(f"📞 **Teléfono:** {cliente.get('telefono', 'N/A')}")
                            st.write(f"📅 **Clienta desde:** {fecha_inicio}")
                        
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

    # --- MÓDULO 2: ALTA DE SERVICIO Y FICHA ---
    elif opcion == "Alta de Servicio / Ficha":
        st.title("📝 Registro de Cita")
        nombre = st.text_input("Nombre de la clienta:").strip().lower()
        if nombre:
            cliente_existente = clientes_col.find_one({"id_negocio": id_negocio, "nombre": nombre})
            with st.form("form_registro"):
                if not cliente_existente:
                    st.warning("⚠️ Creando Ficha Técnica para nueva clienta...")
                    c_tel = st.text_input("Teléfono:")
                    c_foto = st.file_uploader("Foto de Perfil", type=["jpg", "png"])
                else:
                    st.success(f"✅ Ficha activa para {nombre.upper()}")
                
                st.markdown("---")
                st.write("### Detalles del Servicio")
                f_tecnica = st.selectbox("Técnica", ["Acrílico", "Gelish", "Retoque", "Efectos", "Mano Alzada", "Cat Opal Eye"])
                f_precio = st.number_input("Costo del servicio", min_value=0.0, step=10.0)
                f_fecha = st.date_input("Fecha", date.today())
                f_foto = st.file_uploader("Foto del resultado", type=["jpg", "png"])
                f_obs = st.text_area("Observaciones")
                
                if st.form_submit_button("Guardar en Sistema"):
                    if not cliente_existente:
                        res_c = clientes_col.insert_one({
                            "id_negocio": id_negocio, "nombre": nombre, "telefono": c_tel, "foto_perfil": imagen_a_base64(c_foto)
                        })
                        id_c = res_c.inserted_id
                    else:
                        id_c = cliente_existente["_id"]
                    
                    trabajos_col.insert_one({
                        "id_negocio": id_negocio, "id_cliente": id_c, "fecha": str(f_fecha), "tecnica": f_tecnica, 
                        "precio": f_precio, "foto": imagen_a_base64(f_foto), "obs": f_obs
                    })
                    st.success("¡Datos guardados!")

    # --- MÓDULO 3: GESTIÓN DE CLIENTAS ---
    elif opcion == "Gestión de Clientas":
        st.title("⚙️ Administrador de Fichas")
        todos = list(clientes_col.find({"id_negocio": id_negocio}).sort("nombre", 1))
        if todos:
            data_lista = []
            for i, c in enumerate(todos, 1):
                data_lista.append({"No.": i, "Nombre": c['nombre'].upper(), "Teléfono": c.get('telefono', 'N/A'), "_id": c['_id']})
            
            df_ver = pd.DataFrame(data_lista).drop(columns=['_id'])
            st.table(df_ver)
            
            st.markdown("---")
            st.subheader("🗑️ Eliminar Ficha por Número")
            num_eliminar = st.number_input("Escribe el No. de la clienta a eliminar:", min_value=1, max_value=len(data_lista), step=1)
            cliente_ref = data_lista[num_eliminar - 1]
            st.error(f"¿Confirmas borrar a **{cliente_ref['Nombre']}**?")
            if st.button(f"CONFIRMAR BORRADO"):
                trabajos_col.delete_many({"id_cliente": cliente_ref['_id']})
                clientes_col.delete_one({"_id": cliente_ref['_id']})
                st.success("Registro eliminado.")
                st.rerun()
        else:
            st.info("Sin clientas.")

    # --- MÓDULO 4: ESTADÍSTICAS ---
    elif opcion == "Estadísticas Financieras":
        st.title("📊 Análisis de Ventas")
        servicios = list(trabajos_col.find({"id_negocio": id_negocio}))
        if servicios:
            df = pd.DataFrame(servicios)
            st.metric("Ingresos Totales (Acumulado)", f"${df['precio'].sum():,.2f}")
            st.bar_chart(df['tecnica'].value_counts())
        else:
            st.info("Sin datos suficientes.")

    # --- MÓDULO 5: PERSONALIZACIÓN (EL NUEVO TOQUE PREMIUM) ---
    elif opcion == "🎨 Personalizar Estética":
        st.title("🎨 Dale tu estilo a la App")
        st.write("Sube imágenes directamente para cambiar la apariencia de tu sistema.")
        
        with st.form("form_personalizacion"):
            st.subheader("1. Tu Logo")
            st.write("Sube el logo de tu estética (Aparecerá en el menú lateral).")
            nuevo_logo_file = st.file_uploader("Subir Logo (Recomendado: PNG sin fondo)", type=["jpg", "png", "jpeg"])
            
            st.markdown("---")
            st.subheader("2. Fondo de la Aplicación")
            tipo_fondo = st.radio("¿Qué tipo de fondo prefieres?", ["Imagen / Foto", "Color Sólido oscuro"])
            
            nuevo_fondo_file = None
            nuevo_color = "#0d0d0d"
            
            if tipo_fondo == "Imagen / Foto":
                st.write("Sube una foto (El sistema le pondrá un filtro oscuro elegante automáticamente).")
                nuevo_fondo_file = st.file_uploader("Subir Imagen de Fondo", type=["jpg", "png", "jpeg"])
            else:
                color_actual = st.session_state.get('fondo', '#0d0d0d')
                if not color_actual.startswith("#"): color_actual = "#0d0d0d"
                nuevo_color = st.color_picker("Elige un color elegante", color_actual)

            if st.form_submit_button("Guardar Diseño"):
                datos_a_actualizar = {}
                
                if nuevo_logo_file:
                    b64_logo = imagen_a_base64(nuevo_logo_file)
                    datos_a_actualizar["logo"] = b64_logo
                    st.session_state['logo'] = b64_logo
                    
                if tipo_fondo == "Imagen / Foto" and nuevo_fondo_file:
                    b64_fondo = imagen_a_base64(nuevo_fondo_file)
                    datos_a_actualizar["fondo"] = b64_fondo
                    st.session_state['fondo'] = b64_fondo
                elif tipo_fondo == "Color Sólido oscuro":
                    datos_a_actualizar["fondo"] = nuevo_color
                    st.session_state['fondo'] = nuevo_color
                    
                if datos_a_actualizar:
                    usuarios_col.update_one(
                        {"_id": ObjectId(st.session_state['usuario_id'])},
                        {"$set": datos_a_actualizar}
                    )
                    st.success("¡Diseño actualizado exitosamente!")
                    st.rerun() 
                else:
                    st.info("No subiste nuevas imágenes ni cambiaste el color.")