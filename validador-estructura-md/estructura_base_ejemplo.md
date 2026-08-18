# 1. Datos del proyecto

## 1.1 Datos del alumno

1. Nombre: Dejah
2. Primer Apellido: Thoris
3. Segundo Apellido: Barsoon
4. Email: 1711243@email.com
5. Grupo: TI30

## 1.2 Datos del proyecto

1. Nombre del proyecto: AgendaWeb
2. Objetivo: Desarrollar una agenda web para almacenar datos de contactos
3. Módulos desarrollados:
    3.1 Contactos (Gestión de contactos [insertar, borrar, consultar, editar, borrar])
    3.2 Direcciones (Gestión de direcciones de cada contact [insertar, consultar, editar, borrar])

# 2. Proyecto

## 2.1 Estructura del proyecto:

````
webapp/
├── app.py (Aplicación con la libreria web.py y las rutas de cada uno de los módulos.)
├── .venv/ (Ambiente virtual para instalar las librerías de python)
├── views/ (Vistas en html ordenadas por carpetas)
│   ├── index.html (vista en html para la pagina de bienvenida)
│   ├── modulo1/ (vistas en html para cada moódulo para tener un mejor orden)
│   │   ├── listar.html (Vista en html y templator de web.py para listar elementos obtenidos desde la base de datos)
│   │   ├── insertar.html (Vista en html y templator de web.py para insertar nuevos elementos)
│   │   └── layout.html (Vista en html y templator de web.py con la estructura básica, barras de menús, colores, etc.)
│   └── controllers/ (Controladodres en python ordenados por carpetas)
│   │    ├── index.py
│   │    ├── modulo1/ (controladores de un módulo separadas por funciones para simplificar el funcionamiento)
│   │    │   ├── listar.py (Controlador en python y web.py con la conexión a la base de datos, y los metodos GET para renderizar la vista)
│   │    │   └── insertar.py (Controlador en python3 y web.py con metodo POST para recibir datos y insertarlos en la base de datos)
│   └── sql/ (Carpeta con los archivos sql necearios para inicializar la base de datos)
│       ├── schema_db.sql (Script para crear la base de datos en sqlite3 con datos de prueba)
│       └── base.db (Base de datos creada)
├── .gitignore (Configuración base del archivo para no sincronizar *.pyc, __pycache__/, .venv/)
├── requirements.txt (Archivo con las librerias utilizadas en el proyecto, incluida web.py)
├── runtime.txt (Archivo con la versión de python utilizada)
├── README.md (Archivo con la guia de instalación e inicialización del proyecto)
└── LICENSE (Licencia del proyecto generada desde el momento de crear el repositorio de GitHub.)
````

## 2.2 requirements.py

````python
cheroot==11.1.2
jaraco.functools==4.5.0
more-itertools==11.1.0
multipart==1.3.1
web-py==0.76
````

## 2.3 .gitignore

````git
*.pyc
__pycache__/
.venv
````

## 2.4 app.py

````python
import web

urls = (
    '/', 'controllers.index.Index',
    
    # Rutas para el modulo contactos
    '/lista_contactos','controllers.contactos.lista_contactos.ListaContactos',
    '/insertar_contacto','controllers.contactos.insertar_contacto.InsertarContacto',
    '/ver_contacto/(.*)','controllers.contactos.ver_contacto.VerContacto',
    '/editar_contacto/(.*)','controllers.contactos.editar_contacto.EditarContacto',
    '/borrar_contacto/(.*)','controllers.contactos.borrar_contacto.BorrarContacto',
    
    # Rutas del modulo de direcciones
    '/ver_direccion/(.*)', 'controllers.direcciones.ver_direccion.VerDireccion',
    '/editar_direccion/(.*)', 'controllers.direcciones.editar_direccion.EditarDireccion',
    '/borrar_direccion/(.*)', 'controllers.direcciones.borrar_direccion.BorrarDireccion',
    '/insertar_direccion/(.*)', 'controllers.direcciones.insertar_direccion.InsertarDireccion'
    )

app = web.application(urls, globals())

if __name__ == "__main__":
    web.config.debug = False
    app.run()

````

## 2.5 script.sql

````sql
-- Activar el soporte para claves foráneas en SQLite
PRAGMA foreign_keys = ON;
.mode box
.head on

CREATE TABLE contactos(
id_contacto INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT NOT NULL,
primer_apellido TEXT NOT NULL,
segundo_apellido TEXT NOT NULL,
email TEXT NOT NULL,
telefono TEXT NOT NULL
);

CREATE TABLE direcciones(
id_direccion INTEGER PRIMARY KEY AUTOINCREMENT,
id_contacto INTEGER NOT NULL,
pais TEXT NOT NULL,
estado TEXT NOT NULL,
ciudad TEXT NOT NULL,
colonia TEXT NOT NULL,
calle TEXT NOT NULL,
numero_exterior TEXT NOT NULL,
-- Definición de la relación (Clave Foránea)
FOREIGN KEY (id_contacto) REFERENCES contactos(id_contacto)
);

-- Insertar contactos
INSERT INTO contactos(nombre, primer_apellido, segundo_apellido, email, telefono)
VALUES
('Dejah', 'Thoris', 'Barsonn', 'dejah@email.com', '111111111'),
('John', 'Carter', 'Earth', 'john@email.com', '22222222');

-- Insertar 2 direcciones para Dejah (id_contacto = 1)
-- Insertar 2 direcciones para John (id_contacto = 2)
INSERT INTO direcciones(id_contacto, pais, estado, ciudad, colonia, calle, numero_exterior)
VALUES
(1, 'Marte', 'Helium', 'Helium City', 'Royal Sector', 'Palace Avenue', '1'),
(1, 'Marte', 'Zodanga', 'Zodanga', 'Outskirts', 'Red Dust Road', '45'),
(2, 'Tierra', 'Virginia', 'Richmond', 'Downtown', 'Main Street', '100'),
(2, 'Marte', 'Helium', 'Helium City', 'Warrior Sector', 'Warlord Way', '7');

-- Ver todos los contactos
SELECT * FROM contactos;

-- Ver todas las direcciones
SELECT * FROM direcciones;

-- Consulta con JOIN para ver la relación entre contactos y direcciones
SELECT
    c.nombre,
    c.primer_apellido,
    d.pais,
    d.ciudad,
    d.calle,
    d.numero_exterior
FROM contactos c
JOIN direcciones d ON c.id_contacto = d.id_contacto;
````

## 2.6 Views

### 2.6.1 views/index.html

````html
<h1>Index</h1>

<a href="lista_contactos">Contactos</a>
````

### 2.6.2 views/layout.html

````html
$def with (content)
<!DOCTYPE html>
<html lang="es">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta charset="utf-8">
        <title>Controladores</title>
    </head>
    <body>
    $:content
    </body>
</html>
````

### 2.6.3 views/lista_contactos.html

````html
$def with(contactos)

<h1>Lista contactos</h1>
<a href="/insertar_contacto"><button name="nuevo">Nuevo</button></a>

<table border="1">
    <tr>
        <th>ID</th>
        <th>Nombre</th>
        <th>Primer Apellido</th>
        <th>Segundo Apellido</th>
        <th>Email</th>
        <th>Teléfono</th>
        <th>Ver</th>
        <th>Editar</th>
        <th>Borrar</th>
    </tr>
    $for contacto in contactos:
        <tr>
            <td>$contacto['id_contacto']</td>
            <td>$contacto['nombre']</td>
            <td>$contacto['primer_apellido']</td>
            <td>$contacto['segundo_apellido']</td>
            <td>$contacto['email']</td>
            <td>$contacto['telefono']</td>
            <td><a href="/ver_contacto/$contacto['id_contacto']">Ver</td>
            <td><a href="/editar_contacto/$contacto['id_contacto']">Editar</td>
            <td><a href="/borrar_contacto/$contacto['id_contacto']">Borrar</td>
        </tr>
</table>
````

## 2.6.4 views/contactos/ver_contacto.html

````html
$def with(contacto,direcciones)
<h1>Ver contacto</h1>

$if contacto == {}:
    <h1>Ups, no existe este contacto</h1>
    <a href="/lista_contactos"><button type="button">Regresar</button></a>

$else:
    <form  method="post">
        <label for="id_contacto">ID:</label>
        <input type="text" id="id_contacto" name="id_contacto" value=$contacto['id_contacto'] readonly><br><br>

        <label for="nombre">Nombre:</label>
        <input type="text" id="nombre" name="nombre" value=$contacto['nombre'] readonly><br><br>

        <label for="primer_apellido">Primer Apellido:</label>
        <input type="text" id="primer_apellido" name="primer_apellido" value=$contacto['primer_apellido'] readonly><br><br>

        <label for="segundo_apellido">Segundo Apellido:</label>
        <input type="text" id="segundo_apellido" name="segundo_apellido" value=$contacto['segundo_apellido'] readonly><br><br>

        <label for="email">Email:</label>
        <input type="email" id="email" name="email" value=$contacto['email'] readonly><br><br>

        <label for="telefono">Teléfono:</label>
        <input type="tel" id="telefono" name="telefono" value=$contacto['telefono'] readonly><br><br>

        <a href="/lista_contactos"><button type="button">Regresar</button></a>
        <a href="/insertar_direccion/$contacto['id_contacto']"><button type="button" class="btn btn-primary">Nueva dirección</button></a>
    </form>

    <table>
        <thead>
            <tr>
            <th>Pais</th>
            <th>Estado</th>
            <th>Ciudad</th>
            <th>Colonia</th>
            <th>Calle</th>
            <th>Numero exterior</th>
                <th>Ver</th>
                <th>Editar</th>
                <th>Borrar</th>
            </tr>
        </thead>
        <tbody>
            $for direccion in direcciones:
                <tr>
                    <td>$direccion['pais']</td>
                    <td>$direccion['estado']</td>
                    <td>$direccion['ciudad']</td>
                    <td>$direccion['colonia']</td>
                    <td>$direccion['calle']</td>
                    <td>$direccion['numero_exterior']</td>
                        <td><a href="/ver_direccion/$direccion['id_direccion']"><button type="button" class="btn btn-primary btn-sm">Ver</button></a></td>
                        <td><a href="/editar_direccion/$direccion['id_direccion']"><button type="button" class="btn btn-warning btn-sm">Editar</button></a></td>
                        <td><a href="/borrar_direccion/$direccion['id_direccion']"><button type="button" class="btn btn-danger btn-sm">Borrar</button></a></td>
                </tr>
        </tbody>
    </table>
````

## 2.7. Controllers

### 2.7.1 controllers/index.py

````python
import web

render = web.template.render('views', base='layout')

class Index:
    def GET(self):
        return render.index() # type: ignore
````

### 2.7.2 controllers/lista_contactos.py

````python
import web
import sqlite3

render = web.template.render('views/contactos', base='layout')

class ListaContactos:

    def consultarContactos(self):
        try:
            conexion = sqlite3.connect("sql/agenda.db")
            conexion.row_factory = sqlite3.Row
            cursor = conexion.cursor()
            query = "SELECT * FROM contactos;"
            cursor.execute(query)
            resultado = cursor.fetchall()

            datos = []
            for fila in resultado:
                contacto = {
                    "id_contacto":fila[0],
                    "nombre":fila[1],
                    "primer_apellido":fila[2],
                    "segundo_apellido":fila[3],
                    "email":fila[4],
                    "telefono":fila[5]
                }
                datos.append(contacto)
            return datos
        except sqlite3.Error as error:
            print(f"ERROR ListaContactos 400: {error.args}")
            return []
        except Exception as error:
            print(f"ERROR ListaContactos 401: {error.args}")
            return []
        finally:
            if conexion:
                conexion.close()

    def GET(self):
        try:
            contactos = self.consultarContactos()
            return render.lista_contactos(contactos) # type: ignore
        except Exception as error:
            print(f"ERROR ListaContactos 402: {error.args}")
            return f"UPS, algo fallo"
````

### 2.7.3 controllers/contactos/ver_contacto.py

````python
import web
import sqlite3

render = web.template.render('views/contactos', base='layout')

class VerContacto:

    def buscarContacto(self, id_contacto:int):
        try:
            conexion = sqlite3.connect("sql/agenda.db")
            conexion.row_factory = sqlite3.Row
            cursor = conexion.cursor()
            query = "SELECT * FROM contactos WHERE id_contacto = ?"
            cursor.execute(query,(id_contacto,))
            resultado = cursor.fetchone()

            contacto = {
                "id_contacto":resultado[0],
                "nombre":resultado[1],
                "primer_apellido":resultado[2],
                "segundo_apellido":resultado[3],
                "email":resultado[4],
                "telefono":resultado[5]
            }
            return contacto
        except sqlite3.Error as error:
            print(f"ERROR VerContacto 500: {error.args}")
            return {}
        except Exception as error:
            print(f"ERROR VerContacto 501: {error.args}")
            return {}
        finally:
            if conexion:
                conexion.close()

    def buscarDireccionesContacto(self, id_contacto: int)->list:
        try:
            conexion = sqlite3.connect("sql/agenda.db")
            cursor = conexion.cursor()
            query = "SELECT * FROM direcciones WHERE id_contacto = ?;"
            cursor.execute(query,(id_contacto,))
            registros = []
            for row in cursor.fetchall():
                registro = {
                    'id_direccion': row[0],
                    'id_contacto': row[1],
                    'pais': row[2],
                    'estado': row[3],
                    'ciudad': row[4],
                    'colonia': row[5],
                    'calle': row[6],
                    'numero_exterior': row[7]
                }
                registros.append(registro)
            return registros
        except sqlite3.Error as error:
            print(f"ERROR ModelDirecciones obtener: {error.args}")
            return []
        except Exception as error:
            print(f"ERROR ModelDirecciones obtener: {error.args}")
            return []
        finally:
            if conexion:
                conexion.close()

    def GET(self,id_contacto:int):
        try:
            print(f"ID_CONTACTO: {id_contacto}")
            contacto = self.buscarContacto(id_contacto)
            direcciones = self.buscarDireccionesContacto(id_contacto)
            return render.ver_contacto(contacto,direcciones) # type: ignore
        except Exception as error:
            print(f"ERROR VerContacto 502: {error.args}")
            return f"UPS, algo fallo"
````