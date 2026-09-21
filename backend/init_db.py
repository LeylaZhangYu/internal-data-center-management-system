"""Create empty application tables. Use --seed-demo only for local fixture data."""
import sys
from app.core.database import Base, SessionLocal, engine
from app.core.schema_updates import ensure_optional_device_fields
from app.models import models  # Register tables even when demo data is disabled.

Base.metadata.create_all(bind=engine)
ensure_optional_device_fields(engine)

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
