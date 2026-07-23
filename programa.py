import numpy as np

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

def compatibilidad(vars, hors_ocup = [], seccs_compatibles = [], i = 0):
    assert type(vars) == dict
    global ramos, dias, horas_in, combinaciones

    if i == len(ramos):
        return seccs_compatibles
    else:
        secciones = vars[ramos[i]]
        for seccion in secciones:
            j = 0
            aux1 = []
            for hora in vars[ramos[i]][seccion]:
                dia = hora[:2]
                x = dias.index(dia)
                hora_in = hora[3:8]
                y = horas_in.index(hora_in)
                if (x + 1, y + 1) in hors_ocup:
                    j += 1
                    break
                else:
                    aux1.append((x + 1, y + 1))
            if j == 0:
                combinacion = compatibilidad(vars, hors_ocup + aux1, seccs_compatibles + [seccion], i + 1)
                if combinacion != None:
                    combinaciones.append(combinacion)


def crear_matriz():
    global combinaciones, var, dias, horas_in, matrices
    
    for combinacion in combinaciones:
        mat = np.zeros((7, 6), dtype=object)
        dias_com = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
        horas_in_com = ["08:30-10:00", "10:15-11:45", "12:00-13:30", "14:30-16:00", "16:15-17:45", "18:00-19:30"]
        mat[0] = [0] + dias_com

        for i in range(7):
            if i == 0:
                pass
            else:
                mat[i][0] = horas_in_com[i-1]

        for seccion in combinacion:
            ramo = seccion.split("-")
            ramo = ramo[0]
            horario = var[ramo][seccion]
            for hora in horario:
                dia = hora[:2]
                x = dias.index(dia) + 1
                hora_in = hora[3:8]
                y = horas_in.index(hora_in) + 1
                mat[y][x] = seccion
        matrices.append(mat)        
        
def crear_archivo():
    global matrices
    archivo = open("horarios_excel.txt", "w")
    for matriz in matrices:
        for fila in matriz:
            linea = ""
            for columna in fila:
                if columna == 0:
                    linea += ";"
                else:
                    linea += columna + ";"
            archivo.write(linea + "\n")
        archivo.write(";;;;;;;\n")
        archivo.write(";;;;;;;\n")
    archivo.close()

if __name__ == "__main__":
    var = crear_vars("horarios.txt")
    ramos = []
    for key in var:
        ramos.append(key)
    dias = ["Lu", "Ma", "Mi", "Ju", "Vi"]
    horas_in = ["08:30", "10:15", "12:00", "14:30", "16:15", "18:00"]
    combinaciones = []

    compatibilidad(var)
    matrices = []

    crear_matriz()

    crear_archivo()