import pandas as pd
import requests
import json
from pdf2image import convert_from_path
import os
from PIL import Image
import ast


# API endpoints
create_catalog_url = "http://localhost:5055/api/catalog/admin/create"
create_catalog_page_url = "http://localhost:5055/api/catalog-page/admin/create"


df = pd.read_csv('flyer_shop_ids_all.csv')

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

# Function to convert PDF to PNG images
def pdf_to_png(pdf_path, output_folder):
    images = convert_from_path(pdf_path, fmt='png', output_folder=output_folder)
    return images

# Function to create catalog pages
def create_catalog_page(catalog_id, shop_id, page_no, image_path):
    with open(image_path, 'rb') as image_file:
        # Get image dimensions using Pillow
        with Image.open(image_path) as img:
            width, height = img.size
        
        files = {
            'page': (os.path.basename(image_path), image_file, 'image/png')
        }
        data = {
            "catalog": catalog_id,
            "shop": shop_id,
            "status": "ACTIVE",
            "pageNo": page_no,
            "dimension": json.dumps({"width": width, "height": height})  # Dynamic dimensions
        }

        headers = {
        # 'Content-Type': 'application/json',
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI2NWJlOGYzOWNlZWFmNjNkMDAxZGVlNjEiLCJuYW1lIjoiQWRtaW4iLCJlbWFpbCI6ImFkbWluQGdtYWlsLmNvbSIsInJvbGUiOiJBZG1pbiIsImFkZHJlc3MiOiIzNzQvQiBIYWxveWEgSGluZGFnYWxhIFBlcmFkZW5peWEiLCJwaG9uZSI6IjM2MC05NDMtNzMzMiIsImltYWdlIjoiaHR0cHM6Ly9pLmliYi5jby9XcE01eVpaLzkucG5nIiwiaWF0IjoxNzQyMTM4ODUxLCJleHAiOjE3NDIzMTE2NTF9.8dYXrLNJ6iOeDeNUuJNWN8HBwK6TjY0BdYgD7m1L5Dc"
        }
    
        response = requests.post(create_catalog_page_url, files=files, data=data, headers=headers)
        if response.status_code == 200:
            print(f"Page {page_no} created for Catalog ID: {catalog_id}, Shop ID: {shop_id}")
        else:
            print(f"Failed to create page {page_no} for Catalog ID: {catalog_id}, Shop ID: {shop_id}")
            print(f"Response: {response.text}")

# Iterate over DataFrame rows
for index, row in df[:5].iterrows():
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
                for page_no, image in enumerate(images, start=1):
                    image_path = os.path.join(output_folder, f"page_{page_no}.png")
                    image.save(image_path, 'PNG')
                    create_catalog_page(catalog_id, shop_id, page_no, image_path)
                
                # Clean up temporary files
                os.remove(pdf_path)
                for image_file in os.listdir(output_folder):
                    os.remove(os.path.join(output_folder, image_file))
                os.rmdir(output_folder)
    else:
        print(f"Failed to create catalog for {flyer_url}. Status code: {response.status_code}")
        print(f"Response: {response.text}")
