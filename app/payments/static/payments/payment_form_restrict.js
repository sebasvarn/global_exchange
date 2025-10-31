// payment_form_restrict.js - Versión mejorada
function mostrarCamposPorTipo(tipo) {
	var cuentaDiv = document.getElementById('campos-cuenta');
	var billeteraDiv = document.getElementById('campos-billetera');
	var tarjetaDiv = document.getElementById('campos-tarjeta');
	var chequeDiv = document.getElementById('campos-cheque');

	if (cuentaDiv) cuentaDiv.style.display = (tipo === 'cuenta_bancaria') ? '' : 'none';
	if (billeteraDiv) billeteraDiv.style.display = (tipo === 'billetera') ? '' : 'none';
	if (tarjetaDiv) tarjetaDiv.style.display = (tipo === 'tarjeta') ? '' : 'none';
	if (chequeDiv) chequeDiv.style.display = (tipo === 'cheque') ? '' : 'none';

	// Alternar required solo en los campos visibles
	var id_titular_cuenta = document.getElementById('id_titular_cuenta');
	var id_tipo_cuenta = document.getElementById('id_tipo_cuenta');
	var id_banco = document.getElementById('id_banco');
	var id_numero_cuenta = document.getElementById('id_numero_cuenta');
	var id_proveedor_billetera = document.getElementById('id_proveedor_billetera');
	var id_billetera_email_telefono = document.getElementById('id_billetera_email_telefono');
	var id_tarjeta_numero = document.getElementById('id_tarjeta_numero');
	var id_tarjeta_cvv = document.getElementById('id_tarjeta_cvv');
	var id_cheque_numero = document.getElementById('id_cheque_numero');

	if (id_titular_cuenta) id_titular_cuenta.required = (tipo === 'cuenta_bancaria');
	if (id_tipo_cuenta) id_tipo_cuenta.required = (tipo === 'cuenta_bancaria');
	if (id_banco) id_banco.required = (tipo === 'cuenta_bancaria');
	if (id_numero_cuenta) id_numero_cuenta.required = (tipo === 'cuenta_bancaria');
	if (id_proveedor_billetera) id_proveedor_billetera.required = (tipo === 'billetera');
	if (id_billetera_email_telefono) id_billetera_email_telefono.required = (tipo === 'billetera');
	if (id_tarjeta_numero) id_tarjeta_numero.required = (tipo === 'tarjeta');
	if (id_tarjeta_cvv) id_tarjeta_cvv.required = (tipo === 'tarjeta');
	if (id_cheque_numero) id_cheque_numero.required = (tipo === 'cheque');
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
	// === MANEJO DE NÚMERO DE TARJETA ===
	var tarjetaNumero = document.getElementById('id_tarjeta_numero');
	if (tarjetaNumero) {
		// Establecer atributos
		tarjetaNumero.setAttribute('maxlength', '19'); // 16 dígitos + 3 espacios
		tarjetaNumero.setAttribute('placeholder', '1234 5678 9012 3456');
		tarjetaNumero.setAttribute('autocomplete', 'cc-number');
		tarjetaNumero.style.paddingRight = '40px'; // Espacio para el icono
		
		// Agregar contenedor para el icono de marca
		var container = tarjetaNumero.parentElement;
		container.style.position = 'relative';
		var iconoDiv = document.createElement('div');
		iconoDiv.id = 'icono-marca-tarjeta';
		container.appendChild(iconoDiv);
		
		tarjetaNumero.addEventListener('input', function(e) {
			var cursorPos = this.selectionStart;
			var valorAnterior = this.value;
			
			// Solo números y formatear
			var limpio = this.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
			limpio = limpio.slice(0, 16); // Máximo 16 dígitos
			
			var formateado = formatearNumeroTarjeta(limpio);
			this.value = formateado;
			
			// Ajustar cursor
			var espaciosAntes = (valorAnterior.substring(0, cursorPos).match(/\s/g) || []).length;
			var espaciosDespues = (formateado.substring(0, cursorPos).match(/\s/g) || []).length;
			if (espaciosDespues > espaciosAntes) {
				cursorPos++;
			}
			this.setSelectionRange(cursorPos, cursorPos);
			
			// Detectar marca de tarjeta
			var marcaSelect = document.getElementById('id_tarjeta_marca');
			if (marcaSelect && limpio.length >= 2) {
				var marca = detectarMarcaTarjeta(limpio);
				if (marca) {
					marcaSelect.value = marca;
					actualizarIconoMarca(marca);
				} else {
					actualizarIconoMarca('');
				}
			}
		});
		
		tarjetaNumero.addEventListener('paste', function(e) {
			e.preventDefault();
			var texto = (e.clipboardData || window.clipboardData).getData('text');
			var limpio = texto.replace(/\s+/g, '').replace(/[^0-9]/gi, '').slice(0, 16);
			this.value = formatearNumeroTarjeta(limpio);
			
			// Detectar marca después del paste
			var marcaSelect = document.getElementById('id_tarjeta_marca');
			if (marcaSelect && limpio.length >= 2) {
				var marca = detectarMarcaTarjeta(limpio);
				if (marca) {
					marcaSelect.value = marca;
					actualizarIconoMarca(marca);
				}
			}
		});
		
		// Si ya hay un valor (edición), formatearlo
		if (tarjetaNumero.value) {
			var limpio = tarjetaNumero.value.replace(/\s+/g, '');
			tarjetaNumero.value = formatearNumeroTarjeta(limpio);
			
			var marcaSelect = document.getElementById('id_tarjeta_marca');
			if (marcaSelect && marcaSelect.value) {
				actualizarIconoMarca(marcaSelect.value);
			}
		}
	}
	
	// === MANEJO DE FECHA DE VENCIMIENTO ===
	var tarjetaVencimiento = document.getElementById('id_tarjeta_vencimiento');
	if (tarjetaVencimiento) {
		tarjetaVencimiento.setAttribute('maxlength', '7');
		tarjetaVencimiento.setAttribute('placeholder', 'MM/AAAA');
		tarjetaVencimiento.setAttribute('autocomplete', 'cc-exp');
		
		tarjetaVencimiento.addEventListener('input', function(e) {
			var formateado = formatearFechaVencimiento(this.value);
			this.value = formateado;
			
			// Validar mes
			if (formateado.length >= 2) {
				var mes = parseInt(formateado.substring(0, 2));
				if (mes > 12) {
					this.value = '12' + (formateado.length > 2 ? formateado.substring(2) : '');
				} else if (mes === 0) {
					this.value = '01' + (formateado.length > 2 ? formateado.substring(2) : '');
				}
			}
		});
		
		tarjetaVencimiento.addEventListener('paste', function(e) {
			e.preventDefault();
			var texto = (e.clipboardData || window.clipboardData).getData('text');
			this.value = formatearFechaVencimiento(texto);
		});
	}
	
	// === MANEJO DE CVV/CVC ===
	var tarjetaCVV = document.getElementById('id_tarjeta_cvv');
	if (tarjetaCVV) {
		tarjetaCVV.setAttribute('maxlength', '4');
		tarjetaCVV.setAttribute('placeholder', '123');
		tarjetaCVV.setAttribute('autocomplete', 'cc-csc');
		
		tarjetaCVV.addEventListener('input', function(e) {
			// Solo números, máximo 4 (Amex tiene 4, otros 3)
			this.value = this.value.replace(/[^0-9]/g, '').slice(0, 4);
		});
	}
	
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
	
	// === CONFIGURAR SELECT DE BANCO PARA CHEQUES ===
	var chequeBancoSelect = document.getElementById('id_cheque_banco');
	if (chequeBancoSelect) {
		var valorActual = chequeBancoSelect.value;
		
		// Convertir a select si no lo es
		if (chequeBancoSelect.tagName !== 'SELECT') {
			var nuevoSelect = document.createElement('select');
			nuevoSelect.id = 'id_cheque_banco';
			nuevoSelect.name = 'cheque_banco';
			nuevoSelect.className = 'form-control form-select';
			chequeBancoSelect.parentNode.replaceChild(nuevoSelect, chequeBancoSelect);
			chequeBancoSelect = nuevoSelect;
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
		
		chequeBancoSelect.innerHTML = '<option value="">---------</option>';
		bancos.forEach(function(banco) {
			var option = document.createElement('option');
			option.value = banco.toLowerCase().replace(/\s+/g, '_').replace(/á/g, 'a').replace(/ú/g, 'u');
			option.textContent = banco;
			chequeBancoSelect.appendChild(option);
		});
		
		if (valorActual) {
			chequeBancoSelect.value = valorActual;
		}
	}
	
	// === CONFIGURAR SELECT DE MARCA DE TARJETA ===
	var marcaTarjetaSelect = document.getElementById('id_tarjeta_marca');
	if (marcaTarjetaSelect) {
		var valorActual = marcaTarjetaSelect.value;
		
		// Convertir a select si no lo es
		if (marcaTarjetaSelect.tagName !== 'SELECT') {
			var nuevoSelect = document.createElement('select');
			nuevoSelect.id = 'id_tarjeta_marca';
			nuevoSelect.name = 'tarjeta_marca';
			nuevoSelect.className = 'form-control form-select';
			marcaTarjetaSelect.parentNode.replaceChild(nuevoSelect, marcaTarjetaSelect);
			marcaTarjetaSelect = nuevoSelect;
		}
		
		marcaTarjetaSelect.innerHTML = '<option value="">---------</option>' +
			'<option value="visa">Visa</option>' +
			'<option value="mastercard">Mastercard</option>' +
			'<option value="amex">American Express</option>';
		
		if (valorActual) {
			marcaTarjetaSelect.value = valorActual;
			actualizarIconoMarca(valorActual);
		}
		
		// Actualizar icono cuando cambia manualmente
		marcaTarjetaSelect.addEventListener('change', function() {
			actualizarIconoMarca(this.value);
		});
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
			
			// Validaciones específicas para tarjeta
			if (tipoActual === 'tarjeta' && tarjetaNumero) {
				var numLimpio = tarjetaNumero.value.replace(/\s/g, '');
				if (numLimpio.length !== 16) {
					e.preventDefault();
					alert('El número de tarjeta debe tener exactamente 16 dígitos');
					tarjetaNumero.focus();
					return false;
				}
			}
			
			// Validación de fecha de vencimiento MM/AAAA
			if (tipoActual === 'tarjeta' && tarjetaVencimiento) {
				if (tarjetaVencimiento.value.length !== 7) {
					e.preventDefault();
					alert('La fecha de vencimiento debe tener el formato MM/AAAA');
					tarjetaVencimiento.focus();
					return false;
				}
			}
			
			// Validación de CVV
			if (tipoActual === 'tarjeta' && tarjetaCVV) {
				if (tarjetaCVV.value.length < 3) {
					e.preventDefault();
					alert('El CVV debe tener al menos 3 dígitos');
					tarjetaCVV.focus();
					return false;
				}
			}
		});
	}
});