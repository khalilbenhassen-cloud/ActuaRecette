from PIL import Image
import os

def analyze(path):
    if not os.path.exists(path):
        print(f"File {path} does not exist")
        return
        
    img = Image.open(path)
    width, height = img.size
    print(f"\nAnalyzing {path} ({width}x{height}):")
    
    # Left region: x = 0 to 240
    # Right region: x = 240 to 1200
    left_pixels = []
    right_pixels = []
    
    for y in range(0, height, 10):
        for x in range(0, width, 10):
            color = img.getpixel((x, y))
            # If color is RGBA, take RGB
            if len(color) >= 3:
                rgb = color[:3]
                if x < 240:
                    left_pixels.append(rgb)
                else:
                    right_pixels.append(rgb)
                    
    # Print average color and unique colors
    def avg_color(pixels):
        r = sum(p[0] for p in pixels) // len(pixels)
        g = sum(p[1] for p in pixels) // len(pixels)
        b = sum(p[2] for p in pixels) // len(pixels)
        return (r, g, b)
        
    print(f"  Left region (0-240) average color: {avg_color(left_pixels)}")
    print(f"  Right region (240-1200) average color: {avg_color(right_pixels)}")
    
    # Check if left region contains any non-white/non-bg-app pixels (e.g. text/sidebar buttons)
    # The background is white (255, 255, 255)
    non_white_left = sum(1 for p in left_pixels if p != (255, 255, 255) and p != (248, 250, 252))
    print(f"  Non-background pixels in left region: {non_white_left} / {len(left_pixels)}")

for name in ['dashboard_expanded', 'dashboard_collapsed_narrow', 'dashboard_maximized']:
    analyze(f"C:/Users/hp/.gemini/antigravity/brain/7a7f28f3-fd5e-4847-b8f4-5d95e6215948/{name}.png")
