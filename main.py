import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Define the base URL
base_url = "https://dansktip.dk/page/indskoling"
driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()))

# Function to download a PDF file
def download_pdf(pdf_url, folder='pdfs'):
    # Ensure the folder exists
    if not os.path.exists(folder):
        os.makedirs(folder)
    # Get the file name from the URL
    file_name = pdf_url.split('/')[-1]
    # suffix the file name with .pdf
    file_name = f"{file_name}.pdf"
    # Complete path for saving the file
    file_path = os.path.join(folder, file_name)
    # Download the file and save it
    with requests.get(pdf_url, stream=True) as r:
        r.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"Downloaded: {file_name}")

# Function to handle requests with exponential backoff
def make_request(url, max_retries=5):
    retries = 0
    while retries < max_retries:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retries += 1
                wait_time = 2 ** retries  # Exponential backoff
                print(f"Rate limited. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise
    raise Exception(f"Failed to fetch {url} after {max_retries} retries.")

# Load the base page with Selenium
driver.get(base_url)

# Wait for the .wrapper-content elements to be rendered by JavaScript
try:
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, 'wrapper-content'))
    )
except Exception as e:
    print("Error: Wrapper content not found.")
    driver.quit()
    raise

# Parse the page source with BeautifulSoup
soup = BeautifulSoup(driver.page_source, 'html.parser')

# Find all elements with class 'wrapper-content'
wrapper_content = soup.find_all(class_='wrapper-content')

# Loop through each wrapper-content and find links
for content in wrapper_content:
    # Find all <a> tags
    links = content.find_all('a', href=True)
    for link in links:
        href = link['href']
        # Complete URL of the link
        page_url = urljoin(base_url, href)
        try:
            # Use Selenium to load the linked page
            driver.get(page_url)
            # Wait for the download-file links to be rendered by JavaScript
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[data-id^="download-file-"]'))
            )
            # Parse the page source with BeautifulSoup
            page_soup = BeautifulSoup(driver.page_source, 'html.parser')
        except Exception as e:
            print(f"Skipping {page_url} due to error: {e}")
            continue

        # Find all links with data-id="download-file-*"
        download_links = page_soup.find_all('a', {'data-id': lambda x: x and x.startswith('download-file-')})
        for download_link in download_links:
            data_id = download_link['data-id']
            # Extract the ID from data-id="download-file-*"
            file_id = data_id.split('download-file-')[-1]
            # Form the new URL using the extracted ID
            pdf_url = f"https://api.supermatematik.dk/api/download-file/{file_id}"
            download_pdf(pdf_url)

# Quit the Selenium driver
driver.quit()

print("All PDFs have been downloaded.")
