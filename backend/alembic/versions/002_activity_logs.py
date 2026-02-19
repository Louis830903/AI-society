"""添加活动日志表

Revision ID: 002_activity_logs
Revises: 001_initial
Create Date: 2024-02-16

添加智能体活动日志表，记录每个智能体的所有活动，供观察者查看
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_activity_logs'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===================
    # 活动日志表
    # ===================
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('agent_id', sa.String(8), sa.ForeignKey('agents.id', ondelete='CASCADE'), index=True),
        sa.Column('agent_name', sa.String(50)),
        # 活动类型: decision, conversation, reflection, reaction, plan
        sa.Column('activity_type', sa.String(20), index=True),
        # 活动内容
        sa.Column('action', sa.String(50)),
        sa.Column('target', sa.String(100), nullable=True),
        sa.Column('location', sa.String(50), nullable=True),
        # 思考过程
        sa.Column('thinking', sa.Text, nullable=True),
        # 对话相关
        sa.Column('conversation_id', sa.String(8), nullable=True, index=True),
        sa.Column('conversation_partner', sa.String(50), nullable=True),
        sa.Column('message_content', sa.Text, nullable=True),
        # 反思相关
        sa.Column('reflection_content', sa.Text, nullable=True),
        # 时间
        sa.Column('game_time', sa.DateTime, index=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), index=True),
    )
    
    # 复合索引
    op.create_index('ix_activity_logs_agent_time', 'activity_logs', ['agent_id', 'game_time'])
    op.create_index('ix_activity_logs_agent_type', 'activity_logs', ['agent_id', 'activity_type'])


def downgrade() -> None:
    op.drop_index('ix_activity_logs_agent_type', table_name='activity_logs')
    op.drop_index('ix_activity_logs_agent_time', table_name='activity_logs')
    op.drop_table('activity_logs')
