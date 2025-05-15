"""
Main entry point for the SuperAGI application.
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from superagi_replit.agent.agent import Agent
from superagi_replit.lib.logger import logger
from superagi_replit.models.agent import Agent as AgentModel
from superagi_replit.models.agent_execution import AgentExecution
from superagi_replit.models.agent_execution_feed import AgentExecutionFeed
from superagi_replit.models.agent_execution_goal import AgentExecutionGoal
from superagi_replit.models.db import get_db, Base, engine
from superagi_replit.tools.web_search_tool import WebSearchTool


# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(title="SuperAGI Simplified", version="0.1.0")


# Pydantic models for API
class AgentCreate(BaseModel):
    name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of the agent")
    goals: List[str] = Field(..., description="List of goals the agent should achieve")


class AgentRead(BaseModel):
    id: int
    name: str
    description: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AgentExecutionCreate(BaseModel):
    agent_id: int = Field(..., description="ID of the agent to execute")
    user_input: str = Field(..., description="Initial user input for the agent")


class AgentExecutionRead(BaseModel):
    id: int
    agent_id: int
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    current_step: int


class AgentExecutionFeedRead(BaseModel):
    id: int
    role: str
    feed: str
    feed_type: Optional[str] = None
    created_at: Optional[str] = None


class AgentExecutionQuery(BaseModel):
    agent_execution_id: int = Field(..., description="ID of the agent execution")
    user_input: str = Field(..., description="User input to process")


@app.get("/", tags=["Root"])
async def read_root():
    """Get welcome message."""
    return {"message": "Welcome to SuperAGI Simplified API"}


@app.post("/agents", response_model=AgentRead, tags=["Agents"])
async def create_agent(agent_data: AgentCreate, db: Session = Depends(get_db)):
    """Create a new agent."""
    try:
        # Create timestamp
        now = datetime.now().isoformat()
        
        # Create new agent model
        agent = AgentModel(
            name=agent_data.name,
            description=agent_data.description,
            created_at=now,
            updated_at=now
        )
        
        # Add and commit to DB
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        # Create agent goals
        for goal in agent_data.goals:
            execution = AgentExecution(
                agent_id=agent.id,
                status="CREATED",
                created_at=now,
                updated_at=now,
                current_step=1
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)
            
            execution_goal = AgentExecutionGoal(
                agent_execution_id=execution.id,
                goal=goal,
                created_at=now,
                updated_at=now
            )
            db.add(execution_goal)
        
        db.commit()
        
        return agent
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating agent: {str(e)}")


@app.get("/agents", response_model=List[AgentRead], tags=["Agents"])
async def get_agents(db: Session = Depends(get_db)):
    """Get all agents."""
    agents = db.query(AgentModel).filter(AgentModel.is_deleted == False).all()
    return agents


@app.get("/agents/{agent_id}", response_model=AgentRead, tags=["Agents"])
async def get_agent(agent_id: int, db: Session = Depends(get_db)):
    """Get an agent by ID."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id, AgentModel.is_deleted == False).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return agent


@app.post("/agent-execution", tags=["Agent Execution"])
async def execute_agent(execution_data: AgentExecutionCreate, db: Session = Depends(get_db)):
    """Execute an agent with a user query."""
    try:
        # Get the agent
        agent_model = db.query(AgentModel).filter(AgentModel.id == execution_data.agent_id, AgentModel.is_deleted == False).first()
        if not agent_model:
            raise HTTPException(status_code=404, detail=f"Agent {execution_data.agent_id} not found")
        
        # Create an execution record
        now = datetime.now().isoformat()
        execution = AgentExecution(
            agent_id=agent_model.id,
            status="RUNNING",
            created_at=now,
            updated_at=now,
            current_step=1
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        
        # Get agent goals
        agent_goals = []
        for goal in db.query(AgentExecutionGoal).filter(AgentExecutionGoal.agent_execution_id == execution.id).all():
            agent_goals.append(goal.goal)
        
        # Create the agent
        agent = Agent(
            name=agent_model.name,
            description=agent_model.description,
            goals=agent_goals
        )
        
        # Add tools
        agent.add_tool(WebSearchTool())
        
        # Run the agent
        response = agent.run(execution_data.user_input)
        
        # Save the execution feed
        for msg in agent.get_chat_history():
            feed = AgentExecutionFeed(
                agent_execution_id=execution.id,
                role=msg["role"],
                feed=msg["content"],
                feed_type="TEXT",
                created_at=now,
                updated_at=now
            )
            db.add(feed)
        
        # Update execution status
        execution.status = "COMPLETED"
        execution.updated_at = datetime.now().isoformat()
        db.commit()
        
        return {
            "execution_id": execution.id,
            "response": response,
            "status": "COMPLETED"
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error executing agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error executing agent: {str(e)}")


@app.get("/agent-execution/{execution_id}/feed", response_model=List[AgentExecutionFeedRead], tags=["Agent Execution"])
async def get_execution_feed(execution_id: int, db: Session = Depends(get_db)):
    """Get the feed for an agent execution."""
    feeds = db.query(AgentExecutionFeed).filter(AgentExecutionFeed.agent_execution_id == execution_id).all()
    if not feeds:
        raise HTTPException(status_code=404, detail=f"No feeds found for execution {execution_id}")
    return feeds


@app.post("/agent-query", tags=["Agent Execution"])
async def query_agent(query_data: AgentExecutionQuery, db: Session = Depends(get_db)):
    """Send a query to a running agent execution."""
    try:
        # Get the execution
        execution = db.query(AgentExecution).filter(AgentExecution.id == query_data.agent_execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail=f"Execution {query_data.agent_execution_id} not found")
        
        # Get the agent
        agent_model = db.query(AgentModel).filter(AgentModel.id == execution.agent_id).first()
        if not agent_model:
            raise HTTPException(status_code=404, detail=f"Agent {execution.agent_id} not found")
        
        # Get agent goals
        agent_goals = []
        for goal in db.query(AgentExecutionGoal).filter(AgentExecutionGoal.agent_execution_id == execution.id).all():
            agent_goals.append(goal.goal)
        
        # Create the agent
        agent = Agent(
            name=agent_model.name,
            description=agent_model.description,
            goals=agent_goals
        )
        
        # Add tools
        agent.add_tool(WebSearchTool())
        
        # Load previous chat history
        feeds = db.query(AgentExecutionFeed).filter(AgentExecutionFeed.agent_execution_id == execution.id).all()
        for feed in feeds:
            agent.add_message(feed.role, feed.feed)
        
        # Run the agent with the new query
        response = agent.run(query_data.user_input)
        
        # Save the new execution feed
        now = datetime.now().isoformat()
        for msg in agent.get_chat_history()[len(feeds):]:
            feed = AgentExecutionFeed(
                agent_execution_id=execution.id,
                role=msg["role"],
                feed=msg["content"],
                feed_type="TEXT",
                created_at=now,
                updated_at=now
            )
            db.add(feed)
        
        # Update execution
        execution.current_step += 1
        execution.updated_at = now
        db.commit()
        
        return {
            "execution_id": execution.id,
            "response": response,
            "status": execution.status
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error querying agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error querying agent: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    # Use host 0.0.0.0 to make the server accessible outside of localhost
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)