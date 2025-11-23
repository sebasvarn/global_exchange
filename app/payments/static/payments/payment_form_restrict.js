// payment_form_restrict.js - Versión mejorada
function mostrarCamposPorTipo(tipo) {
	var cuentaDiv = document.getElementById('campos-cuenta');
	var billeteraDiv = document.getElementById('campos-billetera');

	if (cuentaDiv) cuentaDiv.style.display = (tipo === 'cuenta_bancaria') ? '' : 'none';
	if (billeteraDiv) billeteraDiv.style.display = (tipo === 'billetera') ? '' : 'none';

	// Alternar required solo en los campos visibles
	var id_titular_cuenta = document.getElementById('id_titular_cuenta');
	var id_tipo_cuenta = document.getElementById('id_tipo_cuenta');
	var id_banco = document.getElementById('id_banco');
	var id_numero_cuenta = document.getElementById('id_numero_cuenta');
	var id_proveedor_billetera = document.getElementById('id_proveedor_billetera');
	var id_billetera_email_telefono = document.getElementById('id_billetera_email_telefono');

	if (id_titular_cuenta) id_titular_cuenta.required = (tipo === 'cuenta_bancaria');
	if (id_tipo_cuenta) id_tipo_cuenta.required = (tipo === 'cuenta_bancaria');
	if (id_banco) id_banco.required = (tipo === 'cuenta_bancaria');
	if (id_numero_cuenta) id_numero_cuenta.required = (tipo === 'cuenta_bancaria');
	if (id_proveedor_billetera) id_proveedor_billetera.required = (tipo === 'billetera');
	if (id_billetera_email_telefono) id_billetera_email_telefono.required = (tipo === 'billetera');
}

// Función para formatear número de tarjeta (grupos de 4)
function formatearNumeroTarjeta(valor) {
	var limpio = valor.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
	var grupos = limpio.match(/.{1,4}/g);
	return grupos ? grupos.join(' ') : '';
}

// Función para formatear fecha MM/AAAA
function formatearFechaVencimiento(valor) {
	var limpio = valor.replace(/\D/g, '');
	if (limpio.length >= 2) {
		return limpio.substring(0, 2) + (limpio.length > 2 ? '/' + limpio.substring(2, 6) : '');
	}
	return limpio;
}

// Función para detectar marca de tarjeta
function detectarMarcaTarjeta(numero) {
	var limpio = numero.replace(/\s/g, '');
	
	// Visa: empieza con 4
	if (/^4/.test(limpio)) return 'visa';
	
	// Mastercard: empieza con 51-55 o 2221-2720
	if (/^5[1-5]/.test(limpio) || /^2[2-7]/.test(limpio)) return 'mastercard';
	
	// Amex: empieza con 34 o 37
	if (/^3[47]/.test(limpio)) return 'amex';
	
	return '';
}

// Función para actualizar icono de marca de tarjeta
function actualizarIconoMarca(marca) {
	var iconoMarca = document.getElementById('icono-marca-tarjeta');
	if (!iconoMarca) return;
	
	iconoMarca.className = 'position-absolute';
	iconoMarca.style.right = '10px';
	iconoMarca.style.top = '50%';
	iconoMarca.style.transform = 'translateY(-50%)';
	iconoMarca.style.fontSize = '24px';
	
	if (marca === 'visa') {
		iconoMarca.innerHTML = '<i class="bi bi-credit-card-2-front text-primary"></i>';
		iconoMarca.title = 'Visa';
	} else if (marca === 'mastercard') {
		iconoMarca.innerHTML = '<i class="bi bi-credit-card-2-front text-danger"></i>';
		iconoMarca.title = 'Mastercard';
	} else if (marca === 'amex') {
		iconoMarca.innerHTML = '<i class="bi bi-credit-card-2-front text-info"></i>';
		iconoMarca.title = 'American Express';
	} else {
		iconoMarca.innerHTML = '';
	}
}

document.addEventListener('DOMContentLoaded', function() {
	
	
	// === CONFIGURAR SELECT DE TIPO DE CUENTA ===
	var tipoCuentaSelect = document.getElementById('id_tipo_cuenta');
	if (tipoCuentaSelect) {
		// Guardar el valor actual si existe
		var valorActual = tipoCuentaSelect.value;
		
		// Convertir a select si no lo es
		if (tipoCuentaSelect.tagName !== 'SELECT') {
			var nuevoSelect = document.createElement('select');
			nuevoSelect.id = 'id_tipo_cuenta';
			nuevoSelect.name = 'tipo_cuenta';
			nuevoSelect.className = 'form-control form-select';
			tipoCuentaSelect.parentNode.replaceChild(nuevoSelect, tipoCuentaSelect);
			tipoCuentaSelect = nuevoSelect;
		}
		
		// Limpiar opciones existentes y agregar solo las dos opciones
		tipoCuentaSelect.innerHTML = '<option value="">---------</option>' +
			'<option value="caja_ahorro">Caja de Ahorro</option>' +
			'<option value="cuenta_corriente">Cuenta Corriente</option>';
		
		// Restaurar el valor si existía
		if (valorActual) {
			tipoCuentaSelect.value = valorActual;
		}
	}
	
	// === CONFIGURAR SELECT DE BANCO ===
	var bancoSelect = document.getElementById('id_banco');
	if (bancoSelect) {
		var valorActual = bancoSelect.value;
		
		// Convertir a select si no lo es
		if (bancoSelect.tagName !== 'SELECT') {
			var nuevoSelect = document.createElement('select');
			nuevoSelect.id = 'id_banco';
			nuevoSelect.name = 'banco';
			nuevoSelect.className = 'form-control form-select';
			bancoSelect.parentNode.replaceChild(nuevoSelect, bancoSelect);
			bancoSelect = nuevoSelect;
		}
		
		var bancos = [
			'Banco Nacional de Fomento',
			'Banco Continental',
			'Ueno Bank',
			'Banco Itaú',
			'Banco Familiar',
			'Banco Atlas',
			'Zeta Bank',
			'Interfisa Banco',
			'Financiera Paraguayo Japonesa'
		];
		
		bancoSelect.innerHTML = '<option value="">---------</option>';
		bancos.forEach(function(banco) {
			var option = document.createElement('option');
			option.value = banco.toLowerCase().replace(/\s+/g, '_').replace(/á/g, 'a').replace(/ú/g, 'u');
			option.textContent = banco;
			bancoSelect.appendChild(option);
		});
		
		if (valorActual) {
			bancoSelect.value = valorActual;
		}
	}
	
	// === OCULTAR CUADRO DE ERROR ===
	var errorBox = document.getElementById('error-box');
	var formInputs = document.querySelectorAll('form input, form select');
	formInputs.forEach(function(input) {
		input.addEventListener('input', function() {
			setTimeout(function() {
				if (!errorBox) return;
				if (document.querySelectorAll('.is-invalid').length > 0) {
					errorBox.style.display = '';
				} else {
					errorBox.style.display = 'none';
				}
			}, 200);
		});
	});
	
	// === MANEJO DE TIPO DE PAGO ===
	var selectTipo = document.getElementById('id_payment_type');
	if (selectTipo) {
		selectTipo.addEventListener('change', function() {
			mostrarCamposPorTipo(this.value);
		});
		mostrarCamposPorTipo(selectTipo.value);
	} else {
		// Si no hay select (estamos editando), buscar el input hidden
		var hiddenTipo = document.querySelector('input[name="payment_type"]');
		if (hiddenTipo) {
			mostrarCamposPorTipo(hiddenTipo.value);
		}
	}
	
	// === VALIDACIÓN DE FORMULARIO ===
	var form = document.querySelector('form');
	if (form) {
		form.addEventListener('submit', function(e) {
			var tipoActual = selectTipo ? selectTipo.value : 
				(document.querySelector('input[name="payment_type"]') ? 
				document.querySelector('input[name="payment_type"]').value : '');
			
		});
	}
});