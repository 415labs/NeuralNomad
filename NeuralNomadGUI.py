# if using SSH to the device: export DISPLAY=:0

"""GUI application for Neural Nomad."""

from tkinter import *
import json
import os
import re
import subprocess
import sys
import threading
import time
import warnings
import wave
from pathlib import Path

import customtkinter
import ollama
import PIL
import whisper
from PIL import Image
from piper.voice import PiperVoice
import tkinter as tk


alphabets= "([A-Za-z])"
prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = "(Mr|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov|edu|me)"
digits = "([0-9])"
multiple_dots = r'\.{2,}'

def split_into_sentences(text: str) -> list[str]:
    """
    Split the text into sentences.

    If the text contains substrings "<prd>" or "<stop>", they would lead 
    to incorrect splitting because they are used as markers for splitting.

    :param text: text to be split into sentences
    :type text: str

    :return: list of sentences
    :rtype: list[str]
    """
    text = " " + text + "  "
    text = text.replace("\n"," ")
    text = re.sub(prefixes,"\\1<prd>",text)
    text = re.sub(websites,"<prd>\\1",text)
    text = re.sub(digits + "[.]" + digits,"\\1<prd>\\2",text)
    text = re.sub(multiple_dots, lambda match: "<prd>" * len(match.group(0)) + "<stop>", text)
    if "Ph.D" in text: text = text.replace("Ph.D.","Ph<prd>D<prd>")
    text = re.sub("\s" + alphabets + "[.] "," \\1<prd> ",text)
    text = re.sub(acronyms+" "+starters,"\\1<stop> \\2",text)
    text = re.sub(alphabets + "[.]" + alphabets + "[.]" + alphabets + "[.]","\\1<prd>\\2<prd>\\3<prd>",text)
    text = re.sub(alphabets + "[.]" + alphabets + "[.]","\\1<prd>\\2<prd>",text)
    text = re.sub(" "+suffixes+"[.] "+starters," \\1<stop> \\2",text)
    text = re.sub(" "+suffixes+"[.]"," \\1<prd>",text)
    text = re.sub(" " + alphabets + "[.]"," \\1<prd>",text)
    if "”" in text: text = text.replace(".”","”.")
    if "\"" in text: text = text.replace(".\"","\".")
    if "!" in text: text = text.replace("!\"","\"!")
    if "?" in text: text = text.replace("?\"","\"?")
    text = text.replace(".",".<stop>")
    text = text.replace("?","?<stop>")
    text = text.replace("!","!<stop>")
    text = text.replace("<prd>",".")
    sentences = text.split("<stop>")
    sentences = [s.strip() for s in sentences]
    if sentences and not sentences[-1]: sentences = sentences[:-1]
    return sentences

def audio_play(text_tts):
    """Plays text using text-to-speech via piper and aplay.
    
    Args:
        text_tts: Text string to convert to speech.
    """
    print("TTS now...")
    cmd = (f"echo '{text_tts}' | /home/mosfet/NeuralNomad/my-venv/bin/piper "
           "--model en_US-lessac-medium --output-raw | "
           "aplay -r 22000 -f S16_LE -t raw")
    os.system(cmd)



def audio_record():
    """Records audio input and converts it to text using speech recognition.
    
    Displays recording status via GUI elements and captures 5 seconds of audio
    using arecord. The audio is then transcribed to text using the model.
    
    Returns:
        str: The transcribed text from the audio recording.
    """
    display_mic_on()
    progressbar.place(relx=0.5, rely=0.8, anchor=CENTER)
    progressbar.configure(
        mode="determinate",
        progress_color="red",
        determinate_speed=0.2
    )
    progressbar.set(0)
    progressbar.start()  # Start the animation
    
    textbox.insert(END, "Speak now!\n")
    textbox.see(tk.END)

    # Record 5 seconds of audio
    record_cmd = (f"arecord -D hw:0,0 -d 5 -f S16 {AUDIO_FILENAME} "
                 f"-r 44100 > /dev/null 2>&1")
    os.system(record_cmd)
    display_mic_off()

    # Redirect stdout/stderr during transcription
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

    textbox.delete('1.0', END)
    textbox.insert(END, "Performing speech to text...\n")
    textbox.see(tk.END)

    progressbar.configure(mode="indeterminate", progress_color="yellow")
    text_out = model.transcribe(str(path), language='en', verbose=False)
    
    # Restore stdout/stderr
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    
    textbox.delete('0.0', END)
    return text_out['text']

def warmup_llm():
    """Warms up the LLM model with a simple test prompt.
    
    Sends a basic prompt to the model
    """
    LLM="llama3.2:1b"
    
    prompt = "what is the color of the sky? answer in a few words"
    textbox.insert(END, "Warming up the model...")
    output = ollama.chat(
        model=LLM,
        messages=[{'role': 'user', 'content': prompt}],
        stream=False)
    textbox.insert(END, "Done!\n")
    progressbar.stop()  # Stop the animation

def LLM_process_thread_func():
	textbox.delete("0.0", "end")  # delete all text
	prompt = audio_record()
	textbox.insert(END,">") 
	textbox.insert(END,prompt) 
	textbox.insert(END, "\n\n") 
	textbox.see(tk.END)
	progressbar.start()  # Start the animation
	root.update()
	stream = ollama.chat(
		model=LLM,
		messages=[{'role': 'user', 'content': prompt}],
		stream=True,
	)
	global LLMProcessing
	LLMProcessing = 1
	
	global requested_interruption
     
	progressbar.set(0)
	progressbar.stop()
	root.update()
	global response
	response=""
	progressbar.configure(mode="indeterminate", progress_color="green")
	progressbar.start()  # Start the animation

	for chunk in stream:
		if requested_interruption == 1:
			break    # break here
		textbox.insert(END,  chunk['message']['content']) 
		textbox.see(tk.END)
		response=response+chunk['message']['content']
		root.update()

	response.replace("\n", ". ")
	bad_chars = ["*", "'", "\""] # get rid of special characters
	response = ''.join(i for i in response if not i in bad_chars)
	print("Reformatted response: [", response,"]")
	progressbar.stop()  # Stop the animation


	if (audio_switch.get() == "on"):
		audio_play(response)
	LLMProcessing = 0
	requested_interruption = 0

def myapp():
    """Handles starting/stopping LLM processing in a separate thread."""
    response = ""
    
    if LLMProcessing == 0:
        thread = threading.Thread(target=LLM_process_thread_func)
        thread.start()
    else:
        requested_interruption = 1


def clear_screen():
    """Clears the text display and shows the initial prompt message."""
    textbox.delete("0.0", "end")  # delete all text
    textbox.insert(END, "Touch the mic to get started!")
    root.update()

def select_model(choice):
    """Updates the global LLM model selection.
    
    Args:
        choice: String name of the LLM model to use.
    """
    global LLM
    LLM = choice

def exit_app():
    """Exits the application by destroying the root window."""
    root.destroy()

def display_mic_on():
    """Displays the microphone 'on' button image in the GUI.
    
    Creates and places a button with the mic_on.png image at the top right
    of the window.
    """
    my_image = customtkinter.CTkImage(
        Image.open("/home/mosfet/NeuralNomad/GUI/images/mic_on.png"),
        size=(60, 60))
    mic_button = customtkinter.CTkButton(
        master=root,
        corner_radius=0,
        width=60,
        height=60,
        image=my_image,
        text="")  # display image with a CTkLabel
    mic_button.place(relx=0.9, rely=0.1, anchor=CENTER)

def display_mic_off():
    """Displays the microphone 'off' button image in the GUI.
    
    Creates and places a button with the mic_off.png image at the top right
    of the window.
    """
    my_image = customtkinter.CTkImage(
        Image.open("/home/mosfet/NeuralNomad/GUI/images/mic_off.png"),
        size=(60, 60))
    mic_button = customtkinter.CTkButton(
        master=root,
        corner_radius=0,
        width=60,
        height=60,
        command=myapp,
        image=my_image,
        text="")  # display image with a CTkLabel
    mic_button.place(relx=0.9, rely=0.1, anchor=CENTER)


# Main code

# Global constants
LLM = "llama3.2:1b"
STT_MODEL = 'tiny'
SYSTEM_INSTRUCTION = '. Provide a short, concise answer.'
AUDIO_FILENAME = 'stt-tmp.wav'

# Global variables
response = ""
global requested_interruption
requested_interruption = False

global LLMProcessing
LLMProcessing = False

# Initialize models
warnings.filterwarnings("ignore")  # Not recommended in production (TODO: remove)
model = whisper.load_model(STT_MODEL)
path = Path(AUDIO_FILENAME)

def init_main_window():
    """Initializes and configures the main application window."""
    root = customtkinter.CTk()
    root.title("NeuralNomad")
    root.attributes('-fullscreen', True)
    root.configure(cursor="none")
    return root

def init_ui_elements(root):
    """Creates and places all UI elements in the main window.
    
    Args:
        root: The main application window
    """
    # Configure appearance
    customtkinter.set_appearance_mode("dark")
    customtkinter.set_default_color_theme("blue")
    
    # Create widgets
    title_button = customtkinter.CTkButton(
        master=root,
        text="-[ NeuralNomad ]-",
        font=("Fixedsys", 26),
        command=clear_screen
    )
    
    model_menu = customtkinter.CTkOptionMenu(
        master=root,
        command=select_model,
        width=170,
        height=30,
        font=("Fixedsys", 14),
        dynamic_resizing=False,
        values=["llama3.2:1b", "tinyllama", "gemma2:2b", 
               "qwen2:0.5b", "phi3:3.8b-mini-128k-instruct-q3_K_S", "llama3.1:8b"]
    )
    
    global audio_switch
    audio_switch = customtkinter.StringVar(value="on")
    audio_toggle = customtkinter.CTkSwitch(
        master=root,
        text="Audio out",
        switch_width=55,
        switch_height=30,
        font=("Fixedsys", 14),
        variable=audio_switch,
        onvalue="on",
        offvalue="off"
    )
    
    exit_button = customtkinter.CTkButton(
        master=root,
        text="Exit",
        width=60,
        height=30,
        font=("Fixedsys", 14),
        command=exit_app
    )
    
    textbox = customtkinter.CTkTextbox(
        root,
        width=450,
        height=180,
        font=("Fixedsys", 14)
    )
    
    progressbar = customtkinter.CTkProgressBar(
        root,
        orientation="horizontal",
        width=200,
        height=20,
        mode="indeterminate"
    )

    # Place widgets
    title_button.place(relx=0.35, rely=0.1, anchor=CENTER)
    model_menu.place(relx=0.2, rely=0.9, anchor=CENTER)
    audio_toggle.place(relx=0.6, rely=0.9, anchor=CENTER)
    audio_toggle.deselect()
    exit_button.place(relx=0.9, rely=0.9, anchor=CENTER)
    textbox.place(relx=0.5, rely=0.5, anchor=CENTER)
    
    return textbox, progressbar

# Initialize application
root = init_main_window()
textbox, progressbar = init_ui_elements(root)

# Setup initial state
display_mic_off()
warmup_llm()

textbox.insert(END, "Touch the mic to get started!")
textbox.see(tk.END)

root.mainloop()
