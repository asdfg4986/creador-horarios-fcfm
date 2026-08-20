# Creador de Horarios FCFM

**Autor:** Franco Iturra H.

## Descripcion

Esta herramienta automatiza la creacion de horarios universitarios sin colisiones (topes de horario). Mediante web scraping, extrae los horarios actualizados directamente del catalogo de cursos y calcula todas las combinaciones posibles utilizando un algoritmo recursivo. Los resultados se exportan automaticamente a un archivo Excel (.xlsx) estructurado y facil de leer.

## Caracteristicas Principales

- **Extraccion automatizada:** Utiliza Requests y BeautifulSoup para obtener los datos desde el portal web de la facultad.
- **Limpieza de datos:** Aplica Expresiones Regulares (Regex) para parsear el HTML en crudo y estructurar los bloques de tiempo saltando caracteres especiales.
- **Algoritmo de resolucion:** Implementa backtracking recursivo para evaluar intersecciones de tiempo (choques) y descartar combinaciones incompatibles.
- **Exportacion a Excel:** Utiliza Pandas y Numpy para estructurar las combinaciones validas en matrices y generar el archivo de salida de forma automatica.

## Requisitos

- Python 3.8 o superior.
- Dependencias principales: pandas, numpy, requests, beautifulsoup4, openpyxl (requerido por pandas para generar archivos de Excel).

## Instalacion y Uso

1. Instala las dependencias necesarias ejecutando el siguiente comando:
```bash
pip install -r requirements.txt
```

2. Ejecuta el script principal desde tu terminal:
```bash
python horarios.py
```

3. Interaccion: El programa presentara una interfaz CLI. Ingresa los codigos de los ramos que deseas inscribir (ej. CC3001, MA2001). Cuando termines, escribe listo.
4. Resultado: El programa descargara los catalogos, calculara las combinaciones y generara un archivo llamado horarios_generados.xlsx en el mismo directorio.

## Decisiones de Diseño

- **Parseo en Crudo (Regex + HTML):** Se decidio procesar las filas HTML como texto en crudo con expresiones regulares para sortear los filtros de decodificacion de BeautifulSoup y manejar las anomalias de caracteres en los dias de la semana de forma 100% segura.
- **Busqueda de Fuerza Bruta Controlada:** Si un codigo ingresado no coincide con el mapeo directo de departamentos, el sistema implementa un barrido de fuerza bruta departamental para asegurar su encuentro sin romper el flujo de ejecucion.
- **Vectores y DataFrames:** La transicion de combinaciones validas hacia matrices de Numpy, y posteriormente a un DataFrame de Pandas, simplifica enormemente la exportacion a Excel, evitando los errores tipicos de formato al escribir archivos CSV manualmente.