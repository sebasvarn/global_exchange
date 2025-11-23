-- Crear tabla de pagos
CREATE TABLE IF NOT EXISTS pagos (
    id_pago VARCHAR(255) PRIMARY KEY,
    monto DECIMAL(15,2) NOT NULL,
    metodo VARCHAR(50) NOT NULL,
    moneda VARCHAR(10) NOT NULL DEFAULT 'PYG',
    estado VARCHAR(50) NOT NULL,
    webhook_url VARCHAR(500),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    numero_tarjeta VARCHAR(20),
    numero_billetera VARCHAR(20),
    numero_comprobante VARCHAR(50),
    motivo_rechazo VARCHAR(500)
);

-- Índices para mejorar rendimiento
CREATE INDEX idx_pagos_estado ON pagos(estado);
CREATE INDEX idx_pagos_fecha ON pagos(fecha DESC);
CREATE INDEX idx_pagos_metodo ON pagos(metodo);
CREATE INDEX idx_pagos_moneda ON pagos(moneda);

-- Vista para estadísticas rápidas
CREATE OR REPLACE VIEW estadisticas_pagos AS
SELECT 
    estado,
    metodo,
    COUNT(*) as cantidad,
    SUM(monto) as monto_total,
    AVG(monto) as monto_promedio,
    MIN(fecha) as primer_pago,
    MAX(fecha) as ultimo_pago
FROM pagos
GROUP BY estado, metodo;

-- Datos de prueba iniciales (opcional)
INSERT INTO pagos (id_pago, monto, metodo, moneda, estado, fecha, numero_tarjeta) 
VALUES 
    ('TEST-001', 100000.00, 'tarjeta', 'PYG', 'exito', NOW(), '4111111111111112'),
    ('TEST-002', 50000.00, 'billetera', 'PYG', 'exito', NOW(), NULL),
    ('TEST-003', 75000.00, 'tarjeta', 'PYG', 'fallo', NOW(), '4111111111111113')
ON CONFLICT (id_pago) DO NOTHING;

-- Función para limpiar pagos antiguos (opcional)
CREATE OR REPLACE FUNCTION limpiar_pagos_antiguos(dias INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    filas_eliminadas INTEGER;
BEGIN
    DELETE FROM pagos 
    WHERE fecha < NOW() - INTERVAL '1 day' * dias;
    GET DIAGNOSTICS filas_eliminadas = ROW_COUNT;
    RETURN filas_eliminadas;
END;
$$ LANGUAGE plpgsql;

-- Log de inicio
DO $$ 
BEGIN
    RAISE NOTICE 'Base de datos inicializada correctamente';
    RAISE NOTICE 'Total de pagos de prueba: %', (SELECT COUNT(*) FROM pagos);
END $$;
