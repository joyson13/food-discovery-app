from flask import Blueprint, render_template, request, jsonify
from food_assistance_api.database import session
from food_assistance_api.models import Agency, HoursOfOperation, WraparoundService, CultureServed
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from sqlalchemy.orm import joinedload
from sqlalchemy import func, text
from database import session
from datetime import datetime
from database import engine
from sqlalchemy.orm import aliased

from config import API_KEY

# Create a Flask Blueprint (modular route handling)
api_blueprint = Blueprint("api", __name__)

def calculate_distance(lat1, lon1, lat2, lon2):
    return round(geodesic((lat1, lon1), (lat2, lon2)).miles, 2)

# Define a route to fetch all agencies
@api_blueprint.route("/agencies", methods=["GET"])
def get_agencies():
    agencies = session.query(Agency).all()
    agency_list = [{"id": agency.id, "name": agency.name} for agency in agencies]
    return jsonify(agency_list)

# Route to fetch a single agency by ID
@api_blueprint.route("/agencies/<string:agency_id>", methods=["GET"])
def get_agency(agency_id):
    agency = session.query(Agency).filter_by(agency_id=agency_id).first()
    if agency:
        return jsonify({"agency id": agency.agency_id, "name": agency.name, "type": agency.type, "Shipping address": agency.address, "phone": agency.phone})
    return jsonify({"error": "Agency not found"}), 404

# Landing Page Route
@api_blueprint.route("/", methods=["GET"])
def landing_page():
    return render_template("index.html", api_key=API_KEY)  # Render landing page

# Search API: Find agencies near a given location
@api_blueprint.route("/search", methods=["GET"])
def search_agencies():
    address = request.args.get("address")  # Get address or ZIP code
    radius = float(request.args.get("radius", 5))  # Default radius = 5 miles

    if not address:
        return jsonify({"error": "Address is required"}), 400

    # Convert address to lat/lon
    geolocator = Nominatim(user_agent="food_assistance_locator")
    location = geolocator.geocode(address)

    if not location:
        return jsonify({"error": "Location not found"}), 404

    user_coords = (location.latitude, location.longitude)

    # Query agencies from database
    agencies = session.query(Agency).all()
    nearby_agencies = []

    for agency in agencies:
        agency_coords = (agency.latitude, agency.longitude)
        distance = geodesic(user_coords, agency_coords).miles  # Calculate distance

        if distance <= radius:
            nearby_agencies.append({
                "id": agency.id,
                "name": agency.name,
                "latitude": agency.latitude,
                "longitude": agency.longitude,
                "distance": round(distance, 2)
            })

    return jsonify(nearby_agencies)

# Query API: Query agencies based on user preferences
@api_blueprint.route("/expertquery", methods=["GET"])
def get_filtered_agencies():

    try:
        # Extract query parameters from request
        user_lat = float(request.args.get('user_lat'))
        user_lon = float(request.args.get('user_lon'))
        day_of_week = request.args.get('day_of_week')
        max_distance = float(request.args.get('max_distance', 5.0))  # Optional with default

        # Aliases for clarity
        agency_alias = aliased(Agency)
        hoop_alias = aliased(HoursOfOperation)
        wrap_alias = aliased(WraparoundService)
        culture_alias = aliased(CultureServed)
        
        query = session.query(agency_alias, hoop_alias, wrap_alias, culture_alias).\
                join(hoop_alias, agency_alias.agency_id == hoop_alias.agency_id).\
                join(wrap_alias, agency_alias.agency_id == wrap_alias.agency_id).\
                join(culture_alias, agency_alias.agency_id == culture_alias.agency_id)

        all_agencies = query.all()
        
        # print hours of operation for debugging
        for agency, hours, wrap, culture in all_agencies:
            if hours.day_of_week == None:
                hours.day_of_week = "None"
            # print(f"Agency: {agency.name}, Hours: {hours.day_of_week}, wraparound: {wrap.service}, culture: {culture.cultures}")
        
        nearby_agencies = []
        for agency, hours, wrap, culture in all_agencies:
            distance = calculate_distance(user_lat, user_lon, agency.latitude, agency.longitude)
            if distance <= max_distance and hours.day_of_week.lower() == day_of_week.lower():
                # print(f"Agency: {agency.name}, Hours: {hours.day_of_week}, wraparound: {wrap.service}, culture: {culture.cultures}")
                nearby_agencies.append(agency)

        for agency in nearby_agencies:
            print(f"Agency: {agency.name}, Hours: {hours.day_of_week}, wraparound: {wrap.service}, culture: {culture.cultures}")

        print(f"Nearby agencies count: {len(nearby_agencies)}")        
        print(f"Unique agencies count: {len(set(nearby_agencies))}")
        
        nearby_agencies = list(set(nearby_agencies))  # Remove duplicates

        print(nearby_agencies)

        filtered_agencies_list = []
        
        for agency in nearby_agencies:
            agency_data = {
                "id": agency.agency_id,
                "name": agency.name,
                "type": agency.type,
                "address": agency.address,
                "phone": agency.phone,
                "distance": calculate_distance(user_lat, user_lon, agency.latitude, agency.longitude),
                "day_of_week": hours.day_of_week,
                "start_time": hours.start_time.isoformat() if hours.start_time else None,
                "end_time": hours.end_time.isoformat() if hours.end_time else None,
                "frequency": hours.frequency,
                "distribution_model": hours.distribution_model,
                "food_format": hours.food_format,
                "appointment_only": bool(hours.appointment_only),
                "pantry_requirements": hours.pantry_requirements,
                "wraparound_services": wrap.service if wrap else None,
                "cultures_served": culture.cultures if culture else None,
            }
            filtered_agencies_list.append(agency_data)

        print(f"Filtered agencies count: {len(filtered_agencies_list)}")
        
        filtered_agencies_list.sort(key=lambda x: x["distance"])

        return jsonify(filtered_agencies_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400