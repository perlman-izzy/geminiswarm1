"""
Agent Execution Goal model for SuperAGI.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from superagi_replit.models.db import Base


class AgentExecutionGoal(Base):
    """
    Agent Execution Goal model for SuperAGI.
    
    Represents a goal for a specific agent execution.
    """
    __tablename__ = "agent_execution_goals"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_execution_id = Column(Integer, ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False)
    goal = Column(Text, nullable=False)
    created_at = Column(String(255), nullable=True)
    updated_at = Column(String(255), nullable=True)
    
    # Relationships
    execution = relationship("AgentExecution", back_populates="goals")
    
    def __repr__(self):
        return f"<AgentExecutionGoal {self.id} - {self.goal[:20]}...>"