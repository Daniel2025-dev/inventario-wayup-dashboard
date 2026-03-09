# Dashboard Inventario – WayUP

Pequeña app en Streamlit para apoyar el conteo físico de inventario: descarga un Excel (OneDrive/URL) o usa el índice local, detecta/normaliza columnas, calcula diferencias y exporta resultados.

## Requisitos
- Python 3.10+ instalado
- Dependencias listadas en `requirements.txt`

## Instalación
1. Crear un entorno virtual (opcional, recomendado):

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2. Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

3. Verificar que `app.py` esté en el repositorio (se han aplicado mejoras de mapeo y exportación).

## Ejecutar la aplicación
La forma recomendada para ver la UI es con Streamlit:

```bash
streamlit run app.py
```

Alternativa (no crea el contexto completo de Streamlit y mostrará advertencias):

```bash
python app.py
```

## Flujo de uso
1. En la barra lateral, puedes añadir nuevos inventarios al índice local (`inventarios_index.csv`) indicando `Nombre` y `URL` si usas OneDrive/SharePoint.
2. Selecciona el archivo de inventario desde el desplegable.
3. Si el archivo tiene encabezados desplazados o nombres distintos, abre el expander "Ver / ajustar mapeo de columnas detectado" y confirma o reasigna manualmente las columnas clave (`Cantidad`, `Cantidad a contar`, `Cod. Producto`, `Contador`, `Cliente`, `Ubicación`).
4. Revisa las métricas y el detalle. Usa los botones de exportación para bajar CSV/XLSX con todo el detalle o solo las diferencias.

## Características añadidas
- Detección y normalización de encabezados, manejo de MultiIndex.
- UI para confirmar o corregir mapeo de columnas.
- Exportar todo el detalle y sólo las diferencias en CSV/XLSX.
- Validaciones y resaltado de filas con diferencias y duplicados por producto.

## Buenas prácticas
- Mantén una columna clara para `Cantidad` (sistema) y `Cantidad a contar` (conteo físico).
- Evita filas de metadatos encima del encabezado; si existen, usa el mapeo para seleccionar la fila correcta.

## Control de versiones
Para subir cambios al repositorio remoto:

```bash
git add app.py README.md
git commit -m "Mejora: mapeo de alias, exportación y validaciones"
git push origin main
```

Si el remoto no está configurado, añade primero:

```bash
git remote add origin <URL-del-repo>
git push -u origin main
```

## Siguientes mejoras posibles
- Carga local de archivos (drag & drop).  
- Guardado de avances parciales por contador.  
- Generación de hojas imprimibles por contador (PDF/XLSX).

---
Si quieres, puedo añadir ejemplos de Excel de prueba dentro del repo o implementar la carga local ahora.
