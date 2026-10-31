# Optimización logística portuaria · Puerto de Cartagena

Sistema de analítica que convierte los registros de atención de buques del Puerto de Cartagena en un tablero interactivo para tomar decisiones de operación: cuánto esperan los buques para atracar, en qué momentos, qué carga se afecta más y por qué.

**Tablero en línea:** [puerto-cartagena.streamlit.app](https://puerto-cartagena.streamlit.app)

Trabajo Colaborativo Contextualizado (TCC) de **Ciencia de Datos I**, Programa de Ingeniería de Software, Universidad de Cartagena.

## Equipo CIPA DEV-OPS

- Esteban David Domínguez Soto
- Erick German Marrugo Canabal
- Kevin Rafael Ochoa Ochoa
- Sebastian Ortiz Navarro
- Valery Tatiana Espinosa Chamorro

Docente: Roberto Carlos Orozco Bonilla

## Hallazgos principales

| Indicador | Valor |
| --- | --- |
| Tiempo promedio de espera | 1.79 h |
| Ocupación de muelles (supuesto de 10 muelles) | 35.4 % |
| Eficiencia de carga y descarga de contenedores | 263 TEU/h |
| Buques en demora crítica | 17 (10 en alerta roja, 7 en amarilla) |

- **El clima es el factor que más pesa:** con tormenta la espera promedio sube a 6.09 h, 4.4 veces la de un día despejado (1.39 h).
- **Hora pico a las 19:00:** 13 buques llegan en esa franja.
- **Granel Líquido** es la carga que más espera (2.08 h) y **Contenedores** la que menos (1.41 h).
- **Conclusión:** las demoras no vienen de falta de muelles, sino del clima y de la concentración de llegadas.

## Arquitectura de datos (ETL)

```
CSV original  →  Limpieza en Python  →  CSV limpio  →  Tablero
(150 × 9)        (pandas)               (150 × 17)     (Streamlit + Plotly)
```

1. **Extraer:** se lee el CSV original con 150 atenciones de agosto de 2026.
2. **Transformar:** se corrigen nulos, valores imposibles y formatos de fecha, y se crean 8 columnas nuevas (hora de salida, fecha, hora del día, día de la semana, tiempo total en puerto, eficiencia en TEU por hora y nivel de alerta).
3. **Cargar:** se guarda el CSV limpio y un reporte con cada corrección.
4. **Visualizar:** el tablero lee solo el CSV limpio, nunca el original.

## Estructura del repositorio

```
tablero-puerto/
├── .streamlit/
│   └── config.toml              # Tema y colores del tablero
├── fase2/                       # Limpieza de datos
│   ├── limpieza_datos.ipynb     # Notebook con explicaciones paso a paso
│   ├── limpieza_datos.py        # El mismo código como script
│   ├── datos_puerto_limpios.csv # Resultado: datos limpios (lo lee el tablero)
│   └── reporte_limpieza.csv     # Registro de las 5 correcciones
└── fase3/                       # Tablero
    ├── app.py                   # Aplicación de Streamlit
    ├── requirements.txt         # Librerías necesarias
    └── *.png                    # Iconos propios del tablero
```

## Cómo ejecutarlo en tu computador

Requisitos: Python 3.10 o superior.

```bash
# 1. Instalar las librerías
pip install -r fase3/requirements.txt

# 2. Abrir el tablero (desde la carpeta fase3)
cd fase3
python -m streamlit run app.py
```

El tablero se abre en el navegador en `http://localhost:8501`.

### Volver a ejecutar la limpieza

Coloca el archivo original `DATOS LOGICOS PUERTO DE CARTAGENA.csv` dentro de `fase2` (o en la carpeta raíz) y ejecuta:

```bash
cd fase2
python limpieza_datos.py
```

También puedes abrir `limpieza_datos.ipynb` en Jupyter o Google Colab y ejecutar las celdas en orden. El script vuelve a generar `datos_puerto_limpios.csv` y `reporte_limpieza.csv`, y el tablero toma los datos nuevos automáticamente.

## Decisiones de limpieza

| Problema | Registro | Decisión |
| --- | --- | --- |
| Tiempo en muelle de −5 h | REG-1088 | Valor imposible: se reemplaza por la mediana de su tipo de carga |
| Tipo de carga vacío | REG-1042 | Se marca como "Sin Clasificar" en lugar de adivinar |
| Sin hora de atraque ni espera | REG-1015 | Mediana de buques con el mismo tipo de carga y clima; el atraque se recalcula |

Se usa la **mediana** y no el promedio porque los valores extremos no la afectan. Cada valor corregido queda marcado en la columna `Dato_Imputado`.

## Supuestos

- El puerto tiene **10 muelles** (el máximo de buques atracados al mismo tiempo en los datos). Se cambia en `NUM_MUELLES`, al inicio de `app.py` y de la limpieza.
- **Alerta amarilla:** espera mayor a 3 h. **Alerta roja:** espera mayor a 4 h.

## Tecnologías

Python · pandas · Streamlit · Plotly · Jupyter · GitHub · Streamlit Community Cloud
