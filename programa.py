import numpy as np
from datetime import datetime
import pandas as pd

def cargar_ramos(ruta_archivo):
    """Lee el archivo .txt y retorna un diccionario con los ramos y sus horarios."""
    datos_ramos = {}
    
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as archivo:
            for linea in archivo:
                linea = linea.strip()
                if not linea:  # Ignora líneas en blanco
                    continue
                    
                partes = linea.split(" ")
                codigo_seccion = partes[0]               # Ej: "CC4101-1"
                codigo_ramo = codigo_seccion.split("-")[0] # Ej: "CC4101"
                bloques_horarios = partes[1:]            # Ej: ["Ma_10:15-11:45", "Ju_10:15-11:45"]
                
                if codigo_ramo not in datos_ramos:
                    datos_ramos[codigo_ramo] = {codigo_seccion: bloques_horarios}
                else:
                    datos_ramos[codigo_ramo][codigo_seccion] = bloques_horarios
                    
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{ruta_archivo}'.")
        return None
    except Exception as e:
        print(f"Error inesperado al leer el archivo: {e}")
        return None
        
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
    
    for combinacion in combinaciones_validas:
        matriz_horario = np.zeros((filas, 6), dtype=object)
        
        nombres_dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
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
    archivo_entrada = "horarios.txt"
    dias_validos = ["Lu", "Ma", "Mi", "Ju", "Vi"]
    
    print(f"Cargando datos desde {archivo_entrada}...")
    datos_ramos = cargar_ramos(archivo_entrada)
    
    if datos_ramos:
        lista_ramos = list(datos_ramos.keys())
        
        print("Calculando combinaciones compatibles...")
        combinaciones = buscar_combinaciones(datos_ramos, lista_ramos)
        
        if not combinaciones:
            print("⚠️ No se encontró ninguna combinación de horario sin choques.")
        else:
            print(f"Se encontraron {len(combinaciones)} opciones. Generando matrices...")
            matrices = generar_matrices(combinaciones, datos_ramos, dias_validos)
            
            print("Exportando...")
            exportar_a_excel(matrices)