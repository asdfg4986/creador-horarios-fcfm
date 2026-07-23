import numpy as np
from datetime import datetime
import pandas as pd

def crear_vars(arch):
    assert type(arch) == str

    archivo = open(arch, "r")

    ramos = {}

    for linea in archivo:
        linea = linea.strip()
        linea_sep = linea.split(" ")
        aux1 = linea_sep[0].split("-")[0]
        if ramos.get(aux1) == None:
            ramos[aux1] = {linea_sep[0]:linea_sep[1:]}
        else:
            aux2 = ramos[aux1]
            aux2[linea_sep[0]] = linea_sep[1:]
    
    archivo.close()
    return ramos

def hay_choque(inicio_A, fin_A, inicio_B, fin_B):
    formato = "%H:%M"
    t_inicio_A = datetime.strptime(inicio_A, formato)
    t_fin_A = datetime.strptime(fin_A, formato)
    t_inicio_B = datetime.strptime(inicio_B, formato)
    t_fin_B = datetime.strptime(fin_B, formato)
    
    # Retorna True si los intervalos se solapan
    return (t_inicio_A < t_fin_B) and (t_fin_A > t_inicio_B)

def compatibilidad(vars, hors_ocup = None, seccs_compatibles = None, i = 0):
    assert type(vars) == dict
    global ramos, combinaciones

    if hors_ocup is None:
        hors_ocup = []
    if seccs_compatibles is None:
        seccs_compatibles = []

    if i == len(ramos):
        return seccs_compatibles
    
    secciones = vars[ramos[i]]
    for seccion in secciones:
        choque = False
        aux1 = [] # Guardará los horarios provisionales de esta sección
        
        horarios_seccion = vars[ramos[i]][seccion]
        
        for hora in horarios_seccion:
            # Desarmamos el string "Ma_10:15-11:45"
            dia = hora[:2]
            tiempos = hora[3:].split("-")
            inicio = tiempos[0]
            fin = tiempos[1]
            
            # Revisamos si choca con los horarios ya ocupados
            for ocupado in hors_ocup:
                dia_ocupado, inicio_ocupado, fin_ocupado = ocupado
                
                if dia == dia_ocupado: # Solo revisamos si es el mismo día
                    if hay_choque(inicio, fin, inicio_ocupado, fin_ocupado):
                        choque = True
                        break # Hay choque, dejamos de buscar en hors_ocup
            
            if choque:
                break # Dejamos de procesar los horarios de esta sección
            else:
                aux1.append((dia, inicio, fin))
                
        # Si revisamos todos los bloques de la sección y j == 0 (no hubo choque)
        if not choque:
            combinacion = compatibilidad(vars, hors_ocup + aux1, seccs_compatibles + [seccion], i + 1)
            if combinacion != None:
                combinaciones.append(combinacion)

def crear_matriz():
    global combinaciones, var, dias, matrices
    
    bloques_base = [
        "08:30-10:00", 
        "10:15-11:45", 
        "12:00-13:30", 
        "14:30-16:00", 
        "16:15-17:45", 
        "18:00-19:30"
    ]
    
    for combinacion in combinaciones:
        # 2. Calculas la cantidad de filas dinámicamente
        filas = len(bloques_base) + 1
        
        # 3. Creas la matriz usando la variable 'filas' y el número de columnas (6)
        mat = np.zeros((filas, 6), dtype=object)
        
        dias_com = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
        mat[0] = [0] + dias_com
        
        # Escribimos los bloques base en la primera columna (Eje Y)
        for i, bloque in enumerate(bloques_base):
            mat[i+1][0] = bloque
            
        for seccion in combinacion:
            ramo = seccion.split("-")[0]
            horarios = var[ramo][seccion]
            
            for hora in horarios:
                dia = hora[:2]
                tiempos = hora[3:].split("-")
                inicio_clase = tiempos[0]
                fin_clase = tiempos[1]
                
                # Posición X (columna del día)
                x = dias.index(dia) + 1
                
                # Revisamos con cuáles bloques base choca este horario
                for y, bloque in enumerate(bloques_base):
                    inicio_base, fin_base = bloque.split("-")
                    
                    # Usamos la misma lógica matemática que en compatibilidad
                    if hay_choque(inicio_clase, fin_clase, inicio_base, fin_base):
                        # Si el horario de la clase toca este bloque base, lo asignamos.
                        # Si la clase dura 3 horas, este 'if' se cumplirá 2 veces.
                        mat[y+1][x] = seccion
                        
        matrices.append(mat)
        
def crear_archivo_excel():
    global matrices
    datos_exportar = []
    
    for i, matriz in enumerate(matrices):
        # 1. Agregamos un título para identificar qué combinación es
        datos_exportar.append([f"--- OPCIÓN DE HORARIO {i+1} ---", "", "", "", "", ""])
        
        # 2. Insertamos los datos de la matriz dinámica que ya creamos
        for fila in matriz:
            datos_exportar.append(fila)
            
        # 3. Agregamos dos filas vacías de separación (reemplaza tus antiguas líneas de ;;;;)
        datos_exportar.append(["", "", "", "", "", ""])
        datos_exportar.append(["", "", "", "", "", ""])
        
    # 4. Convertimos toda la lista a un DataFrame de pandas
    df = pd.DataFrame(datos_exportar)
    
    # 5. Limpiamos los 0 que dejaba numpy en las casillas sin clases
    df = df.replace(0, "")
    
    # 6. Exportamos directamente a .xlsx
    # index=False y header=False evitan que pandas imprima sus propios números de fila y columna
    df.to_excel("horarios_generados.xlsx", index=False, header=False)

if __name__ == "__main__":
    # Si más adelante implementas el Web Scraping, 
    # solo cambias esta línea por: var = extraer_vars_web("URL")
    var = crear_vars("horarios.txt")
    
    # Extraemos los nombres de los ramos directamente del diccionario
    ramos = list(var.keys())
    
    # Mantenemos los días porque crear_matriz aún los usa para las columnas (eje X)
    dias = ["Lu", "Ma", "Mi", "Ju", "Vi"]
    
    # Inicializamos las listas globales vacías
    combinaciones = []
    matrices = []

    print("Calculando combinaciones compatibles...")
    compatibilidad(var)
    
    if len(combinaciones) == 0:
        print("No se encontró ninguna combinación de horario sin choques.")
    else:
        print(f"Se encontraron {len(combinaciones)} combinaciones posibles. Generando matrices...")
        crear_matriz()
        
        print("Exportando a Excel...")
        crear_archivo_excel()
        
        print("¡Listo! Revisa el archivo 'horarios_generados.xlsx'.")