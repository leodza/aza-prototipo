-- Índices secundarios para el tablero, el histórico y la auditoría.
CREATE INDEX IF NOT EXISTS ix_inspecciones_fecha_hora ON inspecciones (fecha_hora);
CREATE INDEX IF NOT EXISTS ix_inspecciones_receta_id ON inspecciones (receta_id);
CREATE INDEX IF NOT EXISTS ix_inspecciones_lote_id   ON inspecciones (lote_id);
CREATE INDEX IF NOT EXISTS ix_inspecciones_batch_id  ON inspecciones (batch_id);
CREATE INDEX IF NOT EXISTS ix_inspecciones_estado    ON inspecciones (estado);
CREATE INDEX IF NOT EXISTS ix_auditoria_fecha        ON auditoria (fecha);
CREATE INDEX IF NOT EXISTS ix_inspecciones_fecha_id  ON inspecciones (fecha_hora, id);

\echo '--- indices en inspecciones y auditoria ---'
SELECT tablename, indexname FROM pg_indexes
WHERE schemaname = 'public' AND tablename IN ('inspecciones', 'auditoria')
ORDER BY tablename, indexname;

\echo '--- tamano de la tabla ---'
SELECT count(*) AS filas FROM inspecciones;
