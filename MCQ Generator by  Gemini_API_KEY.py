import streamlit as st
import google.generativeai as genai
import os
import requests
from bs4 import BeautifulSoup
import socket
from dotenv import load_dotenv
import json
import re

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Function to check internet availability
def is_internet_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

# Function to scrape website title and description
def get_summary_from_website(url):
    if not is_internet_available():
        st.error("No internet connection available. Cannot scrape website.")
        return None
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title').text if soup.find('title') else ""
        description = soup.find('meta', attrs={'name': 'description'})
        description = description.get('content') if description else ""
        return f"Title: {title}\nDescription: {description}"
    except requests.exceptions.RequestException:
        return None

# Function to generate a single quiz question
def generate_quiz_question_gemini(text):
    """Generates a quiz question using the Gemini API and structures the output properly."""
    model = genai.GenerativeModel('gemini-1.5-pro')

    prompt = f"""You are a quiz question generator. Given a short text, generate one MCQ with four options. Indicate the correct answer.

    Text: {text}

    Format:
    Question: [question]
    A: [option A]
    B: [option B]
    C: [option C]
    D: [option D]
    Correct Answer: [A/B/C/D]
    """

    try:
        response = model.generate_content(prompt)
        question_data = response.text.strip()

        # --- Default Values ---
        question, options, correct_answer = None, [], []

        for line in question_data.split("\n"):
            line = line.strip()
            if line.startswith("Question:"):
                question = line[len("Question:"):].strip()
            elif line.startswith("A:"):
                options.append(line[len("A:"):].strip())
            elif line.startswith("B:"):
                options.append(line[len("B:"):].strip())
            elif line.startswith("C:"):
                options.append(line[len("C:"):].strip())
            elif line.startswith("D:"):
                options.append(line[len("D:"):].strip())
            elif line.startswith("Correct Answer:"):
                correct_index = line[len("Correct Answer:"):].strip()
                correct_answer.append(ord(correct_index) - ord('A'))  # Convert 'A'/'B'/'C'/'D' to index (0-3)

        # ✅ Validate extracted data
        if not question or len(options) != 4 or any(ans not in range(4) for ans in correct_answer):
            print("⚠️ Warning: Incomplete question data. Skipping...")
            return None

        # ✅ Return structured JSON-like dictionary
        return {
            "question": question,
            "options": options,  # Options stored in an array
            "correct_answer": correct_answer  # Array of correct answer indices
        }

    except Exception as e:
        print(f"❌ Error generating question: {e}")
        return None

# Function to generate multiple quiz questions
def generate_multiple_quiz_questions(text, num_questions=1):
    """Generates multiple quiz questions and returns them as JSON."""
    questions_list = []

    for i in range(num_questions):
        print(f"🛠 Generating Question {i+1}...")  # Debugging

        quiz_question = generate_quiz_question_gemini(text)

        if quiz_question:
            questions_list.append(quiz_question)
        else:
            print(f"⚠️ Skipping question {i+1} due to errors.")

    return json.dumps(questions_list, indent=4)

# Streamlit UI
def main():
    st.title("AI-Powered Quiz Generator 🧠")
    st.sidebar.header("Enter Details")
    url = st.sidebar.text_input("Enter Website URL:")
    num_questions = st.sidebar.number_input("Number of Questions", min_value=1, max_value=5, value=1)
    
    if st.sidebar.button("Generate Quiz"):
        with st.spinner("Generating JSON-based quiz..."):
            summary = get_summary_from_website(url)
        
        if summary:
            quiz_json = generate_multiple_quiz_questions(summary, num_questions)
            st.success("Quiz Generated Successfully!")
            st.json(json.loads(quiz_json))  # Display JSON output properly
        else:
            st.error("Failed to retrieve summary from the website.")

if __name__ == "__main__":
    main()
    
