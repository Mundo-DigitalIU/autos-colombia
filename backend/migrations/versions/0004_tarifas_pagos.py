"""Tarifas mensuales por tipo de vehículo y pagos de mensualidad.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tarifa",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("tipo_vehiculo", sa.Text(), nullable=False),
        sa.Column("valor_mensual", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint("tipo_vehiculo", name="uq_tarifa_tipo_vehiculo"),
        sa.CheckConstraint("tipo_vehiculo IN ('MOTO', 'AUTOMOVIL', 'CAMIONETA')", name="ck_tarifa_tipo_vehiculo"),
        sa.CheckConstraint("valor_mensual > 0", name="ck_tarifa_valor_positivo"),
    )
    op.create_table(
        "pago",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("vehiculo_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("medio_pago", sa.Text(), nullable=False),
        sa.Column("fecha_pago", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("vigencia_desde", sa.Date(), nullable=False),
        sa.Column("vigencia_hasta", sa.Date(), nullable=False),
        sa.Column("operador_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.Text(), server_default="REGISTRADO", nullable=False),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_por_operador_id", sa.BigInteger(), nullable=True),
        sa.Column("motivo_anulacion", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["vehiculo_id"], ["vehiculo.id"], name="fk_pago_vehiculo", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name="fk_pago_cliente", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operador_id"], ["operador.id"], name="fk_pago_operador", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["anulado_por_operador_id"], ["operador.id"],
                                name="fk_pago_anulado_por_operador", ondelete="RESTRICT"),
        sa.CheckConstraint("valor > 0", name="ck_pago_valor_positivo"),
        sa.CheckConstraint("medio_pago IN ('EFECTIVO', 'TRANSFERENCIA', 'TARJETA')", name="ck_pago_medio_pago"),
        sa.CheckConstraint("estado IN ('REGISTRADO', 'ANULADO')", name="ck_pago_estado"),
        sa.CheckConstraint("vigencia_hasta = vigencia_desde + 30", name="ck_pago_vigencia_30_dias"),
        sa.CheckConstraint(
            "(estado = 'ANULADO' AND anulado_en IS NOT NULL AND anulado_por_operador_id IS NOT NULL "
            "AND motivo_anulacion IS NOT NULL) "
            "OR (estado = 'REGISTRADO' AND anulado_en IS NULL AND anulado_por_operador_id IS NULL "
            "AND motivo_anulacion IS NULL)",
            name="ck_pago_anulacion_coherente",
        ),
    )
    op.create_index("uq_pago_vehiculo_vigencia_registrado", "pago", ["vehiculo_id", "vigencia_desde"], unique=True,
                    postgresql_where=sa.text("estado = 'REGISTRADO'"))
    op.create_index("ix_pago_vehiculo_id", "pago", ["vehiculo_id"])
    op.create_index("ix_pago_cliente_id", "pago", ["cliente_id"])
    op.create_index("ix_pago_fecha_pago", "pago", ["fecha_pago"])


def downgrade() -> None:
    # Solo para una reversión deliberada: elimina todos los pagos y las tarifas.
    op.drop_index("ix_pago_fecha_pago", table_name="pago")
    op.drop_index("ix_pago_cliente_id", table_name="pago")
    op.drop_index("ix_pago_vehiculo_id", table_name="pago")
    op.drop_index("uq_pago_vehiculo_vigencia_registrado", table_name="pago")
    op.drop_table("pago")
    op.drop_table("tarifa")
