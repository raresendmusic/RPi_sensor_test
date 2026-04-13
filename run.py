from flask import Flask, request, render_template_string, redirect, url_for
import os
import subprocess 
import time
import threading
import cv2
import numpy as np
import re
import sqlite3

app = Flask(__name__)

DB_NAME = "plant_monitor.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plant_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                camera_id INTEGER,
                file_size_kb REAL,
                file_path TEXT NOT NULL,
                ndvi_value REAL
            )
        ''')
        conn.commit()
init_db()

# Set up folders
os.makedirs('static', exist_ok=True)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Separate paths for Camera 1 and Camera 2
PHOTO_PATH_1 = "static/cam1_image.jpg"
PHOTO_PATH_2 = "static/cam2_image.jpg"
NDVI_PATH_1 = "static/cam1_ndvi.jpg"
NDVI_PATH_2 = "static/cam2_ndvi.jpg"

script_output = None  
sensor_ndvi = None   
capture_interval = 0  
last_capture_time = 0

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>PlantPi Remote - Dual Camera</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    
    {% if current_interval > 0 %}
        <meta http-equiv="refresh" content="{{ current_interval }}">
    {% endif %}
    
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 30px; background-color: #f4f4f9; }
        button { padding: 15px 30px; font-size: 20px; color: white; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 5px; }
        .btn-green { background-color: #28a745; }
        .btn-green:hover { background-color: #218838; }
        .btn-blue { background-color: #007bff; }
        .btn-blue:hover { background-color: #0056b3; }
        .btn-teal { background-color: #17a2b8; padding: 10px 20px; font-size: 16px; }
        .btn-teal:hover { background-color: #138496; }
        
        select { padding: 10px; font-size: 16px; border-radius: 5px; margin-right: 10px; }
        
        .controls-container { background-color: #fff; padding: 20px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
        
        /* New styling for the action row to put buttons and NDVI side-by-side */
        .action-row { display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 15px; }
        .sensor-display { font-size: 24px; font-weight: bold; background-color: #e9ecef; padding: 15px 25px; border-radius: 8px; border-left: 5px solid #28a745; margin: 5px; }
        
        /* Layout for the cameras */
        .camera-section { margin-top: 30px; padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .image-container { display: flex; justify-content: center; flex-wrap: wrap; gap: 20px; margin-top: 10px; }
        .image-box { max-width: 45%; }
        img { max-width: 100%; border: 3px solid #ddd; border-radius: 10px; }
        
        .result-box {
            margin: 20px auto; padding: 15px; max-width: 85%;
            background-color: #e9ecef; border-left: 5px solid #007bff;
            border-radius: 5px; text-align: left; font-family: monospace;
            white-space: pre-wrap; 
        }
    </style>
</head>
<body>
    <h1>PlantPi Dual Camera Control</h1>
    
    <div class="controls-container">
        <form action="/set_interval" method="POST" style="margin-bottom: 20px;">
            <label for="interval"><b>Auto-Capture Interval:</b></label><br><br>
            <select name="interval" id="interval">
                <option value="0" {% if current_interval == 0 %}selected{% endif %}>Off (Manual Only)</option>
                <option value="10" {% if current_interval == 10 %}selected{% endif %}>Every 10 Seconds</option>
                <option value="30" {% if current_interval == 30 %}selected{% endif %}>Every 30 Seconds</option>
                <option value="60" {% if current_interval == 60 %}selected{% endif %}>Every 1 Minute</option>
                <option value="300" {% if current_interval == 300 %}selected{% endif %}>Every 5 Minutes</option>
                <option value="600" {% if current_interval == 600 %}selected{% endif %}>Every 10 Minutes</option>
            </select>
            <button type="submit" class="btn-blue" style="padding: 10px 20px; font-size: 16px;">Set Auto-Capture</button>
        </form>

        <hr style="border: 1px solid #eee; margin: 20px 0;">

        <div class="action-row">
            <form action="/capture" method="POST" style="margin: 0;">
                <button type="submit" class="btn-green">TAKE PHOTOS NOW</button>
            </form>
            
            <form action="/generate_ndvi" method="POST" style="margin: 0;">
                <button type="submit" class="btn-teal">CALCULATE NDVI (BOTH)</button>
            </form>
            
            <form action="/database" method="GET" style="margin: 0;">
                <button type="submit" class="btn-blue" style="background-color: #6f42c1;">VIEW DATABASE</button>
            </form>
            
            {% if sensor_ndvi %}
            <div class="sensor-display">
                Sensor NDVI: {{ sensor_ndvi }}
            </div>
            {% endif %}
        </div>
    </div>
    
    {% if script_output %}
        <div class="result-box">
            <b>Full Sensor Output:</b><br>
            {{ script_output }}
        </div>
    {% endif %}

    <div class="camera-section">
        <h2>Camera 1</h2>
        {% if cam1_exists %}
            <div class="image-container">
                <div class="image-box">
                    <h3>Original</h3>
                    <img src="{{ url_for('static', filename=cam1_filename) }}?v={{ timestamp }}" alt="Cam 1 Photo">
                </div>
                {% if ndvi1_exists %}
                <div class="image-box">
                    <h3>NDVI Output</h3>
                    <img src="{{ url_for('static', filename='cam1_ndvi.jpg') }}?v={{ timestamp }}" alt="Cam 1 NDVI">
                </div>
                {% endif %}
            </div>
        {% else %}
            <p style="color: gray;">No image captured yet for Camera 1.</p>
        {% endif %}
    </div>

    <div class="camera-section">
        <h2>Camera 2</h2>
        {% if cam2_exists %}
            <div class="image-container">
                <div class="image-box">
                    <h3>Original</h3>
                    <img src="{{ url_for('static', filename=cam2_filename) }}?v={{ timestamp }}" alt="Cam 2 Photo">
                </div>
                {% if ndvi2_exists %}
                <div class="image-box">
                    <h3>NDVI Output</h3>
                    <img src="{{ url_for('static', filename='cam2_ndvi.jpg') }}?v={{ timestamp }}" alt="Cam 2 NDVI">
                </div>
                {% endif %}
            </div>
        {% else %}
            <p style="color: gray;">No image captured yet for Camera 2.</p>
        {% endif %}
    </div>

</body>
</html>
"""

DATABASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Database - PlantPi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 30px; background-color: #f4f4f9; }
        .btn-blue { background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; margin-bottom: 20px;}
        .btn-blue:hover { background-color: #0056b3; }
        .btn-green { background-color: #28a745; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .btn-green:hover { background-color: #218838; }
        table { width: 90%; margin: 0 auto; border-collapse: collapse; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: center; }
        th { background-color: #343a40; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        tr:hover { background-color: #e9ecef; }
    </style>
</head>
<body>
    <h1>PlantPi Database Records</h1>
    <a href="/" class="btn-blue">&larr; Back to Live Cameras</a>
    
    <table>
        <tr>
            <th>ID</th>
            <th>Date / Time</th>
            <th>Camera</th>
            <th>Size (KB)</th>
            <th>NDVI</th>
            <th>Action</th>
        </tr>
        {% for row in rows %}
        <tr>
            <td>{{ row['id'] }}</td>
            <td>{{ row['timestamp'] }}</td>
            <td>Cam {{ row['camera_id'] }}</td>
            <td>{{ "%.1f"|format(row['file_size_kb']) }}</td>
            <td>{{ row['ndvi_value'] if row['ndvi_value'] != None else 'N/A' }}</td>
            <td><a href="/view/{{ row['id'] }}" class="btn-green">View Photo</a></td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

VIEW_PHOTO_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>View Photo #{{ row['id'] }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 30px; background-color: #f4f4f9; }
        .btn-blue { background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; margin-bottom: 20px;}
        .btn-blue:hover { background-color: #0056b3; }
        .info-box { background: white; padding: 15px; border-radius: 8px; display: inline-block; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        img { max-width: 90%; border: 4px solid #ddd; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <h1>Viewing Record #{{ row['id'] }}</h1>
    <a href="/database" class="btn-blue">&larr; Back to Database</a>
    
    <br>
    <div class="info-box">
        <strong>Time:</strong> {{ row['timestamp'] }} &nbsp;|&nbsp; 
        <strong>Camera:</strong> {{ row['camera_id'] }} &nbsp;|&nbsp; 
        <strong>NDVI:</strong> {{ row['ndvi_value'] if row['ndvi_value'] != None else 'N/A' }}
    </div>
    <br>
    
    <img src="/{{ row['file_path'] }}" alt="Plant Photo">
</body>
</html>
"""

def perform_capture():
    global script_output, sensor_ndvi
    
    ts = time.strftime("%Y%m%d_%H%M%S")

    cam1_path = f"static/cam1_{ts}.jpg"
    cam2_path = f"static/cam2_{ts}.jpg"
    subprocess.run(["rpicam-still", "--camera", "0", "-o", cam1_path, "-n", "-t", "1000"])
    subprocess.run(["rpicam-still", "--camera", "1", "-o", cam2_path, "-n", "-t", "1000"])
    
    # 3. Get NDVI value from sensor script
    try:
        result = subprocess.run(["python3", "/home/plantpi/Plantpi/gpio_test.py"], capture_output=True, text=True, timeout=10)
        script_output = result.stdout
        match = re.search(r'NDVI:\s*([0-9.-]+)', script_output)
        if match:
            sensor_ndvi = match.group(1)
        else:
            sensor_ndvi = "N/A"
    except subprocess.TimeoutExpired:
        script_output = "Error: Sensor script took too long."
        sensor_ndvi = "Error"
    except Exception as e:
        script_output = f"Error running script: {e}"
        sensor_ndvi = "Error"

    # 4. Parse NDVI for the database (convert to float, or None if invalid)
    db_ndvi = None
    try:
        # Check if we have a valid number string to convert
        if sensor_ndvi and sensor_ndvi not in ("N/A", "Error"):
            db_ndvi = float(sensor_ndvi)
    except ValueError:
        db_ndvi = None # Will be saved as NULL in SQLite

    # 5. Log everything into the SQLite database
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        if os.path.exists(cam1_path):
            size1_kb = os.path.getsize(cam1_path) / 1024.0
            cursor.execute('''INSERT INTO plant_images 
                              (camera_id, file_size_kb, file_path, ndvi_value) 
                              VALUES (?, ?, ?, ?)''', 
                           (1, size1_kb, cam1_path, db_ndvi))
            
        if os.path.exists(cam2_path):
            size2_kb = os.path.getsize(cam2_path) / 1024.0
            cursor.execute('''INSERT INTO plant_images 
                              (camera_id, file_size_kb, file_path, ndvi_value) 
                              VALUES (?, ?, ?, ?)''', 
                           (2, size2_kb, cam2_path, db_ndvi))
        conn.commit()
    
    try:
        # Added a 10-second timeout as a safety net just in case the sensor script hangs
        result = subprocess.run(["python3", "../Plantpi/gpio_test.py"], capture_output=True, text=True, timeout=10)
        script_output = result.stdout
        
        # Use Regular Expressions (re) to find the "NDVI: [number]" line in the script output
        match = re.search(r'NDVI:\s*([0-9.-]+)', script_output)
        if match:
            sensor_ndvi = match.group(1)
        else:
            sensor_ndvi = "N/A"
            
    except subprocess.TimeoutExpired:
        script_output = "Error: Sensor script took too long to run (is there a 'while True' loop?)."
        sensor_ndvi = "Error"
    except Exception as e:
        script_output = f"Error running script: {e}"
        sensor_ndvi = "Error"

def background_capture_loop():
    global last_capture_time
    while True:
        if capture_interval > 0:
            current_time = time.time()
            if current_time - last_capture_time >= capture_interval:
                perform_capture()
                last_capture_time = time.time()
        time.sleep(1)

threading.Thread(target=background_capture_loop, daemon=True).start()

@app.route("/")
def index():
    cam1_filename = ""
    cam2_filename = ""
    
    # 1. Ask the database for the newest photos
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get newest Cam 1 photo
        cursor.execute("SELECT file_path FROM plant_images WHERE camera_id = 1 ORDER BY timestamp DESC LIMIT 1")
        row1 = cursor.fetchone()
        if row1: 
            # We strip 'static/' from the front because url_for('static', ...) adds it automatically
            cam1_filename = row1['file_path'].replace('static/', '')
            
        # Get newest Cam 2 photo
        cursor.execute("SELECT file_path FROM plant_images WHERE camera_id = 2 ORDER BY timestamp DESC LIMIT 1")
        row2 = cursor.fetchone()
        if row2: 
            cam2_filename = row2['file_path'].replace('static/', '')

    # 2. Verify the files actually exist on the SD card
    cam1_exists = bool(cam1_filename and os.path.exists(f"static/{cam1_filename}"))
    cam2_exists = bool(cam2_filename and os.path.exists(f"static/{cam2_filename}"))
    
    ndvi1_exists = os.path.exists(NDVI_PATH_1)
    ndvi2_exists = os.path.exists(NDVI_PATH_2)
    timestamp = int(time.time())
    
    return render_template_string(
        HTML_TEMPLATE, 
        cam1_exists=cam1_exists, 
        cam2_exists=cam2_exists,
        cam1_filename=cam1_filename,  # Passing the dynamic name to HTML
        cam2_filename=cam2_filename,  # Passing the dynamic name to HTML
        ndvi1_exists=ndvi1_exists,
        ndvi2_exists=ndvi2_exists,
        timestamp=timestamp, 
        script_output=script_output,
        sensor_ndvi=sensor_ndvi,
        current_interval=capture_interval
    )


@app.route("/set_interval", methods=["POST"])
def set_interval():
    global capture_interval, last_capture_time
    try:
        capture_interval = int(request.form.get("interval", 0))
        if capture_interval > 0:
            last_capture_time = 0 
    except ValueError:
        capture_interval = 0
        
    return redirect(url_for('index'))

@app.route("/capture", methods=["POST"])
def capture_photo():
    perform_capture()
    return redirect(url_for('index'))

def process_ndvi(input_path, output_path):
    if not os.path.exists(input_path):
        return
        
    image = cv2.imread(input_path)
    shape = image.shape
    height = int(shape[0] / 2)
    width = int(shape[1] / 2)
    image = cv2.resize(image, (width, height))
    image = image.astype(np.float32) / 255.0
    blue, green, red = cv2.split(image)
    
    ndvi = (red - blue) / (red + blue + 1e-6)
    ndvi_normalized = cv2.normalize(ndvi, None, 0, 255, cv2.NORM_MINMAX)
    ndvi_normalized = ndvi_normalized.astype(np.uint8)
    ndvi_color = cv2.applyColorMap(ndvi_normalized, cv2.COLORMAP_JET)
    
    cv2.imwrite(output_path, ndvi_color)

@app.route("/generate_ndvi", methods=["POST"])
def generate_ndvi():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT file_path FROM plant_images WHERE camera_id = 1 ORDER BY timestamp DESC LIMIT 1")
        row1 = cursor.fetchone()
        if row1:
            process_ndvi(row1['file_path'], NDVI_PATH_1)

        cursor.execute("SELECT file_path FROM plant_images WHERE camera_id = 2 ORDER BY timestamp DESC LIMIT 1")
        row2 = cursor.fetchone()
        if row2:
            process_ndvi(row2['file_path'], NDVI_PATH_2)
            
    return redirect(url_for('index'))
    
@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return "No file provided", 400
    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    return f"Successfully uploaded {file.filename}!", 200
    
@app.route("/database", methods=["GET"])
def database_view():
    with sqlite3.connect(DB_NAME) as conn:
        # This allows us to access columns by name in the HTML template
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        # Fetch all records, newest first
        cursor.execute("SELECT * FROM plant_images ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        
    return render_template_string(DATABASE_TEMPLATE, rows=rows)

@app.route("/view/<int:image_id>", methods=["GET"])
def view_single_photo(image_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Fetch just the specific row the user clicked on
        cursor.execute("SELECT * FROM plant_images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        
    if row is None:
        return "Error: Image record not found in database.", 404
        
    return render_template_string(VIEW_PHOTO_TEMPLATE, row=row)    
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
