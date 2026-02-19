"""创建初始表结构

Revision ID: 001_initial
Revises: 
Create Date: 2024-02-01

AI Society数据库初始化迁移
创建所有核心表：agents, relationships, conversations, messages, memories, world_states, llm_calls
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===================
    # 智能体表
    # ===================
    op.create_table(
        'agents',
        sa.Column('id', sa.String(8), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, index=True),
        sa.Column('age', sa.Integer, default=25),
        sa.Column('gender', sa.String(10), default='男'),
        sa.Column('occupation', sa.String(50), default='自由职业', index=True),
        sa.Column('backstory', sa.Text, nullable=True),
        sa.Column('traits', postgresql.ARRAY(sa.String), nullable=True),
        # 人格特质
        sa.Column('openness', sa.Integer, default=50),
        sa.Column('conscientiousness', sa.Integer, default=50),
        sa.Column('extraversion', sa.Integer, default=50),
        sa.Column('agreeableness', sa.Integer, default=50),
        sa.Column('neuroticism', sa.Integer, default=50),
        # 需求状态
        sa.Column('hunger', sa.Float, default=50.0),
        sa.Column('fatigue', sa.Float, default=50.0),
        sa.Column('social', sa.Float, default=50.0),
        sa.Column('entertainment', sa.Float, default=50.0),
        sa.Column('hygiene', sa.Float, default=50.0),
        sa.Column('comfort', sa.Float, default=50.0),
        # 经济状态
        sa.Column('balance', sa.Float, default=10000.0),
        sa.Column('daily_income', sa.Float, default=0.0),
        sa.Column('daily_expense', sa.Float, default=0.0),
        # 位置信息
        sa.Column('position_x', sa.Float, default=0.0),
        sa.Column('position_y', sa.Float, default=0.0),
        sa.Column('location_id', sa.String(20), nullable=True, index=True),
        sa.Column('location_name', sa.String(50), nullable=True),
        sa.Column('home_location_id', sa.String(20), nullable=True),
        sa.Column('work_location_id', sa.String(20), nullable=True),
        # 行为状态
        sa.Column('state', sa.String(20), default='active', index=True),
        sa.Column('current_action_type', sa.String(20), default='idle'),
        sa.Column('current_action_target', sa.String(50), nullable=True),
        sa.Column('current_action_started_at', sa.DateTime, nullable=True),
        sa.Column('current_action_duration', sa.Integer, default=0),
        sa.Column('current_thinking', sa.Text, nullable=True),
        # LLM配置
        sa.Column('model_name', sa.String(50), default='deepseek-reasoner'),
        # 时间追踪
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_decision_time', sa.DateTime, nullable=True),
        sa.Column('work_hours_today', sa.Float, default=0.0),
    )
    
    op.create_index('ix_agents_state_location', 'agents', ['state', 'location_id'])
    
    # ===================
    # 关系表
    # ===================
    op.create_table(
        'relationships',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('source_agent_id', sa.String(8), sa.ForeignKey('agents.id', ondelete='CASCADE'), index=True),
        sa.Column('target_agent_id', sa.String(8), index=True),
        sa.Column('target_agent_name', sa.String(50)),
        sa.Column('closeness', sa.Integer, default=50),
        sa.Column('trust', sa.Integer, default=50),
        sa.Column('interaction_count', sa.Integer, default=0),
        sa.Column('last_interaction', sa.DateTime, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    op.create_unique_constraint('uq_relationship_pair', 'relationships', ['source_agent_id', 'target_agent_id'])
    op.create_index('ix_relationships_closeness', 'relationships', ['closeness'])
    
    # ===================
    # 对话表
    # ===================
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(8), primary_key=True),
        sa.Column('participant_a_id', sa.String(8), index=True),
        sa.Column('participant_a_name', sa.String(50)),
        sa.Column('participant_b_id', sa.String(8), index=True),
        sa.Column('participant_b_name', sa.String(50)),
        sa.Column('state', sa.String(20), default='pending', index=True),
        sa.Column('location', sa.String(50), default=''),
        sa.Column('location_id', sa.String(20), nullable=True),
        sa.Column('game_time', sa.DateTime, nullable=True),
        sa.Column('started_at', sa.DateTime, server_default=sa.func.now(), index=True),
        sa.Column('ended_at', sa.DateTime, nullable=True),
        sa.Column('topics', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('overall_emotion', sa.String(20), default='中性'),
        sa.Column('relationship_change', sa.Integer, default=0),
        sa.Column('is_memorable', sa.Boolean, default=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('memorable_for_a', sa.Text, nullable=True),
        sa.Column('memorable_for_b', sa.Text, nullable=True),
        sa.Column('message_count', sa.Integer, default=0),
        sa.Column('encounter_count', sa.Integer, default=1),
    )
    
    op.create_index('ix_conversations_participants', 'conversations', ['participant_a_id', 'participant_b_id'])
    op.create_index('ix_conversations_state_time', 'conversations', ['state', 'started_at'])
    
    # ===================
    # 消息表
    # ===================
    op.create_table(
        'messages',
        sa.Column('id', sa.String(8), primary_key=True),
        sa.Column('conversation_id', sa.String(8), sa.ForeignKey('conversations.id', ondelete='CASCADE'), index=True),
        sa.Column('speaker_id', sa.String(8), index=True),
        sa.Column('speaker_name', sa.String(50)),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('emotion', sa.String(20), nullable=True),
        sa.Column('is_end_signal', sa.Boolean, default=False),
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now(), index=True),
    )
    
    # ===================
    # 记忆表
    # ===================
    op.create_table(
        'memories',
        sa.Column('id', sa.String(8), primary_key=True),
        sa.Column('agent_id', sa.String(8), sa.ForeignKey('agents.id', ondelete='CASCADE'), index=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('memory_type', sa.String(20), default='event', index=True),
        sa.Column('importance', sa.Float, default=5.0, index=True),
        sa.Column('access_count', sa.Integer, default=0),
        sa.Column('keywords', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('related_agents', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('location', sa.String(50), nullable=True),
        sa.Column('vector_id', sa.String(50), nullable=True),
        sa.Column('game_time', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), index=True),
        sa.Column('accessed_at', sa.DateTime, nullable=True),
    )
    
    op.create_index('ix_memories_agent_type', 'memories', ['agent_id', 'memory_type'])
    op.create_index('ix_memories_agent_importance', 'memories', ['agent_id', 'importance'])
    
    # ===================
    # 世界状态表
    # ===================
    op.create_table(
        'world_states',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('game_time', sa.DateTime, nullable=False),
        sa.Column('real_time', sa.DateTime, server_default=sa.func.now()),
        sa.Column('clock_state', postgresql.JSONB, nullable=True),
        sa.Column('cost_tracker_state', postgresql.JSONB, nullable=True),
        sa.Column('description', sa.String(200), nullable=True),
        sa.Column('is_auto_save', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), index=True),
    )
    
    op.create_index('ix_world_states_game_time', 'world_states', ['game_time'])
    
    # ===================
    # LLM调用记录表
    # ===================
    op.create_table(
        'llm_calls',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('model_name', sa.String(50), index=True),
        sa.Column('call_type', sa.String(50), index=True),
        sa.Column('agent_id', sa.String(8), nullable=True, index=True),
        sa.Column('input_tokens', sa.Integer, default=0),
        sa.Column('output_tokens', sa.Integer, default=0),
        sa.Column('reasoning_tokens', sa.Integer, default=0),
        sa.Column('cost', sa.Float, default=0.0),
        sa.Column('response_time_ms', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), index=True),
    )
    
    op.create_index('ix_llm_calls_model_time', 'llm_calls', ['model_name', 'created_at'])
    op.create_index('ix_llm_calls_date', 'llm_calls', ['created_at'])


def downgrade() -> None:
    op.drop_table('llm_calls')
    op.drop_table('world_states')
    op.drop_table('memories')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('relationships')
    op.drop_table('agents')
