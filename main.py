import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from supabase import create_client

# Configuración de página
st.set_page_config(
    page_title="Pastelería D'Pandos - Sistema de Gestión",
    page_icon="🧁",
    layout="wide"
)

# Conexión con Supabase
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Función para cargar datos
@st.cache_data(ttl=300)
def cargar_insumos():
    response = sb.table('insumos').select('*').execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=300)
def cargar_categorias():
    response = sb.table('categorias').select('*').execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=300)
def cargar_productos():
    response = sb.table('productos').select('*').execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=300)
def cargar_receta_insumos(producto_id):
    response = sb.table('receta_insumos').select('*').eq('producto_id', producto_id).execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=300)
def cargar_historico_precios():
    response = sb.table('historico_precios').select('*').execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=300)
def cargar_produccion():
    response = sb.table('produccion').select('*').execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=300)
def cargar_compras():
    response = sb.table('compras').select('*').execute()
    return pd.DataFrame(response.data)

# Función para obtener nombre de insumo
def obtener_nombre_insumo(insumo_id):
    insumos = cargar_insumos()
    insumo = insumos[insumos['id'] == insumo_id]
    if not insumo.empty:
        return insumo.iloc[0]['nombre']
    return "Insumo no encontrado"

# Función para obtener nombre de categoría
def obtener_nombre_categoria(categoria_id):
    categorias = cargar_categorias()
    categoria = categorias[categorias['id'] == categoria_id]
    if not categoria.empty:
        return categoria.iloc[0]['nombre']
    return "Categoría no encontrada"

# Nueva función para obtener el precio actual directamente de la tabla insumos
def obtener_precio_actual(insumo_id):
    insumos = cargar_insumos()
    insumo = insumos[insumos['id'] == insumo_id]
    if not insumo.empty:
        return insumo.iloc[0]['precio_actual']
    return 0.0  # Si no encuentra el insumo, retorna 0

# Función para calcular el costo de una receta
def calcular_costo_receta(producto_id):
    # Obtener insumos de la receta
    receta_insumos = cargar_receta_insumos(producto_id)
    insumos = cargar_insumos()
    
    costo_total = 0
    detalles = []
    
    # Calcular costo de insumos
    for _, ingrediente in receta_insumos.iterrows():
        insumo = insumos[insumos['id'] == ingrediente['insumo_id']]
        if not insumo.empty:
            precio = insumo.iloc[0]['precio_actual']
            cantidad = ingrediente['cantidad']
            subtotal = precio * cantidad
            costo_total += subtotal
            
            detalles.append({
                'insumo': obtener_nombre_insumo(ingrediente['insumo_id']),
                'cantidad': cantidad,
                'unidad': ingrediente['unidad_medida'],
                'precio_unitario': precio,
                'subtotal': subtotal
            })
    
    # Obtener costos adicionales
    response = sb.table('receta_costos_adicionales').select('*').eq('producto_id', producto_id).execute()
    costos_adicionales = pd.DataFrame(response.data)
    
    for _, costo in costos_adicionales.iterrows():
        costo_total += costo['costo']
        detalles.append({
            'insumo': costo['concepto'],
            'cantidad': 1,
            'unidad': 'servicio',
            'precio_unitario': costo['costo'],
            'subtotal': costo['costo']
        })
    
    return costo_total, detalles

# Sidebar con menú principal
st.sidebar.image("https://scontent.flim9-1.fna.fbcdn.net/v/t39.30808-6/301893190_443547794459140_2944011405632948968_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=6ee11a&_nc_eui2=AeHPs2DTVyE6QunWMvboCNhPe05rJlI_0CN7TmsmUj_QIwZVNGi7n9miYoyx_6voNOX3rzyYuRPDJNhCcibugrpu&_nc_ohc=P3MOKoAaHw4Q7kNvwHHIMcE&_nc_oc=Adkbu6xjQ67RXJicCtJkeK4qt7alhVdta5c8pvD9lkq-9-0CE585UDdS3KY_ybotHdRTiizftD2p7OVl8NjVPbpQ&_nc_zt=23&_nc_ht=scontent.flim9-1.fna&_nc_gid=wLYEMkiGf_tJSHMrfD96Tw&oh=00_AfHVcPIxfQew61sET-hCOFeJQAtbtW6dDR00VRrVsqLMbw&oe=681D4DE8", width=150)
st.sidebar.title("Pastelería D'Pandos")

# Menú principal
menu = st.sidebar.radio(
    "Menú Principal",
    ["Compras", "Consumos", "Recetas", "Registrar Insumos", "Reportes", "Configuración"]
)

# Página de Compras
if menu == "Compras":
    st.title("Compra del Día")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        tipo_compra = st.selectbox(
            "Tipo de Compra:",
            ["Regular", "Extra"]
        )
        proveedor = st.text_input("Proveedor:", "")
    
    # Inicializar la sesión si no existe
    if 'items_compra' not in st.session_state:
        st.session_state.items_compra = []

    # Cargar datos
    insumos = cargar_insumos()
    
    # Manejo del estado antes del formulario
    if "insumo_id" not in st.session_state:
        st.session_state.insumo_id = insumos['id'].iloc[0] if not insumos.empty else None
    
    # Actualizar el precio cuando cambia el insumo (fuera del formulario)
    insumo_id = st.selectbox(
        "Insumo:",
        options=insumos['id'].tolist(),
        format_func=lambda x: obtener_nombre_insumo(x),
        key="insumo_id"
    )
    
    # Actualizar el precio cuando el insumo cambia
    if "ultimo_insumo_id" not in st.session_state:
        st.session_state.ultimo_insumo_id = insumo_id
        st.session_state.precio = obtener_precio_actual(insumo_id)
    elif st.session_state.ultimo_insumo_id != insumo_id:
        st.session_state.ultimo_insumo_id = insumo_id
        st.session_state.precio = obtener_precio_actual(insumo_id)
    
    # Crear forma para agregar compra
    with st.form("form_compra"):
        st.subheader("Agregar Insumo a la Compra")
        
        # Formulario
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.text(f"Insumo seleccionado: {obtener_nombre_insumo(insumo_id)}")
        
        with col2:
            cantidad = st.number_input("Cantidad:", min_value=0.01, step=0.01, value=1.0)
        
        with col3:
            precio = st.number_input(
                "Precio Unitario:", 
                min_value=0.01, 
                step=0.01, 
                value=st.session_state.precio
            )
        
        # Botón para agregar
        submit_button = st.form_submit_button("Agregar a la Compra")
        
        if submit_button:
            # Calcular subtotal
            subtotal = round(cantidad * precio, 2)
            
            # Agregar a la lista de compras
            nuevo_item = {
                "insumo_id": insumo_id,
                "nombre": obtener_nombre_insumo(insumo_id),
                "cantidad": cantidad,
                "precio_unitario": precio,
                "subtotal": subtotal
            }
            
            st.session_state.items_compra.append(nuevo_item)
            st.success(f"Insumo '{nuevo_item['nombre']}' agregado a la compra.")
    
    # Mostrar los items de la compra
    st.subheader("Detalle de la Compra")
    
    if st.session_state.items_compra:
        # Convertir lista de diccionarios a DataFrame
        df_items = pd.DataFrame(st.session_state.items_compra)
        
        # Mostrar tabla
        st.dataframe(df_items[['nombre', 'cantidad', 'precio_unitario', 'subtotal']])
        
        # Calcular total
        total = sum(item['subtotal'] for item in st.session_state.items_compra)
        st.write(f"**Total:** S/ {total:.2f}")
        
        # Botón para guardar la compra
        if st.button("Guardar Compra"):
            fecha_actual = datetime.now().date()
            
            try:
                # Crear la compra principal
                compra_data = {
                    "fecha": fecha_actual.strftime("%Y-%m-%d"),
                    "proveedor": proveedor,
                    "tipo": tipo_compra,
                    "observaciones": "",
                    "total": total
                }
                
                # Insertar en la tabla de compras
                resultado_compra = sb.table('compras').insert(compra_data).execute()
                compra_id = resultado_compra.data[0]['id']
                
                # Insertar detalles de la compra
                for item in st.session_state.items_compra:
                    detalle_data = {
                        "compra_id": compra_id,
                        "insumo_id": item['insumo_id'],
                        "cantidad": item['cantidad'],
                        "precio_unitario": item['precio_unitario'],
                        "subtotal": item['subtotal']
                    }
                    sb.table('compra_detalles').insert(detalle_data).execute()
                
                # Limpiar los items de la compra
                st.session_state.items_compra = []
                
                st.success("Compra guardada exitosamente!")
                st.rerun()  # Recargar la página para mostrar los cambios
            except Exception as e:
                st.error(f"Error al guardar la compra: {str(e)}")
    else:
        st.info("No hay insumos agregados a la compra.")

# Página de Consumos
elif menu == "Consumos":
    st.title("Registro de Consumos")
    
    tab1, tab2 = st.tabs(["Consumo Manual", "Consumo por Producción"])
    
    with tab1:
        st.subheader("Consumo Manual de Insumos")
        
        # Formulario para consumo manual
        with st.form("form_consumo_manual"):
            # Cargar datos
            insumos = cargar_insumos()
            
            # Formulario
            col1, col2 = st.columns(2)
            
            with col1:
                insumo_id = st.selectbox(
                    "Insumo a Consumir:",
                    options=insumos['id'].tolist(),
                    format_func=lambda x: f"{obtener_nombre_insumo(x)} (Stock: {insumos[insumos['id'] == x].iloc[0]['stock_actual']})"
                )
            
            with col2:
                cantidad = st.number_input("Cantidad a Consumir:", min_value=0.01, step=0.01)
            
            observaciones = st.text_area("Observaciones:", "")
            
            submit_button = st.form_submit_button("Registrar Consumo")
            
            if submit_button:
                # Verificar stock disponible
                stock_actual = insumos[insumos['id'] == insumo_id].iloc[0]['stock_actual']
                
                if cantidad > stock_actual:
                    st.error(f"No hay suficiente stock. Disponible: {stock_actual}")
                else:
                    # Crear nuevo consumo
                    nuevo_consumo = {
                        'fecha': datetime.now().strftime('%Y-%m-%d'),
                        'produccion_id': None,  # No está relacionado a producción
                        'observaciones': observaciones
                    }
                    result = sb.table('consumos').insert(nuevo_consumo).execute()
                    consumo_id = result.data[0]['id']
                    
                    # Agregar detalle de consumo
                    detalle_consumo = {
                        'consumo_id': consumo_id,
                        'insumo_id': insumo_id,
                        'cantidad': cantidad
                    }
                    sb.table('consumo_detalles').insert(detalle_consumo).execute()
                    
                    st.success(f"Consumo de {cantidad} {insumos[insumos['id'] == insumo_id].iloc[0]['unidad_medida']} de {obtener_nombre_insumo(insumo_id)} registrado correctamente!")
    
    with tab2:
        st.subheader("Consumo por Producción")
        
        # Cargar productos
        productos = cargar_productos()
        
        # Formulario para consumo por producción
        with st.form("form_consumo_produccion"):
            col1, col2 = st.columns(2)
            
            with col1:
                if not productos.empty:
                    producto_id = st.selectbox(
                        "Producto a Elaborar:",
                        options=productos['id'].tolist(),
                        format_func=lambda x: productos[productos['id'] == x].iloc[0]['nombre']
                    )
                else:
                    st.warning("No hay productos/recetas registradas.")
                    producto_id = None
            
            with col2:
                cantidad_produccion = st.number_input("Cantidad a Producir:", min_value=1, step=1, value=1)
            
            observaciones = st.text_area("Observaciones Producción:", "")
            
            submit_produccion = st.form_submit_button("Registrar Producción")
            
            if submit_produccion and producto_id:
                # Calcular costo de la receta
                costo_unitario, detalles_receta = calcular_costo_receta(producto_id)
                costo_total = costo_unitario * cantidad_produccion
                
                # Verificar stock disponible para todos los insumos
                insumos = cargar_insumos()
                receta_insumos = cargar_receta_insumos(producto_id)
                
                stock_insuficiente = False
                for _, ingrediente in receta_insumos.iterrows():
                    insumo = insumos[insumos['id'] == ingrediente['insumo_id']]
                    if not insumo.empty:
                        stock_actual = insumo.iloc[0]['stock_actual']
                        cantidad_necesaria = ingrediente['cantidad'] * cantidad_produccion
                        
                        if cantidad_necesaria > stock_actual:
                            st.error(f"Stock insuficiente de {obtener_nombre_insumo(ingrediente['insumo_id'])}. Necesario: {cantidad_necesaria}, Disponible: {stock_actual}")
                            stock_insuficiente = True
                
                if not stock_insuficiente:
                    # Registrar producción
                    nueva_produccion = {
                        'producto_id': producto_id,
                        'fecha': datetime.now().strftime('%Y-%m-%d'),
                        'cantidad': cantidad_produccion,
                        'costo_total': costo_total,
                        'observaciones': observaciones
                    }
                    result = sb.table('produccion').insert(nueva_produccion).execute()
                    produccion_id = result.data[0]['id']
                    
                    # Registrar consumo asociado a la producción
                    nuevo_consumo = {
                        'fecha': datetime.now().strftime('%Y-%m-%d'),
                        'produccion_id': produccion_id,
                        'observaciones': f"Consumo para producción #{produccion_id}"
                    }
                    result = sb.table('consumos').insert(nuevo_consumo).execute()
                    consumo_id = result.data[0]['id']
                    
                    # Registrar consumo de cada insumo
                    for _, ingrediente in receta_insumos.iterrows():
                        detalle_consumo = {
                            'consumo_id': consumo_id,
                            'insumo_id': ingrediente['insumo_id'],
                            'cantidad': ingrediente['cantidad'] * cantidad_produccion
                        }
                        sb.table('consumo_detalles').insert(detalle_consumo).execute()
                    
                    st.success(f"Producción de {cantidad_produccion} unidades de {productos[productos['id'] == producto_id].iloc[0]['nombre']} registrada correctamente!")
                    
                    # Mostrar detalles de la producción
                    st.subheader("Detalles de la Producción:")
                    detalles_df = pd.DataFrame(detalles_receta)
                    detalles_df['cantidad'] = detalles_df['cantidad'] * cantidad_produccion
                    detalles_df['subtotal'] = detalles_df['subtotal'] * cantidad_produccion
                    st.table(detalles_df)
                    st.subheader(f"Costo Total: S/ {costo_total:.2f}")

# Página de Recetas
elif menu == "Recetas":
    st.title("Gestión de Recetas")
    
    tab1, tab2, tab3 = st.tabs(["Ver Recetas", "Nueva Receta", "Editar Receta"])
    
    with tab1:
        st.subheader("Recetas Disponibles")
        
        # Cargar productos/recetas
        productos = cargar_productos()
        
        if not productos.empty:
            # Mostrar lista de recetas
            producto_id = st.selectbox(
                "Seleccionar Receta:",
                options=productos['id'].tolist(),
                format_func=lambda x: productos[productos['id'] == x].iloc[0]['nombre']
            )
            
            if producto_id:
                producto = productos[productos['id'] == producto_id].iloc[0]
                
                st.subheader(f"Receta: {producto['nombre']}")
                st.write(f"Precio de Venta: S/ {producto['precio_venta']:.2f}")
                
                # Mostrar insumos de la receta
                receta_insumos = cargar_receta_insumos(producto_id)
                
                if not receta_insumos.empty:
                    # Agregar información de insumos
                    insumos_df = pd.DataFrame()
                    insumos = cargar_insumos()
                    
                    for _, ingrediente in receta_insumos.iterrows():
                        insumo = insumos[insumos['id'] == ingrediente['insumo_id']]
                        if not insumo.empty:
                            row = {
                                'Insumo': obtener_nombre_insumo(ingrediente['insumo_id']),
                                'Cantidad': ingrediente['cantidad'],
                                'Unidad': ingrediente['unidad_medida'],
                                'Precio Unitario': insumo.iloc[0]['precio_actual'],
                                'Subtotal': ingrediente['cantidad'] * insumo.iloc[0]['precio_actual']
                            }
                            insumos_df = pd.concat([insumos_df, pd.DataFrame([row])], ignore_index=True)
                    
                    st.table(insumos_df)
                
                # Mostrar costos adicionales
                response = sb.table('receta_costos_adicionales').select('*').eq('producto_id', producto_id).execute()
                costos_adicionales = pd.DataFrame(response.data)
                
                if not costos_adicionales.empty:
                    st.subheader("Costos Adicionales:")
                    costos_df = costos_adicionales[['concepto', 'costo']]
                    costos_df.columns = ['Concepto', 'Costo']
                    st.table(costos_df)
                
                # Calcular costo total y margen
                costo_total, _ = calcular_costo_receta(producto_id)
                precio_venta = producto['precio_venta']
                margen = precio_venta - costo_total
                margen_porcentaje = (margen / precio_venta) * 100 if precio_venta > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Costo Total", f"S/ {costo_total:.2f}")
                col2.metric("Precio de Venta", f"S/ {precio_venta:.2f}")
                col3.metric("Margen de Ganancia", f"S/ {margen:.2f} ({margen_porcentaje:.1f}%)")
        else:
            st.info("No hay recetas registradas.")
    
    with tab2:
        st.subheader("Crear Nueva Receta")
        
        # Formulario principal para crear la receta
        with st.form("form_nueva_receta"):
            nombre_receta = st.text_input("Nombre del Producto:")
            descripcion = st.text_area("Descripción:")
            precio_venta = st.number_input("Precio de Venta:", min_value=0.0, step=0.1)
            
            # Sección para agregar insumos
            st.subheader("Insumos de la Receta")
            
            # Lista para almacenar insumos temporales
            if 'insumos_temp' not in st.session_state:
                st.session_state.insumos_temp = []
            
            insumos = cargar_insumos()
            
            # Agregar insumo
            col1, col2, col3 = st.columns(3)
            with col1:
                insumo_id = st.selectbox(
                    "Insumo:",
                    options=insumos['id'].tolist(),
                    format_func=lambda x: obtener_nombre_insumo(x)
                )
            
            with col2:
                cantidad = st.number_input("Cantidad:", min_value=0.01, step=0.01, value=1.0)
            
            with col3:
                unidad = st.selectbox("Unidad:", ["kg", "g", "l", "ml", "unidad", "taza", "cucharada"])
            
            # Botón para agregar insumo
            submit_button = st.form_submit_button("Agregar Insumo a la Receta")
            
            if submit_button:
                insumo_nombre = obtener_nombre_insumo(insumo_id)
                st.session_state.insumos_temp.append({
                    'insumo_id': insumo_id,
                    'nombre': insumo_nombre,
                    'cantidad': cantidad,
                    'unidad_medida': unidad
                })
                st.success(f"Insumo {insumo_nombre} agregado a la receta.")
            
            # Mostrar insumos agregados
            if st.session_state.insumos_temp:
                st.write("Insumos agregados a la receta:")
                insumos_df = pd.DataFrame(st.session_state.insumos_temp)
                st.table(insumos_df[['nombre', 'cantidad', 'unidad_medida']])
            
            # Sección para costos adicionales
            st.subheader("Costos Adicionales")
            
            # if 'costos_adicionales_temp' not in st.session_state:
            #     st.session_state.costos_adicionales_temp = []
            
            # col1, col2 = st.columns(2)
            # with col1:
            #     concepto = st.text_input("Concepto (Mano de obra, gas, etc.):")
            # with col2:
            #     costo = st.number_input("Costo:", min_value=0.0, step=0.1)
            
            # if st.button("Agregar Costo Adicional"):
            #     st.session_state.costos_adicionales_temp.append({
            #         'concepto': concepto,
            #         'costo': costo
            #     })
            #     st.success(f"Costo adicional por {concepto} agregado a la receta.")
            
            # Mostrar costos adicionales
            if st.session_state.costos_adicionales_temp:
                st.write("Costos adicionales:")
                costos_df = pd.DataFrame(st.session_state.costos_adicionales_temp)
                st.table(costos_df)
            
            submit_receta = st.form_submit_button("Guardar Receta")
            
            if submit_receta:
                if nombre_receta and precio_venta > 0 and st.session_state.insumos_temp:
                    # Crear nueva receta/producto
                    nueva_receta = {
                        'nombre': nombre_receta,
                        'descripcion': descripcion,
                        'precio_venta': precio_venta
                    }
                    
                    result = sb.table('productos').insert(nueva_receta).execute()
                    producto_id = result.data[0]['id']
                    
                    # Guardar insumos de la receta
                    for insumo in st.session_state.insumos_temp:
                        receta_insumo = {
                            'producto_id': producto_id,
                            'insumo_id': insumo['insumo_id'],
                            'cantidad': insumo['cantidad'],
                            'unidad_medida': insumo['unidad_medida']
                        }
                        sb.table('receta_insumos').insert(receta_insumo).execute()
                    
                    # Guardar costos adicionales
                    for costo in st.session_state.costos_adicionales_temp:
                        costo_adicional = {
                            'producto_id': producto_id,
                            'concepto': costo['concepto'],
                            'costo': costo['costo']
                        }
                        sb.table('receta_costos_adicionales').insert(costo_adicional).execute()
                    
                    st.success(f"Receta {nombre_receta} guardada correctamente!")
                    # Limpiar variables temporales
                    st.session_state.insumos_temp = []
                    st.session_state.costos_adicionales_temp = []
                else:
                    if not nombre_receta:
                        st.error("Debe ingresar un nombre para la receta.")
                    if precio_venta <= 0:
                        st.error("El precio de venta debe ser mayor que cero.")
                    if not st.session_state.insumos_temp:
                        st.error("Debe agregar al menos un insumo a la receta.")

   
    
    with tab3:
        st.subheader("Editar Receta Existente")
        
        # Cargar productos/recetas
        productos = cargar_productos()
        
        if not productos.empty:
            producto_id = st.selectbox(
                "Seleccionar Receta a Editar:",
                options=productos['id'].tolist(),
                format_func=lambda x: productos[productos['id'] == x].iloc[0]['nombre'],
                key="editar_receta"
            )
            
            if producto_id:
                producto = productos[productos['id'] == producto_id].iloc[0]
                
                with st.form("form_editar_receta"):
                    nombre_receta = st.text_input("Nombre del Producto:", value=producto['nombre'])
                    descripcion = st.text_area("Descripción:", value=producto['descripcion'] if producto['descripcion'] else "")
                    precio_venta = st.number_input("Precio de Venta:", value=float(producto['precio_venta']), min_value=0.0, step=0.1)
                    
                    # Cargar insumos existentes de la receta
                    receta_insumos = cargar_receta_insumos(producto_id)
                    
                    # Lista para almacenar insumos editados
                    if 'insumos_edit' not in st.session_state:
                        # Inicializar con insumos existentes
                        st.session_state.insumos_edit = []
                        for _, insumo in receta_insumos.iterrows():
                            st.session_state.insumos_edit.append({
                                'id': insumo['id'],
                                'insumo_id': insumo['insumo_id'],
                                'nombre': obtener_nombre_insumo(insumo['insumo_id']),
                                'cantidad': insumo['cantidad'],
                                'unidad_medida': insumo['unidad_medida']
                            })
                    
                    # Mostrar insumos existentes
                    st.subheader("Insumos de la Receta")
                    
                    if st.session_state.insumos_edit:
                        insumos_df = pd.DataFrame(st.session_state.insumos_edit)
                        st.table(insumos_df[['nombre', 'cantidad', 'unidad_medida']])
                    
                    # Agregar nuevo insumo
                    st.subheader("Agregar Nuevo Insumo")
                    
                    insumos = cargar_insumos()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        nuevo_insumo_id = st.selectbox(
                            "Insumo:",
                            options=insumos['id'].tolist(),
                            format_func=lambda x: obtener_nombre_insumo(x),
                            key="nuevo_insumo_edit"
                        )
                    with col2:
                        nueva_cantidad = st.number_input("Cantidad:", min_value=0.01, step=0.01, value=1.0, key="nueva_cantidad_edit")
                    with col3:
                        nueva_unidad = st.selectbox("Unidad:", ["kg", "g", "l", "ml", "unidad", "taza", "cucharada"], key="nueva_unidad_edit")
                    
                    # Reemplazar st.button() con st.form_submit_button()
                    submit_insumo_button = st.form_submit_button("Agregar Insumo")
                    
                    if submit_insumo_button:
                        insumo_nombre = obtener_nombre_insumo(nuevo_insumo_id)
                        st.session_state.insumos_edit.append({
                            'id': None,  # Nuevo insumo sin ID en la base de datos aún
                            'insumo_id': nuevo_insumo_id,
                            'nombre': insumo_nombre,
                            'cantidad': nueva_cantidad,
                            'unidad_medida': nueva_unidad
                        })
                        st.success(f"Insumo {insumo_nombre} agregado a la receta.")
                    
                    # Cargar costos adicionales
                    response = sb.table('receta_costos_adicionales').select('*').eq('producto_id', producto_id).execute()
                    costos_adicionales = pd.DataFrame(response.data)
                    
                    # Lista para almacenar costos adicionales editados
                    if 'costos_adicionales_edit' not in st.session_state:
                        # Inicializar con costos existentes
                        st.session_state.costos_adicionales_edit = []
                        for _, costo in costos_adicionales.iterrows():
                            st.session_state.costos_adicionales_edit.append({
                                'id': costo['id'],
                                'concepto': costo['concepto'],
                                'costo': costo['costo']
                            })
                    
                    # Mostrar costos adicionales
                    st.subheader("Costos Adicionales")
                    
                    if st.session_state.costos_adicionales_edit:
                        costos_df = pd.DataFrame(st.session_state.costos_adicionales_edit)
                        st.table(costos_df[['concepto', 'costo']])
                    
                    # Agregar nuevo costo adicional
                    st.subheader("Agregar Nuevo Costo Adicional")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        nuevo_concepto = st.text_input("Concepto (Mano de obra, gas, etc.):", key="nuevo_concepto_edit")
                    with col2:
                        nuevo_costo = st.number_input("Costo:", min_value=0.0, step=0.1, key="nuevo_costo_edit")
                    
                    # Reemplazar st.button() con st.form_submit_button()
                    submit_costo_button = st.form_submit_button("Agregar Costo Adicional")
                    
                    if submit_costo_button:
                        st.session_state.costos_adicionales_edit.append({
                            'id': None,  # Nuevo costo sin ID en la base de datos aún
                            'concepto': nuevo_concepto,
                            'costo': nuevo_costo
                        })
                        st.success(f"Costo adicional por {nuevo_concepto} agregado a la receta.")
                    
                    submit_edit = st.form_submit_button("Guardar Cambios")
                    
                    if submit_edit:
                        if nombre_receta and precio_venta > 0:
                            # Actualizar receta/producto
                            sb.table('productos').update({
                                'nombre': nombre_receta,
                                'descripcion': descripcion,
                                'precio_venta': precio_venta,
                                'updated_at': datetime.now().isoformat()
                            }).eq('id', producto_id).execute()
                            
                            # Actualizar insumos
                            for insumo in st.session_state.insumos_edit:
                                if insumo['id']:  # Insumo existente, actualizar
                                    sb.table('receta_insumos').update({
                                        'cantidad': insumo['cantidad'],
                                        'unidad_medida': insumo['unidad_medida']
                                    }).eq('id', insumo['id']).execute()
                                else:  # Nuevo insumo, insertar
                                    receta_insumo = {
                                        'producto_id': producto_id,
                                        'insumo_id': insumo['insumo_id'],
                                        'cantidad': insumo['cantidad'],
                                        'unidad_medida': insumo['unidad_medida']
                                    }
                                    sb.table('receta_insumos').insert(receta_insumo).execute()
                            
                            # Actualizar costos adicionales
                            for costo in st.session_state.costos_adicionales_edit:
                                if costo['id']:  # Costo existente, actualizar
                                    sb.table('receta_costos_adicionales').update({
                                        'concepto': costo['concepto'],
                                        'costo': costo['costo']
                                    }).eq('id', costo['id']).execute()
                                else:  # Nuevo costo, insertar
                                    costo_adicional = {
                                        'producto_id': producto_id,
                                        'concepto': costo['concepto'],
                                        'costo': costo['costo']
                                    }
                                    sb.table('receta_costos_adicionales').insert(costo_adicional).execute()
                            
                            st.success(f"Receta {nombre_receta} actualizada correctamente!")
                            # Limpiar variables temporales
                            if 'insumos_edit' in st.session_state:
                                del st.session_state.insumos_edit
                            if 'costos_adicionales_edit' in st.session_state:
                                del st.session_state.costos_adicionales_edit
                        else:
                            if not nombre_receta:
                                st.error("Debe ingresar un nombre para la receta.")
                            if precio_venta <= 0:
                                st.error("El precio de venta debe ser mayor que cero.")


# Página de Registrar Insumos
elif menu == "Registrar Insumos":
    st.title("Gestión de Insumos")
    
    tab1, tab2 = st.tabs(["Ver Insumos", "Nuevo Insumo"])
    
    with tab1:
        st.subheader("Insumos Disponibles")
        
        # Cargar insumos
        insumos = cargar_insumos()
        categorias = cargar_categorias()
        
        if not insumos.empty:
            # Agregar nombres de categorías
            insumos['categoria'] = insumos['categoria_id'].apply(obtener_nombre_categoria)
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                categoria_filtro = st.selectbox(
                    "Filtrar por Categoría:",
                    ["Todas"] + categorias['nombre'].tolist()
                )
            
            with col2:
                busqueda = st.text_input("Buscar por Nombre:")
            
            # Aplicar filtros
            insumos_filtrados = insumos.copy()
            if categoria_filtro != "Todas":
                categoria_id = categorias[categorias['nombre'] == categoria_filtro].iloc[0]['id']
                insumos_filtrados = insumos_filtrados[insumos_filtrados['categoria_id'] == categoria_id]
            
            if busqueda:
                insumos_filtrados = insumos_filtrados[insumos_filtrados['nombre'].str.contains(busqueda, case=False)]
            
            # Mostrar tabla de insumos
            tabla_insumos = insumos_filtrados[['nombre', 'categoria', 'precio_actual', 'stock_actual', 'stock_minimo', 'unidad_medida']]
            tabla_insumos.columns = ['Nombre', 'Categoría', 'Precio Actual', 'Stock Actual', 'Stock Mínimo', 'Unidad']
            
            # Resaltar insumos con stock bajo
            def highlight_stock_bajo(row):
                if row['Stock Actual'] < row['Stock Mínimo']:
                    return ['background-color: #ffcccc'] * len(row)
                return [''] * len(row)
            
            st.dataframe(tabla_insumos.style.apply(highlight_stock_bajo, axis=1))
            
            # Mostrar alerta para insumos con stock bajo
            insumos_stock_bajo = insumos_filtrados[insumos_filtrados['stock_actual'] < insumos_filtrados['stock_minimo']]
            if not insumos_stock_bajo.empty:
                st.warning(f"Hay {len(insumos_stock_bajo)} insumo(s) con stock por debajo del mínimo!")
                for _, insumo in insumos_stock_bajo.iterrows():
                    st.error(f"{insumo['nombre']}: Stock actual {insumo['stock_actual']} {insumo['unidad_medida']} (mínimo: {insumo['stock_minimo']} {insumo['unidad_medida']})")
        else:
            st.info("No hay insumos registrados.")
    
    with tab2:
        st.subheader("Registrar Nuevo Insumo")
        
        with st.form("form_nuevo_insumo"):
            col1, col2 = st.columns(2)
            
            with col1:
                nombre = st.text_input("Nombre del Insumo:")
                
                # Cargar categorías
                categorias = cargar_categorias()
                categoria_id = st.selectbox(
                    "Categoría:",
                    options=categorias['id'].tolist(),
                    format_func=lambda x: categorias[categorias['id'] == x].iloc[0]['nombre']
                )
                
                precio = st.number_input("Precio Actual:", min_value=0.01, step=0.01)
            
            with col2:
                stock_actual = st.number_input("Stock Actual:", min_value=0.0, step=0.1)
                stock_minimo = st.number_input("Stock Mínimo:", min_value=0.0, step=0.1)
                unidad_medida = st.selectbox("Unidad de Medida:", ["kg", "g", "l", "ml", "unidad", "paquete", "saco"])
            
            submit_insumo = st.form_submit_button("Guardar Insumo")
            
            if submit_insumo:
                if nombre and precio > 0:
                    # Verificar si ya existe un insumo con el mismo nombre
                    insumos = cargar_insumos()
                    if not insumos.empty and nombre in insumos['nombre'].values:
                        st.error(f"Ya existe un insumo con el nombre '{nombre}'.")
                    else:
                        # Crear nuevo insumo
                        nuevo_insumo = {
                            'nombre': nombre,
                            'categoria_id': categoria_id,
                            'precio_actual': precio,
                            'stock_actual': stock_actual,
                            'stock_minimo': stock_minimo,
                            'unidad_medida': unidad_medida
                        }
                        
                        sb.table('insumos').insert(nuevo_insumo).execute()
                        
                        # Registrar precio histórico
                        historico_precio = {
                            'insumo_id': sb.table('insumos').select('id').eq('nombre', nombre).execute().data[0]['id'],
                            'precio': precio,
                            'fecha': datetime.now().strftime('%Y-%m-%d')
                        }
                        sb.table('historico_precios').insert(historico_precio).execute()
                        
                        st.success(f"Insumo {nombre} registrado correctamente!")
                else:
                    if not nombre:
                        st.error("Debe ingresar un nombre para el insumo.")
                    if precio <= 0:
                        st.error("El precio debe ser mayor que cero.")

# Página de Reportes
elif menu == "Reportes":
    st.title("Reportes y Análisis")
    
    tipo_reporte = st.selectbox(
        "Tipo de Reporte:",
        ["Evolución de Precios de Insumos", "Margen de Ganancia por Producto", "Consumo de Insumos", "Producción Histórica"]
    )
    
    if tipo_reporte == "Evolución de Precios de Insumos":
        st.subheader("Evolución de Precios de Insumos")
        
        # Cargar datos
        historico_precios = cargar_historico_precios()
        insumos = cargar_insumos()
        
        if not historico_precios.empty and not insumos.empty:
            # Agregar nombres de insumos
            historico_precios['insumo'] = historico_precios['insumo_id'].apply(obtener_nombre_insumo)
            
            # Seleccionar insumos
            insumos_seleccionados = st.multiselect(
                "Seleccionar Insumos:",
                options=insumos['nombre'].tolist()
            )
            
            # Rango de fechas
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input("Fecha Inicio:", value=datetime.now() - timedelta(days=30))
            with col2:
                fecha_fin = st.date_input("Fecha Fin:", value=datetime.now())
            
            if insumos_seleccionados:
                # Filtrar datos
                insumos_ids = insumos[insumos['nombre'].isin(insumos_seleccionados)]['id'].tolist()
                datos_filtrados = historico_precios[
                    (historico_precios['insumo_id'].isin(insumos_ids)) &
                    (pd.to_datetime(historico_precios['fecha']) >= pd.to_datetime(fecha_inicio)) &
                    (pd.to_datetime(historico_precios['fecha']) <= pd.to_datetime(fecha_fin))
                ]
                
                if not datos_filtrados.empty:
                    # Crear gráfico
                    fig = px.line(
                        datos_filtrados,
                        x='fecha',
                        y='precio',
                        color='insumo',
                        title='Evolución de Precios de Insumos',
                        labels={'fecha': 'Fecha', 'precio': 'Precio (S/)', 'insumo': 'Insumo'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar tabla de datos
                    tabla_datos = datos_filtrados[['fecha', 'insumo', 'precio']]
                    tabla_datos.columns = ['Fecha', 'Insumo', 'Precio']
                    st.dataframe(tabla_datos.sort_values(['Insumo', 'Fecha']), use_container_width=True)
                else:
                    st.info("No hay datos para el rango de fechas seleccionado.")
            else:
                st.info("Seleccione al menos un insumo para visualizar su evolución de precios.")
        else:
            st.info("No hay datos históricos de precios registrados.")
    
    elif tipo_reporte == "Margen de Ganancia por Producto":
        st.subheader("Análisis de Margen de Ganancia")
        
        # Cargar datos
        productos = cargar_productos()
        
        if not productos.empty:
            # Calcular márgenes para todos los productos
            margenes = []
            
            for _, producto in productos.iterrows():
                costo, _ = calcular_costo_receta(producto['id'])
                precio_venta = producto['precio_venta']
                margen = precio_venta - costo
                margen_porcentaje = (margen / precio_venta) * 100 if precio_venta > 0 else 0
                
                margenes.append({
                    'producto': producto['nombre'],
                    'costo': costo,
                    'precio_venta': precio_venta,
                    'margen': margen,
                    'margen_porcentaje': margen_porcentaje
                })
            
            margenes_df = pd.DataFrame(margenes)
            
            # Crear gráfico de barras para margen por producto
            fig1 = px.bar(
                margenes_df,
                x='producto',
                y=['costo', 'margen'],
                title='Costo vs Margen por Producto',
                barmode='stack',
                labels={'value': 'Monto (S/)', 'producto': 'Producto', 'variable': 'Tipo'}
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Crear gráfico de porcentaje de margen
            fig2 = px.bar(
                margenes_df,
                x='producto',
                y='margen_porcentaje',
                title='Porcentaje de Margen por Producto',
                labels={'margen_porcentaje': '% Margen', 'producto': 'Producto'}
            )
            fig2.update_layout(yaxis_ticksuffix="%")
            st.plotly_chart(fig2, use_container_width=True)
            
            # Mostrar tabla de datos
            tabla_margenes = margenes_df.copy()
            tabla_margenes.columns = ['Producto', 'Costo (S/)', 'Precio Venta (S/)', 'Margen (S/)', 'Margen (%)']
            st.dataframe(tabla_margenes, use_container_width=True)
        else:
            st.info("No hay productos registrados para analizar márgenes.")
    
    elif tipo_reporte == "Consumo de Insumos":
        st.subheader("Análisis de Consumo de Insumos")
        
        # Cargar datos de consumos
        response = sb.table('consumo_detalles').select('*').execute()
        consumos = pd.DataFrame(response.data)
        
        if not consumos.empty:
            # Cargar datos de consumos con fechas
            query = """
            SELECT cd.*, c.fecha, i.nombre as insumo_nombre, i.unidad_medida
            FROM consumo_detalles cd
            JOIN consumos c ON cd.consumo_id = c.id
            JOIN insumos i ON cd.insumo_id = i.id
            """
            response = sb.table('consumo_detalles').select('*').execute()
            consumos_completos = pd.DataFrame(response.data)
            
            # Rango de fechas
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input("Fecha Inicio:", value=datetime.now() - timedelta(days=30), key="consumo_fecha_inicio")
            with col2:
                fecha_fin = st.date_input("Fecha Fin:", value=datetime.now(), key="consumo_fecha_fin")
            
            # Filtrar datos por fecha
            consumos_filtrados = consumos_completos[
                (pd.to_datetime(consumos_completos['fecha']) >= pd.to_datetime(fecha_inicio)) &
                (pd.to_datetime(consumos_completos['fecha']) <= pd.to_datetime(fecha_fin))
            ]
            
            if not consumos_filtrados.empty:
                # Agrupar por insumo
                consumo_por_insumo = consumos_filtrados.groupby('insumo_id').agg({
                    'cantidad': 'sum',
                    'insumo_nombre': 'first',
                    'unidad_medida': 'first'
                }).reset_index()
                
                # Crear gráfico de consumo por insumo
                fig = px.bar(
                    consumo_por_insumo,
                    x='insumo_nombre',
                    y='cantidad',
                    title='Consumo Total por Insumo',
                    labels={'insumo_nombre': 'Insumo', 'cantidad': 'Cantidad Consumida'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Mostrar tabla de datos
                tabla_consumo = consumo_por_insumo[['insumo_nombre', 'cantidad', 'unidad_medida']]
                tabla_consumo.columns = ['Insumo', 'Cantidad Consumida', 'Unidad']
                st.dataframe(tabla_consumo.sort_values('Cantidad Consumida', ascending=False), use_container_width=True)
                
                # Análisis de tendencia de consumo (consumo por día)
                consumos_filtrados['fecha'] = pd.to_datetime(consumos_filtrados['fecha'])
                consumo_diario = consumos_filtrados.groupby([consumos_filtrados['fecha'].dt.date, 'insumo_nombre']).agg({
                    'cantidad': 'sum'
                }).reset_index()
                
                # Seleccionar insumos para tendencia
                insumos_disponibles = consumos_filtrados['insumo_nombre'].unique().tolist()
                insumos_seleccionados = st.multiselect(
                    "Ver Tendencia de Consumo para Insumos:",
                    options=insumos_disponibles,
                    default=insumos_disponibles[:3] if len(insumos_disponibles) >= 3 else insumos_disponibles
                )
                
                if insumos_seleccionados:
                    tendencia_filtrada = consumo_diario[consumo_diario['insumo_nombre'].isin(insumos_seleccionados)]
                    
                    # Crear gráfico de tendencia
                    fig_tendencia = px.line(
                        tendencia_filtrada,
                        x='fecha',
                        y='cantidad',
                        color='insumo_nombre',
                        title='Tendencia de Consumo Diario',
                        labels={'fecha': 'Fecha', 'cantidad': 'Cantidad Consumida', 'insumo_nombre': 'Insumo'}
                    )
                    st.plotly_chart(fig_tendencia, use_container_width=True)
            # else:
            #     st.info("No hay datos de consumo para
