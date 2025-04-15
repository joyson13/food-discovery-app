from flask import Blueprint, request, jsonify, render_template
from food_assistance_api.database import session
from food_assistance_api.models import Agency, HoursOfOperation, WraparoundService, CultureServed
from sqlalchemy.orm import aliased
from geopy.distance import geodesic
import logging
import json
import requests
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Union
from config import API_KEY
from datetime import datetime

api_blueprint = Blueprint("api", __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# ----------------------------
# Utility Functions
# ----------------------------

def get_lat_lon(address):
    api_key = API_KEY
    
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    
    response = requests.get(url)
    data = response.json()
    
    if data["status"] == "OK":
        location = data["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]
    return None, None

def calculate_distance(lat1, lon1, lat2, lon2):
    return round(geodesic((lat1, lon1), (lat2, lon2)).miles, 2)

def format_time_12hr(time_str):
    if not time_str:
        return None
    try:
        time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
        return time_obj.strftime("%I:%M %p").lstrip("0")
    except Exception as e:
        logging.error(f"Time formatting error: {e}")
        return None

def generate_voice_summary(agencies, day_of_week):
    if not agencies:
        return f"I couldn't find any food sites open on {day_of_week}. Would you like to try a different day?"

    summary = f"I found {len(agencies)} food site{'s' if len(agencies) > 1 else ''} near you for {day_of_week}. "

    for agency in agencies:
        name = agency['name'].split(':')[0].strip()
        address = agency['address'].replace("Attn:", "").strip()
        start_time = format_time_12hr(agency['start_time']) if agency['start_time'] else None
        end_time = format_time_12hr(agency['end_time']) if agency['end_time'] else None


        if start_time and end_time:
            time_phrase = f"open from {start_time} to {end_time}"
        else:
            time_phrase = "operating hours are currently not available"

        summary += f"{name} located at {address}, {time_phrase}. "

    summary += "Would you like directions or to hear more options?"
    return summary

# ----------------------------
# Routes
# ----------------------------

@api_blueprint.route("/", methods=["GET"])
def landing_page():
    return render_template("index.html", api_key=API_KEY)

@api_blueprint.route("/agencies", methods=["GET"])
def get_agencies():
    agencies = session.query(Agency).all()
    agency_list = [{"id": agency.id, "name": agency.name} for agency in agencies]
    return jsonify(agency_list)

@api_blueprint.route("/agencies/<string:agency_id>", methods=["GET"])
def get_agency(agency_id):
    agency = session.query(Agency).filter_by(agency_id=agency_id).first()
    if agency:
        return jsonify({
            "agency_id": agency.agency_id,
            "name": agency.name,
            "type": agency.type,
            "address": agency.address,
            "phone": agency.phone
        })
    return jsonify({"error": "Agency not found"}), 404

@api_blueprint.route("/search", methods=["GET"])
def search_agencies():
    from geopy.geocoders import Nominatim

    address = request.args.get("address")
    radius = float(request.args.get("radius", 5))

    if not address:
        return jsonify({"error": "Address is required"}), 400

    geolocator = Nominatim(user_agent="food_assistance_locator")
    location = geolocator.geocode(address)

    if not location:
        return jsonify({"error": "Location not found"}), 404

    user_coords = (location.latitude, location.longitude)
    agencies = session.query(Agency).all()

    nearby_agencies = []
    for agency in agencies:
        agency_coords = (agency.latitude, agency.longitude)
        distance = geodesic(user_coords, agency_coords).miles
        if distance <= radius:
            nearby_agencies.append({
                "id": agency.id,
                "name": agency.name,
                "latitude": agency.latitude,
                "longitude": agency.longitude,
                "distance": round(distance, 2)
            })

    return jsonify(nearby_agencies)

# ----------------------------
# Expert Query Route (Browser)
# ----------------------------

@api_blueprint.route("/expertquery", methods=["GET"])
def get_filtered_agencies():
    try:
        address = request.args.get('address')
        user_lat, user_lon = get_lat_lon(address)
        day_of_week = request.args.get('day_of_week')
        max_distance = float(request.args.get('max_distance', 5.0))

        agency_alias = aliased(Agency)
        hoop_alias = aliased(HoursOfOperation)
        wrap_alias = aliased(WraparoundService)
        culture_alias = aliased(CultureServed)

        query = session.query(agency_alias, hoop_alias, wrap_alias, culture_alias).\
            join(hoop_alias, agency_alias.agency_id == hoop_alias.agency_id).\
            join(wrap_alias, agency_alias.agency_id == wrap_alias.agency_id).\
            join(culture_alias, agency_alias.agency_id == culture_alias.agency_id)

        all_agencies = query.all()

        agency_map = {}

        for agency, hours, wrap, culture in all_agencies:
            if hours.day_of_week and hours.day_of_week.lower() == day_of_week.lower():
                distance = calculate_distance(user_lat, user_lon, agency.latitude, agency.longitude)
                if distance <= max_distance:
                    aid = agency.agency_id
                    if aid not in agency_map:
                        agency_map[aid] = {
                            "id": aid,
                            "name": agency.name,
                            "type": agency.type,
                            "address": agency.address,
                            "phone": agency.phone,
                            "distance": distance,
                            "day_of_week": hours.day_of_week,
                            "start_time": hours.start_time.isoformat() if hours.start_time else None,
                            "end_time": hours.end_time.isoformat() if hours.end_time else None,
                            "frequency": hours.frequency,
                            "distribution_model": hours.distribution_model,
                            "food_format": hours.food_format,
                            "appointment_only": bool(hours.appointment_only),
                            "pantry_requirements": hours.pantry_requirements,
                            "wraparound_services": set(),
                            "cultures_served": set()
                        }

                    # Accumulate services and cultures
                    if wrap and wrap.service:
                        agency_map[aid]["wraparound_services"].add(wrap.service)
                    if culture and culture.cultures:
                        agency_map[aid]["cultures_served"].add(culture.cultures)

        # Finalize results and convert sets to lists
        result = []
        for agency in agency_map.values():
            agency["wraparound_services"] = list(agency["wraparound_services"])
            agency["cultures_served"] = list(agency["cultures_served"])
            result.append(agency)

        result.sort(key=lambda x: x["distance"])
        return jsonify(result), 200

    except Exception as e:
        logging.error(f"Error in /expertquery: {str(e)}")
        return jsonify({"error": str(e)}), 400


# ----------------------------
# VAPI Tool API Route
# ----------------------------

class ToolCallFunction(BaseModel):
    name: str
    arguments: Union[str, Dict]

class ToolCall(BaseModel):
    id: str
    function: ToolCallFunction

class Message(BaseModel):
    toolCalls: List[ToolCall]

class VapiRequest(BaseModel):
    message: Message

@api_blueprint.route("/vapi_expertquery", methods=["POST"])
def vapi_tool_handler():
    try:
        print("Received tool call from VAPI 1:", request)

        payload = request.get_json(force=True)
        # print("Payload received:", payload)

        data = VapiRequest(**payload)

        for tool_call in data.message.toolCalls:
            if tool_call.function.name == "getFoodSites":
                args = tool_call.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)

                address = args["address"]
                day_of_week = args["day_of_week"]

                # Simulate query string for reuse
                request.args = {
                    "address": address,
                    "day_of_week": day_of_week
                }

                # Get response and status from existing function
                response, status_code = get_filtered_agencies()
                response_data = response.get_json()
                
                summary = generate_voice_summary(response_data, day_of_week.title())

                return jsonify({
                    "results": [{
                        "toolCallId": tool_call.id,
                        "result": summary
                    }]
                }), 200

        return jsonify({"error": "No matching tool call found"}), 400

    except ValidationError as e:
        logging.error(f"Validation error: {e}")
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        logging.error(f"Exception in /vapi_expertquery: {e}")
        return jsonify({"error": str(e)}), 500

