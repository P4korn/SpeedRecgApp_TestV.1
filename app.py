import streamlit as st
import speech_recognition as sr
import soundfile as sf
import os
import tempfile
import time
from pydub import AudioSegment


# Specify the directory in the project folder to save audio files and transcripts
project_folder = "transcripts"  # Create a folder named "transcripts" in your project directory
os.makedirs(project_folder, exist_ok=True)

# Function to convert audio to WAV format
def convert_to_wav(audio_file):
    try:
        audio = AudioSegment.from_file(audio_file)
        wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        audio.export(wav_file.name, format="wav")
        return wav_file.name
    except Exception as e:
        st.error(f"Error converting file: {str(e)}")
        return None

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

# Initialize session state variables
if 'transcription' not in st.session_state:
    st.session_state.transcription = ""
if 'transcription_completed' not in st.session_state:
    st.session_state.transcription_completed = False

if uploaded_file is not None:
    try:
        # Check if the uploaded file is not a WAV file
        if uploaded_file.type != "audio/wav":
            st.write("Converting audio to WAV format...")
            wav_file_path = convert_to_wav(uploaded_file)  # Convert to WAV
        else:
            wav_file_path = tempfile.NamedTemporaryFile(delete=False,suffix=".wav").name
            with open(wav_file_path, "wb") as f:
                f.write(uploaded_file.read())

        st.audio(wav_file_path)  # Play the uploaded audio file

    except Exception as e:
        st.error(f"Error processing audio file: {str(e)}")

    if st.button("Transcribe"):
        with st.spinner("Transcribing..."):
            transcription, error_message = transcribe_whole_audio(wav_file_path)

            if transcription is None:
                transcription = transcribe_audio_in_chunks(wav_file_path)

            # Store the transcription in session state
            st.session_state.transcription = transcription
            st.session_state.transcription_completed = True
            
    # Show the transcription result if completed
    if st.session_state.transcription_completed:
        st.subheader("Transcription Result:")
        st.write(st.session_state.transcription)

        # Download button always shown if not cancelled
        st.download_button(
            label="Download Transcription",
            data=st.session_state.transcription,
            file_name="recognized_text.txt",
            mime="text/plain"
        )

        # Cancel button to reset the transcription
        if st.button("Cancel"):
            st.session_state.transcription = ""
            st.session_state.transcription_completed = False
            st.success("Transcription reset. Please upload a new audio file.")
