#!/bin/sh

# Generar archivo htpasswd si las variables de entorno están definidas
echo "Vemos si las variables de entorno permiten crear un archivo htpasswd"
if [ -n "$HTTP_USERNAME" ] && [ -n "$HTTP_PASSWORD" ]; then
    echo "Creamos el archivo htpasswd"
    htpasswd -b -c /etc/nginx/.htpasswd $HTTP_USERNAME $HTTP_PASSWORD
    cat /etc/nginx/.htpasswd
fi

echo "Vemos si existe el directorio /kude"
if [ ! -d "/kude" ]; then
    echo "No existe el directorio /kude, lo creamos"
	mkdir /kude
fi

date > /kude/date.txt

nginx -t

# Ejecutar NGINX en primer plano
exec nginx -g 'daemon off;'