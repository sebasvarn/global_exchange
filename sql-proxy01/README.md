# SQL-Proxy

El SQL-Proxy es el componente de FacturaSegura que permite generar documentos electrónicos tan sólo con SQL. 

Está basado en contenedores, y tiene una base de datos PostgreSQL a la cual se debe conectar y ejecutar los SQL necesarios. 

Se provee además un cliente de demostración de donde se podrán tomar de ejemplo los SQL necesarios para generar los documentos electrónicos.


# Contenedores

A continuación los pasos para realizar la instalación y ejecución de los contenedores.


## Pre-requisitos

- Instalar docker y docker compose, según su sistema operativo.
    - El SQL-Proxy se ha probado con: 
        - Docker Ubuntu Server 24.04
        - Docker Desktop para MacOS
        - Docker Desktop para Windows


## Configurar

Revisar los archivos que tienen las variables de entorno de los contenedores `.env.test`, `.env-sched.test` y `.env.test.db` y personalizar las variables según sus requerimientos. 

El significado de las variables que se pueden modificar están documentados en los archivos. Los valores que tienen estos archivos son perfectamente funcionales.

*ATENCION:* Para servidores con Linux se debe dar permiso de lectura y escritura a los siguientes directorios:

```
chmod a+rw ./volumes/nginx/logs
chmod a+rw ./volumes/web-sched/logs
chmod a+rw ./volumes/web/logs
chmod a+rw ./volumes/web/kude

```


## Ejecutar

Al ejecutar el docker compose se levantarán 4 contenedores: el servidor web `nginx`, la aplicación web fs_proxy `web`, la aplicación web scheduler `web-sched` y la base de datos postgresql `db`. A continuación los comandos básicos para gestionar los contenedores:

```
# Construye los contenedores. Controlar que se construyan correctamente
docker compose -f docker-compose.test.yml build

# Levanta los contenedores. Controlar que se levanten correctamente
# Para terminar presionar Ctrl+C
docker compose -f docker-compose.test.yml up

# Para levantar los contenedores en background
docker compose -f docker-compose.test.yml up -d

# Para visualizar la salida de los contenedores
docker compose -f docker-compose.test.yml logs -f

# Para ejecutar un bash dentro del contenedor "web" 
# (cambiar el nombre para acceder a otro contenedor)
docker compose -f docker-compose.test.yml exec web /bin/bash

# Para detener los contenedores
docker compose -f docker-compose.test.yml stop

# Para bajar los contenedores. Esto elimina los contenedores y sus imágenes 
docker compose -f docker-compose.test.yml down

```


# Acceso a los servicios

A continuación se muestra el acceso a los servicios desde la máquina que está ejecutando los contenedores, en este caso `localhost`.

El acceso desde otra máquina de la red local ya depende de su entorno y configuración.


## Acceder al nginx

El webserver arranca en el puerto `40080`

Contiene la aplicación Flask `fs_proxy`. Se debe mostrar un mensaje informando que la webapp está ejecutandose. 

http://localhost:40080/


En el recurso `/kude` se encontrarán los **KuDE en PDF** y los **XML firmados** de los documentos electrónicos generados. El recurso `/kude` dentro de este URL se encuentra protegido según las credenciales del `.env.test` con basic HTTP AUTH

http://localhost:40080/kude/


## Acceder al postgreSQL

El postgreSQL se encuentra accesible mediante el puerto 45432 con el nombre de BD y las credenciales definidas en el `.env.test.db`.

Si cuenta con el cliente de postgreSQL puede acceder a la base de datos de la siguiente manera (el password lo encuentra en `.env.test.db`):

```
psql -h localhost -p 45432 -U fs_proxy_user -d fs_proxy_bd
```

Se puede acceder a la base de datos desde la red local del servidor Docker con cualquier cliente de PostgreSQL.

Para persistir los datos del postgreSQL se crea un volumen exclusivo en el docker `postgres_data_test`. Tenga CUIDADO de no eliminar ese volumen de postgreSQL sin hacer previamente un backup de la base de datos.


# Acceso a archivos generados por los contenedores

## Acceso a los logs

Los logs de los diferentes contenedores se encuentran en:

* Para el `nginx` dentro de `./volumes/nginx/logs/` se pueden acceder a los archivos `access.log` y `error.log` generados por el servidor.

* Para el `web` dentro de `./volumes/web/logs/` se pueden acceder a los archivos `access.log` y `error.log` generados por la webapp `fs_proxy`.

* Para el `web-sched` dentro de `./volumes/web-sched/logs/` se pueden acceder al archivo `app.log` generado por la webapp `scheduler`.

* Para el `db` se puede visualizar la salida de los contenedores.


## Acceso a los KuDE en PDF y XML firmados

También se puede acceder a los KuDE y XML firmados en `./volumes/web/kude/`. Se recomienda no modificar los archivos dentro de este directorio.


# Cliente Python para pruebas

A modo de realizar pruebas se proporciona dentro del directorio `./client` un ejemplo de cliente en Python en el script `app.py`.


## Pre-requisitos

- Instalar Python 3
- Tener una cuenta de ESI de FacturaSegura. Para obtener su cuenta ESI con FacturaSegura escribir a soporte@facturasegura.com.py


## Ejecutar

Abrir una consola e ir al directorio `client`. Ejecutar el script `setup_and_run` segun su sistema operativo.

Inicializar los datos del ESI según los datos solicitados por el script. Se sugiere primeramente hacer las pruebas en ambiente TEST.

El cliente generará una factura de ejemplo para el establecimiento 001 y punto de expedición 001 según el número que ingrese por consola.

Puede verificar el procesamiento del documento electrónico en la tabla `public.de` y también en el portal de FacturaSegura.

```
select estado, d.* from public.de d order by id desc
```

Puede acceder a `http://localhost:40080/kude` para verificar los KuDE en PDF y los XML firmados generados por FacturaSegura.

En la funcion `insert_de_1` del script `app.py` se deben insertar los valores de los campos según las normas del manual de SIFEN (actualmente la versión 150).

