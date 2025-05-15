"""
Agent Execution model for SuperAGI.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from superagi_replit.models.db import Base


class AgentExecution(Base):
    """
    Agent Execution model for SuperAGI.
    
    Represents a specific execution run of an agent.
    """
    __tablename__ = "agent_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=True)
    status = Column(String(255), nullable=True, default="CREATED")
    last_execution_time = Column(String(255), nullable=True)
    created_at = Column(String(255), nullable=True)
    updated_at = Column(String(255), nullable=True)
    current_step = Column(Integer, default=1)
    
    # Relationships
    agent = relationship("Agent", back_populates="executions")
    goals = relationship("AgentExecutionGoal", back_populates="execution", passive_deletes=True)
    feeds = relationship("AgentExecutionFeed", back_populates="execution", passive_deletes=True)
    
    def __repr__(self):
        return f"<AgentExecution {self.id}>"