
from flask import Flask, request, render_template_string, redirect, url_for
import os
import subprocess 
import time
import threading
import cv2
import numpy as np
import re

app = Flask(__name__)

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
sensor_ndvi = None    # New variable to hold just the NDVI number
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
                    <img src="{{ url_for('static', filename='cam1_image.jpg') }}?v={{ timestamp }}" alt="Cam 1 Photo">
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
                    <img src="{{ url_for('static', filename='cam2_image.jpg') }}?v={{ timestamp }}" alt="Cam 2 Photo">
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

def perform_capture():
    global script_output, sensor_ndvi
    
    # Capture from Camera 0
    subprocess.run(["rpicam-still", "--camera", "0", "-o", PHOTO_PATH_1, "-n", "--immediate"])
    
    # Capture from Camera 1
    subprocess.run(["rpicam-still", "--camera", "1", "-o", PHOTO_PATH_2, "-n", "--immediate"])
    
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
    cam1_exists = os.path.exists(PHOTO_PATH_1)
    cam2_exists = os.path.exists(PHOTO_PATH_2)
    ndvi1_exists = os.path.exists(NDVI_PATH_1)
    ndvi2_exists = os.path.exists(NDVI_PATH_2)
    timestamp = int(time.time())
    
    return render_template_string(
        HTML_TEMPLATE, 
        cam1_exists=cam1_exists, 
        cam2_exists=cam2_exists,
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
    process_ndvi(PHOTO_PATH_1, NDVI_PATH_1)
    process_ndvi(PHOTO_PATH_2, NDVI_PATH_2)
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
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
