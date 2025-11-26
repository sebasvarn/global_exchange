import requests
import json
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from transaccion.models import Transaccion
from clientes.models import Cliente
from .models import FacturaElectronica, ConfiguracionFacturacion
from datetime import datetime

logger = logging.getLogger(__name__)

class ServicioFacturacion:
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
            
            if hasattr(transaccion, 'factura_electronica'):
                return {
                    'success': False, 
                    'error': 'Ya existe una factura para esta transacción'
                }
            
            # CABECERA DEL DE — **SIN dNumDoc** (lo genera SQL-PROXY)
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
                'dInfAdic': f'Transacción #{transaccion.codigo_verificacion} - '
                            f'{transaccion.get_tipo_display()} - {transaccion.moneda.codigo}',
                'estado': 'Confirmado'
            }
            
            de_data.update(self._mapear_datos_cliente(transaccion.cliente))
            
            g_act_eco = [
                {'cActEco': '64910', 'dDesActEco': 'Actividades de servicios de cambio de moneda'}
            ]
            
            g_cam_item = self._mapear_items_transaccion(transaccion)
            
            g_pa_con_e_ini = [{
                'iTiPago': '1',
                'dMonTiPag': str(transaccion.monto_pyg),
                'cMoneTiPag': 'PYG',
                'dTiCamTiPag': '1'
            }]
            
            payload = {
                'de_data': de_data,
                'g_act_eco': g_act_eco,
                'g_cam_item': g_cam_item,
                'g_pa_con_e_ini': g_pa_con_e_ini
            }
            
            url = f"{self.config.sql_proxy_url}/api/facturar"
            logger.info(f"Enviando solicitud a: {url}")
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': response.text,
                    'status_code': response.status_code
                }
            
            result = response.json()
            
            factura = FacturaElectronica.objects.create(
                transaccion=transaccion,
                cdc=result.get('cdc', ''),
                id_de=result.get('id_de'),
                numero_factura=result.get('numero_factura', ''),
                estado_sifen='PROCESANDO'
            )
            
            return {
                'success': True,
                'factura_id': factura.id,
                'cdc': factura.cdc,
                'id_de': factura.id_de,
                'numero_factura': factura.numero_factura,
                'message': 'Factura generada exitosamente'
            }
            
        except Exception as e:
            logger.error(f"Error al generar factura: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Error al generar factura: {str(e)}"
            }
    
    def consultar_estado_factura(self, factura: FacturaElectronica):
        """Consulta el estado de una factura en SIFEN"""
        try:
            if not factura.cdc:
                return {'error': 'La factura no tiene CDC'}
            
            logger.info(f"Consultando estado para factura CDC: {factura.cdc}")
            
            response = requests.get(
                f"{self.config.sql_proxy_url}/api/factura/estado/{factura.cdc}",
                timeout=30
            )
            
            factura.intentos_consulta += 1
            factura.fecha_consulta = datetime.now()
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Estado consultado: {data}")
                
                estado_sifen = data.get('estado_sifen', '')
                if estado_sifen == 'Aprobado':
                    factura.estado_sifen = 'APROBADO'
                    factura.fecha_aprobacion = datetime.now()
                
                factura.descripcion_estado = data.get('desc_sifen', '')
                factura.save()
                
                return {'success': True, 'estado': factura.estado_sifen}
            else:
                error_msg = f"Error en consulta: {response.text}"
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
    
    def descargar_factura(self, factura: FacturaElectronica, formato: str = 'pdf'):
        """Descarga y guarda la factura en el formato especificado"""
        try:
            if not factura.esta_aprobada:
                return {'error': 'La factura no está aprobada'}
            
            logger.info(f"Descargando factura {factura.cdc} en formato {formato}")
            
            response = requests.get(
                f"{self.config.sql_proxy_url}/api/factura/descargar/{factura.cdc}?formato={formato}",
                timeout=30
            )
            
            if response.status_code == 200:
                nombre_archivo = f"factura_{factura.cdc}_{formato.upper()}"
                
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
                error_msg = f"Error al descargar: {response.status_code}"
                logger.error(error_msg)
                return {'error': error_msg}
                
        except Exception as e:
            error_msg = f"Error al descargar factura: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}
