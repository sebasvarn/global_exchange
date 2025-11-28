import requests
import json
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from transaccion.models import Transaccion
from clientes.models import Cliente
from .models import FacturaElectronica, ConfiguracionFacturacion
from datetime import datetime

logger = logging.getLogger("facturacion")

class ServicioFacturacion:
    """
    Servicio para la gestión de facturación electrónica.

    Esta clase centraliza la lógica para:
    - Generar facturas electrónicas a partir de transacciones.
    - Consultar el estado de las facturas en el sistema externo (SIFEN/SQL Proxy).
    - Descargar archivos PDF/XML de facturas aprobadas.
    - Cancelar/inutilizar facturas electrónicas.
    - Regenerar facturas en caso de reemplazo.
    - Mapear y transformar datos de clientes, transacciones y facturas al formato requerido por el sistema fiscal.

    Utiliza la configuración activa de facturación y se comunica con servicios externos definidos en dicha configuración.
    Maneja errores y logs para trazabilidad de los procesos de facturación.
    """
    def __init__(self):
        self.config = ConfiguracionFacturacion.objects.filter(activo=True).first()
        if not self.config:
            logger.error("No hay configuración de facturación activa")
            raise Exception("No hay configuración de facturación activa")
        logger.info(f"Configuración cargada: {self.config.nombre_emisor}")
    
    def _mapear_datos_cliente(self, cliente: Cliente):
        """Mapea los datos del cliente al formato requerido por el DE"""
        return {
            'iNatRec': '1',  # 1=Persona física
            'iTiOpe': '1',   # 1=Venta de bienes
            'cPaisRec': 'PRY',
            'iTiContRec': '2',  # 2=Consumidor final
            'dRucRec': cliente.ruc or '',
            'dDVRec': cliente.ruc_dv or '0',
            'iTipIDRec': '1' if cliente.ruc else '2',  # 1=RUC, 2=Cédula
            'dDTipIDRec': 'RUC' if cliente.ruc else 'Cédula',
            'dNumIDRec': cliente.ruc or cliente.cedula or '',
            'dNomRec': cliente.razon_social or f"{cliente.nombre} {cliente.apellido}",
            'dEmailRec': cliente.email,
            'dDirRec': cliente.direccion or '',
            'cDepRec': getattr(cliente.departamento, 'codigo', '1') if cliente.departamento else '1',
            'dDesDepRec': getattr(cliente.departamento, 'nombre', 'CAPITAL') if cliente.departamento else 'CAPITAL',
            'cCiuRec': getattr(cliente.ciudad, 'codigo', '1') if cliente.ciudad else '1',
            'dDesCiuRec': getattr(cliente.ciudad, 'nombre', 'ASUNCION (DISTRITO)') if cliente.ciudad else 'ASUNCION (DISTRITO)'
        }
    
    def _mapear_items_transaccion(self, transaccion: Transaccion):
        """Mapea los items de la transacción para el DE"""
        items = []
        
        if transaccion.tipo == 'COMPRA':
            descripcion = f'Compra de {transaccion.moneda.codigo}'
        else:
            descripcion = f'Venta de {transaccion.moneda.codigo}'
        
        items.append({
            'dCodInt': 'CONVERSION',
            'dDesProSer': descripcion,
            'dCantProSer': '1',
            'dPUniProSer': str(transaccion.monto_pyg),
            'dDescItem': '0',
            'iAfecIVA': '1',
            'dPropIVA': '100',
            'dTasaIVA': '10',
            'cUniMed': '77',
            'dParAranc': '',
            'dNCM': '',
            'dDncpG': '',
            'dDncpE': '',
            'dGtin': '',
            'dGtinPq': ''
        })
        
        if transaccion.comision and transaccion.comision > 0:
            items.append({
                'dCodInt': 'COMISION',
                'dDesProSer': 'Comisión por servicio de cambio',
                'dCantProSer': '1',
                'dPUniProSer': str(transaccion.comision),
                'dDescItem': '0',
                'iAfecIVA': '1',
                'dPropIVA': '100',
                'dTasaIVA': '10',
                'cUniMed': '77',
                'dParAranc': '',
                'dNCM': '',
                'dDncpG': '',
                'dDncpE': '',
                'dGtin': '',
                'dGtinPq': ''
            })
        
        return items
    
    def generar_factura(self, transaccion: Transaccion):
        """Genera una factura electrónica para una transacción"""
        try:
            logger.info(f"Iniciando generación de factura para transacción {transaccion.id}")

            # Evitar duplicados
            if hasattr(transaccion, 'factura_electronica'):
                return {
                    'success': False,
                    'error': 'Ya existe una factura para esta transacción'
                }

            # =============================
            # MAPEAR DATOS FISCALES DESDE LA TRANSACCIÓN
            # =============================
            datos_fiscales = getattr(transaccion, "datos_fiscales", {})

            # estos vienen desde el modal del frontend
            nombre = datos_fiscales.get("nombre")
            ruc = datos_fiscales.get("ruc")
            dv = datos_fiscales.get("dv")
            cedula = datos_fiscales.get("cedula")
            email = datos_fiscales.get("email")
            direccion = datos_fiscales.get("direccion")

            # =============================
            # ARMAR CABECERA DE DOCUMENTO
            # =============================
            de_data = {
                'iTiDE': '1',
                'dFeEmiDE': datetime.now().strftime("%Y-%m-%d"),
                'dEst': '001',
                'dPunExp': '003',
                'iTipEmi': '1',
                'dNumTim': self.config.numero_timbrado,
                'dFeIniT': self.config.fecha_inicio_timbrado.strftime("%Y-%m-%d"),
                'iTipTra': '2',
                'iTImp': '1',
                'cMoneOpe': 'PYG',
                'dTiCam': '1',
                'dInfoFisc': '',
                'dRucEm': self.config.ruc_emisor,
                'dDVEmi': self.config.dv_emisor,
                'iTipCont': '1',
                'dNomEmi': self.config.nombre_emisor,
                'dDirEmi': self.config.direccion_emisor,
                'dNumCas': self.config.numero_casa,
                'cDepEmi': self.config.departamento_emisor,
                'dDesDepEmi': self.config.descripcion_departamento,
                'cCiuEmi': self.config.ciudad_emisor,
                'dDesCiuEmi': self.config.descripcion_ciudad,
                'dTelEmi': self.config.telefono_emisor,
                'dEmailE': self.config.email_emisor,
                'dSisFact': '1',
                'iIndPres': '1',
                'iCondOpe': '1',
                'iMotEmi': '',  
                'dInfAdic': f'Transacción #{transaccion.codigo_verificacion}',
                'estado': 'Confirmado'
            }

            # =============================
            # MAPEAR DATOS DEL RECEPTOR DESDE FRONTEND
            # =============================
            de_data.update({
                'iNatRec': '1',
                'iTiOpe': '1',
                'cPaisRec': 'PRY',
                'iTiContRec': '2',
                'dRucRec': ruc or '',
                'dDVRec': dv or '0',
                'iTipIDRec': '1' if ruc else '2',
                'dDTipIDRec': 'RUC' if ruc else 'Cédula',
                'dNumIDRec': ruc or cedula or '',
                'dNomRec': nombre,
                'dEmailRec': email or '',
                'dDirRec': direccion or '',
                'cDepRec': '1',
                'dDesDepRec': 'CAPITAL',
                'cCiuRec': '1',
                'dDesCiuRec': 'ASUNCION (DISTRITO)'
            })

            # =============================
            # ITEMS DE LA TRANSACCIÓN
            # =============================
            g_cam_item = self._mapear_items_transaccion(transaccion)

            # =============================
            # FORMAS DE PAGO
            # =============================
            g_pa_con_e_ini = [{
                'iTiPago': '1',
                'dMonTiPag': str(transaccion.monto_pyg),
                'cMoneTiPag': 'PYG',
                'dTiCamTiPag': '1'
            }]

            payload = {
            'de_data': de_data,
            'g_act_eco': [
                {'cActEco': '62010', 'dDesActEco': 'Actividades de programación informática'},
                {'cActEco': '74909', 'dDesActEco': 'Otras actividades profesionales, científicas y técnicas n.c.p.'}
            ],
            'g_cam_item': g_cam_item,
            'g_pa_con_e_ini': g_pa_con_e_ini
        }

            url = f"{self.config.sql_proxy_url}/api/facturar"
            logger.info(f"Enviando solicitud a SQL-PROXY: {url}")

            response = requests.post(url, json=payload, timeout=30)

            if response.status_code != 200:
                return {
                    'success': False,
                    'error': response.text,
                    'status_code': response.status_code
                }

            result = response.json()

            # =============================
            # CREAR FACTURA REAL DESPUÉS DEL SIFEN
            # =============================
            numero_factura = result.get('numero_factura')
        
            # VALIDACIÓN CRÍTICA: Verificar que el número de factura no sea null
            if not numero_factura:
                logger.error("ERROR: La API retornó numero_factura = NULL")
                return {
                    'success': False,
                    'error': 'El servicio de facturación no generó un número de factura válido'
                }

            factura = FacturaElectronica.objects.create(
                transaccion=transaccion,
                cdc=result.get('cdc'),
                id_de=result.get('id_de'),
                numero_factura=numero_factura,  # Esto ya no será null
                nombre_receptor=nombre,
                ruc_receptor=ruc,
                dv_receptor=dv,
                cedula_receptor=cedula,
                email_receptor=email,
                direccion_receptor=direccion,
                estado_sifen='PROCESANDO'
            )

            logger.info(f"Factura creada exitosamente: {factura.numero_factura}")

            return {
                'success': True,
                'cdc': factura.cdc,
                'id_de': factura.id_de,
                'numero_factura': factura.numero_factura
            }

        except Exception as e:
            logger.error(f"Error al generar factura: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Error al generar factura: {str(e)}"
            }


    def obtener_url_kude(self, transaccion_id):
        """Obtiene la URL del KUDE para una transacción"""
        try:
            url = f"{self.config.sql_proxy_url}/api/transaccion/{transaccion_id}/kude"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return {
                        'success': True,
                        'url_pdf': f"{self.config.sql_proxy_url}{result['url_pdf']}",
                        'cdc': result.get('cdc'),
                        'numero_factura': result.get('numero_factura'),
                        'estado': result.get('estado')
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('error', 'Error desconocido')
                    }
            else:
                return {
                    'success': False,
                    'error': f'Error HTTP {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error al obtener KUDE para transacción {transaccion_id}: {str(e)}")
            return {
                'success': False,
                'error': f'Error de conexión: {str(e)}'
            }
    

    def consultar_estado_factura(self, factura: FacturaElectronica):
        """Consulta el estado de una factura por número de factura y actualiza CDC y estado"""
        try:
            logger.info(f"Consultando estado para factura: {factura.numero_factura}")
            
            response = requests.get(
                f"{self.config.sql_proxy_url}/api/factura/estado/{factura.numero_factura}",
                timeout=30
            )
            
            factura.intentos_consulta += 1
            factura.fecha_consulta = datetime.now()
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Respuesta del SQL Proxy: {data}")
                
                if data.get('success'):
                    cdc_actual = data.get('cdc', '')
                    estado_sifen_actual = data.get('estado_sifen', '')
                    desc_sifen_actual = data.get('desc_sifen', '')
                    error_sifen_actual = data.get('error_sifen', '')
                    estado_interno_actual = data.get('estado', '')
                    
                    # Mapear estados del SQL Proxy a nuestros estados
                    estado_mapeado = self._mapear_estado_sifen(estado_sifen_actual, error_sifen_actual)
                    
                    # Actualizar todos los campos
                    cambios = []
                    
                    if cdc_actual and cdc_actual != factura.cdc:
                        factura.cdc = cdc_actual
                        cambios.append(f"CDC: {cdc_actual}")
                    
                    if estado_mapeado and estado_mapeado != factura.estado_sifen:
                        factura.estado_sifen = estado_mapeado
                        cambios.append(f"Estado: {estado_mapeado}")
                    
                    if desc_sifen_actual and desc_sifen_actual != factura.desc_sifen:
                        factura.desc_sifen = desc_sifen_actual
                        cambios.append(f"Desc: {desc_sifen_actual}")
                    
                    if error_sifen_actual and error_sifen_actual != factura.error_sifen:
                        factura.error_sifen = error_sifen_actual
                        cambios.append(f"Error: {error_sifen_actual}")
                    
                    # Si está aprobada, actualizar fecha
                    if estado_mapeado == 'APROBADO' and not factura.fecha_aprobacion:
                        factura.fecha_aprobacion = datetime.now()
                        cambios.append("Fecha aprobación actualizada")
                    
                    factura.save()
                    
                    if cambios:
                        logger.info(f"Factura {factura.numero_factura} actualizada: {', '.join(cambios)}")
                    else:
                        logger.info(f"Factura {factura.numero_factura} sin cambios")
                    
                    return {
                        'success': True, 
                        'estado': factura.estado_sifen,
                        'cdc': factura.cdc,
                        'descripcion': factura.descripcion_estado,
                        'error': factura.error_sifen,
                        'numero_factura': factura.numero_factura
                    }
                else:
                    error_msg = data.get('error', 'Error desconocido')
                    factura.error_message = error_msg
                    factura.save()
                    logger.error(f"Error del SQL Proxy: {error_msg}")
                    return {'error': error_msg}
            else:
                error_msg = f"Error HTTP {response.status_code}: {response.text}"
                factura.error_message = error_msg
                factura.save()
                logger.error(error_msg)
                return {'error': error_msg}
                
        except Exception as e:
            error_msg = f"Error en consulta: {str(e)}"
            factura.error_message = error_msg
            factura.save()
            logger.error(error_msg)
            return {'error': error_msg}

    def _mapear_estado_sifen(self, estado_sql_proxy: str, error_sql_proxy: str) -> str:
        """Mapea los estados del SQL Proxy a nuestros estados"""
        if not estado_sql_proxy or estado_sql_proxy == '1':
            return 'PROCESANDO'
        elif estado_sql_proxy == 'Aprobado' or estado_sql_proxy == 'APROBADO':
            return 'APROBADO'
        elif error_sql_proxy and 'NUMDOC_APROBADO' in error_sql_proxy:
            return 'RECHAZADO'
        elif error_sql_proxy and error_sql_proxy not in ['3', '']:
            return 'ERROR'
        else:
            return 'PROCESANDO'
        

    def descargar_factura(self, factura: FacturaElectronica, formato: str = 'pdf'):
        """Descarga la factura por CDC (no por número de factura)"""
        try:
            if not factura.esta_aprobada:
                return {'error': 'La factura no está aprobada'}
            
            # Verificar que tenemos CDC
            if not factura.cdc or factura.cdc == '0':
                return {'error': 'La factura no tiene CDC asignado'}
            
            logger.info(f"Descargando factura CDC: {factura.cdc} en formato {formato}")
            
            # Usar CDC en lugar de numero_factura
            response = requests.get(
                f"{self.config.sql_proxy_url}/api/factura/descargar/{factura.cdc}?formato={formato}",
                timeout=30
            )
            
            if response.status_code == 200:
                nombre_archivo = f"factura_{factura.numero_factura.replace('-', '_')}_{formato.upper()}"
                
                # Guardar el archivo descargado
                if formato.lower() == 'pdf':
                    factura.pdf_file.save(
                        f"{nombre_archivo}.pdf", 
                        ContentFile(response.content)
                    )
                elif formato.lower() == 'xml':
                    factura.xml_file.save(
                        f"{nombre_archivo}.xml", 
                        ContentFile(response.content)
                    )
                
                factura.save()
                logger.info(f"Factura descargada: {nombre_archivo}")
                return {'success': True, 'archivo': nombre_archivo}
            else:
                error_msg = f"Error al descargar: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {'error': error_msg}
                
        except Exception as e:
            error_msg = f"Error al descargar factura: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}
        

    def _mapear_datos_receptor(self, factura: FacturaElectronica):
        """Mapea datos fiscales guardados en la factura (NO desde Cliente)."""
        return {
            'iNatRec': '1',
            'iTiOpe': '1',
            'cPaisRec': 'PRY',
            'iTiContRec': '2',
            'dRucRec': factura.ruc_receptor or '',
            'dDVRec': factura.dv_receptor or '0',
            'iTipIDRec': '1' if factura.ruc_receptor else '2',
            'dDTipIDRec': 'RUC' if factura.ruc_receptor else 'Cédula',
            'dNumIDRec': factura.ruc_receptor or factura.cedula_receptor or '',
            'dNomRec': factura.nombre_receptor,
            'dEmailRec': factura.email_receptor or '',
            'dDirRec': factura.direccion_receptor or '',
            'cDepRec': '1',
            'dDesDepRec': 'CAPITAL',
            'cCiuRec': '1',
            'dDesCiuRec': 'ASUNCION (DISTRITO)'
        }


    def cancelar_factura(self, factura: FacturaElectronica):
        """Cancela/inutiliza una factura en el SQL Proxy"""
        try:
            logger.info(f"Cancelando factura: {factura.numero_factura}")
            
            response = requests.post(
                f"{self.config.sql_proxy_url}/api/factura/cancelar/{factura.numero_factura}",
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    # Actualizar la factura en Django
                    factura.estado_sifen = 'INUTILIZADO'
                    factura.descripcion_estado = result.get('motivo', 'Documento inutilizado')
                    factura.save()
                    
                    logger.info(f"Factura {factura.numero_factura} cancelada/inutilizada")
                    return {'success': True, 'message': result.get('message')}
                else:
                    return {'error': result.get('error', 'Error desconocido')}
            else:
                return {'error': f'Error HTTP {response.status_code}: {response.text}'}
                
        except Exception as e:
            logger.error(f"Error al cancelar factura: {str(e)}")
            return {'error': str(e)}


    def regenerar_factura(self, factura: FacturaElectronica, transaccion: Transaccion):
        """Regenera una factura después de cancelar la anterior"""
        try:
            logger.info(f"Regenerando factura para transacción {transaccion.id}")
            
            response = requests.post(
                f"{self.config.sql_proxy_url}/api/factura/regenerar/{factura.numero_factura}",
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    # Crear nueva factura en Django
                    nueva_factura = FacturaElectronica.objects.create(
                        transaccion=transaccion,
                        cdc=result.get('cdc', ''),
                        id_de=result.get('id_de_nuevo'),
                        numero_factura=result.get('numero_factura_nuevo'),
                        nombre_receptor=factura.nombre_receptor,
                        ruc_receptor=factura.ruc_receptor,
                        dv_receptor=factura.dv_receptor,
                        cedula_receptor=factura.cedula_receptor,
                        email_receptor=factura.email_receptor,
                        direccion_receptor=factura.direccion_receptor,
                        estado_sifen='PROCESANDO'
                    )
                    
                    # Marcar la factura anterior como reemplazada
                    factura.estado_sifen = 'REEMPLAZADA'
                    factura.descripcion_estado = f'Reemplazada por {nueva_factura.numero_factura}'
                    factura.save()
                    
                    logger.info(f"Factura regenerada: {nueva_factura.numero_factura}")
                    return {
                        'success': True, 
                        'nueva_factura': {
                            'id': nueva_factura.id,
                            'numero_factura': nueva_factura.numero_factura,
                            'cdc': nueva_factura.cdc
                        }
                    }
                else:
                    return {'error': result.get('error', 'Error desconocido')}
            else:
                return {'error': f'Error HTTP {response.status_code}: {response.text}'}
                
        except Exception as e:
            logger.error(f"Error al regenerar factura: {str(e)}")
            return {'error': str(e)}
        