"""Add signature_data column to demande_vacances

Revision ID: 412d53755b3d
Revises: a332ca6c192f
Create Date: 2025-04-13 16:58:40.926413

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '412d53755b3d'
down_revision = 'a332ca6c192f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('demande_vacances', schema=None) as batch_op:
        batch_op.add_column(sa.Column('signature_data', sa.Text(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('demande_vacances', schema=None) as batch_op:
        batch_op.drop_column('signature_data')

    # ### end Alembic commands ###
