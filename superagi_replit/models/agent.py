"""
Agent model for SuperAGI.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from superagi_replit.models.db import Base


class Agent(Base):
    """
    Agent model for SuperAGI.
    
    Represents an AI agent with specific goals and configurations.
    """
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(String(255), nullable=True)
    updated_at = Column(String(255), nullable=True)
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    executions = relationship("AgentExecution", back_populates="agent", passive_deletes=True)
    
    def __repr__(self):
        return f"<Agent {self.name}>"