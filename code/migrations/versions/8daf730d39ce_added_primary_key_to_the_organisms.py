"""added primary key to the organisms

Revision ID: 8daf730d39ce
Revises: 5dbb84329760
Create Date: 2019-04-13 12:57:53.452264

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8daf730d39ce'
down_revision = '5dbb84329760'
branch_labels = None
depends_on = None


def upgrade():
    op.create_primary_key(
        "pk_taxid_organisms",
        "organisms",
        ["taxid"]
    )


def downgrade():
    op.drop_constraint('pk_taxid_organisms', 'organisms', type_='primary')
