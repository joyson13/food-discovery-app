from flask import Flask
from food_assistance_api.database import init_db  # Database setup
from food_assistance_api.routes import api_blueprint  # Importing routes

# Initialize Flask App
app = Flask(__name__, template_folder="templates")

# Configure database (Example: SQLite)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///food_assistance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database tables
init_db()

# Register API routes from routes.py
app.register_blueprint(api_blueprint)

if __name__ == "__main__":
    app.run(debug=True)  # Start the Flask server
