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

def extraer_ramos_especificos(lista_codigos, semestre="20262", depto="5"):
    """Descarga el catálogo del departamento y extrae solo los ramos solicitados por el usuario."""
    datos_ramos = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    url = f"https://ucampus.uchile.cl/m/fcfm_catalogo/?semestre={semestre}&depto={depto}"
    
    try:
        print(f"\nConectando al catálogo de la facultad...")
        respuesta = requests.get(url, headers=headers)
        
        # FIX 1: Forzar la codificación a UTF-8 para que lea los tildes correctamente
        respuesta.encoding = 'utf-8' 
        respuesta.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión al catálogo: {e}")
        return None

    soup = BeautifulSoup(respuesta.text, 'html.parser')
    
    # FIX 2: Ampliamos el diccionario para aceptar días con y sin tilde
    mapa_dias = {
        "Lunes": "Lu", "Martes": "Ma", "Miércoles": "Mi", "Miercoles": "Mi",
        "Jueves": "Ju", "Viernes": "Vi", "Sábado": "Sa", "Sabado": "Sa"
    }
    
    # Expresión regular robusta para las horas
    patron_horario = re.compile(r'(Lunes|Martes|Miércoles|Miercoles|Jueves|Viernes|Sábado|Sabado)\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', re.IGNORECASE)

    print("Procesando ramos solicitados...")
    
    for codigo_buscado in lista_codigos:
        # 1. Buscamos el div que tiene el ID (el que tiene el título)
        div_titulo = soup.find('div', id=codigo_buscado)
        
        if not div_titulo:
            print(f"Ramo {codigo_buscado} no encontrado (revisa que pertenezca a depto={depto}).")
            continue
            
        print(f"{codigo_buscado} encontrado.")
        datos_ramos[codigo_buscado] = {}
        
        # 2. EL FIX CLAVE: Subimos al contenedor principal (<div class="ramo">)
        ramo_html = div_titulo.parent
        
        # 3. Ahora sí, buscamos las secciones dentro de todo el contenedor del ramo
        filas_seccion = ramo_html.find_all('tr')
        
        for fila in filas_seccion:
            id_seccion = fila.get('id')
            if not id_seccion or not id_seccion.startswith(codigo_buscado):
                continue
            
            # --- EL ARREGLO DEFINITIVO ---
            # Ya no usamos get_text(). Convertimos TODA la fila HTML en texto y a minúsculas.
            # Así nos saltamos los filtros y decodificaciones automáticas de BeautifulSoup.
            html_crudo = str(fila).lower()
            
            # La Regex Inmortal: 
            # \S* significa "cero o más caracteres que NO sean espacios".
            # Buscará algo que empiece con 'mi', tenga basura en medio o no, y termine en 'rcoles'.
            # Esto atrapa "miercoles", "miércoles", "mi&eacute;rcoles", "miÃ©rcoles", etc.
            patron_horario = re.compile(r'(lunes|martes|mi\S*rcoles|jueves|viernes|sa\S*bado)\s+(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})')
            
            bloques_encontrados = patron_horario.findall(html_crudo)
            bloques_formateados = []
            
            for dia, inicio, fin in set(bloques_encontrados):
                # Como 'dia' ahora puede contener mutaciones extrañas,
                # solo revisamos cómo empieza la palabra para asignar la columna de forma 100% segura.
                if dia.startswith('lu'): dia_corto = 'Lu'
                elif dia.startswith('ma'): dia_corto = 'Ma'
                elif dia.startswith('mi'): dia_corto = 'Mi'
                elif dia.startswith('ju'): dia_corto = 'Ju'
                elif dia.startswith('vi'): dia_corto = 'Vi'
                elif dia.startswith('sa'): dia_corto = 'Sa'
                else: continue
                
                bloques_formateados.append(f"{dia_corto}_{inicio}-{fin}")
            
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
    
    for i, matriz in enumerate(matrices):
        datos_exportar.append([f"--- OPCIÓN DE HORARIO {i+1} ---", "", "", "", "", ""])
        
        for fila in matriz:
            datos_exportar.append(fila)
            
        datos_exportar.append(["", "", "", "", "", ""])
        datos_exportar.append(["", "", "", "", "", ""])
        
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
    dias_validos = ["Lu", "Ma", "Mi", "Ju", "Vi"]
    semestre_actual = "20262" # Puedes cambiarlo según necesites
    
    # 1. Interacción con el usuario
    ramos_elegidos = solicitar_ramos_usuario()
    
    if not ramos_elegidos:
        print("No ingresaste ningún ramo. Cerrando programa.")
    else:
        # 2. Extracción precisa
        datos_ramos = extraer_ramos_especificos(ramos_elegidos, semestre=semestre_actual)
        
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