"""Add AI fields to conflicts and decisions tables

Revision ID: 002
Revises: 001
Create Date: 2025-09-27 12:00:00.000000

This migration adds AI-specific fields to enable AI optimization integration:
- Conflicts table: ai_analyzed, ai_confidence, ai_solution_id, ai_recommendations, ai_analysis_time
- Decisions table: ai_generated, ai_solver_method, ai_score, ai_confidence

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add AI fields to conflicts and decisions tables"""
    
    # Add AI fields to conflicts table
    op.add_column('conflicts', sa.Column('ai_analyzed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('conflicts', sa.Column('ai_confidence', sa.Numeric(precision=5, scale=4), nullable=True))
    op.add_column('conflicts', sa.Column('ai_solution_id', sa.String(length=100), nullable=True))
    op.add_column('conflicts', sa.Column('ai_recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('conflicts', sa.Column('ai_analysis_time', sa.DateTime(timezone=True), nullable=True))
    
    # Add AI fields to decisions table
    op.add_column('decisions', sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('decisions', sa.Column('ai_solver_method', sa.String(length=50), nullable=True))
    op.add_column('decisions', sa.Column('ai_score', sa.Numeric(precision=8, scale=4), nullable=True))
    op.add_column('decisions', sa.Column('ai_confidence', sa.Numeric(precision=5, scale=4), nullable=True))
    
    # Add check constraints for AI confidence values (must be between 0.0 and 1.0)
    op.create_check_constraint(
        'conflicts_ai_confidence_check',
        'conflicts',
        'ai_confidence IS NULL OR (ai_confidence >= 0.0 AND ai_confidence <= 1.0)'
    )
    
    op.create_check_constraint(
        'decisions_ai_confidence_check',
        'decisions',
        'ai_confidence IS NULL OR (ai_confidence >= 0.0 AND ai_confidence <= 1.0)'
    )
    
    # Add check constraint for AI solver method values
    op.create_check_constraint(
        'decisions_ai_solver_method_check',
        'decisions',
        """ai_solver_method IS NULL OR ai_solver_method IN ('rule_based', 'constraint_programming', 'reinforcement_learning')"""
    )
    
    # Create indexes for better query performance on AI fields
    op.create_index('idx_conflicts_ai_analyzed', 'conflicts', ['ai_analyzed'])
    op.create_index('idx_conflicts_ai_confidence', 'conflicts', ['ai_confidence'])
    op.create_index('idx_decisions_ai_generated', 'decisions', ['ai_generated'])
    op.create_index('idx_decisions_ai_solver_method', 'decisions', ['ai_solver_method'])


def downgrade() -> None:
    """Remove AI fields from conflicts and decisions tables"""
    
    # Drop indexes
    op.drop_index('idx_decisions_ai_solver_method', table_name='decisions')
    op.drop_index('idx_decisions_ai_generated', table_name='decisions')
    op.drop_index('idx_conflicts_ai_confidence', table_name='conflicts')
    op.drop_index('idx_conflicts_ai_analyzed', table_name='conflicts')
    
    # Drop check constraints
    op.drop_constraint('decisions_ai_solver_method_check', 'decisions')
    op.drop_constraint('decisions_ai_confidence_check', 'decisions')
    op.drop_constraint('conflicts_ai_confidence_check', 'conflicts')
    
    # Remove AI columns from decisions table
    op.drop_column('decisions', 'ai_confidence')
    op.drop_column('decisions', 'ai_score')
    op.drop_column('decisions', 'ai_solver_method')
    op.drop_column('decisions', 'ai_generated')
    
    # Remove AI columns from conflicts table
    op.drop_column('conflicts', 'ai_analysis_time')
    op.drop_column('conflicts', 'ai_recommendations')
    op.drop_column('conflicts', 'ai_solution_id')
    op.drop_column('conflicts', 'ai_confidence')
    op.drop_column('conflicts', 'ai_analyzed')