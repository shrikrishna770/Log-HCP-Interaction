from datetime import datetime, timedelta
from app.database import engine, Base, SessionLocal
from app.models import HCP, Material, Interaction, interaction_materials

def seed_db():
    print("Re-creating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Seeding HCPs...")
        hcp1 = HCP(
            name="Dr. John Smith",
            specialty="Cardiology",
            email="john.smith@cardiologyassociates.com",
            phone="555-0192",
            clinic_address="100 Heartbeat Lane, Suite 400, Boston, MA"
        )
        hcp2 = HCP(
            name="Dr. Sarah Jenkins",
            specialty="Oncology",
            email="sjenkins@metro-oncology.org",
            phone="555-0143",
            clinic_address="202 Chemotherapy Blvd, New York, NY"
        )
        hcp3 = HCP(
            name="Dr. Amit Sharma",
            specialty="Endocrinology",
            email="sharma.amit@endocrinehealth.com",
            phone="555-0177",
            clinic_address="50 Pine Tree Way, Suite 12, Chicago, IL"
        )
        hcp4 = HCP(
            name="Dr. Emily Davis",
            specialty="Pediatrics",
            email="emily.davis@pediatriccare.net",
            phone="555-0188",
            clinic_address="88 Playground Circle, Seattle, WA"
        )
        
        db.add_all([hcp1, hcp2, hcp3, hcp4])
        db.commit()
        
        print("Seeding Materials and Samples...")
        # Cardiology
        m1 = Material(name="Cardioxa Efficacy Brochure", type="Material", description="Brochure outlining Phase III efficacy data for Cardioxa.")
        m2 = Material(name="Cardioxa Phase III Clinical Trial Summary", type="Material", description="Clinical trial details and patient outcomes report.")
        s1 = Material(name="Cardioxa 10mg Starter Sample", type="Sample", description="Starter pack of Cardioxa 10mg tablets (10 count).")
        s2 = Material(name="Cardioxa 20mg Trial Kit", type="Sample", description="Trial kit of Cardioxa 20mg tablets (5 count).")
        
        # Oncology
        m3 = Material(name="OncoShield Patient Education Guide", type="Material", description="Educational booklet on managing side effects during therapy.")
        s3 = Material(name="OncoShield 50mg Sample Pack", type="Sample", description="Patient sample pack of OncoShield 50mg tablets.")
        
        # Endocrinology
        m4 = Material(name="GlucoSteady Dose Titration Booklet", type="Material", description="Guide to safety and titration steps for GlucoSteady.")
        s4 = Material(name="GlucoSteady 5mg Samples", type="Sample", description="Starter sample box of GlucoSteady 5mg.")
        
        db.add_all([m1, m2, s1, s2, m3, s3, m4, s4])
        db.commit()
        
        print("Seeding Past Interactions...")
        # Dr. John Smith past interactions
        int1 = Interaction(
            hcp_id=hcp1.id,
            type="Call",
            datetime=datetime.now() - timedelta(days=14),
            attendees=["Dr. John Smith", "Rep Mark"],
            topics="Initial introduction of Cardioxa and side effect profile.",
            sentiment="Neutral",
            outcomes="Dr. Smith requested clinical literature on long-term safety.",
            follow_ups="Email Phase III trial summary brochure."
        )
        
        int2 = Interaction(
            hcp_id=hcp1.id,
            type="Meeting",
            datetime=datetime.now() - timedelta(days=5),
            attendees=["Dr. John Smith", "Rep Mark", "Clinic Manager Clara"],
            topics="Discussion on Cardioxa clinical trial efficacy compared to standard care.",
            sentiment="Positive",
            outcomes="Dr. Smith agreed to try Cardioxa on 5 patients. Requested starter samples.",
            follow_ups="Deliver starter samples and follow up on patient outcomes next visit."
        )
        
        # Dr. Sarah Jenkins past interactions
        int3 = Interaction(
            hcp_id=hcp2.id,
            type="Meeting",
            datetime=datetime.now() - timedelta(days=20),
            attendees=["Dr. Sarah Jenkins", "Rep Mark"],
            topics="Discussion of OncoShield efficacy in second-line non-small cell lung cancer.",
            sentiment="Positive",
            outcomes="Highly receptive to patient education materials. Will review internally.",
            follow_ups="Send patient guide booklet."
        )
        
        db.add_all([int1, int2, int3])
        db.commit()
        
        # Associate materials with past interactions
        # int1 got Cardioxa Brochure
        db.execute(interaction_materials.insert().values(interaction_id=int1.id, material_id=m1.id, relation_type="shared"))
        # int2 got Cardioxa trial summary and starter samples
        db.execute(interaction_materials.insert().values(interaction_id=int2.id, material_id=m2.id, relation_type="shared"))
        db.execute(interaction_materials.insert().values(interaction_id=int2.id, material_id=s1.id, relation_type="distributed"))
        # int3 got OncoShield patient guide
        db.execute(interaction_materials.insert().values(interaction_id=int3.id, material_id=m3.id, relation_type="shared"))
        
        db.commit()
        print("Database seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
