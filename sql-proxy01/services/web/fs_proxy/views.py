import logging
import requests
import os
from fs_proxy import app
from fs_proxy.models import Esi, DE, DE_file,gActEco, gCamDEAsoc, gCamItem, gPaConEIni, row2dict
from fs_proxy.db import db
from datetime import datetime
from requests.adapters import HTTPAdapter, Retry

_CONFIRMADO = "Confirmado"
_CANCELAR = "Cancelar"
_INUTILIZAR = "Inutilizar"
_SOL_APROBACION = "Sol.Aprobacion"
_SOL_APROBACION_FS = "SOL.APROBACION"
_SOL_CANCELACION = "Sol.Cancelacion"
_SOL_INUTILIZACION = "Sol.Inutilizacion"
_APROBADO = "Aprobado"
_APROBADO_OBS_FS = "Aprobado con observación"
_APROBADO_OBS = "Aprobado OBS"
_RECHAZADO = "Rechazado"
_ERROR_SIFEN_FS = "ERROR_SIFEN"
_ERROR_SIFEN = "Error SIFEN"
_ERROR_SIFEN_INU = "Error SIFEN (Inu)"
_ERROR_SIFEN_CAN = "Error SIFEN (Can)"
_ERROR_SIFEN_APR = "Error SIFEN (Apr)"
_CANCELADO = "Cancelado"
_INUTILIZADO = "Inutilizado"
_VERIFICAR_DATOS_INU = "Verificar datos (Rech.Inu.)"
_VERIFICAR_DATOS_CAN = "Verificar datos (Rech.Can.)"
_VERIFICAR_DATOS_APR = "Verificar datos (Rech.Apr.)"
_REINGRESADO = "Reingresado"
_ENVIADO_A_SIFEN = "ENVIADO_A_SIFEN"
_ERROR_ENVIO_LOTE = "ERROR_ENVIO_LOTE"
_REINTENTAR_LOTE = "REINTENTAR_LOTE"
_ERROR_CONSULTA_LOTE = "ERROR_CONSULTA_LOTE"
_KUDE_PATH = "/kude"

def make_request_esi_get(url,method,header):
    resultado = {}
    s = requests.Session()
    retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])
    s.mount('https://', HTTPAdapter(max_retries=retries))
    logging.debug("method "+method)
    logging.debug("url "+url)
    logging.debug("headers "+str(header))
    rsp = s.request(method, url, headers=header)
    resultado["http_code"] = rsp.status_code
    if rsp.status_code != 200:
        logging.debug("Error : SERVER RESPONSE STATUS CODE "+str(rsp.status_code))
        logging.debug(url)
        resultado["error"] = rsp.content.decode()
    else:
        resultado["response"] = rsp
    return resultado

def make_request_esi(url,method,header,data):
    resultado = {}
    s = requests.Session()
    retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])
    s.mount('https://', HTTPAdapter(max_retries=retries))
    logging.debug("method "+method)
    logging.debug("url "+url)
    logging.debug("headers "+str(header))
    logging.debug("data "+str(data))
    rsp = s.request(method, url, headers=header, json=data)
    resultado["http_code"] = rsp.status_code
    if rsp.status_code != 200:
        logging.debug("Error : SERVER RESPONSE STATUS CODE "+str(rsp.status_code))
        logging.debug(url)
        logging.debug(data)
        resultado["error"] = rsp.content.decode()
    else:
        resultado["response"] = rsp.json()
    return resultado

def saveFile(path,fileContent,baseName,extention):
    defile = None
    filepath = ""
    try:
        os.makedirs(path, exist_ok=True)
        filepath = path+baseName+"_"+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+"."+extention
        logging.info('GUARDANDO ARCHIVO BRUTO EN : '+ filepath )
        defile = open(filepath, "w")
        n = defile.write(fileContent) 
        logging.debug('BYTES ESCRITOS: '+ str(n) )
    except Exception as e:
        logging.debug('EXCEPTION GUARDANDO ARCHIVO BRUTO: '+ str(e) )
    finally:
        if defile != None:
            defile.close()
    return filepath

def saveBinaryFile(path,fileContent,baseName,extention):
    defile = None
    filepath = ""
    try:
        os.makedirs(path, exist_ok=True)
        filepath = path+baseName+"_"+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+"."+extention
        logging.info('GUARDANDO ARCHIVO BRUTO EN : '+ filepath )
        defile = open(filepath, "wb")
        n = defile.write(fileContent) 
        logging.debug('BYTES ESCRITOS: '+ str(n) )
    except Exception as e:
        logging.debug('EXCEPTION GUARDANDO ARCHIVO BRUTO: '+ str(e) )
    finally:
        if defile != None:
            defile.close()
    return filepath

def get_token_misife(url,email,passwd):
    token = ""
    data = {"email":email, "password":passwd}
    resultado = make_request_esi(url+"/login?include_auth_token","POST",{"Content-Type": "application/json"},data)
    if "error" in resultado:
        logging.debug("Error al hacer login "+email)
        logging.debug(resultado["error"])
    else:
        resp = resultado["response"] #es json
        token = resp["response"]["user"]["authentication_token"]
    return token    

# Define a simple route
@app.route('/')
def hello_world():
    return "Hello World, fs_proxy!"

# Example route with dynamic URL parameter
@app.route('/hello/<name>')
def hello_name(name):
    return f'Hello dear, {name}!'

def do_DE():
    logging.info("Ejecutamos do_DE")
    esi = Esi()
    esi = Esi.query.filter(Esi.estado=='ACTIVO').order_by(Esi.id).first() #solo procesamos el primer esi
    if esi: 
        logging.info("ESI : "+esi.nombre)
        if esi.esi_passwd is not None:
            if esi.esi_passwd != "":
                logging.debug("Tiene passwd. Obtenemos token")
                logging.debug("URL : "+esi.esi_url)
                #obtenemos token
                token = get_token_misife(esi.esi_url,esi.esi_email,esi.esi_passwd)
                logging.debug("token :"+token)
                esi.esi_token = token
                if token != "":
                    #vaciamos passwd
                    esi.esi_passwd = ""
                    logging.debug("guardamos token")
                db.session.commit()
            else:
                logging.debug("esi_passwd es cadena vacia")
        else:
            logging.debug("esi_passwd es nulo")
        if not (esi.esi_token is None or esi.esi_token.strip() == ""):
            logging.debug("Ya tiene token")
            url = esi.esi_url+"/misife00/v1/esi"
            header = {'accept': 'application/json', "Content-Type": "application/json", "Authentication-Token":esi.esi_token}
            header_get = {"Authentication-Token":esi.esi_token}
            ### PROCESAMOS DE PARA CONSULTAR ESTADO_SIFEN ###
            logging.info("Consultamos estado_sifen...")
            estados_consulta = [_SOL_APROBACION,_SOL_CANCELACION,_SOL_INUTILIZACION,_ERROR_SIFEN]
            for estado in estados_consulta:
                search = "{}%".format(estado)
                list_de = db.session.query(DE).filter(DE.estado.like(search)).order_by(DE.dEst,DE.dPunExp,DE.dNumDoc).all()
                for e_de in list_de:
                    CDC = e_de.CDC
                    dRucEm = e_de.dRucEm
                    data = {"operation":"get_estado_sifen","params":{
                        "CDC":CDC,"dRucEm":dRucEm}}
                    resultado = make_request_esi(url,"POST",header,data)
                    if "error" in resultado:
                        logging.debug("Error :" + str(resultado["error"]))
                        e_de.desc_sifen = str(resultado["error"])
                    else:
                        logging.debug("Respuesta : "+str(resultado["response"]))
                        if  resultado["response"]["code"] < 0:
                            e_de.desc_sifen = str(resultado["response"]["results"][0])
                            continue
                        estado_de = resultado["response"]["results"][0]
                        if e_de.estado in(_SOL_INUTILIZACION , _ERROR_SIFEN_INU):
                            if estado_de["estado_inu"] == _APROBADO:
                                e_de.estado = _INUTILIZADO
                            elif estado_de["estado_inu"] == _RECHAZADO:
                                e_de.estado = _VERIFICAR_DATOS_INU
                            elif estado_de["estado_inu"] == _ERROR_SIFEN_FS:
                                e_de.estado = _ERROR_SIFEN_INU
                        if e_de.estado in (_SOL_CANCELACION, _ERROR_SIFEN_CAN):
                            if estado_de["estado_can"] == _APROBADO:
                                e_de.estado = _CANCELADO
                            elif estado_de["estado_can"] == _RECHAZADO:
                                e_de.estado = _VERIFICAR_DATOS_CAN
                            elif estado_de["estado_can"] == _ERROR_SIFEN_FS:
                                e_de.estado = _ERROR_SIFEN_CAN
                        if e_de.estado in (_SOL_APROBACION, _ERROR_SIFEN_APR):
                            if estado_de["estado_sifen"] == _APROBADO:
                                e_de.estado = _APROBADO
                            elif estado_de["estado_sifen"] == _APROBADO_OBS_FS:
                                e_de.estado = _APROBADO_OBS
                            elif estado_de["estado_sifen"] == _RECHAZADO:
                                e_de.estado = _RECHAZADO
                            elif estado_de["estado_sifen"] == _REINGRESADO:
                                e_de.estado = _REINGRESADO
                            elif estado_de["estado_sifen"] == _SOL_APROBACION_FS:
                                if e_de.estado != _SOL_APROBACION:
                                    e_de.estado = _SOL_APROBACION
                                #NO SE CAMBIA ESTADO
                                pass
                            elif estado_de["estado_sifen"] == _ENVIADO_A_SIFEN:
                                if e_de.estado != _SOL_APROBACION:
                                    e_de.estado = _SOL_APROBACION
                                #NO SE CAMBIA ESTADO
                                pass
                            elif estado_de["estado_sifen"] == _ERROR_SIFEN_FS:
                                e_de.estado = _ERROR_SIFEN_APR
                            elif estado_de["estado_sifen"] == _ERROR_ENVIO_LOTE:
                                e_de.estado = _ERROR_SIFEN_APR
                            elif estado_de["estado_sifen"] == _REINTENTAR_LOTE:
                                e_de.estado = _ERROR_SIFEN_APR
                            elif estado_de["estado_sifen"] == _ERROR_CONSULTA_LOTE:
                                e_de.estado = _ERROR_SIFEN_APR
                        e_de.estado_sifen = estado_de["estado_sifen"]
                        e_de.desc_sifen = estado_de["desc_sifen"]
                        e_de.error_sifen = estado_de["error_sifen"]
                        e_de.fch_sifen = estado_de["fch_sifen"]
                        e_de.estado_can = estado_de["estado_can"]
                        e_de.desc_can = estado_de["desc_can"]
                        e_de.error_can = estado_de["error_can"]
                        e_de.fch_can = estado_de["fch_can"]
                        e_de.estado_inu = estado_de["estado_inu"]
                        e_de.desc_inu = estado_de["desc_inu"]
                        e_de.error_inu = estado_de["error_inu"]
                        e_de.fch_inu = estado_de["fch_inu"]
                #guardamos los estados
                db.session.commit()
            ### PROCESAMOS DE A CANCELAR ###
            logging.info("Procesamos cancelacion ...")
            list_de = db.session.query(DE).filter(DE.estado==_CANCELAR).order_by(DE.dEst,DE.dPunExp,DE.dNumDoc).all()
            for e_de in list_de:
                CDC = e_de.CDC
                dRucEm = e_de.dRucEm
                data = {"operation":"sol_cancelacion","params":{
                    "CDC":CDC,"dRucEm":dRucEm}}
                resultado = make_request_esi(url,"POST",header,data)                
                if "error" in resultado:
                    logging.debug("Error :" + str(resultado["error"]))
                    e_de.error_can = str(resultado["error"])
                    e_de.estado = _VERIFICAR_DATOS_CAN
                else:
                    logging.debug("Respuesta : "+str(resultado["response"]))
                    if  resultado["response"]["code"] < 0:
                        logging.debug("Error proceso WS :" + str(resultado["response"]["description"]))
                        e_de.error_can = str(resultado["response"]["description"])
                        e_de.estado = _VERIFICAR_DATOS_CAN
                        continue
                    e_de.estado = _SOL_CANCELACION
            #guardamos los enviados
            db.session.commit()
            ### PROCESAMOS DE A INUTILIZAR ###
            logging.info("Procesamos inutilizacion ...")
            list_de = db.session.query(DE).filter(DE.estado==_INUTILIZAR).order_by(DE.dEst,DE.dPunExp,DE.dNumDoc).all()
            for e_de in list_de:
                CDC = e_de.CDC
                dRucEm = e_de.dRucEm
                iTiDE = e_de.iTiDE
                dNumTim = e_de.dNumTim
                dEst = e_de.dEst
                dPunExp = e_de.dPunExp
                dNumDoc = e_de.dNumDoc
                data = {"operation":"sol_inutilizacion","params":{
                    "dRucEm":dRucEm,
                    "iTiDE":iTiDE,
                    "dNumTim":dNumTim,
                    "dEst":dEst,
                    "dPunExp":dPunExp,
                    "dNumDoc":dNumDoc}}
                resultado = make_request_esi(url,"POST",header,data)                
                if "error" in resultado:
                    logging.debug("Error :" + str(resultado["error"]))
                    e_de.error_inu = str(resultado["error"])
                    e_de.estado = _VERIFICAR_DATOS_INU
                else:
                    logging.debug("Respuesta : "+str(resultado["response"]))
                    if  resultado["response"]["code"] < 0:
                        logging.debug("Error proceso WS :" + str(resultado["response"]["description"]))
                        e_de.error_inu = str(resultado["response"]["description"])
                        e_de.estado = _VERIFICAR_DATOS_INU
                        continue
                    else:
                        if "CDC" in resultado["response"]["results"][0]:
                            e_de.CDC = resultado["response"]["results"][0]["CDC"]
                    e_de.estado = _SOL_INUTILIZACION
            #guardamos los enviados
            db.session.commit()      

            ### PROCESAMOS DE CONFIRMADOS ###
            logging.info("Procesamos aprobacion ...")
            #creamos el DE
            list_de = db.session.query(DE).filter(DE.estado==_CONFIRMADO).order_by(DE.dEst,DE.dPunExp,DE.dNumDoc).all()
            for e_de in list_de:
                d_de = row2dict(e_de)
                d_de["dCodSeg"] = "0"
                d_de["dDVId"] = "0"
                d_de["gActEco"] = []
                for e in e_de.gActEcos:
                    d_de["gActEco"].append(row2dict(e))
                d_de["gCamItem"] = []
                for e in e_de.gCamItems:
                    d_e = row2dict(e)
                    d_e["dDescGloItem"] = "0"
                    d_e["dAntPreUniIt"] = "0"
                    d_e["dAntGloPreUniIt"] = "0"
                    d_e["cUniMed"] = "77"
                    d_de["gCamItem"].append(d_e)
                d_de["gPaConEIni"] = []
                for e in e_de.gPaConEInis:
                    d_de["gPaConEIni"].append(row2dict(e))
                d_de["gCamDEAsoc"] = []
                for e in e_de.gCamDEAsocs:
                    d_de["gCamDEAsoc"].append(row2dict(e))
                logging.debug(str(d_de))
                #calculamos de
                data = {"operation":"calcular_de","params":{"DE":d_de}}
                resultado = make_request_esi(url,"POST",header,data)
                if "error" in resultado:
                    logging.debug("Error :" + str(resultado["error"]))
                    e_de.error_sifen = str(resultado["error"])
                    e_de.estado = _VERIFICAR_DATOS_APR
                else:
                    logging.debug("Respuesta : "+str(resultado["response"]))
                    if  resultado["response"]["code"] < 0:
                        logging.debug("Error proceso WS :" + str(resultado["response"]["description"]))
                        e_de.error_sifen = str(resultado["response"]["description"])
                        e_de.estado = _VERIFICAR_DATOS_APR
                        continue
                    de_calc = resultado["response"]["results"][0]["DE"]
                    data = {"operation":"generar_de","params":{"DE":de_calc}}
                    resultado = make_request_esi(url,"POST",header,data)
                    if "error" in resultado:
                        logging.debug("Error :" + str(resultado["error"]))
                        e_de.error_sifen = str(resultado["error"])
                        e_de.estado = _VERIFICAR_DATOS_APR
                    else:
                        logging.debug("Respuesta : "+str(resultado["response"]))
                        if  resultado["response"]["code"] < 0:
                            logging.debug("Error proceso WS :" + str(resultado["response"]["description"]))
                            e_de.error_sifen = str(resultado["response"]["description"])
                            e_de.estado = _VERIFICAR_DATOS_APR
                            continue
                        CDC = resultado["response"]["results"][0]["CDC"]
                        e_de.CDC = CDC
                        e_de.estado = _SOL_APROBACION
            #guardamos los enviados
            db.session.commit()

            ### PROCESAMOS DE APROBADOS PARA BAJAR XML Y PDF ###
            logging.info("Bajamos XML ...")
            estados_consulta = [_APROBADO,_APROBADO_OBS]
            for estado in estados_consulta:
                search = "{}%".format(estado)
                list_de = db.session.query(DE
                    ).filter(DE.estado.like(search)
                    ).filter(~DE_file.query.filter(DE_file.estado=="ACTIVO"
                                                ).filter(DE_file.tipo=="XML"
                                                ).filter(DE.id == DE_file.de_id).exists()
                    ).order_by(DE.dEst,DE.dPunExp,DE.dNumDoc).all()
                for e_de in list_de:
                    
                    dRucEm = e_de.dRucEm
                    CDC = e_de.CDC
                    anho_mes = CDC[25:31]
                    file_name = e_de.dEst + "-" + e_de.dPunExp + "-" + e_de.dNumDoc 
                    #bajamos xml 
                    tipo = 'XML'
                    url_get = url + "/dwn_xml/"+dRucEm+"/"+CDC
                    resultado = make_request_esi_get(url_get,"GET",header_get)                
                    if "error" in resultado:
                        logging.debug("Error :" + str(resultado["error"]))
                    else:
                        file_path = saveFile(_KUDE_PATH+"/"+anho_mes+"/",resultado["response"].text,file_name,"xml")
                        e_de_file = DE_file()
                        e_de_file.tipo = tipo
                        e_de_file.estado = "ACTIVO"
                        e_de_file.path = file_path
                        e_de.DE_files.append(e_de_file)
                #guardamos los enviados
                db.session.commit()   
            logging.info("Bajamos PDF ...")
            for estado in estados_consulta:
                search = "{}%".format(estado)
                list_de = db.session.query(DE
                    ).filter(DE.estado.like(search)
                    ).filter(~DE_file.query.filter(DE_file.estado=="ACTIVO"
                                                ).filter(DE_file.tipo=="PDF"
                                                ).filter(DE.id == DE_file.de_id).exists()
                    ).order_by(DE.dEst,DE.dPunExp,DE.dNumDoc).all()
                for e_de in list_de:
                    dRucEm = e_de.dRucEm
                    CDC = e_de.CDC
                    file_name = e_de.dEst + "-" + e_de.dPunExp + "-" + e_de.dNumDoc 
                    anho_mes = CDC[25:31]         
                    #bajamos pdf
                    tipo = 'PDF'
                    url_get = url + "/dwn_kude/"+dRucEm+"/"+CDC
                    resultado = make_request_esi_get(url_get,"GET",header_get)                
                    if "error" in resultado:
                        logging.debug("Error :" + str(resultado["error"]))
                    else:
                        file_path = saveBinaryFile(_KUDE_PATH+"/"+anho_mes+"/",resultado["response"].content,file_name,"pdf")
                        e_de_file = DE_file()
                        e_de_file.tipo = tipo
                        e_de_file.estado = "ACTIVO"
                        e_de_file.path = file_path
                        e_de.DE_files.append(e_de_file)
                #guardamos los enviados
                db.session.commit()
    else:
        logging.debug("No existe esi")

@app.route('/task/<name>',methods=['POST'])
def task(name):
    if name == "do_de":
        do_DE()
        logging.debug("Ejecutado do_DE")
        return 'Ejecutado do_DE'
    return f'Tarea {name} no encotrada!'