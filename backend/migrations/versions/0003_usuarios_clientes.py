"""Usuarios con roles, sesiones, clientes y restricción del tipo de celda.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("nombre_usuario", sa.Text(), nullable=False),
        sa.Column("clave_hash", sa.Text(), nullable=False),
        sa.Column("rol", sa.Text(), nullable=False),
        sa.Column("operador_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["operador_id"], ["operador.id"], name="fk_usuario_operador", ondelete="RESTRICT"),
        sa.UniqueConstraint("nombre_usuario", name="uq_usuario_nombre_usuario"),
        sa.UniqueConstraint("operador_id", name="uq_usuario_operador"),
        sa.CheckConstraint("nombre_usuario ~ '[^[:space:]]'", name="ck_usuario_nombre_no_vacio"),
        sa.CheckConstraint(
            "nombre_usuario = lower(regexp_replace(nombre_usuario, '^[[:space:]]+|[[:space:]]+$', '', 'g'))",
            name="ck_usuario_nombre_normalizado",
        ),
        sa.CheckConstraint("clave_hash ~ '[^[:space:]]'", name="ck_usuario_clave_no_vacia"),
        sa.CheckConstraint("rol IN ('ADMINISTRADOR', 'OPERADOR')", name="ck_usuario_rol"),
    )
    op.create_table(
        "sesion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("creada", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expira", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocada", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], name="fk_sesion_usuario", ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_sesion_token_hash"),
    )
    op.create_index("ix_sesion_usuario_id", "sesion", ["usuario_id"])
    op.create_table(
        "cliente",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("documento", sa.Text(), nullable=False),
        sa.Column("telefono", sa.Text(), nullable=False),
        sa.UniqueConstraint("documento", name="uq_cliente_documento"),
        sa.CheckConstraint("nombre ~ '[^[:space:]]'", name="ck_cliente_nombre_no_vacio"),
        sa.CheckConstraint("telefono ~ '[^[:space:]]'", name="ck_cliente_telefono_no_vacio"),
        sa.CheckConstraint("documento ~ '[^[:space:]]'", name="ck_cliente_documento_no_vacio"),
        sa.CheckConstraint(
            "documento = regexp_replace(documento, '^[[:space:]]+|[[:space:]]+$', '', 'g')",
            name="ck_cliente_documento_normalizado",
        ),
    )
    op.add_column("vehiculo", sa.Column("cliente_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_vehiculo_cliente", "vehiculo", "cliente", ["cliente_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_vehiculo_cliente_id", "vehiculo", ["cliente_id"])
    # NOT VALID: no revisa las filas existentes (p. ej. 'Libre'); solo las inserciones y cambios nuevos.
    op.execute(
        "ALTER TABLE celda ADD CONSTRAINT ck_celda_tipo_valido "
        "CHECK (tipo IN ('MOTO', 'AUTOMOVIL', 'CAMIONETA')) NOT VALID"
    )


def downgrade() -> None:
    # Solo para una reversión deliberada: elimina usuarios, sesiones y clientes.
    op.drop_constraint("ck_celda_tipo_valido", "celda", type_="check")
    op.drop_index("ix_vehiculo_cliente_id", table_name="vehiculo")
    op.drop_constraint("fk_vehiculo_cliente", "vehiculo", type_="foreignkey")
    op.drop_column("vehiculo", "cliente_id")
    op.drop_table("cliente")
    op.drop_index("ix_sesion_usuario_id", table_name="sesion")
    op.drop_table("sesion")
    op.drop_table("usuario")
