import openai
import streamlit as st
import PyPDF2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
#import os

# Load environment variables from .env file
load_dotenv()

# Set your OpenAI API key from the environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')
# Set your OpenAI API key
#openai.api_key = 'sk-proj-8b2aBpZUZakPVmzOGxkET3BlbkFJD9xj7qgq5NNYYUZCMktY'

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

# Function to estimate the number of tokens in a text
def estimate_tokens(text):
    return len(text.split())

# Function to query GPT model with a chunk of text
def query_gpt(prompt, model="gpt-3.5-turbo"):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error: {str(e)}"

# Function to scrape information from the websites
def scrape_websites():
    urls = [
        "https://www.bou.ac.bd/BOU/VCProfile",
        "https://www.bousst.edu.bd/",
        "https://www.bou.ac.bd/BOU/vc",
        "https://www.bou.ac.bd/BOU/VCOffice"
        #"https://www.bou.ac.bd/BOU/StatutoryBodies",
        #"https://www.bou.ac.bd/Authority/TreasurerOffice",
        #"https://www.bou.ac.bd/Registrar/Office",
        "https://www.bou.ac.bd/Authority/FormerVC",
        "https://www.bou.ac.bd/Contact/RegionalCentre/"
    ]
    scraped_data = ""
    for url in urls:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            for p in soup.find_all('p'):
                scraped_data += p.get_text() + "\n"
            for h in soup.find_all(['h1', 'h2', 'h3']):
                scraped_data += h.get_text() + "\n"
        except Exception as e:
            continue
    return scraped_data if scraped_data else None

# Function to split text into overlapping chunks
def split_text_into_chunks(text, max_tokens=16000, overlap=1000):
    tokens = text.split()
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunks.append(' '.join(tokens[start:end]))
        start += (max_tokens - overlap)  # Slide the window by max_tokens - overlap
    return chunks

# List of PDF files
pdf_files = ["1.pdf", "2.pdf", "3.pdf"]

# Streamlit UI
st.title("BOUSST AI PORTAL")

# Initialize session state
if 'answer' not in st.session_state:
    st.session_state.answer = ''
if 'current_pdf_index' not in st.session_state:
    st.session_state.current_pdf_index = 0
if 'question' not in st.session_state:
    st.session_state.question = ''

# Form for asking question
with st.form(key='ask_form'):
    question = st.text_input("Enter your question:", key="question_input", value=st.session_state.question)
    submitted = st.form_submit_button("Ask AI")

    # When the form is submitted
    if submitted and question:
        # Reset the current PDF index and answer for each new question
        st.session_state.current_pdf_index = 0
        st.session_state.answer = ''

        # Flag to track if an answer is found
        answer_found = False

        # Loop through PDF files sequentially
        while st.session_state.current_pdf_index < len(pdf_files):
            pdf_path = pdf_files[st.session_state.current_pdf_index]
            pdf_text = extract_text_from_pdf(pdf_path)

            # Split the PDF text into overlapping chunks
            for chunk in split_text_into_chunks(pdf_text):
                # Ensure token count of the chunk and question together is <= 16000
                if estimate_tokens(chunk) + estimate_tokens(question) <= 16000:
                    prompt = f"Based on the following text from a document, answer the user’s query:\n\n{chunk}\n\nUser's query: {question}. If the answer is not found in the document, please respond with 'I am sorry.'"
                    response = query_gpt(prompt)

                    # Check if the GPT response is satisfactory
                    if response != "I am sorry.":
                        st.session_state.answer = response
                        answer_found = True
                        break  # Exit loop if a satisfactory answer is received

            if answer_found:
                break  # Exit if answer found after processing all chunks of a PDF

            # Move to the next PDF
            st.session_state.current_pdf_index += 1

        # If no satisfactory answer from PDFs, scrape the websites
        if not answer_found:
            st.session_state.answer = "Trying to browse the website..."

            # Scrape the websites for additional information
            scraped_data = scrape_websites()
            if scraped_data:
                # Split the scraped data into overlapping chunks
                for chunk in split_text_into_chunks(scraped_data):
                    if estimate_tokens(chunk) + estimate_tokens(question) <= 16000:
                        prompt = f"Based on the following scraped information, answer the user’s query:\n\n{chunk}\n\nUser's query: {question}."
                        response = query_gpt(prompt)
                        if response and response != "I am sorry.":
                            st.session_state.answer += "\n\n" + response
                            answer_found = True
                            break  # Exit loop if a satisfactory answer is received

                if not answer_found:
                    st.session_state.answer += " Sorry, I cannot provide the information this time. Please try again later."
            else:
                st.session_state.answer = "Sorry, I cannot provide the information this time. Please try again later."

# Display the answer
st.text_area("Answer", value=st.session_state.answer, height=200)

# Reset the PDF index if needed
if st.button("Reset"):
    st.session_state.current_pdf_index = 0
    st.session_state.answer = ''
