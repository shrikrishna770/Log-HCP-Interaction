from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Table, JSON
from sqlalchemy.orm import relationship
from app.database import Base

# Association table for Interaction and Material/Sample
interaction_materials = Table(
    "interaction_materials",
    Base.metadata,
    Column("interaction_id", Integer, ForeignKey("interactions.id", ondelete="CASCADE"), primary_key=True),
    Column("material_id", Integer, ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True),
    # To identify if it was Shared (Material) or Distributed (Sample)
    Column("relation_type", String, default="shared") # "shared" or "distributed"
)

class HCP(Base):
    __tablename__ = "hcps"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    specialty = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=True)
    clinic_address = Column(String, nullable=True)
    
    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")

class Material(Base):
    __tablename__ = "materials"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)  # "Material" or "Sample"
    description = Column(String, nullable=True)

class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)  # "Meeting", "Call", "Email", "Conference", etc.
    datetime = Column(DateTime, nullable=False)
    attendees = Column(JSON, default=list)  # List of names/strings
    topics = Column(Text, nullable=True)
    sentiment = Column(String, nullable=False)  # "Positive", "Neutral", "Negative"
    outcomes = Column(Text, nullable=True)
    follow_ups = Column(Text, nullable=True)
    
    hcp = relationship("HCP", back_populates="interactions")
    materials = relationship(
        "Material",
        secondary=interaction_materials,
        backref="interactions"
    )
