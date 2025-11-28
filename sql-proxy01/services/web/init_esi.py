#!/usr/bin/env python3
"""
Script para inicializar la configuración ESI automáticamente usando variables de entorno
"""
import os
import psycopg2
import time
import sys
from dotenv import load_dotenv

load_dotenv()

def init_esi():
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"Intento {attempt + 1}/{max_retries} de conectar a la base de datos...")
            
            # Usar DATABASE_URL desde variables de entorno
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                print(f"Usando DATABASE_URL: {database_url.split('@')[1] if '@' in database_url else database_url}")
                connection = psycopg2.connect(database_url)
            else:
                # Fallback a variables individuales
                db_config = {
                    'host': os.getenv("DB_HOST", "sql_proxy_db"),
                    'port': os.getenv("DB_PORT", "5432"),
                    'database': os.getenv("DB_NAME", "fs_proxy_bd"),
                    'user': os.getenv("DB_USER", "fs_proxy_user"),
                    'password': os.getenv("DB_PASSWORD", "p123456")
                }
                print(f"Usando conexión individual: {db_config['user']}@{db_config['host']}:{db_config['port']}")
                connection = psycopg2.connect(**db_config)
            
            cursor = connection.cursor()
            
            # Verificar si ya existe configuración ESI
            cursor.execute("SELECT COUNT(*) FROM public.esi;")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("Insertando configuración ESI desde variables de entorno...")
                
                # Obtener valores de variables de entorno
                esi_ruc = os.getenv("ESI_RUC", "2595733")
                esi_dv = os.getenv("ESI_DV", "3")
                esi_nombre = os.getenv("ESI_NOMBRE", "Global Exchange")
                esi_descripcion = os.getenv("ESI_DESCRIPCION", "Proyecto IS2 - Cambio de Divisas")
                esi_email = os.getenv("ESI_EMAIL", "globalexchange10is2@gmail.com")
                esi_passwd = os.getenv("ESI_PASSWD", "")
                
                # Determinar URL según ambiente
                ambiente = os.getenv("ESI_AMBIENTE", "TEST")
                esi_url = "https://apitest.facturasegura.com.py" if ambiente == "TEST" else "https://api.facturasegura.com.py"
                
                # Token puede venir de variable de entorno o usar el default
                esi_token = os.getenv("ESI_TOKEN", "eyJ2ZXIiOiI1IiwidWlkIjoiOTc0Mjk4OGJjYThhNGVjNjkzMTM0ZTQ2ZjVkMzQxMjciLCJzaWQiOjAsImV4cCI6MH0.aSiYqg.JQTcjKyv2biOTI609mBu_QL-JYM")
                
                print(f"Configurando ESI: {esi_nombre} (RUC: {esi_ruc}-{esi_dv})")
                
                insert_query = """
                INSERT INTO public.esi (
                    id, ruc, ruc_dv, nombre, descripcion, estado, 
                    fch_ins, fch_upd, esi_email, esi_passwd, esi_token, esi_url
                ) VALUES (
                    1, 
                    %s, 
                    %s, 
                    %s, 
                    %s, 
                    'ACTIVO',
                    NOW(), 
                    NOW(), 
                    %s, 
                    %s, 
                    %s, 
                    %s
                );
                """
                
                cursor.execute(insert_query, (
                    esi_ruc, esi_dv, esi_nombre, esi_descripcion,
                    esi_email, esi_passwd, esi_token, esi_url
                ))
                
                connection.commit()
                print("✓ Configuración ESI insertada exitosamente desde variables de entorno")
            else:
                print("✓ Configuración ESI ya existe")
            
            cursor.close()
            connection.close()
            return True
            
        except psycopg2.OperationalError as e:
            print(f"✗ Error de conexión: {e}")
            if attempt < max_retries - 1:
                print(f"Esperando {retry_delay} segundos antes de reintentar...")
                time.sleep(retry_delay)
            else:
                print("✗ No se pudo conectar a la base de datos después de varios intentos")
                return False
        except Exception as e:
            print(f"✗ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = init_esi()
    sys.exit(0 if success else 1)