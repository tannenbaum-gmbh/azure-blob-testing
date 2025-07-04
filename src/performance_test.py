#!/usr/bin/env python3
"""
Azure Blob Storage Performance Testing Script

This script performs the following operations:
1. Creates a random image file (up to 5MB)
2. Uploads the file to Azure Blob Storage
3. Creates a SAS link to the file
4. Downloads the file using the SAS link
5. Measures and reports timing for all operations
"""

import os
import time
import random
import json
import logging
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

from PIL import Image
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.identity import DefaultAzureCredential


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Class to track and store performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'test_id': f"test_{int(time.time())}_{random.randint(1000, 9999)}",
            'start_time': datetime.utcnow().isoformat(),
            'file_size_mb': 0,
            'upload_time_ms': 0,
            'sas_generation_time_ms': 0,
            'download_time_ms': 0,
            'total_time_ms': 0,
            'upload_to_download_time_ms': 0
        }
    
    def to_json(self):
        return json.dumps(self.metrics, indent=2)


def create_random_image(max_size_mb=5):
    """
    Create a random image file with size up to max_size_mb
    
    Returns:
        tuple: (image_data as bytes, file_size in MB)
    """
    # Generate random dimensions that will result in a file up to max_size_mb
    # Estimate: RGB image needs ~3 bytes per pixel
    max_pixels = (max_size_mb * 1024 * 1024) // 3
    
    # Random dimensions ensuring we stay under the limit
    width = random.randint(100, int((max_pixels ** 0.5) * 0.8))
    height = random.randint(100, max_pixels // width)
    
    # Create random RGB image
    img = Image.new('RGB', (width, height))
    pixels = []
    
    for _ in range(width * height):
        pixels.append((
            random.randint(0, 255),  # R
            random.randint(0, 255),  # G
            random.randint(0, 255)   # B
        ))
    
    img.putdata(pixels)
    
    # Convert to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG', quality=95)
    img_data = img_bytes.getvalue()
    
    size_mb = len(img_data) / (1024 * 1024)
    
    logger.info(f"Generated random image: {width}x{height} pixels, {size_mb:.2f} MB")
    
    return img_data, size_mb


def upload_blob(blob_service_client, container_name, blob_name, data):
    """
    Upload data to Azure Blob Storage
    
    Returns:
        float: Upload time in milliseconds
    """
    start_time = time.time()
    
    blob_client = blob_service_client.get_blob_client(
        container=container_name, 
        blob=blob_name
    )
    
    blob_client.upload_blob(data, overwrite=True)
    
    end_time = time.time()
    upload_time_ms = (end_time - start_time) * 1000
    
    logger.info(f"Upload completed in {upload_time_ms:.2f} ms")
    
    return upload_time_ms


def generate_sas_url(blob_service_client, container_name, blob_name):
    """
    Generate a SAS URL for the blob
    
    Returns:
        tuple: (sas_url, generation_time in milliseconds)
    """
    start_time = time.time()
    
    # Get the account key for SAS generation
    # Note: In production, you might want to use a different approach for SAS generation
    # when using managed identity, such as user delegation SAS
    try:
        # Try to get account key if available
        account_key = None
        if hasattr(blob_service_client, 'credential') and hasattr(blob_service_client.credential, 'account_key'):
            account_key = blob_service_client.credential.account_key
        
        if account_key:
            # Generate SAS token using account key
            sas_token = generate_blob_sas(
                account_name=blob_service_client.account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=1)
            )
        else:
            # For managed identity scenarios, we'll just use the blob URL without SAS
            # In a real scenario, you would generate a user delegation SAS
            logger.warning("No account key available, using blob URL directly (requires appropriate permissions)")
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            end_time = time.time()
            generation_time_ms = (end_time - start_time) * 1000
            logger.info(f"Blob URL generation completed in {generation_time_ms:.2f} ms")
            return blob_client.url, generation_time_ms
        
        # Construct SAS URL
        blob_client = blob_service_client.get_blob_client(
            container=container_name, 
            blob=blob_name
        )
        sas_url = f"{blob_client.url}?{sas_token}"
        
    except Exception as e:
        logger.warning(f"SAS generation failed: {e}. Using blob URL directly.")
        blob_client = blob_service_client.get_blob_client(
            container=container_name, 
            blob=blob_name
        )
        sas_url = blob_client.url
    
    end_time = time.time()
    generation_time_ms = (end_time - start_time) * 1000
    
    logger.info(f"SAS URL generation completed in {generation_time_ms:.2f} ms")
    
    return sas_url, generation_time_ms


def download_blob_via_sas(sas_url, blob_service_client=None, container_name=None, blob_name=None):
    """
    Download blob using SAS URL or direct blob access
    
    Returns:
        tuple: (downloaded_data, download_time in milliseconds)
    """
    start_time = time.time()
    
    try:
        # Try downloading via URL first (works for SAS URLs and public blobs)
        import urllib.request
        with urllib.request.urlopen(sas_url) as response:
            data = response.read()
    except Exception as e:
        # If URL download fails, try using blob client directly (for auth scenarios)
        logger.warning(f"URL download failed: {e}. Trying direct blob client access.")
        if blob_service_client and container_name and blob_name:
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            data = blob_client.download_blob().readall()
        else:
            raise e
    
    end_time = time.time()
    download_time_ms = (end_time - start_time) * 1000
    
    logger.info(f"Download completed in {download_time_ms:.2f} ms")
    
    return data, download_time_ms


def main():
    """Main function to run the performance test"""
    
    # Get environment variables
    storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
    storage_account_endpoint = os.getenv('AZURE_STORAGE_ACCOUNT_ENDPOINT')
    
    if not storage_account_name:
        logger.error("AZURE_STORAGE_ACCOUNT_NAME environment variable is required")
        return 1
        
    if not storage_account_endpoint:
        storage_account_endpoint = f"https://{storage_account_name}.blob.core.windows.net"
    
    logger.info(f"Starting performance test against storage account: {storage_account_name}")
    
    # Initialize metrics
    metrics = PerformanceMetrics()
    
    try:
        # Initialize blob service client
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(
            account_url=storage_account_endpoint,
            credential=credential
        )
        
        # Test parameters
        container_name = "performance-test"
        blob_name = f"test-image-{metrics.metrics['test_id']}.jpg"
        
        test_start_time = time.time()
        
        # Step 1: Create random image
        logger.info("Step 1: Creating random image...")
        image_data, file_size_mb = create_random_image()
        metrics.metrics['file_size_mb'] = round(file_size_mb, 2)
        
        # Step 2: Upload to blob storage
        logger.info("Step 2: Uploading to blob storage...")
        upload_start_time = time.time()
        upload_time_ms = upload_blob(blob_service_client, container_name, blob_name, image_data)
        metrics.metrics['upload_time_ms'] = round(upload_time_ms, 2)
        
        # Step 3: Generate SAS URL
        logger.info("Step 3: Generating SAS URL...")
        sas_url, sas_generation_time_ms = generate_sas_url(blob_service_client, container_name, blob_name)
        metrics.metrics['sas_generation_time_ms'] = round(sas_generation_time_ms, 2)
        
        # Step 4: Download via SAS URL
        logger.info("Step 4: Downloading via SAS URL...")
        downloaded_data, download_time_ms = download_blob_via_sas(
            sas_url, blob_service_client, container_name, blob_name
        )
        download_end_time = time.time()
        metrics.metrics['download_time_ms'] = round(download_time_ms, 2)
        
        # Calculate total and upload-to-download times
        test_end_time = time.time()
        total_time_ms = (test_end_time - test_start_time) * 1000
        upload_to_download_time_ms = (download_end_time - upload_start_time) * 1000
        
        metrics.metrics['total_time_ms'] = round(total_time_ms, 2)
        metrics.metrics['upload_to_download_time_ms'] = round(upload_to_download_time_ms, 2)
        
        # Verify download
        if len(downloaded_data) == len(image_data):
            logger.info("✓ Download verification successful - file sizes match")
        else:
            logger.warning(f"⚠ Download verification failed - size mismatch: {len(downloaded_data)} vs {len(image_data)}")
        
        # Output results
        logger.info("Performance Test Results:")
        logger.info("=" * 50)
        logger.info(f"Test ID: {metrics.metrics['test_id']}")
        logger.info(f"File Size: {metrics.metrics['file_size_mb']} MB")
        logger.info(f"Upload Time: {metrics.metrics['upload_time_ms']} ms")
        logger.info(f"SAS Generation Time: {metrics.metrics['sas_generation_time_ms']} ms")
        logger.info(f"Download Time: {metrics.metrics['download_time_ms']} ms")
        logger.info(f"Total Time: {metrics.metrics['total_time_ms']} ms")
        logger.info(f"Upload to Download Time: {metrics.metrics['upload_to_download_time_ms']} ms")
        logger.info("=" * 50)
        
        # Output JSON for programmatic consumption
        print(f"PERFORMANCE_METRICS_JSON:{metrics.to_json()}")
        
        # Clean up
        logger.info("Cleaning up test blob...")
        blob_client = blob_service_client.get_blob_client(
            container=container_name, 
            blob=blob_name
        )
        blob_client.delete_blob()
        
        logger.info("Performance test completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Performance test failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())