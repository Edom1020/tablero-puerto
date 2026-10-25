# %% [markdown]
# # Fase 2: Limpieza de datos (ETL)
# **TCC: Optimización Logística Portuaria, Puerto de Cartagena**
#
# Este script sigue las tres etapas de un pipeline ETL:
# 1. **Extracción:** leer el CSV original.
# 2. **Transformación:** revisar la calidad, corregir nulos, duplicados, fechas y valores imposibles, y crear variables nuevas.
# 3. **Carga:** guardar el CSV limpio que usará el tablero, junto con un reporte de cambios.
#
# Supuestos acordados en la Fase 1:
# - El puerto tiene **10 muelles** (el máximo de buques atracados al mismo tiempo en los datos).
# - **Demora crítica:** alerta amarilla con más de 3 horas de espera y alerta roja con más de 4 horas.

# %%
from pathlib import Path

import pandas as pd

# Rutas: el script busca el CSV original en su misma carpeta o en la carpeta de arriba
CARPETA = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
NOMBRE_ORIGINAL = "DATOS LOGICOS PUERTO DE CARTAGENA.csv"
ARCHIVO_ORIGINAL = next((c / NOMBRE_ORIGINAL for c in (CARPETA, CARPETA.parent) if (c / NOMBRE_ORIGINAL).exists()),
                        CARPETA / NOMBRE_ORIGINAL)
ARCHIVO_LIMPIO = CARPETA / "datos_puerto_limpios.csv"
ARCHIVO_REPORTE = CARPETA / "reporte_limpieza.csv"
ARCHIVO_EXCEL = CARPETA / "datos_puerto_limpios.xlsx"

# Parámetros del negocio (se cambian aquí y todo el script se ajusta)
NUM_MUELLES = 10
UMBRAL_AMARILLO_H = 3
UMBRAL_ROJO_H = 4
FORMATO_FECHA = "%Y-%m-%d %H:%M"

# Aquí se va anotando cada corrección para el reporte de calidad
cambios = []


def registrar(id_registro, columna, valor_antes, valor_despues, motivo):
    cambios.append({
        "ID_Registro": id_registro,
        "Columna": columna,
        "Valor_Original": valor_antes,
        "Valor_Nuevo": valor_despues,
        "Motivo": motivo,
    })

# %% [markdown]
# ## 1. Extracción
# Leemos el archivo y miramos su forma (filas × columnas) y los tipos de dato.
# Las fechas llegan como texto (`str`): eso hay que corregirlo.

# %%
df_original = pd.read_csv(ARCHIVO_ORIGINAL)
df = df_original.copy()  # trabajamos sobre una copia para no perder el original

print(f"Filas: {df.shape[0]}  |  Columnas: {df.shape[1]}")
print(df.dtypes)
df.head()

# %% [markdown]
# ## 2. Diagnóstico de calidad
# Antes de corregir hay que **medir**: cuántos nulos tiene cada columna, si hay duplicados y si hay valores imposibles.

# %%
print("Valores nulos por columna:")
print(df.isna().sum())
print(f"\nFilas duplicadas exactas: {df.duplicated().sum()}")
print(f"IDs de registro repetidos: {df['ID_Registro'].duplicated().sum()}")
print(f"Tiempos en muelle <= 0: {(df['Tiempo_Muelle_Horas'] <= 0).sum()}")
print(f"Tiempos de espera < 0: {(df['Tiempo_Espera_Horas'] < 0).sum()}")
print(f"TEUs negativos: {(df['TEUs_Ocupados'] < 0).sum()}")

df[df.isna().any(axis=1) | (df["Tiempo_Muelle_Horas"] <= 0)]

# %% [markdown]
# ## 3. Transformación
# ### 3.1 Estandarizar textos
# Quitamos espacios sobrantes al inicio y al final. Así, por ejemplo, `"Despejado "` y `"Despejado"` no quedan como dos categorías distintas.

# %%
for col in ["ID_Registro", "Buque", "Tipo_Carga", "Condicion_Climatica"]:
    df[col] = df[col].str.strip()

print(df["Tipo_Carga"].value_counts(dropna=False))
print(df["Condicion_Climatica"].value_counts(dropna=False))

# %% [markdown]
# ### 3.2 Eliminar duplicados
# Un registro duplicado haría contar dos veces el mismo buque e inflaría los promedios.
# Se eliminan las filas idénticas y luego los IDs repetidos, conservando la primera aparición.
# En este dataset no se encontraron, pero el código queda listo por si llega un archivo nuevo que sí los tenga.

# %%
filas_antes = len(df)
for _, fila in df[df.duplicated(keep="first")].iterrows():
    registrar(fila["ID_Registro"], "(fila completa)", "duplicada", "eliminada", "Fila duplicada exacta")
df = df.drop_duplicates(keep="first")

for _, fila in df[df["ID_Registro"].duplicated(keep="first")].iterrows():
    registrar(fila["ID_Registro"], "ID_Registro", fila["ID_Registro"], "eliminada", "ID de registro repetido")
df = df.drop_duplicates(subset="ID_Registro", keep="first")

print(f"Duplicados eliminados: {filas_antes - len(df)}")

# %% [markdown]
# ### 3.3 Formato de fechas
# Convertimos el texto `2026-08-12 21:43` en una **fecha real** (`datetime`), que permite restar horas y agrupar por hora o día.
# `errors="coerce"` convierte en nulo cualquier fecha mal escrita en lugar de detener el programa.

# %%
df["Hora_Llegada"] = pd.to_datetime(df["Hora_Llegada"], format=FORMATO_FECHA, errors="coerce")
df["Hora_Atraque"] = pd.to_datetime(df["Hora_Atraque"], format=FORMATO_FECHA, errors="coerce")
print(df[["Hora_Llegada", "Hora_Atraque"]].dtypes)

# Sin hora de llegada el registro no sirve para ningún KPI, así que se elimina
sin_llegada = df["Hora_Llegada"].isna()
for id_reg in df.loc[sin_llegada, "ID_Registro"]:
    registrar(id_reg, "Hora_Llegada", "nulo", "eliminada", "Sin hora de llegada no se puede analizar")
df = df[~sin_llegada]

# %% [markdown]
# ### 3.4 Valores imposibles
# Un buque no puede estar **−5 horas** en el muelle. Lo tratamos como un error de digitación: lo volvemos nulo y en el paso siguiente se rellena igual que los otros nulos.

# %%
invalidos = df["Tiempo_Muelle_Horas"] <= 0
for _, fila in df[invalidos].iterrows():
    registrar(fila["ID_Registro"], "Tiempo_Muelle_Horas", fila["Tiempo_Muelle_Horas"], "nulo (temporal)",
              "Valor imposible (<= 0 horas)")
df.loc[invalidos, "Tiempo_Muelle_Horas"] = pd.NA

invalidos_espera = df["Tiempo_Espera_Horas"] < 0
for _, fila in df[invalidos_espera].iterrows():
    registrar(fila["ID_Registro"], "Tiempo_Espera_Horas", fila["Tiempo_Espera_Horas"], "nulo (temporal)",
              "Valor imposible (< 0 horas)")
df.loc[invalidos_espera, "Tiempo_Espera_Horas"] = pd.NA

# %% [markdown]
# ### 3.5 Tratamiento de nulos
# No todos los nulos se tratan igual. La estrategia depende de la columna:
#
# | Columna | Estrategia | Por qué |
# |---|---|---|
# | `Tipo_Carga` | Rellenar con **"Sin Clasificar"** | Un mismo buque transporta distintos tipos de carga, así que no se puede adivinar el tipo. Se conserva el registro porque sus tiempos sí son válidos. |
# | `Tiempo_Muelle_Horas` | **Mediana** del mismo tipo de carga | La mediana no se deja arrastrar por valores extremos, y cada tipo de carga tarda distinto en el muelle. |
# | `Tiempo_Espera_Horas` y `Hora_Atraque` | **Mediana** de la espera del mismo tipo de carga **y** clima; luego atraque = llegada + espera | La espera depende mucho del clima (con tormenta es 4 veces mayor), así que se compara con casos parecidos. |
#
# Cada valor rellenado queda marcado en la columna `Dato_Imputado`, para que sea transparente en el tablero.

# %%
df["Dato_Imputado"] = False

# a) Tipo de carga
nulos = df["Tipo_Carga"].isna()
for id_reg in df.loc[nulos, "ID_Registro"]:
    registrar(id_reg, "Tipo_Carga", "nulo", "Sin Clasificar", "Tipo de carga desconocido")
df.loc[nulos, "Tipo_Carga"] = "Sin Clasificar"
df.loc[nulos, "Dato_Imputado"] = True

# b) Tiempo en muelle: mediana por tipo de carga (o mediana general si no hay con qué comparar)
mediana_muelle = df.groupby("Tipo_Carga")["Tiempo_Muelle_Horas"].transform("median")
mediana_muelle = mediana_muelle.fillna(df["Tiempo_Muelle_Horas"].median()).round(2)
nulos = df["Tiempo_Muelle_Horas"].isna()
for idx in df.index[nulos]:
    registrar(df.at[idx, "ID_Registro"], "Tiempo_Muelle_Horas", "nulo", mediana_muelle[idx],
              f"Mediana de {df.at[idx, 'Tipo_Carga']}")
df.loc[nulos, "Tiempo_Muelle_Horas"] = mediana_muelle[nulos]
df.loc[nulos, "Dato_Imputado"] = True

# c) Espera y atraque. Si solo falta uno de los dos, se calcula a partir del otro.
calc_espera = (df["Hora_Atraque"] - df["Hora_Llegada"]).dt.total_seconds() / 3600
solo_falta_espera = df["Tiempo_Espera_Horas"].isna() & df["Hora_Atraque"].notna()
df.loc[solo_falta_espera, "Tiempo_Espera_Horas"] = calc_espera[solo_falta_espera].round(2)

faltan_ambos = df["Tiempo_Espera_Horas"].isna()
mediana_espera = df.groupby(["Tipo_Carga", "Condicion_Climatica"])["Tiempo_Espera_Horas"].transform("median")
mediana_espera = mediana_espera.fillna(df.groupby("Condicion_Climatica")["Tiempo_Espera_Horas"].transform("median"))
mediana_espera = mediana_espera.fillna(df["Tiempo_Espera_Horas"].median()).round(2)
for idx in df.index[faltan_ambos]:
    registrar(df.at[idx, "ID_Registro"], "Tiempo_Espera_Horas", "nulo", mediana_espera[idx],
              f"Mediana de {df.at[idx, 'Tipo_Carga']} con {df.at[idx, 'Condicion_Climatica']}")
df.loc[faltan_ambos, "Tiempo_Espera_Horas"] = mediana_espera[faltan_ambos]
df.loc[faltan_ambos, "Dato_Imputado"] = True

falta_atraque = df["Hora_Atraque"].isna()
nuevo_atraque = (df["Hora_Llegada"] + pd.to_timedelta(df["Tiempo_Espera_Horas"], unit="h")).dt.floor("min")
for idx in df.index[falta_atraque]:
    registrar(df.at[idx, "ID_Registro"], "Hora_Atraque", "nulo", str(nuevo_atraque[idx]),
              "Llegada + espera imputada")
df.loc[falta_atraque, "Hora_Atraque"] = nuevo_atraque[falta_atraque]
df.loc[falta_atraque, "Dato_Imputado"] = True

print(f"Nulos restantes: {df.isna().sum().sum()}")

# %% [markdown]
# ### 3.6 Validación de consistencia
# La espera registrada debe ser igual a *atraque − llegada*. Si la diferencia es mayor a 5 minutos, recalculamos la espera desde las fechas, que son el dato más confiable.

# %%
calc_espera = (df["Hora_Atraque"] - df["Hora_Llegada"]).dt.total_seconds() / 3600
inconsistentes = (calc_espera - df["Tiempo_Espera_Horas"]).abs() > 5 / 60
for idx in df.index[inconsistentes]:
    registrar(df.at[idx, "ID_Registro"], "Tiempo_Espera_Horas", df.at[idx, "Tiempo_Espera_Horas"],
              round(calc_espera[idx], 2), "No coincidía con atraque - llegada")
df.loc[inconsistentes, "Tiempo_Espera_Horas"] = calc_espera[inconsistentes].round(2)
print(f"Registros inconsistentes corregidos: {inconsistentes.sum()}")

# %% [markdown]
# ### 3.7 Variables derivadas
# Creamos las columnas que necesitan los KPIs y los gráficos del tablero:
#
# | Nueva columna | Para qué sirve |
# |---|---|
# | `Hora_Salida` | Atraque + tiempo en muelle; con ella se calcula la ocupación de muelles |
# | `Fecha`, `Hora_Del_Dia`, `Dia_Semana` | Gráfico de horas pico y filtros por fecha |
# | `Eficiencia_TEU_Hora` | KPI de eficiencia (solo aplica a contenedores) |
# | `Tiempo_Total_Puerto_Horas` | Espera + muelle: el tiempo total del buque en el puerto |
# | `Nivel_Alerta` | Alertas visuales: Normal, Amarilla o Roja |

# %%
DIAS = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}

df["Hora_Salida"] = (df["Hora_Atraque"] + pd.to_timedelta(df["Tiempo_Muelle_Horas"], unit="h")).dt.floor("min")
df["Fecha"] = df["Hora_Llegada"].dt.date
df["Hora_Del_Dia"] = df["Hora_Llegada"].dt.hour
df["Dia_Semana"] = df["Hora_Llegada"].dt.dayofweek.map(DIAS)
df["Tiempo_Total_Puerto_Horas"] = (df["Tiempo_Espera_Horas"] + df["Tiempo_Muelle_Horas"]).round(2)

es_contenedor = df["Tipo_Carga"] == "Contenedores"
df["Eficiencia_TEU_Hora"] = (df["TEUs_Ocupados"] / df["Tiempo_Muelle_Horas"]).where(es_contenedor).round(1)

df["Nivel_Alerta"] = "Normal"
df.loc[df["Tiempo_Espera_Horas"] > UMBRAL_AMARILLO_H, "Nivel_Alerta"] = "Amarilla"
df.loc[df["Tiempo_Espera_Horas"] > UMBRAL_ROJO_H, "Nivel_Alerta"] = "Roja"

print(df["Nivel_Alerta"].value_counts())

# %% [markdown]
# ## 4. Carga
# Ordenamos por hora de llegada, guardamos el CSV limpio para el tablero y guardamos el reporte de cambios.
#
# Se guarda con `encoding="utf-8-sig"` para que Excel muestre bien las tildes (Sólido, Líquido, Miércoles).
# Además se guarda una copia en Excel (.xlsx), cómoda para revisar los datos: en Excel en español, un CSV
# separado por comas suele abrirse todo en una sola columna, porque Excel espera punto y coma.

# %%
df = df.sort_values("Hora_Llegada").reset_index(drop=True)
reporte = pd.DataFrame(cambios, columns=["ID_Registro", "Columna", "Valor_Original", "Valor_Nuevo", "Motivo"])

df.to_csv(ARCHIVO_LIMPIO, index=False, date_format=FORMATO_FECHA, encoding="utf-8-sig")
reporte.to_csv(ARCHIVO_REPORTE, index=False, encoding="utf-8-sig")
with pd.ExcelWriter(ARCHIVO_EXCEL) as excel:
    df.to_excel(excel, sheet_name="Datos limpios", index=False)
    reporte.to_excel(excel, sheet_name="Reporte de cambios", index=False)

print(f"Guardado: {ARCHIVO_LIMPIO.name} ({len(df)} filas, {df.shape[1]} columnas)")
print(f"Guardado: {ARCHIVO_REPORTE.name} ({len(reporte)} cambios)")
print(f"Guardado: {ARCHIVO_EXCEL.name} (hojas: Datos limpios, Reporte de cambios)")
reporte

# %% [markdown]
# ## 5. Resumen antes y después
# Esta tabla es útil para el documento técnico y para la sustentación.

# %%
resumen = pd.DataFrame({
    "Antes": [len(df_original), int(df_original.isna().sum().sum()),
              int(df_original.duplicated().sum()), int((df_original["Tiempo_Muelle_Horas"] <= 0).sum()),
              "texto", df_original.shape[1]],
    "Después": [len(df), int(df.drop(columns=["Eficiencia_TEU_Hora"]).isna().sum().sum()),
                int(df.duplicated().sum()), int((df["Tiempo_Muelle_Horas"] <= 0).sum()),
                "fecha-hora", df.shape[1]],
}, index=["Registros", "Celdas nulas", "Duplicados", "Tiempos en muelle imposibles",
          "Tipo de dato de las fechas", "Columnas"])
print("(Eficiencia_TEU_Hora queda vacía a propósito en las cargas que no son contenedores)")
resumen

# %% [markdown]
# ## 6. Primera mirada a los datos limpios
# Un adelanto de los KPIs que irán en el tablero (Fase 3).

# %%
# Periodo = desde el primer día a las 00:00 hasta el final del último día (igual que en el tablero)
horas_periodo = (df["Hora_Llegada"].max().normalize() + pd.Timedelta(days=1)
                 - df["Hora_Llegada"].min().normalize()).total_seconds() / 3600
kpis = {
    "Tiempo Promedio de Espera (h)": round(df["Tiempo_Espera_Horas"].mean(), 2),
    "Ocupación de muelles (%)": round(100 * df["Tiempo_Muelle_Horas"].sum() / (NUM_MUELLES * horas_periodo), 1),
    "Eficiencia contenedores (TEU/h)": round(df["Eficiencia_TEU_Hora"].mean(), 1),
    "Buques en alerta roja": int((df["Nivel_Alerta"] == "Roja").sum()),
    "Buques en alerta amarilla": int((df["Nivel_Alerta"] == "Amarilla").sum()),
}
for nombre, valor in kpis.items():
    print(f"{nombre}: {valor}")

df.groupby("Tipo_Carga")[["Tiempo_Espera_Horas", "Tiempo_Muelle_Horas"]].mean().round(2)
