import os
from flask import Blueprint, request, jsonify, current_app, send_file, abort
from fs_proxy import app, db
from fs_proxy.models import Esi, DE, DE_file, gActEco, gCamItem, gPaConEIni, row2dict
from datetime import datetime
from sqlalchemy import text
import logging

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/facturar', methods=['POST'])
def api_facturar():
    """
    Endpoint para generar facturas desde Global Exchange
    """
    try:
        data = request.get_json()
        current_app.logger.info("Datos recibidos para facturación:")
        current_app.logger.info(data)

        if not data:
            current_app.logger.error("No se recibieron datos JSON")
            return jsonify({
                'success': False,
                'error': 'No se recibieron datos JSON'
            }), 400

        # Validar datos requeridos
        required_fields = ['de_data', 'g_act_eco', 'g_cam_item', 'g_pa_con_e_ini']
        for field in required_fields:
            if field not in data:
                current_app.logger.error(f"Campo faltante: {field}")
                return jsonify({
                    'success': False,
                    'error': f'Campo requerido faltante: {field}'
                }), 400

        de_data = data['de_data']
        current_app.logger.info(f"Datos DE: {de_data}")

        # Crear DE
        current_app.logger.info("Creando instancia DE()")
        de = DE()

        # Copiar campos
        campos_de = [
            'iTiDE', 'dFeEmiDE', 'dEst', 'dPunExp', 'iTipEmi',
            'dNumTim', 'dFeIniT', 'iTipTra', 'iTImp', 'cMoneOpe', 'dTiCam',
            'dRucEm', 'dDVEmi', 'iTipCont', 'dNomEmi', 'dDirEmi', 'dNumCas',
            'cDepEmi', 'dDesDepEmi', 'cCiuEmi', 'dDesCiuEmi', 'dTelEmi', 'dEmailE',
            'iNatRec', 'iTiOpe', 'cPaisRec', 'iTiContRec', 'dRucRec', 'dDVRec',
            'iTipIDRec', 'dDTipIDRec', 'dNumIDRec', 'dNomRec', 'dEmailRec',
            'dDirRec', 'dNumCasRec', 'cDepRec', 'dDesDepRec', 'cCiuRec', 'dDesCiuRec',
            'dInfAdic', 'estado'
        ]

        for campo in campos_de:
            if campo in de_data:
                setattr(de, campo, de_data[campo])
                current_app.logger.debug(f"   ✔️ Campo {campo} = {de_data[campo]}")

        # ============================
        #   GENERAR NUMERO DE FACTURA - CORREGIDO
        # ============================
        est = de_data.get('dEst', '001')
        pexp = de_data.get('dPunExp', '003')

        current_app.logger.info(f"Buscando última factura para {est}-{pexp}")

        # Buscar el último número de manera más robusta
        ultimo = (
            DE.query
            .filter(DE.dEst == est, DE.dPunExp == pexp, DE.dNumDoc.isnot(None))
            .order_by(DE.dNumDoc.desc())
            .first()
        )

        if ultimo and ultimo.dNumDoc:
            try:
                # EXTRAER SOLO LA PARTE NUMÉRICA (últimos 7 dígitos)
                import re
                match = re.search(r'(\d{7})$', ultimo.dNumDoc)
                if match:
                    ultimo_num = int(match.group(1))
                    current_app.logger.info(f"Último número extraído: {ultimo_num}")
                else:
                    # Si no encuentra el patrón, intentar convertir directamente
                    ultimo_num = int(ultimo.dNumDoc)
                    current_app.logger.info(f"Último número convertido directamente: {ultimo_num}")
            except Exception as e:
                current_app.logger.warning(f"No se pudo parsear último número: {e}, usando 250")
                ultimo_num = 250
        else:
            current_app.logger.info("ℹ No hay facturas previas, comenzando en 250")
            ultimo_num = 250

        nuevo_num = ultimo_num + 1

        # Reset si excede límite
        if nuevo_num > 9999999:  # Límite para 7 dígitos
            current_app.logger.warning("Número excede límite, reseteando a 1")
            nuevo_num = 1

        # FORMATO CORREGIDO: Solo la parte numérica con 7 dígitos
        numero_generado = f"{nuevo_num:07d}"  # Solo "0000252", no "001-003-0000252"
        current_app.logger.info(f"Número generado (solo numérico): {numero_generado}")

        # Asignar número al DE (solo la parte numérica)
        de.dNumDoc = numero_generado

        # Campos predeterminados
        de.CDC = '0'
        de.dSerieNum = ''
        de.estado_sifen = '1'
        de.desc_sifen = '2'
        de.error_sifen = '3'
        de.fch_sifen = '4'
        de.estado_can = '5'
        de.desc_can = '6'
        de.error_can = '7'
        de.fch_can = '8'
        de.estado_inu = '9'
        de.desc_inu = '10'
        de.error_inu = '11'
        de.fch_inu = '12'
        de.dSisFact = '1'
        de.iIndPres = '1'  
        de.iCondOpe = '1'  
        de.dInfoFisc = ''  
        de.iMotEmi = ''    

        current_app.logger.info("Insertando DE en la sesión")
        db.session.add(de)
        
        # Hacer commit para asegurar que se genera el ID y número
        db.session.commit()
        
        # Refrescar el objeto para obtener los valores de la BD
        db.session.refresh(de)

        current_app.logger.info(f"DE creado con ID {de.id}, Número: {de.dNumDoc}")

        # Validar que el número se generó correctamente
        if not de.dNumDoc:
            current_app.logger.error("ERROR: dNumDoc es NULL después del commit")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': 'No se pudo generar el número de factura'
            }), 500

        # ============================
        #   ACTIVIDADES ECONÓMICAS
        # ============================
        for act_eco_data in data['g_act_eco']:
            current_app.logger.debug(f"Agregando actividad económica: {act_eco_data}")
            act_eco = gActEco()
            act_eco.de_id = de.id
            act_eco.cActEco = act_eco_data.get('cActEco', '')
            act_eco.dDesActEco = act_eco_data.get('dDesActEco', '')
            db.session.add(act_eco)

        # ============================
        #   ITEMS
        # ============================
        for item_data in data['g_cam_item']:
            current_app.logger.debug(f"Agregando item: {item_data}")
            item = gCamItem()
            item.de_id = de.id

            campos_item = [
                'dCodInt', 'dDesProSer', 'dCantProSer', 'dPUniProSer', 'dDescItem',
                'iAfecIVA', 'dPropIVA', 'dTasaIVA', 'cUniMed', 'dParAranc', 'dNCM',
                'dDncpG', 'dDncpE', 'dGtin', 'dGtinPq'
            ]

            for campo in campos_item:
                if campo in item_data:
                    setattr(item, campo, item_data[campo])

            db.session.add(item)

        # ============================
        #   FORMAS DE PAGO
        # ============================
        for pago_data in data['g_pa_con_e_ini']:
            current_app.logger.debug(f"Agregando pago: {pago_data}")
            pago = gPaConEIni()
            pago.de_id = de.id
            pago.iTiPago = pago_data.get('iTiPago', '1')
            pago.dMonTiPag = pago_data.get('dMonTiPag', '0')
            pago.cMoneTiPag = pago_data.get('cMoneTiPag', 'PYG')
            pago.dTiCamTiPag = pago_data.get('dTiCamTiPag', '1')
            db.session.add(pago)

        # Guardar todo
        current_app.logger.info("Commit final a la BD")
        db.session.commit()

        current_app.logger.info(f"Factura generada correctamente: {de.dNumDoc}")

        # RETORNAR FORMATO COMPLETO EN LA RESPUESTA PERO GUARDAR SOLO NUMÉRICO
        numero_completo_para_respuesta = f"{est}-{pexp}-{de.dNumDoc}"

        return jsonify({
            'success': True,
            'id_de': de.id,
            'cdc': de.CDC,
            'numero_factura': numero_completo_para_respuesta,  # Formato completo para respuesta
            'message': 'Documento electrónico creado exitosamente.'
        })

    except Exception as e:
        current_app.logger.exception("🚨 Error al crear factura")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f"Error interno del servidor: {str(e)}"
        }), 500
    

@api_bp.route('/api/kude/<path:filename>')
def servir_kude(filename):
    """
    Endpoint para servir archivos KUDE (PDFs) desde el directorio /kude
    """
    try:
        # Ruta base donde se almacenan los KUDEs
        kude_base_path = "/kude"
        file_path = os.path.join(kude_base_path, filename)
        
        # Verificar que el archivo existe y es seguro
        if not os.path.exists(file_path):
            current_app.logger.error(f"Archivo KUDE no encontrado: {file_path}")
            abort(404)
        
        # Verificar que está dentro del directorio permitido
        if not os.path.realpath(file_path).startswith(os.path.realpath(kude_base_path)):
            current_app.logger.error(f"Intento de acceso a ruta no permitida: {file_path}")
            abort(403)
        
        # Servir el archivo
        return send_file(file_path, as_attachment=False)
    
    except Exception as e:
        current_app.logger.error(f"Error al servir KUDE {filename}: {str(e)}")
        abort(500)

@api_bp.route('/api/kude/cdc/<cdc>')
def servir_kude_por_cdc(cdc):
    """
    Endpoint para servir KUDE por CDC
    """
    try:
        # Buscar el DE por CDC
        de = DE.query.filter(DE.CDC == cdc).first()
        if not de:
            current_app.logger.error(f"DE no encontrado para CDC: {cdc}")
            abort(404)
        
        # Buscar archivo PDF asociado
        pdf_file = DE_file.query.filter(
            DE_file.de_id == de.id,
            DE_file.tipo == 'PDF',
            DE_file.estado == 'ACTIVO'
        ).first()
        
        if not pdf_file or not os.path.exists(pdf_file.path):
            current_app.logger.error(f"PDF no encontrado para CDC: {cdc}")
            abort(404)
        
        # Servir el archivo
        return send_file(
            pdf_file.path, 
            as_attachment=False, 
            download_name=f"factura_{cdc}.pdf"
        )
    
    except Exception as e:
        current_app.logger.error(f"Error al servir KUDE por CDC {cdc}: {str(e)}")
        abort(500)

@api_bp.route('/api/transaccion/<int:transaccion_id>/kude')
def kude_por_transaccion(transaccion_id):
    """
    Endpoint para obtener información del KUDE de una transacción
    Busca por el código de verificación en dInfAdic
    """
    try:
        # Buscar DEs que tengan referencia a esta transacción en dInfAdic
        de = DE.query.filter(
            DE.dInfAdic.like(f'%Transacción #{transaccion_id}%')
        ).first()
        
        if not de:
            return jsonify({
                'success': False,
                'error': 'No se encontró factura para esta transacción'
            }), 404
        
        # Verificar si tiene PDF
        pdf_file = DE_file.query.filter(
            DE_file.de_id == de.id,
            DE_file.tipo == 'PDF',
            DE_file.estado == 'ACTIVO'
        ).first()
        
        if pdf_file and os.path.exists(pdf_file.path):
            return jsonify({
                'success': True,
                'cdc': de.CDC,
                'numero_factura': f"{de.dEst}-{de.dPunExp}-{de.dNumDoc}",
                'estado': de.estado,
                'url_pdf': f"/api/kude/cdc/{de.CDC}"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Factura encontrada pero PDF no disponible'
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error al buscar KUDE para transacción {transaccion_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500

@api_bp.route('/api/factura/estado/<path:numero_factura>')
def estado_factura(numero_factura):
    """
    Endpoint para consultar el estado de una factura por número de factura
    Formato: 001-003-0000251
    """
    try:
        # Parsear el número de factura
        parts = numero_factura.split('-')
        if len(parts) != 3:
            return jsonify({
                'success': False,
                'error': 'Formato de número de factura inválido. Use: EST-PEXP-NUM'
            }), 400
        
        est, pexp, num_doc = parts
        
        de = DE.query.filter(
            DE.dEst == est,
            DE.dPunExp == pexp,
            DE.dNumDoc == num_doc
        ).first()
        
        if not de:
            return jsonify({
                'success': False,
                'error': 'Factura no encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'id': de.id,
            'numero_factura': f"{de.dEst}-{de.dPunExp}-{de.dNumDoc}",
            'cdc': de.CDC,  
            'estado_sifen': de.estado_sifen,
            'desc_sifen': de.desc_sifen,
            'error_sifen': de.error_sifen,
            'fecha_emision': de.dFeEmiDE,
            'estado': de.estado
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al consultar estado de factura {numero_factura}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500
    
@api_bp.route('/api/factura/descargar/<cdc>')
def descargar_factura(cdc):
    """
    Endpoint para descargar factura en diferentes formatos
    """
    try:
        formato = request.args.get('formato', 'pdf').lower()
        de = DE.query.filter(DE.CDC == cdc).first()
        
        if not de:
            return jsonify({
                'success': False,
                'error': 'Factura no encontrada'
            }), 404
        
        if formato == 'pdf':
            pdf_file = DE_file.query.filter(
                DE_file.de_id == de.id,
                DE_file.tipo == 'PDF',
                DE_file.estado == 'ACTIVO'
            ).first()
            
            if pdf_file and os.path.exists(pdf_file.path):
                return send_file(
                    pdf_file.path,
                    as_attachment=True,
                    download_name=f"factura_{cdc}.pdf"
                )
            else:
                return jsonify({
                    'success': False,
                    'error': 'PDF no disponible'
                }), 404
                
        elif formato == 'xml':
            xml_file = DE_file.query.filter(
                DE_file.de_id == de.id,
                DE_file.tipo == 'XML',
                DE_file.estado == 'ACTIVO'
            ).first()
            
            if xml_file and os.path.exists(xml_file.path):
                return send_file(
                    xml_file.path,
                    as_attachment=True,
                    download_name=f"factura_{cdc}.xml"
                )
            else:
                return jsonify({
                    'success': False,
                    'error': 'XML no disponible'
                }), 404
        else:
            return jsonify({
                'success': False,
                'error': 'Formato no soportado. Use "pdf" o "xml"'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error al descargar factura {cdc}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500
    

@api_bp.route('/api/factura/cancelar/<path:numero_factura>', methods=['POST'])
def cancelar_factura(numero_factura):
    """
    Endpoint para cancelar/inutilizar una factura por número de factura
    """
    try:
        # Parsear el número de factura
        parts = numero_factura.split('-')
        if len(parts) != 3:
            return jsonify({
                'success': False,
                'error': 'Formato de número de factura inválido. Use: EST-PEXP-NUM'
            }), 400
        
        est, pexp, num_doc = parts
        
        # Buscar el DE
        de = DE.query.filter(
            DE.dEst == est,
            DE.dPunExp == pexp,
            DE.dNumDoc == num_doc
        ).first()
        
        if not de:
            return jsonify({
                'success': False,
                'error': 'Factura no encontrada'
            }), 404
        
        # Verificar si ya está cancelado/inutilizado
        if de.estado in ['CANCELADO', 'INUTILIZADO']:
            return jsonify({
                'success': False,
                'error': 'La factura ya está cancelada/inutilizada'
            }), 400
        
        # Actualizar estado a INUTILIZADO (para casos de error de número duplicado)
        de.estado = 'INUTILIZADO'
        de.estado_sifen = 'INUTILIZADO'
        de.desc_sifen = f'Documento inutilizado por error: {de.error_sifen}'
        de.fch_sifen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Factura inutilizada correctamente',
            'numero_factura': numero_factura,
            'estado': de.estado,
            'motivo': de.desc_sifen
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al cancelar factura {numero_factura}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500

@api_bp.route('/api/factura/regenerar/<path:numero_factura>', methods=['POST'])
def regenerar_factura(numero_factura):
    """
    Endpoint para regenerar una factura (crear nueva después de cancelar la anterior)
    """
    try:
        #data = request.get_json()
        
        # Parsear el número de factura original
        parts = numero_factura.split('-')
        if len(parts) != 3:
            return jsonify({
                'success': False,
                'error': 'Formato de número de factura inválido. Use: EST-PEXP-NUM'
            }), 400
        
        est, pexp, num_doc = parts
        
        # Buscar el DE original para obtener los datos
        de_original = DE.query.filter(
            DE.dEst == est,
            DE.dPunExp == pexp,
            DE.dNumDoc == num_doc
        ).first()
        
        if not de_original:
            return jsonify({
                'success': False,
                'error': 'Factura original no encontrada'
            }), 404
        
        # Verificar si el DE original tiene error de número duplicado
        if 'NUMDOC_APROBADO' not in (de_original.error_sifen or ''):
            return jsonify({
                'success': False,
                'error': 'Solo se pueden regenerar facturas con error de número duplicado'
            }), 400
        
        # ============================
        # GENERAR NUEVO NÚMERO DE FACTURA
        # ============================
        current_app.logger.info(f"Buscando última factura para {est}-{pexp}")

        ultimo = (
            DE.query
            .filter(DE.dEst == est, DE.dPunExp == pexp, DE.dNumDoc.isnot(None))
            .order_by(DE.dNumDoc.desc())
            .first()
        )

        if ultimo and ultimo.dNumDoc:
            try:
                import re
                match = re.search(r'(\d{7})$', ultimo.dNumDoc)
                if match:
                    ultimo_num = int(match.group(1))
                else:
                    ultimo_num = int(ultimo.dNumDoc)
            except Exception as e:
                current_app.logger.warning(f"No se pudo parsear último número: {e}, usando 250")
                ultimo_num = 250
        else:
            current_app.logger.info("ℹ No hay facturas previas, comenzando en 250")
            ultimo_num = 250

        nuevo_num = ultimo_num + 1

        if nuevo_num > 9999999:
            current_app.logger.warning("Número excede límite, reseteando a 1")
            nuevo_num = 1

        numero_generado = f"{nuevo_num:07d}"
        current_app.logger.info(f"Nuevo número generado: {numero_generado}")

        # ============================
        # CREAR NUEVO DE
        # ============================
        nuevo_de = DE()
        
        # Copiar campos del DE original
        campos_a_copiar = [
            'iTiDE', 'iTipEmi', 'dNumTim', 'dFeIniT', 'iTipTra', 'iTImp', 
            'cMoneOpe', 'dTiCam', 'dRucEm', 'dDVEmi', 'iTipCont', 'dNomEmi', 
            'dDirEmi', 'dNumCas', 'cDepEmi', 'dDesDepEmi', 'cCiuEmi', 'dDesCiuEmi', 
            'dTelEmi', 'dEmailE', 'iNatRec', 'iTiOpe', 'cPaisRec', 'iTiContRec', 
            'dRucRec', 'dDVRec', 'iTipIDRec', 'dDTipIDRec', 'dNumIDRec', 'dNomRec', 
            'dEmailRec', 'dDirRec', 'dNumCasRec', 'cDepRec', 'dDesDepRec', 
            'cCiuRec', 'dDesCiuRec', 'dSisFact', 'iIndPres', 'iCondOpe'
        ]
        
        for campo in campos_a_copiar:
            if hasattr(de_original, campo):
                setattr(nuevo_de, campo, getattr(de_original, campo))
        
        # Asignar nuevos valores
        nuevo_de.dFeEmiDE = datetime.now().strftime("%Y-%m-%d")
        nuevo_de.dEst = est
        nuevo_de.dPunExp = pexp
        nuevo_de.dNumDoc = numero_generado
        nuevo_de.dInfAdic = f"Regenerado por error en {numero_factura}. {de_original.dInfAdic}"
        nuevo_de.estado = 'Confirmado'
        nuevo_de.CDC = '0'
        nuevo_de.dSerieNum = ''
        nuevo_de.estado_sifen = '1'
        nuevo_de.desc_sifen = '2'
        nuevo_de.error_sifen = '3'
        nuevo_de.fch_sifen = '4'
        nuevo_de.estado_can = '5'
        nuevo_de.desc_can = '6'
        nuevo_de.error_can = '7'
        nuevo_de.fch_can = '8'
        nuevo_de.estado_inu = '9'
        nuevo_de.desc_inu = '10'
        nuevo_de.error_inu = '11'
        nuevo_de.fch_inu = '12'
        nuevo_de.dInfoFisc = ''
        nuevo_de.iMotEmi = ''

        db.session.add(nuevo_de)
        db.session.commit()
        db.session.refresh(nuevo_de)

        # ============================
        # COPIAR DATOS RELACIONADOS
        # ============================
        
        # Copiar actividades económicas
        actividades_originales = gActEco.query.filter_by(de_id=de_original.id).all()
        for act in actividades_originales:
            nueva_act = gActEco()
            nueva_act.de_id = nuevo_de.id
            nueva_act.cActEco = act.cActEco
            nueva_act.dDesActEco = act.dDesActEco
            db.session.add(nueva_act)

        # Copiar items
        items_originales = gCamItem.query.filter_by(de_id=de_original.id).all()
        for item in items_originales:
            nuevo_item = gCamItem()
            nuevo_item.de_id = nuevo_de.id
            for campo in ['dCodInt', 'dDesProSer', 'dCantProSer', 'dPUniProSer', 
                         'dDescItem', 'iAfecIVA', 'dPropIVA', 'dTasaIVA', 'cUniMed', 
                         'dParAranc', 'dNCM', 'dDncpG', 'dDncpE', 'dGtin', 'dGtinPq']:
                if hasattr(item, campo):
                    setattr(nuevo_item, campo, getattr(item, campo))
            db.session.add(nuevo_item)

        # Copiar formas de pago
        pagos_originales = gPaConEIni.query.filter_by(de_id=de_original.id).all()
        for pago in pagos_originales:
            nuevo_pago = gPaConEIni()
            nuevo_pago.de_id = nuevo_de.id
            nuevo_pago.iTiPago = pago.iTiPago
            nuevo_pago.dMonTiPag = pago.dMonTiPag
            nuevo_pago.cMoneTiPag = pago.cMoneTiPag
            nuevo_pago.dTiCamTiPag = pago.dTiCamTiPag
            db.session.add(nuevo_pago)

        db.session.commit()

        numero_completo_nuevo = f"{est}-{pexp}-{nuevo_de.dNumDoc}"

        return jsonify({
            'success': True,
            'message': 'Factura regenerada correctamente',
            'id_de_anterior': de_original.id,
            'id_de_nuevo': nuevo_de.id,
            'numero_factura_anterior': numero_factura,
            'numero_factura_nuevo': numero_completo_nuevo,
            'cdc': nuevo_de.CDC
        })

    except Exception as e:
        current_app.logger.error(f"Error al regenerar factura {numero_factura}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500