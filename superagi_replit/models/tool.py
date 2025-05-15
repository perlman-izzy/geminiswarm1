"""
Tool model for SuperAGI.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean

from superagi_replit.models.db import Base


class Tool(Base):
    """
    Tool model for SuperAGI.
    
    Represents a tool that agents can use.
    """
    __tablename__ = "tools"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    folder_name = Column(String(255), nullable=True)
    class_name = Column(String(255), nullable=True)
    file_name = Column(String(255), nullable=True)
    built_in = Column(Boolean, default=False)
    created_at = Column(String(255), nullable=True)
    updated_at = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<Tool {self.name}>"