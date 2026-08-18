# Validador de estructura Markdown (genérico)

App Flask chica para validar que un `.md` de entrega siga el formato esperado:

```
# 1. Datos del proyecto
## 1.1 Datos del alumno
## 1.2 Datos del proyecto
# 2. Proyecto
## 2.1 Estructura del proyecto
## 2.2, 2.3, ... (archivos de código, cada uno con su bloque ```)
```

Toda la lógica de parseo (regex, extracción de secciones, checklist)
vive en `parser.py`, sin depender de Flask — se puede importar y usar
desde una terminal o probar por separado (`test_parser.py`).

## Estructura

```
validador-estructura-md/
├── app.py                     # rutas Flask, solo recibe input y renderiza
├── parser.py                  # lógica pura de validación (sin Flask)
├── test_parser.py             # pruebas unitarias del parser
├── estructura_base_ejemplo.md # archivo de ejemplo usado en las pruebas
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    └── style.css
```

## Correr localmente

```bash
pip install -r requirements.txt
python app.py
```

Abre `http://127.0.0.1:5000`, sube tu `.md` (o pégalo) y dale "Validar estructura".

## Correr las pruebas

```bash
python test_parser.py -v
```

13 pruebas en total, probadas contra tres archivos distintos en `ejemplos/`
y `estructura_base_ejemplo.md` — el parser no depende del contenido de
ningún proyecto en particular, solo de que se respete la plantilla de
secciones. Sirve para validar el .md de cualquier persona que use este
formato de entrega, no solo el tuyo.

## Qué valida

- Presencia de las 5 secciones esperadas (1, 1.1, 1.2, 2, 2.1)
- Los 5 campos del alumno (Nombre, Primer Apellido, Segundo Apellido, Email, Grupo)
- Nombre y objetivo del proyecto, y la lista de módulos (3.1, 3.2, ...)
- El árbol de carpetas (bloque de código bajo 2.1)
- Cada sección `## 2.x` / `### 2.x.x` que tenga un bloque de código inmediatamente
  debajo se detecta como archivo de código fuente (con su lenguaje y número de líneas)
