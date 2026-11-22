-- Convierte la bitácora a JSONB conservando el contenido anterior.
ALTER TABLE auditoria
    ALTER COLUMN detalle TYPE jsonb
    USING CASE
        WHEN detalle IS NULL THEN NULL
        WHEN detalle::text LIKE '{%' THEN detalle::jsonb
        ELSE jsonb_build_object('mensaje', detalle::text)
    END;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'auditoria'
ORDER BY ordinal_position;
