# if using SSH to the device: export DISPLAY=:0
 
from tkinter import *
import tkinter as tk
import customtkinter
import time
import os
import subprocess
import whisper
from pathlib import Path
import json
import warnings
import ollama
import time
import sys
import threading
import PIL
from PIL import Image
import wave
from piper.voice import PiperVoice

import re
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

def audio_play(text_TTS):
	print("TTS now...")
	os.system("echo '" +  text_TTS + "' |   /home/mosfet/NeuralNomad/my-venv/bin/piper --model en_US-lessac-medium  --output-raw | aplay -r 22000 -f S16_LE -t raw")

def audio_record():
	display_mic_on()
	progressbar.place(relx=0.5, rely=0.8, anchor=CENTER)
	progressbar.configure(mode="determinate", progress_color="red", determinate_speed=0.2)
	progressbar.set(0)
	progressbar.start()  # Start the animation
	
	textbox.insert(END,  "Speak now!\n") 
	textbox.see(tk.END)

	os.system("arecord -D hw:0,0 -d 5 -f S16 " + filename + " -r 44100 > /dev/null 2>&1")
	display_mic_off()
	sys.stdout = open(os.devnull, "w")
	sys.stderr = open(os.devnull, "w")

	textbox.delete('1.0', END)
	textbox.insert(END,  "Performing speech to text...\n") 
	textbox.see(tk.END)

	progressbar.configure(mode="indeterminate", progress_color="yellow")
	text_out = model.transcribe(str(path), language='en', verbose=False)
	sys.stdout = sys.__stdout__
	sys.stderr = sys.__stderr__
	textbox.delete('0.0', END)
	return text_out['text']

def warmup_LLM():
	prompt = "what is the color of the sky? answer in a few words"
	textbox.insert(END, "Warming up the model...") 
	output = ollama.chat(
		model=LLM,
		messages=[{'role': 'user', 'content': prompt}],
		stream=False,
		)
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
	global requestedInterruption
	
	progressbar.set(0)
	progressbar.stop()
	root.update()
	global response
	response=""
	progressbar.configure(mode="indeterminate", progress_color="green")
	progressbar.start()  # Start the animation

	for chunk in stream:
		if requestedInterruption == 1:
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
	requestedInterruption = 0

def myapp():
	response=""
	global LLMProcessing
	global requestedInterruption
	if (LLMProcessing == 0):
			thread = threading.Thread(target=LLM_process_thread_func)
			thread.start()
	else:
		requestedInterruption=1


def clearScreen():
	textbox.delete("0.0", "end")  # delete all text
	textbox.insert(END,  "Touch the mic to get started!") 
	root.update()

def select_model(choice):
	global LLM
	LLM=choice

def exit_app():
    root.destroy()

def display_mic_on():
	my_image = customtkinter.CTkImage(Image.open("/home/mosfet/NeuralNomad/GUI/images/mic_on.png"), size=(60, 60))
	mic_button = customtkinter.CTkButton(master=root, corner_radius=0, width=60, height=60, image=my_image, text="")  # display image with a CTkLabel
	mic_button.place(relx=0.9, rely=0.1, anchor=CENTER)

def display_mic_off():
	my_image = customtkinter.CTkImage(Image.open("/home/mosfet/NeuralNomad/GUI/images/mic_off.png"), size=(60, 60))
	mic_button = customtkinter.CTkButton(master=root, corner_radius=0, width=60, height=60, command=myapp, image=my_image, text="")  # display image with a CTkLabel
	mic_button.place(relx=0.9, rely=0.1, anchor=CENTER)

LLM="gemma2:2b"
LLM="llama3.1:8b"
LLM="qwen2:0.5b"
LLM="llama3.1:8b"
LLM="gemma2:2b"
LLM="qwen2:0.5b"
LLM="tinyllama"
LLM="llama3.2:1b"

STTModel='tiny'
SystemInstruction = '. Provide a short, concise answer.'

#disable all warnings (not recommended!)
warnings.filterwarnings("ignore")

response=""


model = whisper.load_model('tiny')
filename = 'stt-tmp.wav'
path = Path(filename)

LLMProcessing = 0
requestedInterruption = 0

# Create the main window
root = customtkinter.CTk()
root.title("NeuralNomad")
root.attributes('-fullscreen', True)
root.configure(cursor="none") 

audio_switch = customtkinter.StringVar(value="on")
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

button = customtkinter.CTkButton(master=root, text="-[ NeuralNomad ]-", font=("Fixedsys",26), command=clearScreen)
button.place(relx=0.35, rely=0.1, anchor=CENTER)

optionmenu_1 = customtkinter.CTkOptionMenu(master=root, command=select_model, width=170, height=30,  font=("Fixedsys",14), dynamic_resizing=False, values=["llama3.2:1b", "tinyllama", "gemma2:2b", "qwen2:0.5b", "phi3:3.8b-mini-128k-instruct-q3_K_S", "llama3.1:8b"])
optionmenu_1.place(relx=0.2, rely=0.9, anchor=CENTER)

switch=customtkinter.CTkSwitch(master=root, text="Audio out", switch_width=55, switch_height=30,  font=("Fixedsys",14), variable=audio_switch, onvalue="on", offvalue="off")
switch.place(relx=0.6, rely=0.9, anchor=CENTER)
switch.deselect()

exitButton = customtkinter.CTkButton(master=root, text="Exit", width=60, height=30, font=("Fixedsys",14), command=exit_app)
exitButton.place(relx=0.9, rely=0.9, anchor=CENTER)

textbox = customtkinter.CTkTextbox(root, width=450, height=180,  font=("Fixedsys",14))
textbox.place(relx=0.5, rely=0.5, anchor=CENTER)

progressbar = customtkinter.CTkProgressBar(root, orientation="horizontal", width=200, height=20, mode="indeterminate")

display_mic_off()

warmup_LLM()

textbox.insert(END,  "Touch the mic to get started!") 
textbox.see(tk.END)

root.mainloop()
