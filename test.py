import openai
import streamlit as st
import PyPDF2
import requests
from bs4 import BeautifulSoup

# Get the API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Function to read PDF and extract text
def read_pdf(file_path):
    pdf_text = ""  # Initialize an empty string to store the PDF text
    with open(file_path, 'rb') as file:  # Open the PDF file in binary read mode
        reader = PyPDF2.PdfReader(file)  # Create a PDF reader object
        for page in reader.pages:  # Loop through each page in the PDF
            pdf_text += page.extract_text()  # Extract and append the text from the page
    return pdf_text  # Return the full extracted text

# Function to query GPT-3.5 Turbo
def query_gpt_turbo(question, text, max_tokens=4096):
    # Call the OpenAI API to get a response from GPT-3.5
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Specify the model to use
        messages=[  # Set up the messages for the conversation
            {"role": "system", "content": "You are a helpful assistant."},  # System message to set context
            {"role": "user", "content": f"{question}\n\n{text}"}  # User message with the question and text
        ],
        max_tokens=max_tokens,  # Set the maximum number of tokens for the response
        temperature=0.5  # Control randomness of the response
    )
    return response.choices[0].message['content']  # Return the content of the response

# Function to scrape a website
def scrape_website(url):
    response = requests.get(url)  # Make a GET request to the specified URL
    soup = BeautifulSoup(response.text, 'html.parser')  # Parse the HTML content with BeautifulSoup
    # Scrape all h1 tags from the webpage
    data = [tag.get_text() for tag in soup.find_all('h1')]
    return "\n".join(data)  # Return the scraped data as a single string

# Function to analyze PDF and scrape if answer is "not available"
def analyze_pdf_and_scrape(question, pdf_file, websites):
    pdf_text = read_pdf(pdf_file)  # Read the PDF and get its text
    chunk_size = 16380  # Set the size limit for each chunk of text sent to GPT
    start = 0  # Initialize the starting index for the chunking process

    # Step 1: Sending PDF chunks to GPT
    while start < len(pdf_text):  # While there is more text to process
        chunk = pdf_text[start:start + chunk_size]  # Get a chunk of text from the PDF
        answer = query_gpt_turbo(question, chunk)  # Query GPT with the current chunk
        
        # If GPT does not provide an answer
        if answer.lower() == "not available":  # Check if the answer is "not available"
            start += chunk_size  # Move to the next chunk of the PDF
            continue  # Continue to the next iteration of the loop
        else:
            return answer  # Return the answer if found

    # Step 2: If no satisfactory answer from PDF, proceed with website scraping
    for site in websites:  # Loop through each website to scrape
        scraped_data = scrape_website(site)  # Scrape the website for data
        # Use GPT to analyze the scraped data
        gpt_answer_from_scraping = query_gpt_turbo(question, scraped_data) 
        
        # If GPT provides a meaningful answer from scraping, return it
        if gpt_answer_from_scraping.lower() != "not available":  # Check if the answer is not "not available"
            return f"Answer from website scraping: {gpt_answer_from_scraping}"  # Return the answer from scraping
    
    return "No answer found from PDF or website scraping."  # Return a final message if no answer is found

# Streamlit app
#st.title("BOUSST AI PORTAL")  # Set the title of the app
st.markdown("<h1 style='text-align: center;'>BOUSST AI PORTAL</h1>", unsafe_allow_html=True)  # Centered title


# Ask a question
question = st.text_input("Enter your question")  # Create an input field for the user to enter a question

# PDF file path (hardcoded or passed dynamically if needed)
pdf_file_path = 'path_to_your_pdf.pdf'  # Set the path to the PDF file

# Websites to scrape (You can modify or add more websites)
websites = ['https://www.bou.ac.bd/BOU/VCProfile', 'https://www.bousst.edu.bd/faculty-members']  # List of websites to scrape

if question:  # If a question is provided
    with st.spinner("Processing..."):  # Show a spinner while processing
        answer = analyze_pdf_and_scrape(question, pdf_file_path, websites)  # Analyze the PDF and scrape if needed
        st.write(answer)  # Display the answer in the Streamlit app

