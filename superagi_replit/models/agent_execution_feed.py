"""
Agent Execution Feed model for SuperAGI.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from superagi_replit.models.db import Base


class AgentExecutionFeed(Base):
    """
    Agent Execution Feed model for SuperAGI.
    
    Represents a message or action in the agent execution feed.
    """
    __tablename__ = "agent_execution_feeds"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_execution_id = Column(Integer, ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(255), nullable=True)
    feed = Column(Text, nullable=True)
    feed_type = Column(String(255), nullable=True)
    created_at = Column(String(255), nullable=True)
    updated_at = Column(String(255), nullable=True)
    
    # Relationships
    execution = relationship("AgentExecution", back_populates="feeds")
    
    def __repr__(self):
        return f"<AgentExecutionFeed {self.id} - {self.role}>"