import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
from pydub import AudioSegment
import speech_recognition as sr
from moviepy.editor import VideoFileClip
import random
import requests
from PIL import Image
import pytesseract
from web_scrap import SeleniumScraper  # Import the web scraper class
import yt_dlp
# Load environment variables from .env
load_dotenv()

# API Keys and Configuration
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
MODEL = "llama-3.1-sonar-small-128k-online"
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")

# Word limit
WORD_LIMIT = 50000

# Helper Functions
def truncate_to_word_limit(text, word_limit=WORD_LIMIT):
    words = text.split()
    return " ".join(words[:word_limit])

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
    return truncate_to_word_limit(text)

def extract_text_from_word(file_path):
    doc = Document(file_path)
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    return truncate_to_word_limit(text)

def load_text(file_path):
    if os.path.isfile(file_path):
        if file_path.endswith('.pdf'):
            return extract_text_from_pdf(file_path)
        elif file_path.endswith('.docx'):
            return extract_text_from_word(file_path)
        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            return truncate_to_word_limit(text)
        else:
            raise ValueError("Unsupported file format. Use PDF, Word (.docx), or plain text files.")
    return truncate_to_word_limit(file_path)

def audio_to_text(audio_path):
    try:
        if not audio_path.endswith(".wav"):
            sound = AudioSegment.from_file(audio_path)
            audio_path = "converted_audio.wav"
            sound.export(audio_path, format="wav")

        recognizer = sr.Recognizer()
        reprocessed_audio = "reprocessed_audio.wav"
        os.system(f"ffmpeg -y -i {audio_path} -acodec pcm_s16le -ar 16000 {reprocessed_audio}")
        audio_path = reprocessed_audio

        audio = AudioSegment.from_wav(audio_path)
        chunk_length_ms = 60 * 1000
        overlap_ms = 10 * 1000
        chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms - overlap_ms)]

        full_text = []
        for idx, chunk in enumerate(chunks):
            chunk_path = f"chunk_{idx}.wav"
            chunk.export(chunk_path, format="wav")
            with sr.AudioFile(chunk_path) as source:
                audio_chunk = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_chunk)
                full_text.append(text)
            except sr.UnknownValueError:
                print(f"Could not understand chunk {idx + 1}")
            except sr.RequestError as e:
                print(f"Error with Google Speech Recognition service: {e}")
            finally:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)

        return truncate_to_word_limit(" ".join(full_text))
    except Exception as e:
        print(f"Error processing audio file: {e}")
        return "Failed to process audio file."
    finally:
        if os.path.exists("reprocessed_audio.wav"):
            os.remove("reprocessed_audio.wav")

def extract_audio_from_video(video_path):
    try:
        output_audio_path = "extracted_audio.wav"
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(output_audio_path, codec='pcm_s16le')
        return output_audio_path
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return None

def convert_video_to_text(video_path):
    audio_path = extract_audio_from_video(video_path)
    if audio_path:
        return audio_to_text(audio_path)
    return "Failed to process the video."

# Function to convert image to text
def images_to_text(image_paths):
    """
    Extract text from a list of image file paths using Tesseract OCR.
    :param image_paths: List of paths to image files.
    :return: Dictionary with file names as keys and extracted text as values.
    """
    extracted_texts = {}
    for image_path in image_paths:
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            extracted_texts[image_path] = text
        except Exception as e:
            extracted_texts[image_path] = f"Error processing image: {e}"
    return extracted_texts

# Function to process input from the web link
def web_link_to_text(url, word_limit=50000):
    """
    Extract text from a given web link using SeleniumScraper and limit the text to the specified word limit.
    """
    scraper = SeleniumScraper(headless=True)
    content = scraper.scrape_web_content(url, word_limit=word_limit)
    # Truncate content to word limit, if necessary
    return truncate_to_word_limit(content)

def download_video(url, format="bestaudio"):
    """
    Download audio from a YouTube video using yt-dlp.

    Parameters:
    - url (str): The URL of the YouTube video.
    - format (str): Format for downloading (default: 'bestaudio').
    """
    ydl_opts = {
        'format': format,
        'outtmpl': '%(title)s.%(ext)s',  # Save as title.extension
        'quiet': False,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            return "Download completed!"
        except Exception as e:
            return f"An error occurred: {e}"

def translate_text(text, target_language):
    api_url = "https://translation.googleapis.com/language/translate/v2"
    params = {
        "q": text,
        "target": target_language,
        "format": "text",
        "key": GOOGLE_TRANSLATE_API_KEY,
    }
    try:
        response = requests.post(api_url, params=params)
        response.raise_for_status()
        return response.json()["data"]["translations"][0]["translatedText"]
    except requests.exceptions.RequestException as e:
        return f"Error during translation: {e}"

def query_perplexity(prompt):
    if not PERPLEXITY_API_KEY:
        raise ValueError("Perplexity API key is missing.")

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant for generating educational questions."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 10000,
    }
    try:
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"Error querying Perplexity API: {e}"
    
# Question generation functions with difficulty
def generate_mcq(syllabus, num_questions, difficulty):
    prompt = f"""
    Syllabus:
    {syllabus}

    Based on the syllabus above, generate {num_questions} multiple-choice questions (MCQs).
    Provide 4 options for each question, and clearly indicate the correct answer.
    Difficulty Level: {difficulty}.
    """
    return query_perplexity(prompt)

def generate_fill_in_the_blanks(syllabus, num_questions, difficulty):
    prompt = f"""
    Syllabus:
    {syllabus}

    Instructions:
    - Generate {num_questions} 'Fill in the Blanks' questions.
    - Do NOT repeat any context or explanation from the syllabus within the questions.
    - Format the output **strictly** as below, or the response will be considered incorrect.
    - Include concise answers and explanations at the end.

    Format:

    Questions:
    1. Fill in the blank: Question text with ____________.
    2. Fill in the blank: Question text with ____________.

    Answers:
    1. Correct Answer - Brief Explanation
    2. Correct Answer - Brief Explanation

    Failure to strictly follow the format will result in rejection. Ensure all blanks are clear and concise.
    Difficulty Level: {difficulty}.
    """
    return query_perplexity(prompt)

def generate_true_false(syllabus, num_questions, difficulty):
    prompt = f"""
    Syllabus:
    {syllabus}

    Based on the syllabus above, generate {num_questions} True/False questions.
    Clearly indicate the correct answers.
    Difficulty Level: {difficulty}.
    """
    return query_perplexity(prompt)

def generate_matching_questions(syllabus, num_questions, difficulty):
    prompt = f"""
    Syllabus:
    {syllabus}

    Generate {num_questions} matching questions based on the syllabus.

    **Instructions**:
    - Provide {num_questions} pairs of terms/items in two columns.
    - Format the response EXACTLY as follows:

    Example:
    1. Term A1 | Match A1
    2. Term A2 | Match A2
    3. Term A3 | Match A3

    **Output Format**:
    - No extra explanations, no introductions, and no additional context.
    - Each line should contain exactly one pair, separated by '|' symbol.
    - Only output the pairs as shown in the example above.
    """

    # Call Perplexity API
    matching_pairs = query_perplexity(prompt)
    print("Raw API Response:", matching_pairs)  # Debugging raw response

    matching_pairs = query_perplexity(prompt)
    col1, col2 = [], []

    # Split pairs and shuffle
    for pair in matching_pairs.split('\n'):
        if '|' in pair:
            left, right = map(str.strip, pair.split('|'))
            col1.append(left)
            col2.append(right)

    random.shuffle(col1)
    random.shuffle(col2)
    return col1, col2
  
# Main Function

def main():
    print("Welcome to the Question Generator")

    input_type = input("Enter input type (Text, File, Image, Audio, Video, Youtube, Web link): ").strip().lower()
    syllabus = None

    if input_type == "text":
        syllabus = truncate_to_word_limit(input("Enter the syllabus or content: "))

    elif input_type == "file":
        file_path = input("Enter the file path: ").strip()
        syllabus = load_text(file_path)

    elif input_type == "audio":
        audio_path = input("Enter the audio file path: ").strip()
        syllabus = audio_to_text(audio_path)

    elif input_type == "video":
        video_path = input("Enter the video file path: ").strip()
        syllabus = convert_video_to_text(video_path)

    elif input_type == "image":
        image_paths = input("Enter the paths to image files (comma-separated): ").strip().split(',')
        image_texts = images_to_text(image_paths)
        syllabus = "\n".join(image_texts.values())

    elif input_type == "web link":
        url = input("Enter the web link (URL): ").strip()
        syllabus = web_link_to_text(url)

    elif input_type == "youtube":
        youtube_url = input("Enter the YouTube video URL: ").strip()
        print("Downloading audio from YouTube...")
        audio_file_path = download_video(youtube_url, format="bestaudio")
        
        if audio_file_path:
            print(f"Audio downloaded to: {audio_file_path}")
            print("Converting audio to text...")
            syllabus = audio_to_text(audio_file_path)
            print(f"Extracted Syllabus: {syllabus}")
        else:
            print("Failed to download or process the YouTube video.")
    else:
        print("Invalid input type.")
        return

    print(f"Extracted Syllabus (Truncated to {WORD_LIMIT} words): {syllabus}")

    question_type = input("Select question type (MCQ, Fill in the Blanks, True/False, Matching): ").strip()
    num_questions = int(input("Enter the number of questions: "))
    difficulty = input("Enter difficulty level (easy, medium, hard): ").strip().lower()
    output_language = input("Enter desired output language (e.g., en for English, hi for Hindi): ").strip()

    if question_type.lower() == "mcq":
        result = generate_mcq(syllabus, num_questions, difficulty)
    elif question_type.lower() == "fill in the blanks":
        result = generate_fill_in_the_blanks(syllabus, num_questions, difficulty)
    elif question_type.lower() == "true/false":
        result = generate_true_false(syllabus, num_questions, difficulty)
    elif question_type.lower() == "matching":
        col1, col2 = generate_matching_questions(syllabus, num_questions, difficulty)
        result = "\n".join([f"{l} | {r}" for l, r in zip(col1, col2)])
    else:
        print("Invalid question type.")
        return

    translated_result = translate_text(result, output_language)
    print("\nGenerated Questions:")
    print(translated_result)

if __name__ == "__main__":
    main()
