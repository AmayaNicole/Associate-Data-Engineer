-- Identificación de saltos bruscos de dinero utilizando Window Functions sobre el modelo Snowflake
WITH transacciones_validas AS (
    SELECT 
        id_transaccion,
        id_cliente,
        fecha_hora,
        monto_usd,
        -- Obtenemos el monto anterior del mismo cliente de manera secuencial cronológica
        LAG(monto_usd) OVER(PARTITION BY id_cliente ORDER BY fecha_hora) AS monto_anterior
    FROM fact_transacciones
    WHERE estado_transaccion = 'aprobada' -- REGLA DE NEGOCIO 4: Solo aprobadas
)
SELECT 
    id_transaccion,
    id_cliente,
    fecha_hora,
    monto_anterior,
    monto_usd AS monto_actual,
    -- Redondeamos el factor de incremento a 2 decimales para una vista limpia
    ROUND((monto_usd / NULLIF(monto_anterior, 0))::numeric, 2) AS factor_incremento
FROM transacciones_validas
WHERE monto_anterior IS NOT NULL 
  AND monto_usd >= (5 * monto_anterior)
ORDER BY id_cliente, fecha_hora;