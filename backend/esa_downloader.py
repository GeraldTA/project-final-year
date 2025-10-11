"""
Alternative Sentinel-2 downloader using ESA Copernicus Open Access Hub API.
This is often more reliable for automated downloads.
"""

import requests
import os
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
import time
import sys

# Add utils to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(src_dir))

from src.utils.config import get_config
from src.utils.logger import LoggerMixin

class ESASentinelDownloader(LoggerMixin):
    """
    Alternative Sentinel-2 downloader using ESA Copernicus Open Access Hub.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the ESA Sentinel downloader."""
        self.config = get_config(config_path)
        
        # ESA Copernicus Open Access Hub
        self.base_url = "https://apihub.copernicus.eu/apihub"
        self.search_url = f"{self.base_url}/search"
        
        # Use same credentials
        self.username = self.config.get('apis.copernicus.username')
        self.password = self.config.get('apis.copernicus.password')
        
        if not self.username or not self.password:
            raise ValueError("Copernicus API credentials not provided")
        
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        
        # Create download directory
        self.download_dir = self.config.get_data_dir('raw_images')
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("ESA Sentinel downloader initialized")
    
    def search_products(
        self,
        start_date: str,
        end_date: str,
        max_cloud_cover: float = 20,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for Sentinel-2 products using ESA API.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_cloud_cover: Maximum cloud cover percentage
            max_results: Maximum number of results
            
        Returns:
            List of product dictionaries
        """
        bounds = self.config.get_region_bounds()
        
        # Build the query string
        footprint = f"POLYGON(({bounds['west']} {bounds['south']},{bounds['east']} {bounds['south']},{bounds['east']} {bounds['north']},{bounds['west']} {bounds['north']},{bounds['west']} {bounds['south']}))"
        
        query_params = {
            'q': (
                f"platformname:Sentinel-2 AND "
                f"producttype:S2MSI2A AND "
                f"beginposition:[{start_date}T00:00:00.000Z TO {end_date}T23:59:59.999Z] AND "
                f"footprint:\"Intersects({footprint})\" AND "
                f"cloudcoverpercentage:[0 TO {max_cloud_cover}]"
            ),
            'rows': max_results,
            'start': 0,
            'format': 'json'
        }
        
        try:
            self.logger.info(f"Searching ESA Hub for Sentinel-2 products from {start_date} to {end_date}")
            response = self.session.get(self.search_url, params=query_params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            products = data.get('feed', {}).get('entry', [])
            
            if not isinstance(products, list):
                products = [products] if products else []
            
            self.logger.info(f"Found {len(products)} products matching criteria")
            return products
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def download_product(self, product: Dict[str, Any], extract: bool = True) -> Optional[Path]:
        """
        Download a single product from ESA Hub.
        
        Args:
            product: Product dictionary from search results
            extract: Whether to extract the downloaded zip file
            
        Returns:
            Path to downloaded/extracted product
        """
        try:
            product_id = product['id']
            product_title = product['title']
            
            # Get download URL
            download_url = f"{self.base_url}/odata/v1/Products('{product_id}')/$value"
            
            # Determine output path
            safe_title = "".join(c for c in product_title if c.isalnum() or c in ('-', '_', '.'))
            output_file = self.download_dir / f"{safe_title}.zip"
            
            if output_file.exists():
                self.logger.info(f"Product already exists: {output_file}")
                if extract:
                    return self._extract_if_needed(output_file, safe_title)
                return output_file
            
            self.logger.info(f"Downloading: {product_title}")
            
            # Download with progress
            response = self.session.get(download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Progress every 100MB
                        if downloaded_size % (100 * 1024 * 1024) < 8192:
                            progress = (downloaded_size / total_size) * 100 if total_size > 0 else 0
                            self.logger.info(f"Download progress: {progress:.1f}%")
            
            self.logger.info(f"Successfully downloaded: {output_file}")
            
            if extract:
                return self._extract_if_needed(output_file, safe_title)
            return output_file
            
        except Exception as e:
            self.logger.error(f"Download failed for {product.get('title', 'unknown')}: {e}")
            return None
    
    def _extract_if_needed(self, zip_path: Path, extract_dir_name: str) -> Path:
        """Extract zip file if needed."""
        extract_dir = self.download_dir / extract_dir_name
        
        if extract_dir.exists():
            return extract_dir
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            self.logger.info(f"Extracted to: {extract_dir}")
            return extract_dir
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            return zip_path

def test_esa_downloader():
    """Test the ESA downloader."""
    print("🧪 Testing ESA Copernicus Open Access Hub Downloader")
    print("=" * 60)
    
    try:
        downloader = ESASentinelDownloader()
        
        # Search for recent products
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        products = downloader.search_products(start_date, end_date, max_cloud_cover=20, max_results=5)
        
        if products:
            print(f"✅ Found {len(products)} products")
            
            # Show first product
            first_product = products[0]
            print(f"📸 First product: {first_product['title']}")
            
            # Try to download first product
            print("🔄 Attempting download...")
            result = downloader.download_product(first_product, extract=False)
            
            if result:
                print(f"✅ Download successful: {result}")
            else:
                print("❌ Download failed")
        else:
            print("❌ No products found")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_esa_downloader()
