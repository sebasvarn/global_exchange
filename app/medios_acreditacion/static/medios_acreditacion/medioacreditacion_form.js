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

document.addEventListener('DOMContentLoaded', function() {

    var selectTipo = document.getElementById('id_tipo_medio');
    if (selectTipo) {
        selectTipo.addEventListener('change', function() {
            mostrarCamposPorTipo(this.value);
        });
        mostrarCamposPorTipo(selectTipo.value);
    } else {
        // Si no hay select (estamos editando), buscar el input hidden
        var hiddenTipo = document.querySelector('input[name="tipo_medio"]');
        if (hiddenTipo) {
            mostrarCamposPorTipo(hiddenTipo.value);
        }
    }

});
