import cv2
import numpy as np

def generate_retro_asset(image_path, output_path):
    # 1. Load the original image from the Portland Quarry trail
    img = cv2.imread(image_path)
    
    # 2. Line Art Tracing (Sobel Filter / Edge Isolation)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY, 9, 2)
    
    # 3. Create Dual-Tone Outrun Remapping Matrix
    # We turn dark tones into deep navy and midtones into hot neon pinks/cyans
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    # Restructure color fields dynamically based on brightness values
    neon_canvas = np.zeros_like(img)
    neon_canvas[v < 85] = [51, 12, 11]       # Deep Midnight Navy (#0B0C10)
    neon_canvas[(v >= 85) & (v < 170)] = [85, 0, 255] # Hot Synth Magenta (#FF0055)
    neon_canvas[v >= 170] = [255, 240, 0]    # Electric Game Cyan (#00F0FF)
    
    # 4. Combine Traced Line Work with Neon Shading
    edges_3ch = cv2.merge([edges, edges, edges])
    final_graphic = cv2.bitwise_and(neon_canvas, edges_3ch)
    
    # 5. Save the processed game-ready asset map
    cv2.imwrite(output_path, final_graphic)
    print(f"Asset pipeline complete! Saved to: {output_path}")

# Example invocation for your workspace
# generate_retro_asset("Assets/DropZone/portland_photo.png", "Assets/Textures/character_sprite.png")
