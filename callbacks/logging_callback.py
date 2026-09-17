# callbacks/logging_callback.py
import logging
from typing import Optional

# Import the necessary Callback and context classes from the ADK
from google.adk.callbacks import (
    Callback,
    AgentInput,
    AgentOutput,
    ToolInput,
    ToolOutput,
)

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ObservabilityCallback(Callback):
    """A custom callback to log the inner workings of the agent system."""

    def before_agent(self, agent_input: AgentInput) -> Optional[AgentInput]:
        """Called before any agent (manager or sub-agent) starts execution."""
        agent_name = agent_input.agent.name
        user_id = agent_input.session.user_id
        session_id = agent_input.session.id
        
        # Log the user's message only if it's the start of the chain (for the manager)
        if agent_input.new_message:
            message = agent_input.new_message.parts[0].text
            logging.info(f"--- START [User: {user_id} | Session: {session_id}] ---")
            logging.info(f"USER_MESSAGE: '{message}'")
        
        logging.info(f"AGENT_START: Running '{agent_name}'...")
        return agent_input

    def before_tool(self, tool_input: ToolInput) -> Optional[ToolInput]:
        """Called before any tool is executed."""
        tool_name = tool_input.tool.__name__
        # Log parameters, but exclude the large tool_context object for cleaner logs
        params = {k: v for k, v in tool_input.params.items() if k != "tool_context"}
        
        logging.info(f"  TOOL_CALL: Agent is calling '{tool_name}' with params: {params}")
        return tool_input

    def after_tool(self, tool_output: ToolOutput) -> Optional[ToolOutput]:
        """Called after any tool finishes execution."""
        tool_name = tool_output.input.tool.__name__
        result = tool_output.result
        
        logging.info(f"  TOOL_RESULT: '{tool_name}' returned: {result}")
        return tool_output

    def after_agent(self, agent_output: AgentOutput) -> Optional[AgentOutput]:
        """Called after any agent (manager or sub-agent) finishes execution."""
        agent_name = agent_output.agent.name
        final_response = agent_output.content.text if agent_output.is_final_response() and agent_output.content else "'' (No final text response)"
        
        logging.info(f"AGENT_END: '{agent_name}' finished.")
        
        # Log the final response only if it's the end of the entire chain
        if agent_output.is_final_response():
            logging.info(f"FINAL_RESPONSE: '{final_response}'")
            logging.info(f"--- END [User: {agent_output.session.user_id} | Session: {agent_output.session.id}] ---\n")
        return agent_output