import openai
import streamlit as st
import PyPDF2
import requests
from bs4 import BeautifulSoup

# Get the API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

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
        "https://www.bou.ac.bd/BOU/VCOffice",
        "https://www.bou.ac.bd/Authority/FormerVC",
        "https://www.bou.ac.bd/Contact/RegionalCentre/",
        "https://www.bousst.edu.bd/faculty-members"
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
        start += (max_tokens - overlap)
    return chunks

# List of PDF files
pdf_files = ["1.pdf", "2.pdf", "3.pdf","4.pdf"]

# Streamlit UI
st.title("BOUSST AI PORTAL")

# Initialize session state variables
if 'is_bousst_student' not in st.session_state:
    st.session_state.is_bousst_student = None
if 'student_id' not in st.session_state:
    st.session_state.student_id = None
if 'answer' not in st.session_state:
    st.session_state.answer = ''
if 'current_pdf_index' not in st.session_state:
    st.session_state.current_pdf_index = 0

# Initial question about student status
if st.session_state.is_bousst_student is None:
    student_response = st.text_input("Are you a student of BOUSST? (Yes/No):")
    if student_response.lower() == "yes":
        st.session_state.is_bousst_student = True
    elif student_response.lower() == "no":
        st.session_state.is_bousst_student = False
        st.write("Access denied. You must confirm you are a BOUSST student.")
        st.stop()

# Ask for student ID if they are confirmed as a student
if st.session_state.is_bousst_student:
    st.session_state.student_id = st.text_input("Enter the last 3 digits of your ID:")
    
    if st.session_state.student_id and len(st.session_state.student_id) == 3:
        st.write(f"Your ID: {st.session_state.student_id}")

# Show the question input and answer area after entering ID
if st.session_state.is_bousst_student and st.session_state.student_id:
    st.subheader("Ask your question:")
    question = st.text_input("Enter your question:")
    if question:
        st.session_state.current_pdf_index = 0
        st.session_state.answer = ''

        answer_found = False

        # Loop through PDF files
        while st.session_state.current_pdf_index < len(pdf_files):
            pdf_path = pdf_files[st.session_state.current_pdf_index]
            pdf_text = extract_text_from_pdf(pdf_path)

            # Split PDF text into chunks
            for chunk in split_text_into_chunks(pdf_text):
                if estimate_tokens(chunk) + estimate_tokens(question) <= 16000:
                    prompt = f"Based on the following text from a document, answer the user’s query:\n\n{chunk}\n\nUser's query: {question}. If the answer is not found, respond with 'I am sorry.'"
                    response = query_gpt(prompt)

                    if response != "I am sorry.":
                        st.session_state.answer = response
                        answer_found = True
                        break

            if answer_found:
                break

            st.session_state.current_pdf_index += 1

        # If no answer is found in PDFs, scrape websites
        if not answer_found:
            scraped_data = scrape_websites()

            if scraped_data:
                for chunk in split_text_into_chunks(scraped_data):
                    if estimate_tokens(chunk) + estimate_tokens(question) <= 16000:
                        prompt = f"Based on the following scraped information, answer the user’s query:\n\n{chunk}\n\nUser's query: {question}."
                        response = query_gpt(prompt)
                        if response and response != "I am sorry.":
                            st.session_state.answer += "\n\n" + response
                            answer_found = True
                            break
                        elif response == "I am sorry.":
                            # If scraping fails, ask GPT for general information
                            st.session_state.answer = query_gpt("What is the current time?")

        # If no satisfactory answer is found, fallback to OpenAI GPT for general questions
        if not answer_found and st.session_state.answer == '':
            # Directly ask GPT for a general answer
            st.session_state.answer = query_gpt(f"Answer the following query:\n\n{question}")

    # Display the answer
    st.text_area("Answer", value=st.session_state.answer, height=200)

# Reset functionality
if st.button("Reset"):
    # Clear all session state variables to restart the process
    st.session_state.clear()
    st.session_state.is_bousst_student = None  # Keep the state for student check
    st.session_state.student_id = None
    st.session_state.answer = ''
    st.session_state.current_pdf_index = 0
    st.rerun()  # Use this for rerunning the app

