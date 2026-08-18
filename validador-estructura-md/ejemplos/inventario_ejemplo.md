# 1. Datos del proyecto

## 1.1 Datos del alumno

1. Nombre: Marco
2. Primer Apellido: Reyes
3. Segundo Apellido: Islas
4. Email: mreyes@email.com
5. Grupo: TI22

## 1.2 Datos del proyecto

1. Nombre del proyecto: InventarioWeb
2. Objetivo: Controlar el inventario de una tienda pequeña
3. Módulos desarrollados:
    3.1 Productos (Gestión de productos [insertar, editar, borrar, consultar])
    3.2 Proveedores (Gestión de proveedores [insertar, editar, borrar, consultar])

# 2. Proyecto

## 2.1 Estructura del proyecto:

````
inventarioweb/
├── app.py (Aplicación principal con las rutas)
├── models/
│   └── producto.py
├── static/
│   └── style.css
└── templates/
    └── index.html
````

## 2.2 requirements.txt

````
flask==3.0.3
````

## 2.3 app.py

````python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Inventario"

if __name__ == "__main__":
    app.run(debug=True)
````

### 2.3.1 templates/index.html

````html
<h1>Inventario</h1>
````
