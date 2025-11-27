#!/usr/bin/env python3
"""
Script para inicializar la configuración ESI automáticamente
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def init_esi():
    try:
        connection = psycopg2.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "db"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME")
        )
        cursor = connection.cursor()
        
        # Verificar si ya existe configuración ESI
        cursor.execute("SELECT COUNT(*) FROM public.esi;")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insertar configuración ESI desde variables de entorno
            ambiente = os.getenv("ESI_AMBIENTE", "TEST")
            esi_url = "https://apitest.facturasegura.com.py" if ambiente == "TEST" else "https://api.facturasegura.com.py"
            
            insert_query = """
            INSERT INTO public.esi (ruc, ruc_dv, nombre, descripcion, estado, esi_email, esi_passwd, esi_token, esi_url)
            VALUES (%s, %s, %s, %s, 'ACTIVO', %s, %s, '', %s);
            """
            
            cursor.execute(insert_query, (
                os.getenv("ESI_RUC"),
                os.getenv("ESI_DV", "0"),
                os.getenv("ESI_NOMBRE", "Global Exchange"),
                os.getenv("ESI_DESCRIPCION", "Configuración para Global Exchange"),
                os.getenv("ESI_EMAIL"),
                os.getenv("ESI_PASSWD"),
                esi_url
            ))
            
            connection.commit()
            print("✓ Configuración ESI inicializada exitosamente")
        else:
            print("✓ Configuración ESI ya existe")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"✗ Error al inicializar ESI: {e}")

if __name__ == "__main__":
    init_esi()