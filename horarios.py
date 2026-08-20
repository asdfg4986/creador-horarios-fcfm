import numpy as np
from datetime import datetime
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup

def solicitar_ramos_usuario():
    """Pregunta al usuario qué ramos desea buscar interactivamente."""
    print("\n" + "="*40)
    print("CREADOR DE HORARIOS FCFM")
    print("="*40)
    print("Ingresa los códigos de los ramos que quieres inscribir (ej: CC3001, MA2001).")
    print("Escribe 'listo' cuando hayas terminado.\n")
    
    ramos_deseados = []
    
    while True:
        codigo = input("▶ Código del ramo (o 'listo'): ").strip().upper()
        
        # Limpiamos espacios intermedios por si escriben "CC 3001"
        codigo = codigo.replace(" ", "")
        
        if codigo == 'LISTO':
            break
            
        if codigo:
            ramos_deseados.append(codigo)
            
    # Retornamos la lista sin duplicados usando set()
    return list(set(ramos_deseados))

def clasificar_ramos(lista_codigos, mapa_deptos):
    """Analiza los prefijos de los códigos y los agrupa por departamento."""
    ramos_por_depto = {}
    ramos_desconocidos = []
    
    for codigo in lista_codigos:
        prefijo = codigo[:2].upper()
        depto_id = mapa_deptos.get(prefijo)
        
        if depto_id:
            if depto_id not in ramos_por_depto:
                ramos_por_depto[depto_id] = []
            ramos_por_depto[depto_id].append(codigo)
        else:
            ramos_desconocidos.append(codigo)
            
    return ramos_por_depto, ramos_desconocidos

def obtener_todos_los_ramos(lista_codigos, semestre="20262"):
    """Orquesta la descarga de datos utilizando enrutamiento y búsqueda de respaldo."""
    mapa_deptos = {
        "AA": "12060003", "AS": "3", "CC": "5", "CI": "6",
        "CM": "306", "DR": "7", "EH": "8", "EI": "9",
        "FT": "9", "CD": "12060002", "IE": "12060002", "EL": "10",
        "FI": "13", "GF": "15", "GL": "16", "IN": "19",
        "MA": "21", "ME": "22", "MI": "23", "BT": "307", "IQ": "307"
    }
    
    # Delegamos la clasificación a la función experta
    ramos_por_depto, ramos_desconocidos = clasificar_ramos(lista_codigos, mapa_deptos)
    
    datos_totales_malla = {}
    
    # Coordinamos la descarga normal
    for depto, codigos_a_buscar in ramos_por_depto.items():
        datos_parciales = extraer_ramos_por_depto(codigos_a_buscar, depto, semestre)
        if datos_parciales:
            datos_totales_malla.update(datos_parciales)

    # Coordinamos la búsqueda de respaldo para ramos con prefijo desconocido
    if ramos_desconocidos:
        print("\n" + "="*50)
        print(f"Iniciando BÚSQUEDA DE RESPALDO para ramos desconocidos: {', '.join(ramos_desconocidos)}")
        print("="*50)
        
        deptos_a_barrer = list(set(mapa_deptos.values()))
        ramos_pendientes = set(ramos_desconocidos)
        
        for depto in deptos_a_barrer:
            if not ramos_pendientes:
                break 
                
            datos_parciales = extraer_ramos_por_depto(list(ramos_pendientes), depto, semestre)
            
            if datos_parciales:
                datos_totales_malla.update(datos_parciales)
                for ramo_encontrado in datos_parciales.keys():
                    ramos_pendientes.remove(ramo_encontrado)

        if ramos_pendientes:
            print("\n ADVERTENCIA CRÍTICA: RAMOS NO ENCONTRADOS")
            print(f" Los siguientes códigos no existen en los departamentos de la facultad: {', '.join(ramos_pendientes)}")
            print(" Se generará una versión PARCIAL del horario excluyendo estos ramos.\n")
            
    return datos_totales_malla

def descargar_html_departamento(depto, semestre, prefijos):
    """Se encarga exclusivamente de la conexión HTTP y retorna el HTML crudo."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    url = f"https://ucampus.uchile.cl/m/fcfm_catalogo/?semestre={semestre}&depto={depto}"
    print(f"\nDescargando catálogo de la facultad para el departamento ({prefijos})...")
    
    try:
        respuesta = requests.get(url, headers=headers)
        respuesta.encoding = 'utf-8' 
        respuesta.raise_for_status()
        return respuesta.text
    except requests.exceptions.RequestException as e:
        print(f"Error al cargar el departamento {depto}: {e}")
        return None

def formatear_bloques_horarios(html_crudo, patron_horario, patron_control):
    """Limpia los controles y formatea los días a partir de un fragmento HTML."""
    # Eliminamos los controles de la cadena
    html_crudo = patron_control.sub("", html_crudo)
    
    # Extraemos los horarios
    bloques_encontrados = patron_horario.findall(html_crudo)
    bloques_formateados = []
    
    for dia, inicio, fin in set(bloques_encontrados):
        if dia.startswith('lu'): dia_corto = 'Lu'
        elif dia.startswith('ma'): dia_corto = 'Ma'
        elif dia.startswith('mi'): dia_corto = 'Mi'
        elif dia.startswith('ju'): dia_corto = 'Ju'
        elif dia.startswith('vi'): dia_corto = 'Vi'
        elif dia.startswith('sa'): dia_corto = 'Sa'
        else: continue
        
        bloques_formateados.append(f"{dia_corto}_{inicio}-{fin}")
        
    return bloques_formateados

def extraer_ramos_por_depto(lista_codigos, depto, semestre="20262"):
    """Coordina la descarga y extracción para un departamento específico."""
    datos_ramos = {}
    prefijos = ", ".join(sorted(set(codigo[:2].upper() for codigo in lista_codigos)))

    # Delegamos la red (I/O)
    html_texto = descargar_html_departamento(depto, semestre, prefijos)
    if not html_texto:
        return {} # Retornamos diccionario vacío para que el orquestador no colapse

    # Parseo
    soup = BeautifulSoup(html_texto, 'html.parser')

    patron_horario = re.compile(r'(lunes|martes|mi\S*rcoles|jueves|viernes|sa\S*bado)\s+(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})')
    patron_control = re.compile(r'control[a-z]*\s*:.*?(?=<|&#10;|"|\n)')

    for codigo_buscado in lista_codigos:
        div_titulo = soup.find('div', id=codigo_buscado)
        
        if not div_titulo:
            print(f"Ramo {codigo_buscado} no encontrado en este departamento.")
            continue
            
        print(f"{codigo_buscado} encontrado.")
        datos_ramos[codigo_buscado] = {}
        
        ramo_html = div_titulo.parent
        filas_seccion = ramo_html.find_all('tr')
        
        for fila in filas_seccion:
            id_seccion = fila.get('id')
            if not id_seccion or not id_seccion.startswith(codigo_buscado):
                continue
            
            # Delegamos la limpieza de texto a nuestra función experta
            bloques_formateados = formatear_bloques_horarios(str(fila).lower(), patron_horario, patron_control)
            
            if bloques_formateados:
                datos_ramos[codigo_buscado][id_seccion] = bloques_formateados
                
        if not datos_ramos[codigo_buscado]:
            del datos_ramos[codigo_buscado]
            print(f"{codigo_buscado} sin secciones disponibles o horarios 'Por fijar'.")

    return datos_ramos

def hay_choque(inicio_A, fin_A, inicio_B, fin_B):
    """Verifica si dos rangos de tiempo se superponen."""
    formato = "%H:%M"
    t_inicio_A = datetime.strptime(inicio_A, formato)
    t_fin_A = datetime.strptime(fin_A, formato)
    t_inicio_B = datetime.strptime(inicio_B, formato)
    t_fin_B = datetime.strptime(fin_B, formato)
    
    # Retorna True si los intervalos se solapan
    return (t_inicio_A < t_fin_B) and (t_fin_A > t_inicio_B)

def buscar_combinaciones(datos_ramos, lista_ramos, indice_ramo=0, horarios_ocupados=None, combinacion_actual=None, combinaciones_validas=None):
    """Función recursiva que busca todas las combinaciones de horario sin choques."""
    if horarios_ocupados is None: 
        horarios_ocupados = []
    if combinacion_actual is None: 
        combinacion_actual = []
    if combinaciones_validas is None: 
        combinaciones_validas = []

    # Condición de salida: si ya revisamos todos los ramos, guardamos la combinación exitosa
    if indice_ramo == len(lista_ramos):
        combinaciones_validas.append(combinacion_actual)
        return combinaciones_validas
    
    codigo_ramo = lista_ramos[indice_ramo]
    secciones = datos_ramos[codigo_ramo]
    
    for seccion in secciones:
        hubo_choque = False
        horarios_provisionales = []
        
        horarios_seccion = datos_ramos[codigo_ramo][seccion]
        
        for hora in horarios_seccion:
            dia = hora[:2]
            tiempos = hora[3:].split("-")
            inicio_clase = tiempos[0]
            fin_clase = tiempos[1]
            
            for ocupado in horarios_ocupados:
                dia_ocupado, inicio_ocupado, fin_ocupado = ocupado
                
                if dia == dia_ocupado:
                    if hay_choque(inicio_clase, fin_clase, inicio_ocupado, fin_ocupado):
                        hubo_choque = True
                        break 
            
            if hubo_choque:
                break 
            else:
                horarios_provisionales.append((dia, inicio_clase, fin_clase))
                
        if not hubo_choque:
            # Llamada recursiva pasando el estado actualizado
            buscar_combinaciones(
                datos_ramos, 
                lista_ramos, 
                indice_ramo + 1, 
                horarios_ocupados + horarios_provisionales, 
                combinacion_actual + [seccion], 
                combinaciones_validas
            )
            
    return combinaciones_validas

def generar_matrices(combinaciones_validas, datos_ramos, dias_semana):
    """Convierte las combinaciones válidas en matrices estructuradas para el Excel."""
    matrices_generadas = []
    bloques_base = [
        "08:30-10:00", "10:15-11:45", "12:00-13:30", 
        "14:30-16:00", "16:15-17:45", "18:00-19:30"
    ]
    
    filas = len(bloques_base) + 1
    # Calculamos la cantidad de columnas según los días que usaremos + 1 para la columna de las horas
    columnas = len(dias_semana) + 1 
    
    for combinacion in combinaciones_validas:
        matriz_horario = np.zeros((filas, columnas), dtype=object)
        
        # Diccionario para traducir de "Lu" a "Lunes" en los encabezados dinámicamente
        mapa_nombres = {"Lu": "Lunes", "Ma": "Martes", "Mi": "Miércoles", "Ju": "Jueves", "Vi": "Viernes", "Sa": "Sábado"}
        nombres_dias = [mapa_nombres[d] for d in dias_semana]
        
        matriz_horario[0] = [0] + nombres_dias
        
        for i, bloque in enumerate(bloques_base):
            matriz_horario[i+1][0] = bloque
            
        for seccion in combinacion:
            codigo_ramo = seccion.split("-")[0]
            horarios = datos_ramos[codigo_ramo][seccion]
            
            for hora in horarios:
                dia = hora[:2]
                tiempos = hora[3:].split("-")
                inicio_clase = tiempos[0]
                fin_clase = tiempos[1]
                
                columna_dia = dias_semana.index(dia) + 1
                
                for fila_bloque, bloque in enumerate(bloques_base):
                    inicio_base, fin_base = bloque.split("-")
                    
                    if hay_choque(inicio_clase, fin_clase, inicio_base, fin_base):
                        matriz_horario[fila_bloque+1][columna_dia] = seccion
                        
        matrices_generadas.append(matriz_horario)
        
    return matrices_generadas
        
def exportar_a_excel(matrices, nombre_archivo="horarios_generados.xlsx"):
    """Exporta las matrices generadas a un archivo Excel (.xlsx)."""
    if not matrices:
        print("No hay matrices para exportar.")
        return
        
    datos_exportar = []

    num_columnas = matrices[0].shape[1]
    
    for i, matriz in enumerate(matrices):
        # Creamos una fila vacía con el tamaño exacto necesario
        fila_vacia = [""] * num_columnas
        
        # Copiamos la fila vacía y le ponemos el título en la primera celda
        fila_titulo = list(fila_vacia)
        fila_titulo[0] = f"--- OPCIÓN DE HORARIO {i+1} ---"
        
        datos_exportar.append(fila_titulo)
        
        # Guardamos la matriz convirtiendo las filas de numpy a listas estándar de Python
        for fila in matriz:
            datos_exportar.append(fila.tolist())
            
        datos_exportar.append(fila_vacia)
        datos_exportar.append(fila_vacia)
        
    df = pd.DataFrame(datos_exportar)
    df = df.replace(0, "")
    
    try:
        df.to_excel(nombre_archivo, index=False, header=False)
        print(f"¡Éxito! Horarios guardados en '{nombre_archivo}'.")
    except PermissionError:
        print(f"Error de permisos: Cierra el archivo '{nombre_archivo}' e intenta nuevamente.")
    except Exception as e:
        print(f"Error inesperado al guardar el Excel: {e}")

if __name__ == "__main__":
    dias_validos = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa"]
    semestre_actual = "20262" # Cambiar segun se necesite
    
    # Interacción con el usuario
    ramos_elegidos = solicitar_ramos_usuario()
    
    if not ramos_elegidos:
        print("No ingresaste ningún ramo. Cerrando programa.")
    else:
        # Extracción precisa
        datos_ramos = obtener_todos_los_ramos(ramos_elegidos, semestre=semestre_actual)
        
        if datos_ramos:
            lista_ramos = list(datos_ramos.keys())
            
            print(f"\nCalculando combinaciones compatibles para {len(lista_ramos)} ramos...")
            combinaciones = buscar_combinaciones(datos_ramos, lista_ramos)
            
            if not combinaciones:
                print("No se encontró ninguna combinación de horario sin choques para esos ramos.")
            else:
                print(f"Se encontraron {len(combinaciones)} opciones posibles. Generando matrices...")
                matrices = generar_matrices(combinaciones, datos_ramos, dias_validos)
                
                print("Exportando...")
                exportar_a_excel(matrices)