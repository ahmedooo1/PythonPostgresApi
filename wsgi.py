# This file is not being used currently
# We're using Flask in main.py which is directly compatible with Gunicorn
from main import app

# For local development
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)