import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import queue
import json
import os
import datetime
import ast
import operator as op
import sounddevice as sd
import pyttsx3
from vosk import Model, KaldiRecognizer


# ============================================================
# FRIDAY - OFFLINE AI ASSISTANT
# ============================================================

APP_NAME = "FRIDAY"

# ------------------------------------------------------------
# Find Vosk model
# ------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")


def find_vosk_model():
    """
    Looks for a Vosk model in:
        FRIDAY/model/
    or
        FRIDAY/model/vosk-model-small-en-us-0.15/
    """

    if not os.path.exists(MODEL_DIR):
        return None

    # Check if model files are directly inside model/
    required = ["am", "conf"]

    if all(os.path.exists(os.path.join(MODEL_DIR, x))
           for x in required):
        return MODEL_DIR

    # Check subfolders
    for item in os.listdir(MODEL_DIR):
        possible = os.path.join(MODEL_DIR, item)

        if os.path.isdir(possible):
            if all(os.path.exists(os.path.join(possible, x))
                   for x in required):
                return possible

    return None


VOSK_MODEL_PATH = find_vosk_model()

vosk_model = None

if VOSK_MODEL_PATH:
    try:
        vosk_model = Model(VOSK_MODEL_PATH)
    except Exception as e:
        print("Vosk model error:", e)


# ------------------------------------------------------------
# Text-to-Speech
# ------------------------------------------------------------

engine = pyttsx3.init()

engine.setProperty("rate", 165)
engine.setProperty("volume", 1.0)


def speak(text):
    """
    Speak response offline.
    """

    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("Speech error:", e)


# ------------------------------------------------------------
# Safe calculator
# ------------------------------------------------------------

allowed_operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
}


def calculate(expression):

    def evaluate(node):

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value

        if isinstance(node, ast.BinOp):
            left = evaluate(node.left)
            right = evaluate(node.right)

            operator_type = type(node.op)

            if operator_type in allowed_operators:
                return allowed_operators[operator_type](left, right)

        if isinstance(node, ast.UnaryOp):
            value = evaluate(node.operand)

            operator_type = type(node.op)

            if operator_type in allowed_operators:
                return allowed_operators[operator_type](value)

        raise ValueError("Invalid calculation")

    tree = ast.parse(expression, mode="eval")

    return evaluate(tree.body)


# ------------------------------------------------------------
# Add message to conversation
# ------------------------------------------------------------

def add_message(sender, message):

    conversation.config(state=tk.NORMAL)

    conversation.insert(
        tk.END,
        f"{sender}: {message}\n\n"
    )

    conversation.see(tk.END)

    conversation.config(state=tk.DISABLED)


# ------------------------------------------------------------
# FRIDAY command processor
# ------------------------------------------------------------

def process_command(command):

    command = command.lower().strip()

    if not command:
        return

    add_message("YOU", command)

    # ------------------------------------------
    # HELLO
    # ------------------------------------------

    if "hello" in command or "hi" in command:

        response = "Hello. I am FRIDAY. How can I help you?"

    # ------------------------------------------
    # TIME
    # ------------------------------------------

    elif "time" in command:

        current_time = datetime.datetime.now().strftime("%I:%M %p")

        response = f"The current time is {current_time}."

    # ------------------------------------------
    # DATE
    # ------------------------------------------

    elif "date" in command:

        current_date = datetime.datetime.now().strftime("%d %B %Y")

        response = f"Today's date is {current_date}."

    # ------------------------------------------
    # WHO ARE YOU
    # ------------------------------------------

    elif "who are you" in command or "your name" in command:

        response = (
            "I am FRIDAY, your offline personal assistant. "
            "I can recognize speech and perform simple commands "
            "without cloud services."
        )

    # ------------------------------------------
    # CALCULATOR
    # ------------------------------------------

    elif command.startswith("calculate"):

        expression = command.replace("calculate", "", 1).strip()

        try:
            result = calculate(expression)

            response = f"The answer is {result}"

        except Exception:
            response = (
                "I could not calculate that. "
                "Please use numbers and operators such as plus, minus, "
                "multiply or divide."
            )

    # ------------------------------------------
    # SIMPLE MATH COMMANDS
    # ------------------------------------------

    elif "what is" in command and any(
        symbol in command for symbol in ["+", "-", "*", "/"]
    ):

        try:

            expression = command.replace("what is", "").strip()

            result = calculate(expression)

            response = f"The answer is {result}"

        except Exception:

            response = "Sorry, I could not calculate that."

    # ------------------------------------------
    # NOTE
    # ------------------------------------------

    elif command.startswith("note"):

        note = command.replace("note", "", 1).strip()

        if note:

            with open(
                os.path.join(BASE_DIR, "notes.txt"),
                "a",
                encoding="utf-8"
            ) as file:

                file.write(
                    datetime.datetime.now().strftime(
                        "%d-%m-%Y %H:%M"
                    )
                    + " - "
                    + note
                    + "\n"
                )

            response = "Your note has been saved."

        else:

            response = "Please tell me what you want me to note."

    # ------------------------------------------
    # SHOW NOTES
    # ------------------------------------------

    elif "show notes" in command:

        notes_file = os.path.join(BASE_DIR, "notes.txt")

        if os.path.exists(notes_file):

            with open(
                notes_file,
                "r",
                encoding="utf-8"
            ) as file:

                notes = file.read()

            if notes.strip():

                response = "Here are your saved notes."

                add_message("FRIDAY", notes)

            else:

                response = "You don't have any saved notes."

        else:

            response = "You don't have any saved notes."

    # ------------------------------------------
    # STATUS
    # ------------------------------------------

    elif "status" in command:

        response = "All systems are working. FRIDAY is ready."

    # ------------------------------------------
    # EXIT
    # ------------------------------------------

    elif "exit" in command or "quit" in command:

        response = "Goodbye."

        add_message("FRIDAY", response)

        speak(response)

        root.after(1000, root.destroy)

        return

    # ------------------------------------------
    # UNKNOWN COMMAND
    # ------------------------------------------

    else:

        response = (
            "I heard you say "
            + command
            + ". I don't have a command for that yet."
        )

    add_message("FRIDAY", response)

    threading.Thread(
        target=speak,
        args=(response,),
        daemon=True
    ).start()


# ------------------------------------------------------------
# Voice recognition
# ------------------------------------------------------------

audio_queue = queue.Queue()

listening = False


def audio_callback(indata, frames, time, status):

    if status:
        print(status)

    audio_queue.put(bytes(indata))


def listen():

    global listening

    if not vosk_model:

        add_message(
            "SYSTEM",
            "Vosk model not found. Put the model inside the model folder."
        )

        speak(
            "Vosk model not found. Please put the offline model inside the model folder."
        )

        return

    if listening:
        return

    listening = True

    status_label.config(
        text="● LISTENING..."
    )

    listen_button.config(
        state=tk.DISABLED
    )

    stop_button.config(
        state=tk.NORMAL
    )

    # Clear old audio
    while not audio_queue.empty():

        try:
            audio_queue.get_nowait()

        except queue.Empty:
            break

    threading.Thread(
        target=recognize_speech,
        daemon=True
    ).start()


def recognize_speech():

    global listening

    recognizer = KaldiRecognizer(
        vosk_model,
        16000
    )

    recognizer.SetWords(True)

    try:

        with sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=audio_callback
        ):

            start_time = datetime.datetime.now()

            while listening:

                # Stop after 10 seconds
                elapsed = (
                    datetime.datetime.now()
                    - start_time
                ).total_seconds()

                if elapsed > 10:
                    break

                try:

                    data = audio_queue.get(
                        timeout=0.5
                    )

                except queue.Empty:

                    continue

                if recognizer.AcceptWaveform(data):

                    result = json.loads(
                        recognizer.Result()
                    )

                    text = result.get(
                        "text",
                        ""
                    )

                    if text.strip():

                        root.after(
                            0,
                            lambda t=text:
                            process_command(t)
                        )

                        break

            # Get final result
            if listening:

                final_result = json.loads(
                    recognizer.FinalResult()
                )

                final_text = final_result.get(
                    "text",
                    ""
                )

                if final_text.strip():

                    root.after(
                        0,
                        lambda t=final_text:
                        process_command(t)
                    )

    except Exception as e:

        root.after(
            0,
            lambda:
            add_message(
                "SYSTEM",
                f"Microphone error: {e}"
            )
        )

    finally:

        listening = False

        root.after(
            0,
            reset_listen_button
        )


def reset_listen_button():

    status_label.config(
        text="● READY"
    )

    listen_button.config(
        state=tk.NORMAL
    )

    stop_button.config(
        state=tk.DISABLED
    )


def stop_listening():

    global listening

    listening = False

    reset_listen_button()


# ------------------------------------------------------------
# GUI
# ------------------------------------------------------------

root = tk.Tk()

root.title(
    "FRIDAY - Offline AI Assistant"
)

root.geometry(
    "1100x700"
)

root.minsize(
    900,
    600
)

root.configure(
    bg="#07111f"
)


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------

header = tk.Frame(
    root,
    bg="#07111f"
)

header.pack(
    fill="x",
    padx=30,
    pady=20
)


title = tk.Label(
    header,
    text="FRIDAY",
    font=("Arial", 30, "bold"),
    fg="white",
    bg="#07111f"
)

title.pack(
    side="left"
)


subtitle = tk.Label(
    header,
    text="   OFFLINE AI ASSISTANT",
    font=("Arial", 13, "bold"),
    fg="#00bfff",
    bg="#07111f"
)

subtitle.pack(
    side="left",
    pady=10
)


status_label = tk.Label(
    header,
    text="● READY",
    font=("Arial", 11, "bold"),
    fg="#00ff88",
    bg="#07111f"
)

status_label.pack(
    side="right"
)


# ------------------------------------------------------------
# Main area
# ------------------------------------------------------------

main_frame = tk.Frame(
    root,
    bg="#07111f"
)

main_frame.pack(
    fill="both",
    expand=True,
    padx=30,
    pady=10
)


# ------------------------------------------------------------
# Left panel
# ------------------------------------------------------------

left_panel = tk.Frame(
    main_frame,
    bg="#0b1728",
    width=350
)

left_panel.pack(
    side="left",
    fill="y",
    padx=(0, 15)
)

left_panel.pack_propagate(False)


core_title = tk.Label(
    left_panel,
    text="FRIDAY CORE",
    font=("Arial", 18, "bold"),
    fg="white",
    bg="#0b1728"
)

core_title.pack(
    pady=30
)


# Circle

canvas = tk.Canvas(
    left_panel,
    width=250,
    height=250,
    bg="#0b1728",
    highlightthickness=0
)

canvas.pack()

canvas.create_oval(
    40, 40,
    210, 210,
    outline="#1688d8",
    width=2
)

canvas.create_oval(
    65, 65,
    185, 185,
    outline="#1688d8",
    width=2
)

canvas.create_oval(
    90, 90,
    160, 160,
    fill="#00bfff",
    outline="#00bfff"
)


ready_text = tk.Label(
    left_panel,
    text="Ready for your next command",
    font=("Arial", 12),
    fg="white",
    bg="#0b1728"
)

ready_text.pack(
    pady=10
)


# Quick commands

quick_title = tk.Label(
    left_panel,
    text="Quick Commands",
    font=("Arial", 11, "bold"),
    fg="#00bfff",
    bg="#0b1728"
)

quick_title.pack(
    pady=(20, 10)
)


def quick_command(command):

    process_command(command)


time_button = tk.Button(
    left_panel,
    text="🕐  Time",
    command=lambda: quick_command("time"),
    font=("Arial", 11),
    fg="white",
    bg="#13253a",
    activebackground="#1c3955",
    activeforeground="white",
    relief="flat",
    width=25,
    pady=8
)

time_button.pack(
    pady=5
)


calc_button = tk.Button(
    left_panel,
    text="🧮  Calculator",
    command=lambda: quick_command("calculate 10 + 20"),
    font=("Arial", 11),
    fg="white",
    bg="#13253a",
    activebackground="#1c3955",
    activeforeground="white",
    relief="flat",
    width=25,
    pady=8
)

calc_button.pack(
    pady=5
)


note_button = tk.Button(
    left_panel,
    text="📝  Note",
    command=lambda: quick_command("note remember my project"),
    font=("Arial", 11),
    fg="white",
    bg="#13253a",
    activebackground="#1c3955",
    activeforeground="white",
    relief="flat",
    width=25,
    pady=8
)

note_button.pack(
    pady=5
)


# ------------------------------------------------------------
# Right panel
# ------------------------------------------------------------

right_panel = tk.Frame(
    main_frame,
    bg="#0b1728"
)

right_panel.pack(
    side="right",
    fill="both",
    expand=True
)


conversation_title = tk.Label(
    right_panel,
    text="Conversation",
    font=("Arial", 20, "bold"),
    fg="white",
    bg="#0b1728"
)

conversation_title.pack(
    anchor="w",
    padx=25,
    pady=(25, 10)
)


conversation = scrolledtext.ScrolledText(
    right_panel,
    wrap=tk.WORD,
    font=("Arial", 12),
    bg="#07111f",
    fg="white",
    insertbackground="white",
    relief="flat",
    padx=15,
    pady=15
)

conversation.pack(
    fill="both",
    expand=True,
    padx=25,
    pady=10
)

conversation.config(
    state=tk.DISABLED
)


# ------------------------------------------------------------
# Initial messages
# ------------------------------------------------------------

if vosk_model:

    add_message(
        "FRIDAY",
        "System online. I am ready to help — completely offline."
    )

    add_message(
        "SYSTEM",
        "Vosk model loaded successfully. Click LISTEN and speak."
    )

else:

    add_message(
        "FRIDAY",
        "System online. I am ready to help — completely offline."
    )

    add_message(
        "SYSTEM",
        "Vosk model not found. Put an offline Vosk model inside the model folder."
    )


# ------------------------------------------------------------
# Bottom controls
# ------------------------------------------------------------

bottom = tk.Frame(
    right_panel,
    bg="#0b1728"
)

bottom.pack(
    fill="x",
    padx=25,
    pady=20
)


listen_button = tk.Button(
    bottom,
    text="🎤  LISTEN",
    command=listen,
    font=("Arial", 12, "bold"),
    fg="white",
    bg="#0088cc",
    activebackground="#00aaff",
    activeforeground="white",
    relief="flat",
    padx=30,
    pady=12
)

listen_button.pack(
    side="left"
)


stop_button = tk.Button(
    bottom,
    text="■  STOP",
    command=stop_listening,
    font=("Arial", 12, "bold"),
    fg="white",
    bg="#7a2020",
    activebackground="#aa3030",
    activeforeground="white",
    relief="flat",
    padx=30,
    pady=12,
    state=tk.DISABLED
)

stop_button.pack(
    side="left",
    padx=10
)


# ------------------------------------------------------------
# Text command box
# ------------------------------------------------------------

command_entry = tk.Entry(
    bottom,
    font=("Arial", 12),
    bg="#13253a",
    fg="white",
    insertbackground="white",
    relief="flat"
)

command_entry.pack(
    side="left",
    fill="x",
    expand=True,
    padx=10,
    ipady=10
)


def send_text_command():

    text = command_entry.get().strip()

    if text:

        command_entry.delete(
            0,
            tk.END
        )

        process_command(text)


send_button = tk.Button(
    bottom,
    text="SEND",
    command=send_text_command,
    font=("Arial", 11, "bold"),
    fg="white",
    bg="#0088cc",
    activebackground="#00aaff",
    relief="flat",
    padx=20,
    pady=10
)

send_button.pack(
    side="right"
)


command_entry.bind(
    "<Return>",
    lambda event: send_text_command()
)


# ------------------------------------------------------------
# Start application
# ------------------------------------------------------------

root.mainloop()
