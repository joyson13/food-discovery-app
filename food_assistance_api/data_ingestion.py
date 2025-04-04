import pandas as pd
from sqlalchemy.orm import sessionmaker
from database import engine, init_db, SessionLocal
from models import Agency, WraparoundService, CultureServed, DistributionSite

# Initialize database
init_db()
session = SessionLocal()

# Helper function to load Excel files
def load_excel(file_path):
    return pd.read_excel(file_path, engine='openpyxl')  # `openpyxl` is required for `.xlsx` files

# Load Agencies
agency_data = load_excel("data/CAFB_Markets_HOO.xlsx")
for _, row in agency_data.iterrows():
    agency = session.query(Agency).filter_by(id=row["Agency ID"]).first()
    if not agency:
        agency = Agency(id=row["Agency ID"], name=row["Agency Name"])
        session.add(agency)

# Load Wraparound Services
wraparound_data = load_excel("data/CAFB_Markets_Wraparound_Services.xlsx")
for _, row in wraparound_data.iterrows():
    service = WraparoundService(agency_id=row["Agency ID"], service=row["Wraparound Service"])
    session.add(service)

# Load Cultural Populations Served
culture_data = load_excel("data/CAFB_Markets_Cultures_Served.xlsx")
for _, row in culture_data.iterrows():
    for culture in row["Cultural Populations Served"].split(","):
        culture_entry = CultureServed(agency_id=row["Agency ID"], culture=culture.strip())
        session.add(culture_entry)

# Load Distribution Sites
dist_data = load_excel("data/CAFB_Markets_HOO.xlsx")
for _, row in dist_data.iterrows():
    site = DistributionSite(
        agency_id=row["Agency ID"],
        shipping_address=row["Shipping Address"],
        day_of_week=row["Day of Week"],
        start_time=row["Starting Time"],
        end_time=row["Ending Time"],
        food_format=row.get("Food Format", None),
        distribution_model=row.get("Distribution Models", None)
    )
    session.add(site)

# Commit changes
session.commit()
session.close()
print("✅ Data Ingestion Completed!")
