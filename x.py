import pandas as pd
import requests
import json
import os
from PIL import Image
import ast
import fitz  # PyMuPDF
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

# API endpoints
create_catalog_url = "http://localhost:5055/api/catalog/admin/create"
create_catalog_page_url = "http://localhost:5055/api/catalog-page/admin/create"

# Read the CSV file
df = pd.read_csv('flyer_shop_ids_all.csv')

# Create a PoolManager for urllib3
http = urllib3.PoolManager()

# Function to download PDF from URL
def download_pdf(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    else:
        print(f"Failed to download PDF from {url}")
        return False

# Function to convert PDF to PNG images using PyMuPDF
def pdf_to_png(pdf_path, output_folder):
    images = []
    pdf_document = fitz.open(pdf_path)
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap()
        image_path = os.path.join(output_folder, f"page_{page_num + 1}.png")
        pix.save(image_path)
        images.append(image_path)  # Store the image path instead of the Image object
    return images

# Function to create catalog pages using urllib3
def create_catalog_page(catalog_id, shop_id, page_no, image_path):
    with open(image_path, 'rb') as image_file:
        # Get image dimensions using Pillow
        with Image.open(image_path) as img:
            width, height = img.size
        
        # Prepare the multipart/form-data payload
        fields = {
            'data': json.dumps({  # Send the data as a JSON string
                "catalog": catalog_id,
                "shop": shop_id,
                "status": "ACTIVE",
                "pageNo": page_no,
                "dimension": {"width": width, "height": height}
            }),
            'page': (os.path.basename(image_path), image_file.read(), 'image/png')  # File upload
        }

        # Set the headers (do NOT include 'Content-Type')
        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI2NWJlOGYzOWNlZWFmNjNkMDAxZGVlNjEiLCJuYW1lIjoiQWRtaW4iLCJlbWFpbCI6ImFkbWluQGdtYWlsLmNvbSIsInJvbGUiOiJBZG1pbiIsImFkZHJlc3MiOiIzNzQvQiBIYWxveWEgSGluZGFnYWxhIFBlcmFkZW5peWEiLCJwaG9uZSI6IjM2MC05NDMtNzMzMiIsImltYWdlIjoiaHR0cHM6Ly9pLmliYi5jby9XcE01eVpaLzkucG5nIiwiaWF0IjoxNzQyMTM4ODUxLCJleHAiOjE3NDIzMTE2NTF9.8dYXrLNJ6iOeDeNUuJNWN8HBwK6TjY0BdYgD7m1L5Dc"
        }
    
        # Make the POST request
        response = http.request(
            'POST',
            create_catalog_page_url,
            fields=fields,
            headers=headers
        )
        
        # Process the response
        if response.status == 200:
            print(f"Page {page_no} created for Catalog ID: {catalog_id}, Shop ID: {shop_id}")
        else:
            print(f"Failed to create page {page_no} for Catalog ID: {catalog_id}, Shop ID: {shop_id}")
            print(f"Response: {response.data.decode('utf-8')}")

# Function to process a single row
def process_row(row):
    flyer_url = row['Flyer URLs']
    shop_ids = ast.literal_eval(row['Shop IDs'])
    
    # Extract title from flyer URL
    title = flyer_url.split('/')[-1].split('.')[0]
    
    # Prepare the request body for creating catalog
    payload = {
        "description": "test des",
        "expireDate": "2025-04-11",
        "isFeatured": True,
        "shop": "",
        "shops": shop_ids,
        "startDate": "2025-03-11",
        "status": "ACTIVE",
        "title": title
    }
    
    # Convert payload to JSON
    headers = {
        'Content-Type': 'application/json',
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI2NWJlOGYzOWNlZWFmNjNkMDAxZGVlNjEiLCJuYW1lIjoiQWRtaW4iLCJlbWFpbCI6ImFkbWluQGdtYWlsLmNvbSIsInJvbGUiOiJBZG1pbiIsImFkZHJlc3MiOiIzNzQvQiBIYWxveWEgSGluZGFnYWxhIFBlcmFkZW5peWEiLCJwaG9uZSI6IjM2MC05NDMtNzMzMiIsImltYWdlIjoiaHR0cHM6Ly9pLmliYi5jby9XcE01eVpaLzkucG5nIiwiaWF0IjoxNzQyMTM4ODUxLCJleHAiOjE3NDIzMTE2NTF9.8dYXrLNJ6iOeDeNUuJNWN8HBwK6TjY0BdYgD7m1L5Dc"
    }
    response = requests.post(create_catalog_url, data=json.dumps(payload), headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        response_data = response.json()
        created_catalogs = response_data.get('data', {}).get('createdCatalogs', [])
        
        # Process each created catalog
        for catalog in created_catalogs:
            catalog_id = catalog.get('_id')
            shop_id = catalog.get('shop')
            
            # Download PDF
            pdf_path = f"temp_{catalog_id}.pdf"
            if download_pdf(flyer_url, pdf_path):
                # Convert PDF to PNG images
                output_folder = f"pages_{catalog_id}"
                os.makedirs(output_folder, exist_ok=True)
                images = pdf_to_png(pdf_path, output_folder)
                
                # Create catalog pages for each image
                for page_no, image_path in enumerate(images, start=1):
                    create_catalog_page(catalog_id, shop_id, page_no, image_path)
                
                # Clean up temporary files
                os.remove(pdf_path)
                for image_file in os.listdir(output_folder):
                    image_path = os.path.join(output_folder, image_file)
                    os.remove(image_path)
                os.rmdir(output_folder)
    else:
        print(f"Failed to create catalog for {flyer_url}. Status code: {response.status_code}")
        print(f"Response: {response.text}")

# Parallel processing using ThreadPoolExecutor
def process_rows_parallel(df):
    with ThreadPoolExecutor(max_workers=5) as executor:  # Adjust max_workers as needed
        futures = [executor.submit(process_row, row) for _, row in df.iterrows()]
        for future in as_completed(futures):
            try:
                future.result()  # Wait for the task to complete
            except Exception as e:
                print(f"Error processing row: {e}")

# Process rows in parallel
process_rows_parallel(df[5:10])  # Process a subset of rows for testing
