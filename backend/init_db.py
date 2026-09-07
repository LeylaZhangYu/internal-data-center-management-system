"""Create empty application tables. Use --seed-demo only for local fixture data."""
import sys
from app.core.database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)

if "--seed-demo" in sys.argv:
    from app.services.seed import seed_demo_data
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
    print("Database initialized with demo data.")
else:
    print("Database initialized without demo data.")
