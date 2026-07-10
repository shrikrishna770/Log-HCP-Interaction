import json
import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from app.agent.tools import (
    call_groq,
    log_interaction_node,
    edit_interaction_node,
    suggest_follow_ups_node,
    hcp_history_node,
    materials_recommender_node
)

logger = logging.getLogger(__name__)

# Define the State of the LangGraph agent
class AgentState(TypedDict):
    message: str
    history: List[Dict[str, str]]
    current_form_state: Optional[Dict[str, Any]]
    
    # Routing and orchestration state
    next_node: str
    intent: str
    tool_calls_made: List[str]
    
    # Internal tool data exchange
    hcp_id: Optional[int]
    interaction_id: Optional[int]
    extracted_data: Optional[Dict[str, Any]]
    history_summary: Optional[str]
    suggested_follow_ups: List[str]
    recommended_materials: List[Dict[str, Any]]
    recommended_samples: List[Dict[str, Any]]
    
    # Final Output
    reply: str
    parsed_form_data: Optional[Dict[str, Any]]

# Router Node: Analyzes intent of user query
def router_node(state: AgentState) -> Dict[str, Any]:
    message = state.get("message", "")
    history = state.get("history", [])
    
    prompt = f"""
    Analyze the user message and history to determine the primary intent.
    User Message: "{message}"
    
    Categorize the intent into one of the following exact categories:
    - "log": The user is describing an interaction they had with an HCP to log it (e.g., "Met Dr. Smith, discussed X", or general interaction notes).
    - "edit": The user is asking to modify or update an existing field or interaction (e.g., "change the sentiment to positive", "correct the doctor's name", "add attendee").
    - "history": The user is asking for the past interaction history, trends, or context of an HCP (e.g., "what is Dr. Smith's history?", "how did my last visit with Dr. Jones go?").
    - "recommend": The user is asking for material or sample recommendations for an HCP (e.g., "what materials should I share with Dr. Smith?", "suggest samples for cardio topics").
    - "general": General questions, greeting, help, or chatting.
    
    Respond with EXACTLY a JSON object with this key:
    - intent: string (one of: "log", "edit", "history", "recommend", "general")
    - reason: string (brief explanation)
    
    Ensure the output is valid JSON.
    """
    
    res_json = call_groq(prompt, json_mode=True)
    intent = "general"
    try:
        data = json.loads(res_json)
        intent = data.get("intent", "general")
    except Exception as e:
        logger.error(f"Failed to parse router intent: {e}")
        # Basic regex/keyword backup
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["log", "met", "visited", "had a call", "spoke to"]):
            intent = "log"
        elif any(w in msg_lower for w in ["change", "edit", "update", "correct", "modify"]):
            intent = "edit"
        elif any(w in msg_lower for w in ["history", "past", "previous", "last time"]):
            intent = "history"
        elif any(w in msg_lower for w in ["recommend", "suggest materials", "samples to give"]):
            intent = "recommend"
            
    logger.info(f"Detected intent: {intent}")
    return {"intent": intent, "next_node": intent}

# Conditional Router Function
def route_next(state: AgentState) -> str:
    intent = state.get("intent", "general")
    if intent == "log":
        return "log_interaction"
    elif intent == "edit":
        return "edit_interaction"
    elif intent == "history":
        return "hcp_history"
    elif intent == "recommend":
        return "materials_recommender"
    else:
        return "responder"

# Responder Node: Compiles outputs and creates chat answer
def responder_node(state: AgentState) -> Dict[str, Any]:
    message = state.get("message", "")
    intent = state.get("intent", "general")
    history_summary = state.get("history_summary")
    suggested_follow_ups = state.get("suggested_follow_ups", [])
    rec_materials = state.get("recommended_materials", [])
    rec_samples = state.get("recommended_samples", [])
    extracted_data = state.get("extracted_data")
    parsed_form_data = state.get("parsed_form_data")
    
    # Synthesize conversational reply
    context = ""
    if intent == "log" and extracted_data:
        context += f"\n- Logged interaction for: {extracted_data.get('hcp_name')}"
        context += f"\n- Sentiment: {extracted_data.get('sentiment')}"
        if suggested_follow_ups:
            context += f"\n- Suggested Follow-ups: {', '.join(suggested_follow_ups[:3])}"
    elif intent == "edit" and parsed_form_data:
        context += f"\n- Updated interaction details in form: {json.dumps(parsed_form_data)}"
    elif intent == "history" and history_summary:
        context += f"\n- HCP History Summary: {history_summary}"
    elif intent == "recommend":
        mats = [m.get("name") for m in rec_materials]
        samps = [s.get("name") for s in rec_samples]
        context += f"\n- Recommended Materials: {', '.join(mats)}"
        context += f"\n- Recommended Samples: {', '.join(samps)}"
        
    prompt = f"""
    You are an AI assistant in a pharmaceutical CRM. The user is a sales representative.
    User's message: "{message}"
    
    We performed actions matching intent: "{intent}".
    System context generated during tools execution:
    {context}
    
    Provide a professional, friendly, and helpful response to the rep.
    - If an interaction was logged, confirm what was saved and mention any auto-suggested follow-ups or materials.
    - If edited, summarize the edits made.
    - If history was summarized, explain it clearly.
    - If recommending, list the recommendations and why they fit.
    - If general, answer the query or guide them on how to log/query.
    
    Keep the response concise (2-4 sentences). Do not use placeholders.
    """
    
    reply = call_groq(prompt, json_mode=False)
    
    return {
        "reply": reply,
        # Ensure we return the state values
        "parsed_form_data": parsed_form_data
    }

# Build LangGraph Workflow
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("router", router_node)
workflow.add_node("log_interaction", log_interaction_node)
workflow.add_node("edit_interaction", edit_interaction_node)
workflow.add_node("suggest_follow_ups", suggest_follow_ups_node)
workflow.add_node("hcp_history", hcp_history_node)
workflow.add_node("materials_recommender", materials_recommender_node)
workflow.add_node("responder", responder_node)

# Set Entry Point
workflow.set_entry_point("router")

# Define conditional edges from router
workflow.add_conditional_edges(
    "router",
    route_next,
    {
        "log_interaction": "log_interaction",
        "edit_interaction": "edit_interaction",
        "hcp_history": "hcp_history",
        "materials_recommender": "materials_recommender",
        "responder": "responder"
    }
)

# Flow after logging: we suggest follow-ups and materials recommendations automatically
workflow.add_edge("log_interaction", "suggest_follow_ups")
workflow.add_edge("suggest_follow_ups", "materials_recommender")
workflow.add_edge("materials_recommender", "responder")

# Flow after editing: suggest follow-ups, then respond
workflow.add_edge("edit_interaction", "suggest_follow_ups")

# Flows from queries
workflow.add_edge("hcp_history", "responder")

# Terminals
workflow.add_edge("responder", END)

# Compile graph
agent_graph = workflow.compile()
