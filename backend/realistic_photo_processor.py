"""
Realistic Photo Processor for Deforestation Detection

This module processes satellite images to look like realistic photographs
and creates interactive maps showing before/after comparisons.
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import folium
from io import BytesIO

class RealisticPhotoProcessor:
    """Process satellite images to look like realistic photographs."""
    
    def __init__(self):
        """Initialize the realistic photo processor."""
        self.base_dir = Path('deforestation_maps')
        self.images_dir = self.base_dir / 'images'
        self.realistic_dir = self.images_dir / 'realistic'
        
        # Create directories if they don't exist
        self.realistic_dir.mkdir(parents=True, exist_ok=True)
    
    def enhance_image_realism(self, image_path: str) -> str:
        """
        Enhance a satellite image to look like a realistic photograph.
        
        Args:
            image_path: Path to the input satellite image
            
        Returns:
            Path to the enhanced realistic image
        """
        try:
            # Load the image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Apply realistic enhancements
                # 1. Enhance contrast for more natural look
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)
                
                # 2. Enhance color saturation for more vivid colors
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.2)
                
                # 3. Slightly enhance brightness for daylight effect
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.1)
                
                # 4. Apply slight sharpening for photo-like quality
                img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
                
                # 5. Add very subtle blur for natural camera effect
                img = img.filter(ImageFilter.GaussianBlur(radius=0.3))
                
                # Create output filename
                input_path = Path(image_path)
                output_filename = f"realistic_{input_path.name}"
                output_path = self.realistic_dir / output_filename
                
                # Save the enhanced image
                img.save(output_path, 'PNG', quality=95)
                
                print(f"    📷 Created realistic photo: {output_filename}")
                return str(output_path)
                
        except Exception as e:
            print(f"    ❌ Error enhancing {image_path}: {e}")
            return None
    
    def image_to_base64(self, image_path: str) -> Optional[str]:
        """Convert image to base64 string for HTML embedding."""
        try:
            with open(image_path, 'rb') as img_file:
                img_data = img_file.read()
                b64_data = base64.b64encode(img_data).decode('utf-8')
                return b64_data
        except Exception as e:
            print(f"Error converting image to base64: {e}")
            return None
    
    def create_realistic_photo_map(self) -> Tuple[Optional[str], int]:
        """
        Create an interactive map with realistic satellite photographs.
        
        Returns:
            Tuple of (output file path, number of processed locations)
        """
        try:
            # Load coordinates and report data
            coords_file = 'deforestation_maps/deforestation_coordinates.json'
            report_file = 'deforestation_maps/deforestation_report.json'
            
            with open(coords_file, 'r') as f:
                coordinates_data = json.load(f)
            
            with open(report_file, 'r') as f:
                report = json.load(f)
            
            print("📷 Processing existing satellite images to look REALISTIC...")
            print("🎨 Making them look like natural photographs anyone would recognize...")
            
            # Check for existing images
            available_images = []
            for i in range(1, 6):  # Check for up to 5 locations
                before_path = self.images_dir / f'before_{i}.png'
                after_path = self.images_dir / f'after_{i}.png'
                
                if before_path.exists() and after_path.exists():
                    location = coordinates_data[i-1] if i-1 < len(coordinates_data) else {
                        'latitude': -20.1667 + (i-1) * 0.01,
                        'longitude': 28.5833 + (i-1) * 0.01
                    }
                    
                    print(f"📍 Found real satellite images {i}: making them look realistic...")
                    
                    # Create realistic versions
                    print(f"    📷 Making {before_path.name} look like a realistic photograph...")
                    realistic_before = self.enhance_image_realism(str(before_path))
                    
                    print(f"    📷 Making {after_path.name} look like a realistic photograph...")
                    realistic_after = self.enhance_image_realism(str(after_path))
                    
                    if realistic_before and realistic_after:
                        available_images.append({
                            'location': location,
                            'before': realistic_before,
                            'after': realistic_after,
                            'number': i
                        })
                        print(f"    ✅ Successfully processed realistic photos for location {i}")
            
            if not available_images:
                print("❌ No satellite images found to process")
                return None, 0
            
            print(f"📷 Processed {len(available_images)} locations with realistic-looking photographs")
            
            # Create map centered on analysis region
            center_lat = report['coordinates']['south'] + (report['coordinates']['north'] - report['coordinates']['south']) / 2
            center_lon = report['coordinates']['west'] + (report['coordinates']['east'] - report['coordinates']['west']) / 2
            
            # Create map with multiple tile layers like the original deforestation map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=12,
                tiles='OpenStreetMap'
            )
            
            # Add satellite imagery layer
            satellite_layer = folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satellite',
                overlay=False,
                control=True
            )
            satellite_layer.add_to(m)
            
            # Add NDVI overlay layers from Google Earth Engine (like the original deforestation map)
            print("🌍 Adding NDVI overlay layers...")
            
            # NDVI Before layer
            print("  📊 Adding NDVI Before layer...")
            ndvi_before_layer = folium.TileLayer(
                tiles='https://earthengine.googleapis.com/v1/projects/trans-scheme-463112-q8/maps/b525432bc1fb4cad4cb1c2344c10285d-21eede5b391f25bbcdc08862c0496511/tiles/{z}/{x}/{y}',
                attr='Google Earth Engine',
                name='NDVI Before',
                overlay=True,
                control=True,
                opacity=0.7
            )
            ndvi_before_layer.add_to(m)
            
            # NDVI After layer  
            print("  📊 Adding NDVI After layer...")
            ndvi_after_layer = folium.TileLayer(
                tiles='https://earthengine.googleapis.com/v1/projects/trans-scheme-463112-q8/maps/0ebda117cf572efbbe32421699dce3b1-fffded86e3f11ffd9730e6738cdb53cc/tiles/{z}/{x}/{y}',
                attr='Google Earth Engine',
                name='NDVI After',
                overlay=True,
                control=True,
                opacity=0.7
            )
            ndvi_after_layer.add_to(m)
            
            # NDVI Change layer (Red = Deforestation)
            print("  📊 Adding NDVI Change layer...")
            ndvi_change_layer = folium.TileLayer(
                tiles='https://earthengine.googleapis.com/v1/projects/trans-scheme-463112-q8/maps/5a1d7fe4ce6c15ca91c32773ba40ccfb-dd7cdc1f66801e168ce317275b586ad6/tiles/{z}/{x}/{y}',
                attr='Google Earth Engine',
                name='NDVI Change (Red=Deforestation)',
                overlay=True,
                control=True,
                opacity=0.8
            )
            ndvi_change_layer.add_to(m)
            
            print("✅ Successfully added all NDVI overlay layers")
            
            # Add NDVI legend to the map
            ndvi_legend_html = '''
            <div style="position: fixed; 
                        top: 10px; left: 10px; width: 220px; height: auto; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:14px; padding: 10px; border-radius: 5px;
                        box-shadow: 0 0 15px rgba(0,0,0,0.2);">
                <h4 style="margin-top:0; text-align:center; color:#2E8B57;">🌿 NDVI Legend</h4>
                <p style="margin: 5px 0;"><span style="color:#8B0000; font-weight:bold;">■</span> 0.0-0.2: Bare soil/rock</p>
                <p style="margin: 5px 0;"><span style="color:#FF4500; font-weight:bold;">■</span> 0.2-0.3: Sparse vegetation</p>
                <p style="margin: 5px 0;"><span style="color:#FFD700; font-weight:bold;">■</span> 0.3-0.4: Moderate vegetation</p>
                <p style="margin: 5px 0;"><span style="color:#9ACD32; font-weight:bold;">■</span> 0.4-0.6: Dense vegetation</p>
                <p style="margin: 5px 0;"><span style="color:#228B22; font-weight:bold;">■</span> 0.6-1.0: Very dense vegetation</p>
                <hr style="margin: 10px 0;">
                <p style="margin: 5px 0; font-size:12px; color:#FF0000; font-weight:bold;">🔴 Red areas = Deforestation</p>
                <p style="margin: 5px 0; font-size:12px; color:#666;">📷 Camera icons = Realistic photos</p>
                <p style="margin: 5px 0; font-size:12px; color:#666;">☑️ Use checkboxes to toggle layers</p>
            </div>
            '''
            
            m.get_root().html.add_child(folium.Element(ndvi_legend_html))
            
            # Add layer control to switch between map types and toggle overlays
            folium.LayerControl().add_to(m)
            
            # Add markers for each location with realistic photos
            for img_data in available_images:
                location = img_data['location']
                i = img_data['number']
                
                # Convert images to base64
                before_b64 = self.image_to_base64(img_data['before'])
                after_b64 = self.image_to_base64(img_data['after'])
                
                if before_b64 and after_b64:
                    # Create compact popup with realistic photographs
                    popup_html = f"""
                    <div style="width: 400px; font-family: 'Segoe UI', Arial, sans-serif;">
                        <h3 style="text-align: center; color: #d32f2f; margin: 0 0 15px 0; background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); padding: 15px; border-radius: 8px; border: 2px solid #f44336; font-size: 18px;">
                            📷 Location #{i}
                        </h3>
                        
                        <div style="text-align: center; background: #f5f5f5; padding: 12px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #ddd;">
                            <p style="margin: 5px 0; font-weight: bold; font-size: 14px;">📍 {location['latitude']:.4f}, {location['longitude']:.4f}</p>
                            <p style="margin: 5px 0; font-size: 12px; color: #666;">March 2025 → September 2025</p>
                        </div>
                        
                        <div style="display: flex; gap: 10px; margin: 15px 0;">
                            <div style="flex: 1; text-align: center;">
                                <div style="background: #4caf50; color: white; padding: 8px; border-radius: 6px; margin-bottom: 8px; font-weight: bold; font-size: 12px;">
                                    🌲 BEFORE
                                </div>
                                <img src="data:image/png;base64,{before_b64}" 
                                     style="width: 100%; border: 2px solid #4caf50; border-radius: 6px;" 
                                     alt="Before - Forest">
                            </div>
                            
                            <div style="flex: 1; text-align: center;">
                                <div style="background: #f44336; color: white; padding: 8px; border-radius: 6px; margin-bottom: 8px; font-weight: bold; font-size: 12px;">
                                    🏜️ AFTER
                                </div>
                                <img src="data:image/png;base64,{after_b64}" 
                                     style="width: 100%; border: 2px solid #f44336; border-radius: 6px;" 
                                     alt="After - Cleared">
                            </div>
                        </div>
                        
                        <div style="text-align: center; background: #e3f2fd; padding: 10px; border-radius: 6px; margin-top: 15px;">
                            <p style="margin: 0; font-size: 12px; color: #1976d2;">📷 Realistic satellite imagery</p>
                        </div>
                    </div>
                    """
                    
                    # Add marker with realistic photos
                    folium.Marker(
                        location=[location['latitude'], location['longitude']],
                        popup=folium.Popup(popup_html, max_width=450),
                        tooltip=f"📷 Realistic Photos #{i} - Natural-looking satellite photographs!",
                        icon=folium.Icon(color='red', icon='camera', prefix='fa')
                    ).add_to(m)
            
            # Add analysis region
            bounds = report['coordinates']
            region_bounds = [[bounds['south'], bounds['west']], [bounds['north'], bounds['east']]]
            rectangle = folium.Rectangle(region_bounds, {
                'color': 'blue',
                'fillColor': 'blue',
                'fillOpacity': 0.1,
                'weight': 2
            })
            rectangle.add_to(m)
            
            # Add layer control
            folium.LayerControl().add_to(m)
            
            # Save the realistic photo map
            output_file = Path('deforestation_maps/realistic_satellite_photos.html')
            m.save(str(output_file))
            
            print(f"📷 Realistic satellite photo map created: {output_file}")
            print(f"🎨 Successfully processed {len(available_images)} locations with realistic-looking photos")
            print(f"📸 Realistic photos saved in: {self.realistic_dir}")
            
            return output_file, len(available_images)
            
        except Exception as e:
            print(f"❌ Error creating realistic photo map: {e}")
            import traceback
            traceback.print_exc()
            return None, 0

def main():
    """Main function."""
    try:
        processor = RealisticPhotoProcessor()
        
        print("📷 MAKING EXISTING SATELLITE IMAGES LOOK REALISTIC")
        print("=" * 60)
        print("🎨 Processing real satellite images to look like natural photographs!")
        print("📸 Making them look realistic and recognizable!")
        print("🌲🏜️ Natural-looking forest vs. cleared land!")
        print()
        
        # Process existing satellite images to look realistic
        map_file, processed_count = processor.create_realistic_photo_map()
        
        if map_file and processed_count > 0:
            print()
            print("🚀 REALISTIC SATELLITE PHOTOGRAPHS READY!")
            print("=" * 55)
            print(f"📍 File: {map_file}")
            print(f"📷 Locations with realistic photos: {processed_count}")
            print("📸 Click camera markers to see natural-looking photographs")
            print("🎨 These look like realistic photographs anyone would recognize!")
            print("🌲🏜️ Natural forest vs. cleared land images!")
            print()
            print("✅ SUCCESS - Realistic photographs created from satellite data!")
        else:
            print("❌ No satellite images found to make realistic")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()