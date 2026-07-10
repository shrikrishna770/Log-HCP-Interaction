import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.database import SessionLocal
from app.models import HCP, Material, Interaction, interaction_materials

logger = logging.getLogger(__name__)

# Helper to call Groq LLM
def call_groq(prompt: str, json_mode: bool = False, model: str = "gemma2-9b-it") -> str:
    api_key = settings.GROQ_API_KEY
    if not api_key:
        logger.warning("GROQ_API_KEY not found in environment. Using mock responses for demo.")
        return get_mock_response(prompt, json_mode)
    
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        response_format = {"type": "json_object"} if json_mode else None
        
        # System message for json mode
        messages = []
        if json_mode:
            messages.append({
                "role": "system",
                "content": "You are a precise data extractor. You must respond ONLY with a valid JSON object matching the requested schema. Do not include markdown formatting or wrapping."
            })
        messages.append({"role": "user", "content": prompt})
        
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format=response_format,
            temperature=0.1 if json_mode else 0.7
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling Groq API: {str(e)}. Falling back to mock data.")
        return get_mock_response(prompt, json_mode)

def get_mock_response(prompt: str, json_mode: bool) -> str:
    """Provides high-quality mock data when GROQ_API_KEY is not configured."""
    prompt_lower = prompt.lower()
    
    # Try to extract the user's message/note/topics from the prompt to avoid matching instructions
    target_text = ""
    if "user's message: \"" in prompt_lower:
        try:
            target_text = prompt.split("User's message: \"")[1].split('"')[0]
        except Exception:
            pass
    elif 'user message: "' in prompt_lower:
        try:
            target_text = prompt.split('User Message: "')[1].split('"')[0]
        except Exception:
            pass
    elif 'note: "' in prompt_lower:
        try:
            target_text = prompt.split('Note: "')[1].split('"')[0]
        except Exception:
            pass
    elif 'the user wants to make the following edits:\n    "' in prompt_lower:
        try:
            target_text = prompt.split('the user wants to make the following edits:\n    "')[1].split('"')[0]
        except Exception:
            pass
    elif 'the user wants to make the following edits:\n    ' in prompt_lower:
        try:
            target_text = prompt.split('the user wants to make the following edits:\n    ')[1].split('\n')[0]
        except Exception:
            pass
    elif 'the user wants to make the following edits:\n"' in prompt_lower:
        try:
            target_text = prompt.split('the user wants to make the following edits:\n"')[1].split('"')[0]
        except Exception:
            pass
    elif 'topics discussed:' in prompt_lower:
        try:
            target_text = prompt.split('Topics Discussed: ')[1].split('\n')[0]
        except Exception:
            pass

    if not target_text:
        target_text = prompt
        
    target_lower = target_text.lower()
    
    if json_mode:
        # Check if it's intent classification
        if "categorize the intent" in prompt_lower or "primary intent" in prompt_lower:
            intent = "general"
            if any(w in target_lower for w in ["history", "past", "previous", "last time"]):
                intent = "history"
            elif any(w in target_lower for w in ["recommend", "suggest materials", "samples to give"]):
                intent = "recommend"
            elif any(w in target_lower for w in ["change", "edit", "update", "correct", "modify"]):
                intent = "edit"
            elif any(w in target_lower for w in ["log", "met", "visited", "had a call", "spoke to"]):
                intent = "log"
            return json.dumps({
                "intent": intent,
                "reason": f"Mock detected intent '{intent}' based on user message: {target_text}"
            })

        # Check if it's logging/extracting
        if "extract the structured details" in prompt_lower or "extract these fields" in prompt_lower:
            # Try to guess HCP name from target_lower
            hcp_name = "Dr. Sarah Jenkins"
            if "smith" in target_lower:
                hcp_name = "Dr. John Smith"
            elif "sharma" in target_lower:
                hcp_name = "Dr. Amit Sharma"
            elif "davis" in target_lower:
                hcp_name = "Dr. Emily Davis"
            else:
                import re
                match = re.search(r'(?:met with|met|spoke to|call with)\s+([A-Za-z\.\s]+?)(?:\s+and|\s+to|\s+discuss|\s+on|\s*[\.,]|$)', target_lower)
                if match:
                    hcp_name = "Dr. " + match.group(1).replace("dr.", "").replace("Dr.", "").strip().title()
                
            sentiment = "Positive"
            if "negative" in target_lower:
                sentiment = "Negative"
            elif "neutral" in target_lower:
                sentiment = "Neutral"
                
            itype = "Meeting"
            if "call" in target_lower:
                itype = "Call"
            elif "email" in target_lower:
                itype = "Email"
                
            # Dynamic topic extraction
            topics = "Discussed clinical products."
            if "discussed" in target_lower:
                try:
                    topics_part = target_text.split("discussed")[-1].strip()
                    if "." in topics_part:
                        topics_part = topics_part.split(".")[0].strip()
                    if "," in topics_part and "sentiment" in topics_part:
                        topics_part = topics_part.split(",")[0].strip()
                    topics = topics_part.strip().capitalize() + "."
                except Exception:
                    pass

            # Dynamic datetime parsing
            import re
            dt_match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', target_lower)
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', target_lower)
            
            dt_val = datetime.now()
            if dt_match:
                try:
                    month = int(dt_match.group(1))
                    day = int(dt_match.group(2))
                    year = int(dt_match.group(3))
                    dt_val = dt_val.replace(year=year, month=month, day=day)
                except Exception:
                    pass
            if time_match:
                try:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    ampm = time_match.group(3)
                    if ampm == 'pm' and hour < 12:
                        hour += 12
                    elif ampm == 'am' and hour == 12:
                        hour = 0
                    dt_val = dt_val.replace(hour=hour, minute=minute)
                except Exception:
                    pass
            datetime_str = dt_val.strftime("%Y-%m-%dT%H:%M")

            # Dynamic materials mapping
            materials_shared = []
            if any(w in target_lower for w in ["brochure", "brochures", "efficacy"]):
                materials_shared.append("Cardioxa Efficacy Brochure")
            if "trial summary" in target_lower:
                materials_shared.append("Cardioxa Phase III Clinical Trial Summary")
            if "guide" in target_lower or "oncology guide" in target_lower:
                materials_shared.append("OncoShield Patient Education Guide")
            if "titration" in target_lower or "booklet" in target_lower:
                materials_shared.append("GlucoSteady Dose Titration Booklet")
                
            samples_distributed = []
            if "starter" in target_lower or "sample" in target_lower:
                samples_distributed.append("Cardioxa 10mg Starter Sample")
            if "trial kit" in target_lower:
                samples_distributed.append("Cardioxa 20mg Trial Kit")
            if "titration titration" in target_lower:
                samples_distributed.append("GlucoSteady 5mg Samples")

            # Dynamic attendees extraction
            attendees = []
            import re
            title_names = re.findall(r'\b(dr\.|dr|rep|nurse|clinic manager)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\b', target_text, re.IGNORECASE)
            for title, name in title_names:
                full_name = f"{title.title()} {name.title()}"
                if full_name not in attendees:
                    attendees.append(full_name)
                    
            if "smith" in target_lower and not any("smith" in a.lower() for a in attendees):
                attendees.append("Dr. John Smith")
            if "jenkins" in target_lower and not any("jenkins" in a.lower() for a in attendees):
                attendees.append("Dr. Sarah Jenkins")
            if "sharma" in target_lower and not any("sharma" in a.lower() for a in attendees):
                attendees.append("Dr. Amit Sharma")
            if "davis" in target_lower and not any("davis" in a.lower() for a in attendees):
                attendees.append("Dr. Emily Davis")
                
            # If a rep is explicitly mentioned, parse and add it
            rep_match = re.search(r'\brep\s+([a-zA-Z]+)\b', target_text, re.IGNORECASE)
            if rep_match:
                rep_name = f"Rep {rep_match.group(1).capitalize()}"
                if rep_name not in attendees:
                    attendees.append(rep_name)
                    
            # Deduplicate subnames
            final_attendees = []
            for name in attendees:
                is_sub = False
                for other in attendees:
                    if name != other and name in other:
                        is_sub = True
                        break
                if not is_sub:
                    final_attendees.append(name)
            attendees = final_attendees

            return json.dumps({
                "hcp_name": hcp_name,
                "type": itype,
                "datetime": datetime_str,
                "attendees": attendees,
                "topics": topics,
                "sentiment": sentiment,
                "outcomes": "HCP expressed strong interest and was receptive to information.",
                "follow_ups": "Follow up next week.",
                "materials_shared": materials_shared,
                "samples_distributed": samples_distributed
            })
            
        elif "wants to make the following edits" in prompt_lower:
            # Check what edits were requested
            topics = "Updated: Discussed Cardioxa and side-effect profiles."
            sentiment = "Neutral"
            if "positive" in target_lower:
                sentiment = "Positive"
            elif "negative" in target_lower:
                sentiment = "Negative"
                
            attendees = ["Dr. John Smith", "Rep Mark"]
            if "collins" in target_lower:
                attendees.append("Dr. Collins")
                
            return json.dumps({
                "type": "Meeting",
                "topics": topics,
                "sentiment": sentiment,
                "outcomes": "Updated: Client was very responsive.",
                "follow_ups": "Send Cardioxa Phase III Clinical Trial Summary and follow up.",
                "attendees": attendees,
                "shared_material_ids": [2],
                "distributed_sample_ids": [3]
            })
            
        elif "recommend the 2-3 most relevant" in prompt_lower or "recommender" in prompt_lower:
            # Return materials and samples
            return json.dumps({
                "recommended_materials": [
                    {"id": 1, "name": "Cardioxa Efficacy Brochure", "reason": "Matches interest in efficacy data"},
                    {"id": 2, "name": "Cardioxa Phase III Clinical Trial Summary", "reason": "Supports efficacy discussion"}
                ],
                "recommended_samples": [
                    {"id": 3, "name": "Cardioxa 10mg Starter Sample", "reason": "Starter pack requested by cardiologist Dr. Smith"}
                ]
            })
        return "{}"
    else:
        # Non-JSON Mode conversational response
        if "history" in target_lower or "past" in target_lower:
            return "Based on past interactions, Dr. John Smith has a highly positive engagement trend. Last month, he discussed clinical trials and was sent the Cardioxa Brochure. He prefers face-to-face meetings and has consistently expressed interest in cardiovascular solutions."
        elif "suggest" in target_lower or "follow-up" in target_lower:
            return "Here are the suggested follow-ups:\n1. Send the Cardioxa Phase III Efficacy Study PDF (High priority).\n2. Schedule a brief 10-minute follow-up call in 2 weeks to discuss sample feedback.\n3. Invite Dr. Smith to the upcoming regional cardiology roundtable event next month."
        elif "recommend" in target_lower:
            return "Based on the topics, I recommend sharing the Cardioxa Clinical Brochure and distributing Cardioxa Starter Samples."
        else:
            return "I've successfully parsed your notes. The form fields have been populated with Positive sentiment for your review. Please click 'Log Interaction' to save it to the database."


# --- Tool 1: Log Interaction Tool ---
class LogInteractionInput(BaseModel):
    text: str = Field(description="Raw text of the interaction note to log")

def log_interaction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    text = state.get("message", "")
    logger.info(f"Running Log Interaction Tool on: {text[:50]}...")
    
    prompt = f"""
    Analyze the following pharmaceutical field representative interaction note and extract the structured details.
    
    Note: "{text}"
    
    Extract these fields and format your response EXACTLY as a JSON object with these keys:
    - hcp_name: string (The name of the doctor or healthcare professional. Include 'Dr.' prefix if appropriate)
    - type: string (One of: "Meeting", "Call", "Email", "Conference", "Other")
    - datetime: string (ISO datetime. If not mentioned, use current time: {datetime.now().isoformat()})
    - attendees: list of strings (Names of participants)
    - topics: string (Summary of clinical/scientific topics discussed)
    - sentiment: string (MUST be one of: "Positive", "Neutral", "Negative")
    - outcomes: string (Summary of outcomes, agreement, next steps agreed upon)
    - follow_ups: string (Specific follow-up actions mentioned)
    - materials_shared: list of strings (Names of documents, brochures, or clinical trial studies shared)
    - samples_distributed: list of strings (Names of drug samples or starter kits distributed)
    
    Ensure the output is valid JSON.
    """
    
    extracted_json = call_groq(prompt, json_mode=True)
    try:
        data = json.loads(extracted_json)
    except Exception as e:
        logger.error(f"Failed to parse JSON: {extracted_json}. Error: {e}")
        data = {}
        
    db = SessionLocal()
    tool_calls = list(state.get("tool_calls_made", []))
    tool_calls.append("Log Interaction Tool")
    
    hcp_id = None
    shared_ids = []
    distributed_ids = []
    
    if data:
        # 1. Resolve HCP
        hcp_name = data.get("hcp_name", "")
        if hcp_name:
            # Search database
            hcp_db = db.query(HCP).filter(HCP.name.ilike(f"%{hcp_name.replace('Dr. ', '').strip()}%")).first()
            if hcp_db:
                hcp_id = hcp_db.id
                data["hcp_name"] = hcp_db.name
            else:
                # If no HCP matched, try to get the first available or create a mock
                first_hcp = db.query(HCP).first()
                if first_hcp:
                    hcp_id = first_hcp.id
                    data["hcp_name"] = first_hcp.name
        
        # 2. Resolve Materials & Samples
        materials_shared = data.get("materials_shared", [])
        for m_name in materials_shared:
            mat = db.query(Material).filter(Material.name.ilike(f"%{m_name}%"), Material.type == "Material").first()
            if mat:
                shared_ids.append(mat.id)
                
        samples_dist = data.get("samples_distributed", [])
        for s_name in samples_dist:
            samp = db.query(Material).filter(Material.name.ilike(f"%{s_name}%"), Material.type == "Sample").first()
            if samp:
                distributed_ids.append(samp.id)
                
        # Format date
        dt_str = data.get("datetime")
        try:
            dt = datetime.fromisoformat(dt_str)
        except Exception:
            dt = datetime.now()
            
        # Do NOT store in DB yet. The user will review the form and click "Log Interaction" to save.
        if hcp_id:
            data["id"] = None  # Ensure ID is null so it's treated as a new/unsaved interaction
            data["hcp_id"] = hcp_id
            data["shared_material_ids"] = shared_ids
            data["distributed_sample_ids"] = distributed_ids
    
    db.close()
    
    return {
        "extracted_data": data,
        "parsed_form_data": data,
        "tool_calls_made": tool_calls,
        "hcp_id": hcp_id
    }


# --- Tool 2: Edit Interaction Tool ---
class EditInteractionInput(BaseModel):
    interaction_id: int = Field(description="The ID of the interaction to edit")
    edit_instruction: str = Field(description="Natural language instruction of what to modify")

def edit_interaction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    # Extract details
    message = state.get("message", "")
    tool_calls = list(state.get("tool_calls_made", []))
    tool_calls.append("Edit Interaction Tool")
    
    db = SessionLocal()
    
    # Try to find the interaction_id from state or extract it from prompt
    interaction_id = state.get("interaction_id")
    if not interaction_id and state.get("current_form_state"):
        interaction_id = state.get("current_form_state", {}).get("id")
        
    if not interaction_id:
        # Search DB for the latest interaction
        latest = db.query(Interaction).order_by(Interaction.id.desc()).first()
        if latest:
            interaction_id = latest.id
            
    if not interaction_id:
        db.close()
        return {
            "reply": "I couldn't find an active interaction to edit. Please select or create an interaction first.",
            "tool_calls_made": tool_calls
        }
        
    db_interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not db_interaction:
        db.close()
        return {
            "reply": f"Could not find an interaction with ID {interaction_id} to edit.",
            "tool_calls_made": tool_calls
        }
        
    # Get current values
    current_data = {
        "type": db_interaction.type,
        "topics": db_interaction.topics,
        "sentiment": db_interaction.sentiment,
        "outcomes": db_interaction.outcomes,
        "follow_ups": db_interaction.follow_ups,
        "attendees": db_interaction.attendees or []
    }
    
    prompt = f"""
    The current details of the interaction (ID {interaction_id}) are:
    {json.dumps(current_data, indent=2)}
    
    The user wants to make the following edits:
    "{message}"
    
    Resolve these instructions and output a revised JSON object containing the fields to update.
    Only include the fields that are being updated, or output the fully resolved new state.
    
    Return EXACTLY a JSON object with these keys (if updated):
    - type: string (One of: "Meeting", "Call", "Email", "Conference", "Other")
    - topics: string
    - sentiment: string (One of: "Positive", "Neutral", "Negative")
    - outcomes: string
    - follow_ups: string
    - attendees: list of strings
    
    Ensure the output is valid JSON.
    """
    
    edited_json = call_groq(prompt, json_mode=True)
    try:
        updates = json.loads(edited_json)
    except Exception as e:
        logger.error(f"Failed to parse edit JSON: {e}")
        updates = {}
        
    if updates:
        for key, val in updates.items():
            if hasattr(db_interaction, key):
                setattr(db_interaction, key, val)
        db.commit()
        db.refresh(db_interaction)
        
        # Prepare full updated data for frontend sync
        updated_form = {
            "id": db_interaction.id,
            "hcp_id": db_interaction.hcp_id,
            "type": db_interaction.type,
            "topics": db_interaction.topics,
            "sentiment": db_interaction.sentiment,
            "outcomes": db_interaction.outcomes,
            "follow_ups": db_interaction.follow_ups,
            "attendees": db_interaction.attendees,
            "datetime": db_interaction.datetime.isoformat()
        }
    else:
        updated_form = current_data
        
    db.close()
    
    return {
        "parsed_form_data": updated_form,
        "tool_calls_made": tool_calls,
        "interaction_id": interaction_id
    }


# --- Tool 3: Suggest Follow-ups Tool ---
class SuggestFollowUpsInput(BaseModel):
    topics: str = Field(description="Topics discussed in the interaction")
    sentiment: str = Field(description="HCP sentiment")
    specialty: str = Field(description="HCP specialty")

def suggest_follow_ups_node(state: Dict[str, Any]) -> Dict[str, Any]:
    tool_calls = list(state.get("tool_calls_made", []))
    tool_calls.append("Suggest Follow-ups Tool")
    
    form = state.get("current_form_state") or state.get("parsed_form_data") or {}
    topics = form.get("topics", "General drug introduction")
    sentiment = form.get("sentiment", "Neutral")
    hcp_id = form.get("hcp_id") or state.get("hcp_id")
    
    specialty = "Cardiology"
    db = SessionLocal()
    if hcp_id:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if hcp:
            specialty = hcp.specialty
    db.close()
            
    prompt = f"""
    Given the following pharmaceutical interaction details:
    - HCP Specialty: {specialty}
    - Topics Discussed: {topics}
    - HCP Sentiment: {sentiment}
    
    Suggest 3 high-value, specific follow-up actions for the sales representative.
    Format your response as a JSON array of strings under the key "suggested_follow_ups".
    Example response format:
    {{
      "suggested_follow_ups": [
        "Send Clinical Efficacy Brochure",
        "Deliver 10mg Starter Samples",
        "Invite to Cardiology Webinar"
      ]
    }}
    """
    
    res_json = call_groq(prompt, json_mode=True)
    try:
        res_data = json.loads(res_json)
        follow_ups = res_data.get("suggested_follow_ups", [])
    except Exception:
        follow_ups = [
            f"Send {specialty} Clinical Study PDF",
            "Follow up via phone in 7 business days",
            "Deliver Starter Samples next clinic visit"
        ]
        
    return {
        "suggested_follow_ups": follow_ups,
        "tool_calls_made": tool_calls
    }


# --- Tool 4: HCP History / Context Tool ---
class HCPHistoryInput(BaseModel):
    hcp_id: int = Field(description="The ID of the HCP to query history for")

def hcp_history_node(state: Dict[str, Any]) -> Dict[str, Any]:
    tool_calls = list(state.get("tool_calls_made", []))
    tool_calls.append("HCP History/Context Tool")
    
    hcp_id = state.get("hcp_id")
    if not hcp_id and state.get("current_form_state"):
        hcp_id = state.get("current_form_state", {}).get("hcp_id")
        
    db = SessionLocal()
    
    if not hcp_id:
        # Fallback: get the first HCP
        hcp = db.query(HCP).first()
        if hcp:
            hcp_id = hcp.id
        else:
            db.close()
            return {
                "history_summary": "No HCP records found in the database.",
                "tool_calls_made": tool_calls
            }
            
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        db.close()
        return {
            "history_summary": f"HCP with ID {hcp_id} not found.",
            "tool_calls_made": tool_calls
        }
        
    # Get last 5 interactions
    past_interactions = db.query(Interaction).filter(Interaction.hcp_id == hcp_id).order_by(Interaction.datetime.desc()).limit(5).all()
    
    history_list = []
    for pi in past_interactions:
        history_list.append({
            "date": pi.datetime.strftime("%Y-%m-%d"),
            "type": pi.type,
            "sentiment": pi.sentiment,
            "topics": pi.topics,
            "outcomes": pi.outcomes
        })
        
    db.close()
    
    if not history_list:
        summary = f"No past interactions logged for {hcp.name}. This is a new engagement."
    else:
        prompt = f"""
        Summarize the engagement history and sentiment trend of the following HCP:
        Name: {hcp.name}
        Specialty: {hcp.specialty}
        
        Past interactions:
        {json.dumps(history_list, indent=2)}
        
        Write a concise, professional summary (2-3 sentences) detailing:
        1. Overall sentiment trend (e.g. positive, declining, stable).
        2. Dominant themes or topics discussed previously.
        3. A quick tip for the rep's next interaction based on this history.
        """
        summary = call_groq(prompt, json_mode=False)
        
    return {
        "history_summary": summary,
        "tool_calls_made": tool_calls,
        "hcp_id": hcp_id
    }


# --- Tool 5: Materials/Sample Recommender Tool ---
class MaterialsRecommenderInput(BaseModel):
    topics: str = Field(description="Topics discussed during the interaction")
    specialty: str = Field(description="HCP specialty")

def materials_recommender_node(state: Dict[str, Any]) -> Dict[str, Any]:
    tool_calls = list(state.get("tool_calls_made", []))
    tool_calls.append("Materials Recommender Tool")
    
    form = state.get("current_form_state") or state.get("parsed_form_data") or {}
    topics = form.get("topics", "")
    hcp_id = form.get("hcp_id") or state.get("hcp_id")
    
    specialty = "Cardiology"
    db = SessionLocal()
    if hcp_id:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if hcp:
            specialty = hcp.specialty
            
    # Fetch all materials and samples
    all_mats = db.query(Material).all()
    mats_list = [{"id": m.id, "name": m.name, "type": m.type, "description": m.description} for m in all_mats]
    db.close()
    
    prompt = f"""
    Given the following HCP context and discussion topics:
    - HCP Specialty: {specialty}
    - Topics Discussed: {topics}
    
    And the list of available brochures/materials and drug samples:
    {json.dumps(mats_list, indent=2)}
    
    Recommend the 2-3 most relevant Materials (type="Material") and 1-2 relevant Samples (type="Sample").
    Explain why each is recommended.
    Format your response EXACTLY as a JSON object with two keys:
    - "recommended_materials": list of objects containing "id", "name", and "reason"
    - "recommended_samples": list of objects containing "id", "name", and "reason"
    
    Ensure the output is valid JSON.
    """
    
    res_json = call_groq(prompt, json_mode=True)
    try:
        recommendations = json.loads(res_json)
        rec_mats = recommendations.get("recommended_materials", [])
        rec_samps = recommendations.get("recommended_samples", [])
    except Exception:
        # Fallback matching
        rec_mats = [m for m in mats_list if m["type"] == "Material"][:2]
        for m in rec_mats:
            m["reason"] = "Highly relevant to clinical cardiology discussion."
        rec_samps = [m for m in mats_list if m["type"] == "Sample"][:1]
        for s in rec_samps:
            s["reason"] = "Starter sample to evaluate patient tolerance."
            
    return {
        "recommended_materials": rec_mats,
        "recommended_samples": rec_samps,
        "tool_calls_made": tool_calls
    }
