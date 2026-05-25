import json
import logging
import asyncio
from typing import Dict, Any, AsyncGenerator, List, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class TaskNode(BaseModel):
    id: str
    description: str
    dependencies: List[str] = []
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    tools_to_use: List[str] = []

class TaskGraph(BaseModel):
    tasks: List[TaskNode]

class Orchestrator:
    """
    Manus-style Orchestrator Service.
    Manages the Planning-Execution loop, decoupling the Planner from the Executor.
    """
    def __init__(self, planner_agent=None, executor_agent=None, verifier_agent=None):
        self.planner_agent = planner_agent
        self.executor_agent = executor_agent
        self.verifier_agent = verifier_agent
        self.context_store = {} 
        self.client = genai.Client()

    async def _plan_tasks(self, user_intent: str) -> List[TaskNode]:
        """Use Gemini to decompose the user intent into a task graph."""
        prompt = f"""You are a Planner Agent in a Manus-style architecture.
Your goal is to decompose the user's intent into a logical sequence of sub-tasks.
Keep it simple. Usually 1-3 tasks are enough.

User Intent: {user_intent}
"""
        response = self.client.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TaskGraph,
            ),
        )
        try:
            graph = TaskGraph.model_validate_json(response.text)
            return graph.tasks
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return [TaskNode(id="t1", description="Process user intent directly")]

    async def execute_task_graph(self, user_intent: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Main Event Loop for Orchestration:
        1. Input -> Planner (Decompose intent into Task Graph)
        2. Execute Tasks iteratively via Tool Gateway/Sandbox
        3. Verify Results
        """
        yield {"type": "step", "text": "🎯 Planner: Analyzing intent and generating Task Graph..."}
        
        # 1. Plan Tasks
        tasks = await self._plan_tasks(user_intent)
        
        yield {"type": "step", "text": f"🗺️ Task Graph generated: {len(tasks)} steps planned."}
        
        # 2. Execute Tasks
        # In a real setup, this passes to the Executor (which wraps the ADK runner).
        # For Phase 1, we yield the plan, and then we will let the main server.py runner execute it.
        for task in tasks:
            yield {"type": "step", "text": f"⚙️ Executor: Scheduled [{task.id}] {task.description}"}
            task.status = "queued"
            
        yield {"type": "step", "text": "🏁 Orchestrator: Handing off to Execution layer."}
        
        # Yield a special control event to tell server.py to run the actual ADK runner
        yield {
            "type": "control",
            "action": "execute_runner",
            "tasks": [t.model_dump() for t in tasks]
        }

# Global instance to be imported by server.py
orchestrator = Orchestrator()
