import requests
import json
from django.conf import settings
from django.core.files.base import ContentFile
from transaccion.models import Transaccion
from clientes.models import Cliente
from .models import FacturaElectronica, ConfiguracionFacturacion
from datetime import datetime
import base64

class ServicioFacturacion:
    def __init__(self):
        self.config = ConfiguracionFacturacion.objects.filter(activo=True).first()
        if not self.config:
            raise Exception("No hay configuración de facturación activa")
    
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
        
        # Descripción según tipo de transacción
        if transaccion.tipo == 'COMPRA':
            descripcion = f'Compra de {transaccion.moneda.codigo}'
        else:  # VENTA
            descripcion = f'Venta de {transaccion.moneda.codigo}'
        
        # Item principal: Conversión de divisas
        items.append({
            'dCodInt': 'CONVERSION',
            'dDesProSer': descripcion,
            'dCantProSer': '1',
            'dPUniProSer': str(transaccion.monto_pyg),
            'dDescItem': '0',
            'iAfecIVA': '1',  # 1=Gravado IVA
            'dPropIVA': '100',
            'dTasaIVA': '10',  # 10% IVA
            'cUniMed': '77',  # Servicio
            'dParAranc': '',
            'dNCM': '',
            'dDncpG': '',
            'dDncpE': '',
            'dGtin': '',
            'dGtinPq': ''
        })
        
        # Item para comisión si aplica
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
            # Verificar si ya existe factura
            if hasattr(transaccion, 'factura_electronica'):
                return {
                    'success': False, 
                    'error': 'Ya existe una factura para esta transacción'
                }
            
            # Datos básicos del DE
            numero_factura = str(transaccion.id).zfill(7)
            
            de_data = {
                'iTiDE': '1',  # 1=Factura electrónica
                'dFeEmiDE': datetime.now().strftime("%Y-%m-%d"),
                'dEst': '001',  # Establecimiento
                'dPunExp': '001',  # Punto de expedición
                'dNumDoc': numero_factura,
                'iTipEmi': '1',
                'dNumTim': self.config.numero_timbrado,
                'dFeIniT': self.config.fecha_inicio_timbrado.strftime("%Y-%m-%d"),
                'iTipTra': '2',  # 2=Venta
                'iTImp': '1',  # 1=Total
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
                'dInfAdic': f'Transacción #{transaccion.codigo_verificacion} - {transaccion.get_tipo_display()} - {transaccion.moneda.codigo}',
                'estado': 'Confirmado'  # Para procesamiento inmediato
            }
            
            # Agregar datos del cliente
            de_data.update(self._mapear_datos_cliente(transaccion.cliente))
            
            # Datos para las tablas relacionadas
            g_act_eco = [
                {
                    'cActEco': '64910',  # Actividades de servicios de cambio de moneda
                    'dDesActEco': 'Actividades de servicios de cambio de moneda'
                }
            ]
            
            g_cam_item = self._mapear_items_transaccion(transaccion)
            
            g_pa_con_e_ini = [
                {
                    'iTiPago': '1',  # 1=Contado
                    'dMonTiPag': str(transaccion.monto_pyg),
                    'cMoneTiPag': 'PYG',
                    'dTiCamTiPag': '1'
                }
            ]
            
            payload = {
                'de_data': de_data,
                'g_act_eco': g_act_eco,
                'g_cam_item': g_cam_item,
                'g_pa_con_e_ini': g_pa_con_e_ini
            }
            
            # Llamar al sql-proxy01
            response = requests.post(
                f"{self.config.sql_proxy_url}/api/facturar",
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Crear registro de factura
                factura = FacturaElectronica.objects.create(
                    transaccion=transaccion,
                    cdc=result.get('cdc', ''),
                    id_de=result.get('id_de'),
                    numero_factura=numero_factura,
                    estado_sifen='PROCESANDO'
                )
                
                return {
                    'success': True,
                    'factura_id': factura.id,
                    'cdc': result.get('cdc'),
                    'id_de': result.get('id_de'),
                    'message': 'Factura generada exitosamente'
                }
            else:
                error_msg = f"Error del servicio: {response.status_code} - {response.text}"
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Error al generar factura: {str(e)}"
            }
    
    def consultar_estado_factura(self, factura: FacturaElectronica):
        """Consulta el estado de una factura en SIFEN"""
        try:
            if not factura.cdc:
                return {'error': 'La factura no tiene CDC'}
            
            response = requests.get(
                f"{self.config.sql_proxy_url}/api/factura/estado/{factura.cdc}",
                timeout=30
            )
            
            factura.intentos_consulta += 1
            factura.fecha_consulta = datetime.now()
            
            if response.status_code == 200:
                data = response.json()
                
                # Actualizar estado
                estado_sifen = data.get('estado_sifen', '')
                if estado_sifen == 'Aprobado':
                    factura.estado_sifen = 'APROBADO'
                    factura.fecha_aprobacion = datetime.now()
                elif estado_sifen == 'Aprobado con observación':
                    factura.estado_sifen = 'APROBADO_OBS'
                    factura.fecha_aprobacion = datetime.now()
                elif estado_sifen == 'Rechazado':
                    factura.estado_sifen = 'RECHAZADO'
                
                factura.descripcion_estado = data.get('desc_sifen', '')
                factura.save()
                
                return {'success': True, 'estado': factura.estado_sifen}
            else:
                factura.error_message = f"Error en consulta: {response.text}"
                factura.save()
                return {'error': f"Error al consultar estado: {response.text}"}
                
        except Exception as e:
            error_msg = f"Error en consulta: {str(e)}"
            factura.error_message = error_msg
            factura.save()
            return {'error': error_msg}
    
    def descargar_factura(self, factura: FacturaElectronica, formato: str = 'pdf'):
        """Descarga y guarda la factura en el formato especificado"""
        try:
            if not factura.esta_aprobada:
                return {'error': 'La factura no está aprobada'}
            
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
                return {'success': True, 'archivo': nombre_archivo}
            else:
                return {'error': f"Error al descargar: {response.status_code}"}
                
        except Exception as e:
            return {'error': f"Error al descargar factura: {str(e)}"}