from flask import Flask
from database import init_db  # Database setup
from routes import api_blueprint  # Importing routes
from flask_cors import CORS

# Initialize Flask App
app = Flask(__name__, template_folder="templates")
CORS(app)

# Configure database (Example: SQLite)
app.config.from_pyfile('config.py')
# Initialize database tables
init_db()

# Register API routes from routes.py
app.register_blueprint(api_blueprint)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
