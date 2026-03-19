import tkinter as tk
from PIL import Image, ImageTk
import subprocess
import os
import cv2
import numpy as np

def take_photo():
    photo_path = "/home/plantpi/Desktop/captured_image.jpg"

    subprocess.run(["rpicam-still", "-o", photo_path, "-n", "--immediate"])

    img = Image.open(photo_path)
    img.thumbnail((400, 300))
    img_tk = ImageTk.PhotoImage(img)

    label_image.config(image=img_tk)
    label_image.image = img_tk
    status_label.config(text="Photo saved to Desktop!")

def take_ndvi_photo():
    image_path = "/home/plantpi/Desktop/captured_image.jpg"
    ndvi_path = "/home/plantpi/Desktop/ndvi_image.jpg"
    if not os.path.exists(image_path):
        status_label.config(text="No image found. Take a photo first.")
        return
    
    image = cv2.imread(image_path)
    shape = image.shape
    height = int(shape[0] / 2)
    width = int(shape[1] / 2)
    image = cv2.resize(image, (width, height))

    image = cv2.resize(image, (width, height))
    # Convert to float
    image = image.astype(np.float32) / 255.0

    # Split channels (OpenCV is BGR)
    blue, green, red = cv2.split(image)

    # NDVI formula (assuming NIR = Red channel for modified camera)
    ndvi = (red - blue) / (red + blue + 1e-6)

    # Normalize NDVI to 0-255
    ndvi_normalized = cv2.normalize(ndvi, None, 0, 255, cv2.NORM_MINMAX)
    ndvi_normalized = ndvi_normalized.astype(np.uint8)

    # Apply NDVI colormap
    ndvi_color = cv2.applyColorMap(ndvi_normalized, cv2.COLORMAP_JET)

    # Show results

    cv2.imwrite(ndvi_path, ndvi_color)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    status_label.config(text="NDVI processed!")

# UI
root = tk.Tk()
root.title("PlantPi Camera Control")
root.geometry("500x500")

title_label = tk.Label(root, text="Pi Camera Interface", font=("Arial", 16))
title_label.pack(pady=10)

btn_snap = tk.Button(
    root,
    text="📸 TAKE PHOTO",
    command=take_photo,
    bg="green",
    fg="white",
    font=("Arial", 12, "bold"),
    height=2,
    width=15
)
btn_snap.pack(pady=10)

# NDVI Button
btn_ndvi = tk.Button(
    root,
    text="🌿 CALCULATE NDVI",
    command=take_ndvi_photo,
    bg="blue",
    fg="white",
    font=("Arial", 12, "bold"),
    height=2,
    width=15
)
btn_ndvi.pack(pady=10)

status_label = tk.Label(root, text="Ready", fg="gray")
status_label.pack()

label_image = tk.Label(
    root,
    text="No image captured yet",
    bg="lightgray",
    width=50,
    height=15
)

label_image.pack(pady=20)

root.mainloop()

