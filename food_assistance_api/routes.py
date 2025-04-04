from flask import Flask, request, jsonify
from sqlalchemy.orm import sessionmaker
from database import engine, SessionLocal
from models import Agency, WraparoundService, CultureServed, DistributionSite

app = Flask(__name__)
session = SessionLocal()

@app.route('/find_food', methods=['GET'])
def find_food():
    query = session.query(DistributionSite)

    # Filters based on user input
    preferred_day = request.args.get("preferred_day")
    if preferred_day:
        query = query.filter(DistributionSite.day_of_week.ilike(f"%{preferred_day}%"))

    preferred_time = request.args.get("preferred_time")
    if preferred_time:
        query = query.filter(
            (DistributionSite.start_time <= preferred_time) & 
            (DistributionSite.end_time >= preferred_time)
        )

    # Execute Query
    results = query.all()
    response = [
        {
            "agency_name": site.agency.name,
            "address": site.shipping_address,
            "day_of_week": site.day_of_week,
            "start_time": site.start_time,
            "end_time": site.end_time,
            "food_format": site.food_format,
            "distribution_model": site.distribution_model
        }
        for site in results
    ]
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
