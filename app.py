import streamlit as st
import speech_recognition as sr
import soundfile as sf
import os
import tempfile
import time
import subprocess

# Check if ffmpeg is available
try:
    subprocess.run(["ffmpeg", "-version"], check=True)
    subprocess.run(["ffprobe", "-version"], check=True)
    st.success("FFmpeg is available!")
except FileNotFoundError:
    st.error("FFmpeg or ffprobe is not available.")

# Specify the directory in the project folder to save audio files and transcripts
project_folder = "transcripts"  # Create a folder named "transcripts" in your project directory
os.makedirs(project_folder, exist_ok=True)

# Function to convert audio to WAV format
def convert_to_wav(audio_file):
    # Load the audio file and save as a temporary WAV file
    audio_data, sample_rate = sf.read(audio_file)
    wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(wav_file.name, audio_data, sample_rate)
    return wav_file.name

# Function to try transcribing the entire audio first
def transcribe_whole_audio(audio_file):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="th-TH")
        return text, None  # If successful, return the transcription and no error
    except sr.RequestError as e:
        return None, f"Request error: {e}"
    except sr.UnknownValueError:
        return None, "Could not understand audio"

# Function to transcribe audio in chunks if full transcription fails
def transcribe_audio_in_chunks(audio_file):
    recognizer = sr.Recognizer()
    audio_data, sample_rate = sf.read(audio_file)
    
    chunk_length = 30 * sample_rate  # 30 seconds in samples
    num_chunks = len(audio_data) // chunk_length + (len(audio_data) % chunk_length > 0)
    recognized_text = []

    for i in range(num_chunks):
        start_sample = i * chunk_length
        end_sample = start_sample + chunk_length
        chunk = audio_data[start_sample:end_sample]

        chunk_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        sf.write(chunk_file.name, chunk, sample_rate)

        with sr.AudioFile(chunk_file.name) as source:
            audio_data_chunk = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data_chunk, language="th-TH")
                recognized_text.append(text)
            except sr.UnknownValueError:
                recognized_text.append("Could not understand audio")
            except sr.RequestError as e:
                recognized_text.append(f"Could not request results; {e}")

    full_text = "\n".join(recognized_text)
    return full_text

# Streamlit app
st.title("Thai Audio Transcription App")
st.write("Upload an audio file (WAV or M4A format) to transcribe.")

# File uploader
uploaded_file = st.file_uploader("Choose an audio file", type=["wav", "m4a"])

if uploaded_file is not None:
    try:
        # Check if the uploaded file is not a WAV file
        if uploaded_file.type != "audio/wav":
            st.write("Converting audio to WAV format...")
            wav_file_path = convert_to_wav(uploaded_file)  # Convert to WAV
        else:
            wav_file_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
            with open(wav_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        st.audio(wav_file_path)  # Play the uploaded audio file
    except Exception as e:
        st.error(f"Error processing audio file: {str(e)}")

    if st.button("Transcribe"):
        with st.spinner("Transcribing..."):
            # First try to transcribe the whole audio
            transcription, error_message = transcribe_whole_audio(wav_file_path)

            if transcription is None:
                # If whole transcription fails, show the error and fallback to chunking
                transcription = transcribe_audio_in_chunks(wav_file_path)

        # Show the transcription result
        st.subheader("Transcription Result:")
        st.write(transcription)

        # Provide a download link for the transcription as text
        st.download_button(
            label="Download Transcription",
            data=transcription,
            file_name="recognized_text.txt",
            mime="text/plain"
        )
