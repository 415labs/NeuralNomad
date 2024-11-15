import os
import subprocess
import whisper
from pathlib import Path
import json
import warnings
import ollama
import time
import sys

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


#disable all warnings (not recommended!)
warnings.filterwarnings("ignore")

LLM="qwen2:0.5b"
LLM="gemma2:2b"
LLM="llama3.1:8b"
LLM="qwen2:0.5b"
LLM="llama3.1:8b"
LLM="gemma2:2b"
LLM="tinyllama"

STTModel='tiny'
SystemInstruction = '. Provide a short, concise answer.'



model = whisper.load_model('tiny')
filename = 'stt-tmp.wav'
path = Path(filename)
print(bcolors.BOLD + '>> Welcome to NeuralNomad' + bcolors.ENDC)
print('>> STT: Whisper-tiny')
print('>> LLM: ' + LLM)
print('>> System Instruction:' + SystemInstruction)

time.sleep(1)
prompt=""

while 1:
	while len(prompt)<1:
		print(bcolors.RED + '[Mic ON]' + bcolors.ENDC + bcolors.BOLD + ' - Ask me anything! You have 7 seconds.' + bcolors.ENDC)
		os.system("arecord -D hw:0,0 -d 7 -f S16 " + filename + " -r 44100 > /dev/null 2>&1")
		print('Voice processing...')
		sys.stdout = open(os.devnull, "w")
		sys.stderr = open(os.devnull, "w")
		result = model.transcribe(str(path), language='en', verbose=False)
		sys.stdout = sys.__stdout__
		sys.stderr = sys.__stderr__
		prompt = result['text']
		if (len(prompt)<1):
			print("I did not get it - Let's try again!\n")
			time.sleep(1)

	SystemInstruction = '. Provide a short, concise answer'
	print("Prompt: " + bcolors.BOLD + prompt + bcolors.ENDC)
	stream = ollama.chat(
		model=LLM,
		messages=[{'role': 'user', 'content': prompt + SystemInstruction}],
		stream=True,
	)
	output = ""
	for chunk in stream:
		print(bcolors.BOLD + chunk['message']['content'] + bcolors.ENDC, end='', flush=True)
		output = output + chunk['message']['content']

	os.system("echo '" +  output + "' |   ./my-venv/bin/piper --model en_US-lessac-medium  --output-raw | aplay -r 22000 -f S16_LE -t raw")

	print("\n")
	prompt=""
	time.sleep(1)
