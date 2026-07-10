from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.database import engine, Base, get_db
from app.models import HCP, Material, Interaction, interaction_materials
from app.schemas import (
    HCPResponse, MaterialResponse, InteractionCreate, 
    InteractionUpdate, InteractionResponse, ChatRequest, ChatResponse
)
from app.agent import agent_graph
from app.seed import seed_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(title="AI-First CRM HCP Module API")

# Add CORS Middleware to support React frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to ensure database is created and seeded
@app.on_event("startup")
def startup_event():
    # Create tables
    Base.metadata.create_all(bind=engine)
    # Check if we need to seed
    db = Session(bind=engine)
    need_seeding = False
    try:
        if db.query(HCP).count() == 0:
            need_seeding = True
    finally:
        db.close()
        
    if need_seeding:
        logger.info("Database empty. Seeding demo data...")
        seed_db(drop_tables=False)

# Helper to construct InteractionResponse
def build_interaction_response(db_interaction: Interaction) -> InteractionResponse:
    # Separate materials and samples based on the Material model's type field
    shared = [MaterialResponse.from_orm(m) for m in db_interaction.materials if m.type == "Material"]
    distributed = [MaterialResponse.from_orm(m) for m in db_interaction.materials if m.type == "Sample"]
    
    return InteractionResponse(
        id=db_interaction.id,
        hcp_id=db_interaction.hcp_id,
        hcp=HCPResponse.from_orm(db_interaction.hcp),
        type=db_interaction.type,
        datetime=db_interaction.datetime,
        attendees=db_interaction.attendees or [],
        topics=db_interaction.topics,
        sentiment=db_interaction.sentiment,
        outcomes=db_interaction.outcomes,
        follow_ups=db_interaction.follow_ups,
        shared_materials=shared,
        distributed_samples=distributed
    )

# --- HCP Endpoints ---
@app.get("/api/hcps/search", response_model=List[HCPResponse])
def search_hcps(q: str = Query("", description="Search term for HCP name or specialty"), db: Session = Depends(get_db)):
    if not q:
        return db.query(HCP).limit(10).all()
    return db.query(HCP).filter(
        (HCP.name.ilike(f"%{q}%")) | (HCP.specialty.ilike(f"%{q}%"))
    ).limit(10).all()

# --- Materials/Samples Endpoints ---
@app.get("/api/materials/search", response_model=List[MaterialResponse])
def search_materials(q: str = Query("", description="Search term for material/sample name"), db: Session = Depends(get_db)):
    if not q:
        return db.query(Material).limit(10).all()
    return db.query(Material).filter(Material.name.ilike(f"%{q}%")).limit(10).all()

# --- Interaction Endpoints ---
@app.post("/api/interactions", response_model=InteractionResponse)
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    # Verify HCP exists
    hcp = db.query(HCP).filter(HCP.id == payload.hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")
        
    db_interaction = Interaction(
        hcp_id=payload.hcp_id,
        type=payload.type,
        datetime=payload.datetime,
        attendees=payload.attendees,
        topics=payload.topics,
        sentiment=payload.sentiment,
        outcomes=payload.outcomes,
        follow_ups=payload.follow_ups
    )
    
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    
    # Associate materials and samples
    for m_id in payload.shared_material_ids:
        db.execute(interaction_materials.insert().values(interaction_id=db_interaction.id, material_id=m_id, relation_type="shared"))
    for s_id in payload.distributed_sample_ids:
        db.execute(interaction_materials.insert().values(interaction_id=db_interaction.id, material_id=s_id, relation_type="distributed"))
        
    db.commit()
    db.refresh(db_interaction)
    
    return build_interaction_response(db_interaction)

@app.put("/api/interactions/{id}", response_model=InteractionResponse)
def update_interaction(id: int, payload: InteractionUpdate, db: Session = Depends(get_db)):
    db_interaction = db.query(Interaction).filter(Interaction.id == id).first()
    if not db_interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
        
    update_data = payload.dict(exclude_unset=True)
    
    # Exclude relations for special handling
    shared_material_ids = update_data.pop("shared_material_ids", None)
    distributed_sample_ids = update_data.pop("distributed_sample_ids", None)
    
    # Update simple fields
    for key, value in update_data.items():
        setattr(db_interaction, key, value)
        
    # Update relations if provided
    if shared_material_ids is not None or distributed_sample_ids is not None:
        # Delete existing relations first
        db.execute(interaction_materials.delete().where(interaction_materials.c.interaction_id == id))
        db.commit()
        
        if shared_material_ids:
            for m_id in shared_material_ids:
                db.execute(interaction_materials.insert().values(interaction_id=id, material_id=m_id, relation_type="shared"))
        if distributed_sample_ids:
            for s_id in distributed_sample_ids:
                db.execute(interaction_materials.insert().values(interaction_id=id, material_id=s_id, relation_type="distributed"))
                
    db.commit()
    db.refresh(db_interaction)
    
    return build_interaction_response(db_interaction)

@app.get("/api/interactions/{id}", response_model=InteractionResponse)
def get_interaction(id: int, db: Session = Depends(get_db)):
    db_interaction = db.query(Interaction).filter(Interaction.id == id).first()
    if not db_interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return build_interaction_response(db_interaction)

@app.get("/api/interactions", response_model=List[InteractionResponse])
def get_interactions(db: Session = Depends(get_db)):
    interactions = db.query(Interaction).order_by(Interaction.datetime.desc()).all()
    return [build_interaction_response(i) for i in interactions]


# --- LangGraph Agent Chat Endpoint ---
@app.post("/api/agent/chat", response_model=ChatResponse)
def agent_chat(payload: ChatRequest):
    logger.info(f"Agent received message: {payload.message}")
    
    # Prepare initial state for LangGraph
    initial_state = {
        "message": payload.message,
        "history": [{"role": m.role, "content": m.content} for m in payload.history],
        "current_form_state": payload.current_form_state,
        "next_node": "",
        "intent": "",
        "tool_calls_made": [],
        "hcp_id": payload.current_form_state.get("hcp_id") if payload.current_form_state else None,
        "interaction_id": payload.current_form_state.get("id") if payload.current_form_state else None,
        "extracted_data": None,
        "history_summary": None,
        "suggested_follow_ups": [],
        "recommended_materials": [],
        "recommended_samples": [],
        "reply": "",
        "parsed_form_data": None
    }
    
    try:
        # Run LangGraph Agent workflow
        final_state = agent_graph.invoke(initial_state)
        
        # Format the response
        reply = final_state.get("reply", "I've processed your request.")
        parsed_form = final_state.get("parsed_form_data") or final_state.get("extracted_data")
        tool_calls = final_state.get("tool_calls_made", [])
        suggested_follow_ups = final_state.get("suggested_follow_ups", [])
        
        # Enrich suggested follow-ups: if none generated, fall back to what's in state
        if not suggested_follow_ups and parsed_form and parsed_form.get("follow_ups"):
            suggested_follow_ups = [parsed_form.get("follow_ups")]
            
        return ChatResponse(
            reply=reply,
            parsed_form_data=parsed_form,
            tool_calls=tool_calls,
            suggested_follow_ups=suggested_follow_ups
        )
    except Exception as e:
        logger.error(f"Error in LangGraph Agent execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent runtime error: {str(e)}")
