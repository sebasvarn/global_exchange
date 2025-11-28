import psycopg2
from dotenv import load_dotenv
import os
from datetime import datetime
import sys

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

def connect_to_db():
    try:
        connection = psycopg2.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME")
        )
        cursor = connection.cursor()
        print("Conectado a la base de datos")

        # Consulta de ejemplo
        cursor.execute("SELECT version();")
        record = cursor.fetchone()
        print("Conectado a - ", record, "\n")

        return connection, cursor

    except (Exception, psycopg2.Error) as error:
        print("Error al conectar a PostgreSQL", error)
        return None, None

def check_esi_exists(connection, cursor):
    try:
        cursor.execute("SELECT COUNT(*) FROM public.esi;")
        count = cursor.fetchone()[0]
        return count > 0
    except (Exception, psycopg2.Error) as error:
        print("Error al verificar la existencia de registros en la tabla 'esi'", error)
        return False
    
def delete_all_esi_records(connection, cursor):
    try:
        cursor.execute("DELETE FROM public.esi;")
        connection.commit()
        print("Todos los registros de la tabla 'esi' han sido eliminados")
        return True
    except (Exception, psycopg2.Error) as error:
        print("Error al eliminar los registros de la tabla 'esi'", error)
        return False

def insert_de_1(connection, cursor):
    # Pedir por consola el valor de dNumDoc
    #dNumDoc = input("Ingrese el valor de dNumDoc (debe ser un string numérico de longitud 7): ")
    dNumDoc = input("Ingrese el número de documento (251-300): ")
    dNumDoc = dNumDoc.zfill(7)  # Completar con ceros a la izquierda si es necesario

    # Obtener la fecha del sistema en formato YYYY-MM-DD
    dFeEmiDE = datetime.now().strftime("%Y-%m-%d")

    try:
        insert_query = f"""
        INSERT INTO public.de
        (iTiDE, dFeEmiDE, dEst, dPunExp, dNumDoc, CDC, dSerieNum, estado, 
        estado_sifen, desc_sifen, error_sifen, fch_sifen, estado_can, desc_can, error_can, fch_can, estado_inu, desc_inu, error_inu, fch_inu, 
        iTipEmi, dNumTim, dFeIniT, iTipTra, iTImp, cMoneOpe, dTiCam, dInfoFisc, dRucEm, dDVEmi, 
        iTipCont, dNomEmi, dDirEmi, dNumCas, 
        cDepEmi, dDesDepEmi, cCiuEmi, dDesCiuEmi, dTelEmi, dEmailE, 
        iNatRec, iTiOpe, cPaisRec, iTiContRec, dRucRec, dDVRec, iTipIDRec, dDTipIDRec, dNumIDRec, 
        dNomRec, dEmailRec, 
        dDirRec, dNumCasRec, cDepRec, dDesDepRec, cCiuRec, dDesCiuRec, 
        iNatVen, iTipIDVen, dNumIDVen, dNomVen, dDirVen, dNumCasVen, cDepVen, dDesDepVen, cCiuVen, dDesCiuVen, 
        dDirProv, cDepProv, dDesDepProv, cCiuProv, dDesCiuProv, 
        iMotEmi, 
        iIndPres, iCondOpe, dPlazoCre, 
        dModCont, dEntCont, dAnoCont, dSecCont, dFeCodCont, 
        dSisFact, dInfAdic, 
        iMotEmiNR, iRespEmiNR, 
        iTipTrans, iModTrans, iRespFlete, dIniTras, dFinTras, 
        dDirLocSal, dNumCasSal, cDepSal, dDesDepSal, cCiuSal, dDesCiuSal, 
        dDirLocEnt, dNumCasEnt, cDepEnt, dDesDepEnt, cCiuEnt, dDesCiuEnt, 
        dTiVehTras, dMarVeh, dTipIdenVeh, dNroIDVeh, dNroMatVeh, 
        iNatTrans, dNomTrans, dRucTrans, dDVTrans, iTipIDTrans, dNumIDTrans, 
        dNumIDChof, dNomChof, 
        fch_ins, fch_upd)
        VALUES( '1', '{dFeEmiDE}', '001', '003', '{dNumDoc}', '0', '', 'Borrador', 
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 
        '1', '02595733', '2025-03-27', '2', '5', 'PYG', '1', '', '2595733', '3', 
        '1', 'DE generado en ambiente de prueba - sin valor comercial ni fiscal', 'YVAPOVO C/ TOBATI', '1543',  
        '1', 'CAPITAL', '1', 'ASUNCION (DISTRITO)', '(0961)988439', 'ggonzar@gmail.com', 
        '1', '1', 'PRY', '2', '80026216', '6', '1', 'RUC', '80026216', 
        'GUILLERMO GONZALEZ', 'soporte@facturasegura.com.py',
        '', '', '', '', '', '', 
        '', '', '', '', '', '', '', '', '', '', 
        '', '', '', '', '', 
        '', 
        '1', '1', '', 
        '', '', '', '', '', 
        '1', 'informacion adicional', 
        '', '', 
        '', '', '', '', '', 
        '', '', '', '', '', '', 
        '', '', '', '', '', '', 
        '', '', '', '', '', 
        '', '', '', '', '', '', 
        '', '', 
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id;
        """
        cursor.execute(insert_query)
        connection.commit()
        inserted_id = cursor.fetchone()[0]
        print("Registro insertado exitosamente, ID:", inserted_id)
        return inserted_id

    except (Exception, psycopg2.Error) as error:
        print("Error al insertar el registro en PostgreSQL", error)
        return None

def insert_gActEco(connection, cursor, de_id):
    try:
        insert_query = f"""
        INSERT INTO public.gActEco
        (cActEco, dDesActEco, fch_ins, fch_upd, de_id) VALUES
        ('62010', 'Actividades de programación informática', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, {de_id}),
        ('74909', 'Otras actividades profesionales, científicas y técnicas n.c.p.', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, {de_id});
        """
        cursor.execute(insert_query)
        connection.commit()
        print("Registros de gActEco insertados exitosamente")
        return True

    except (Exception, psycopg2.Error) as error:
        print("Error al insertar registros de gActEco en PostgreSQL", error)
        return None

def insert_gCamItem(connection, cursor, de_id):
    try:
        insert_query = f"""
        INSERT INTO public.gCamItem
        (dCodInt, dDesProSer, dCantProSer, dPUniProSer, dDescItem, 
        iAfecIVA, dPropIVA, dTasaIVA, 
        dParAranc, dNCM, dDncpG, dDncpE, dGtin, dGtinPq, 
        fch_ins, fch_upd, 
        de_id) VALUES
        ('1', 'ALQUILER CASA ITURBE', '1', '2000000', '0', 
        '1', '100', '5', 
        '', '', '', '', '', '', 
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 
        {de_id}),
        ('1', 'REMERA DE LA COMISION', '1', '20000', '4000', 
        '1', '100', '10', 
        '', '', '', '', '', '', 
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 
        {de_id}),
        ('1', 'MERCADERIA EXONERADA', '1', '15000', '0', 
        '2', '0', '0', 
        '', '', '', '', '', '', 
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 
        {de_id}),
        ('1', 'MERCADERIA EXENTA', '1', '19500', '0', 
        '3', '0', '0', 
        '', '', '', '', '', '', 
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 
        {de_id}),
        ('1', 'MERCADERIA GRAVADO PARCIAL', '1', '100000', '0', 
        '4', '30', '10', 
        '', '', '', '', '', '', 
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 
        {de_id});
        """
        cursor.execute(insert_query)
        connection.commit()
        print("Registros de gCamItem insertados exitosamente")
        return True

    except (Exception, psycopg2.Error) as error:
        print("Error al insertar registros de gCamItem en PostgreSQL", error)
        return None

def insert_gPaConEIni(connection, cursor, de_id):
    try:
        insert_query = f"""
        INSERT INTO public.gPaConEIni
        (iTiPago, dMonTiPag, cMoneTiPag, dTiCamTiPag, 
        dNumCheq, dBcoEmi, 
        iDenTarj, iForProPa, 
        fch_ins, fch_upd, de_id)
        VALUES('1', '0', 'PYG', '1', 
        '', '', 
        '', '', 
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, {de_id});
        """
        cursor.execute(insert_query)
        connection.commit()
        print("Registro de gPaConEIni insertado exitosamente")
        return True

    except (Exception, psycopg2.Error) as error:
        print("Error al insertar registro de gPaConEIni en PostgreSQL", error)
        return None

def update_de_confirmado(connection, cursor, de_id):
    try:
        update_query = f"""
        UPDATE public.de
        SET estado = 'Confirmado'
        WHERE estado = 'Borrador'
        AND id = {de_id};
        """
        cursor.execute(update_query)
        connection.commit()
        print("Registro actualizado a 'Confirmado' exitosamente")
        return True

    except (Exception, psycopg2.Error) as error:
        print("Error al actualizar el registro a 'Confirmado' en PostgreSQL", error)
        return None

def update_de_cancelar(connection, cursor, cdc):
    try:
        update_query = f"""
        UPDATE public.de
        SET estado = 'Cancelar'
        WHERE cdc = '{cdc}';
        """
        cursor.execute(update_query)
        connection.commit()
        print("Registro actualizado a 'Cancelar' exitosamente")
        return True

    except (Exception, psycopg2.Error) as error:
        print("Error al actualizar el registro a 'Cancelar' en PostgreSQL", error)
        return None

def insert_de_inutilizar(connection, cursor):
    # Pedir por consola el valor de dNumDoc
    dNumDoc = input("Ingrese el valor de dNumDoc (debe ser un string numérico de longitud 7): ")
    dNumDoc = dNumDoc.zfill(7)  # Completar con ceros a la izquierda si es necesario

    try:
        insert_query = f"""
        INSERT INTO public.de
        (iTiDE, dFeEmiDE, dEst, dPunExp, dNumDoc, CDC, dSerieNum, estado, 
        estado_sifen, desc_sifen, error_sifen, fch_sifen, estado_can, desc_can, error_can, fch_can, estado_inu, desc_inu, error_inu, fch_inu, 
        iTipEmi, dNumTim, dFeIniT, iTipTra, iTImp, cMoneOpe, dTiCam, dInfoFisc, dRucEm, dDVEmi, 
        iTipCont, dNomEmi, dDirEmi, dNumCas, 
        cDepEmi, dDesDepEmi, cCiuEmi, dDesCiuEmi, dTelEmi, dEmailE, 
        iNatRec, iTiOpe, cPaisRec, iTiContRec, dRucRec, dDVRec, iTipIDRec, dDTipIDRec, dNumIDRec, 
        dNomRec, dEmailRec, 
        dDirRec, dNumCasRec, cDepRec, dDesDepRec, cCiuRec, dDesCiuRec, 
        iNatVen, iTipIDVen, dNumIDVen, dNomVen, dDirVen, dNumCasVen, cDepVen, dDesDepVen, cCiuVen, dDesCiuVen, 
        dDirProv, cDepProv, dDesDepProv, cCiuProv, dDesCiuProv, 
        iMotEmi, 
        iIndPres, iCondOpe, dPlazoCre, 
        dModCont, dEntCont, dAnoCont, dSecCont, dFeCodCont, 
        dSisFact, dInfAdic, 
        iMotEmiNR, iRespEmiNR, 
        iTipTrans, iModTrans, iRespFlete, dIniTras, dFinTras, 
        dDirLocSal, dNumCasSal, cDepSal, dDesDepSal, cCiuSal, dDesCiuSal, 
        dDirLocEnt, dNumCasEnt, cDepEnt, dDesDepEnt, cCiuEnt, dDesCiuEnt, 
        dTiVehTras, dMarVeh, dTipIdenVeh, dNroIDVeh, dNroMatVeh, 
        iNatTrans, dNomTrans, dRucTrans, dDVTrans, iTipIDTrans, dNumIDTrans, 
        dNumIDChof, dNomChof, 
        fch_ins, fch_upd)
        VALUES( '1', '', '001', '001', '{dNumDoc}', '0', '', 'Inutilizar', 
        '', '', '', '', '', '', '', '', '', '', '', '', 
        '', '80143335', '', '', '', '', '', '', '80143335', '', 
        '', '', '', '', 
        '', '', '', '', '', '', 
        '', '', '', '', '', '', '', '', '', 
        '', '', 
        '', '', '', '', '', '', 
        '', '', '', '', '', '', '', '', '', '', 
        '', '', '', '', '', 
        '', 
        '', '', '', 
        '', '', '', '', '', 
        '', '', 
        '', '', 
        '', '', '', '', '', 
        '', '', '', '', '', '', 
        '', '', '', '', '', '', 
        '', '', '', '', '', 
        '', '', '', '', '', '', 
        '', '', 
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """
        cursor.execute(insert_query)
        connection.commit()
        print("Registro insertado con estado 'Inutilizar' exitosamente")
        return True

    except (Exception, psycopg2.Error) as error:
        print("Error al insertar el registro con estado 'Inutilizar' en PostgreSQL", error)
        return None

def insert_esi(connection, cursor):
    # Solicitar datos por consola
    ruc = input("Ingrese el RUC del ESI: ")
    ruc_dv = input("Ingrese el DV del ESI: ")
    nombre = input("Ingrese el Nombre del ESI: ")
    descripcion = input("Ingrese la Descripción del ESI: ")
    esi_email = input("Ingrese el email del ESI: ")
    esi_passwd = input("Ingrese la contraseña del ESI: ")
    ambiente = input("¿Es para el Ambiente TEST o PROD? (Ingrese 'TEST' o 'PROD'): ").strip().upper()

    if ambiente == "TEST":
        esi_url = "https://apitest.facturasegura.com.py"
    elif ambiente == "PROD":
        esi_url = "https://api.facturasegura.com.py"
    else:
        print("Ambiente no válido. Debe ser 'TEST' o 'PROD'.")
        return None

    try:
        insert_query = f"""
        INSERT INTO public.esi (ruc, ruc_dv, nombre, descripcion, estado, esi_email, esi_passwd, esi_token, esi_url)
        VALUES ('{ruc}', '{ruc_dv}', '{nombre}', '{descripcion}', 'ACTIVO', '{esi_email}', '{esi_passwd}', '', '{esi_url}');
        """
        cursor.execute(insert_query)
        connection.commit()
        print("Registro insertado en la tabla 'esi' exitosamente")
        return True

    except (Exception, psycopg2.Error) as error:
        print("Error al insertar el registro en la tabla 'esi' en PostgreSQL", error)
        return None

if __name__ == "__main__":
    connection, cursor = connect_to_db()
    if connection and cursor:
        if not check_esi_exists(connection, cursor):
            print("No existe ningún registro en la tabla 'esi'. Inicializando...")
            insert_esi(connection, cursor)
        else:
            while True:
                print("Opciones disponibles:")
                print("1. Aprobar")
                print("2. Cancelar")
                print("3. Inutilizar")
                print("4. Inicializar ESI")
                print("5. Finalizar")
                opcion = input("Ingrese la acción que quiere realizar: ").strip().lower()

                if opcion == "aprobar" or opcion == "1":
                    de_id = insert_de_1(connection, cursor)
                    if de_id:
                        insert_gActEco(connection, cursor, de_id)
                        insert_gCamItem(connection, cursor, de_id)
                        insert_gPaConEIni(connection, cursor, de_id)
                        update_de_confirmado(connection, cursor, de_id)
                elif opcion == "cancelar" or opcion == "2":
                    cdc = input("Ingrese el valor de CDC: ")
                    update_de_cancelar(connection, cursor, cdc)
                elif opcion == "inutilizar" or opcion == "3":
                    insert_de_inutilizar(connection, cursor)
                elif opcion == "inicializar" or opcion == "4":
                    if check_esi_exists(connection, cursor):
                        confirm = input("Ya existen registros de configuracion ESI. ¿Desea inicializar el ESI igualmente? (s/n): ").strip().lower()
                        if confirm != 's':
                            print("Inicialización cancelada.")
                        else:
                            delete_all_esi_records(connection, cursor)
                            insert_esi(connection, cursor)
                elif opcion == "finalizar" or opcion == "5":
                    break
                else:
                    print("Opción no válida. Por favor, intente de nuevo.")

        cursor.close()
        connection.close()
        print("Conexión a PostgreSQL cerrada")
