import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import random
import pygame
import cv2
import speech_recognition as sr
import threading
import pyttsx3
import webbrowser
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
from deepface import DeepFace
import time
import logging
import re
import numpy as np
mid_screen_text = {"text": ""}
is_music_paused = False
current_audio = {"playing": False, "paused": False}
song_queue = []
current_song_index = {"index": 1}



# Optional: completely disable all TensorFlow logging
logging.getLogger('tensorflow').setLevel(logging.FATAL)


# Global stop event for webcam
webcam_stop_event = threading.Event()

def play_background_video(canvas, video_path, stop_flag):
    cap = cv2.VideoCapture(video_path)
    width, height = 1019, 512

    while not stop_flag["stop"]:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        frame = cv2.resize(frame, (width, height))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)

        # Update canvas from the main thread using after()
        root.after(0, lambda: update_canvas_image(canvas, imgtk))

        # Yield control briefly to avoid blocking main thread too much
        # while still providing animation.
        # This is a simple approach; more complex video players use queues.
        root.update_idletasks() # Ensure pending tasks are processed for smooth animation
        root.update() # Update the display

    cap.release()

def update_canvas_image(canvas, imgtk):
    # Check if the canvas still exists before updating
    if canvas.winfo_exists():
        canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        canvas.imgtk = imgtk # Keep a reference!

root = tk.Tk()
root.geometry("1019x512")
root.resizable(False, False)
root.configure(bg="black")
root.title("Emotion-Based Music Player")

pygame.mixer.init()
engine = pyttsx3.init()

image_refs = []

moods = ["Happy", "Sad", "Energetic", "Relaxed", "Motivated", "Anger"]
all_emotions = [m.lower() for m in moods]

song_library = {mood: [f"{mood.lower()}{i}.mp3" for i in range(1, 6)] for mood in moods}
user_added_songs = {mood: [] for mood in moods}
temp_removed_songs = {mood: [] for mood in moods}

current_song = None
app_paused_due_to_online = False

def play_song(song_path):
    global current_song, app_paused_due_to_online
    try:
        pygame.mixer.music.load(song_path)
        pygame.mixer.music.play()
        current_song = song_path
        app_paused_due_to_online = False
    except Exception as e:
        messagebox.showerror("Error", f"Failed to play {song_path}:\n{e}")

def pause_song():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()

def resume_song():
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.unpause()

def random_color():
    return "#" + ''.join([random.choice('89ABCDEF') for _ in range(6)])

def show_splash():
    root.unbind("<Return>")
    splash = tk.Frame(root)
    splash.place(relwidth=1, relheight=1)

    try:
        img = Image.open("Background.png")
        img = img.resize((1019, 512))
        bg_photo = ImageTk.PhotoImage(img)
        image_refs.append(bg_photo)
        tk.Label(splash, image=bg_photo).place(relx=0, rely=0, relwidth=1, relheight=1)
    except:
        tk.Label(splash, text="Missing Background.png", font=("Arial", 20), fg="red", bg="black").pack(expand=True)

    # Bind Enter key to skip splash
    def skip_splash(event=None):
        show_main_menu(splash)
    root.bind("<Return>", skip_splash)

    # Automatically go to menu after 2 seconds (if Enter isn't pressed)
    root.after(50000, skip_splash)
def pause_song():
    global is_music_paused
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()
        is_music_paused = True
        current_audio["paused"] = True  # Sync VoiceZone state if active

def resume_song():
    global is_music_paused
    if is_music_paused:
        pygame.mixer.music.unpause()
        is_music_paused = False
        current_audio["paused"] = False  # Sync VoiceZone state if active


def show_main_menu(prev=None):
    if prev and prev.winfo_exists():
        prev.destroy()

    stop_animation = {"stop": False}

    main_frame = tk.Frame(root, bg="white")
    main_frame.place(relwidth=1, relheight=1)

    canvas = tk.Canvas(main_frame, bg="white", highlightthickness=0)
    canvas.place(relwidth=1, relheight=1)

    # Top-left Resume button
    resume_btn = tk.Button(main_frame, text="▶ Resume", font=("Arial", 12, "bold"),
                           bg="#2ecc71", fg="white", width=10, command=resume_song)
    resume_btn.place(x=20, y=10)

    # Top-right Pause button
    pause_btn = tk.Button(main_frame, text="⏸ Pause", font=("Arial", 12, "bold"),
                          bg="#f1c40f", fg="black", width=10, command=pause_song)
    pause_btn.place(x=880, y=10)

    # Emoji animation setup
    emojis = []
    for _ in range(15):
        x = random.randint(0, 950)
        y = random.randint(0, 500)
        emoji = canvas.create_text(x, y, text="🎵", font=("Arial", 24), fill="black")
        emojis.append((emoji, random.choice([-2, -1, 1, 2]), random.choice([-2, -1, 1, 2])))

    def animate_emojis():
        if stop_animation["stop"] or not canvas.winfo_exists():
            return
        for i, (emoji, dx, dy) in enumerate(emojis):
            coords = canvas.coords(emoji)
            if not coords:
                continue
            x, y = coords
            if x < 0 or x > 1000: dx *= -1
            if y < 0 or y > 500: dy *= -1
            canvas.move(emoji, dx, dy)
            emojis[i] = (emoji, dx, dy)
        root.after(50, animate_emojis)

    animate_emojis()

    # Title
    tk.Label(main_frame, text="Emotion-Based Music Player",
             font=("Arial", 24, "bold","underline"), fg="black", bg="white").pack(pady=40)

    # Menu buttons
    tk.Button(main_frame, text="Manual Select Emotion",
              font=("Arial", 16, "bold"), fg="white", bg="#3498db",
              width=25, height=2,
              command=lambda: (stop_animation.update({"stop": True}), show_mood_grid(main_frame))
              ).pack(pady=15)

    tk.Button(main_frame, text="AI Music Assistant",
              font=("Arial", 16, "bold"), fg="white", bg="#e67e22",
              width=25, height=2,
              command=lambda: (stop_animation.update({"stop": True}), show_ai_music_mode(main_frame))
              ).pack(pady=5)

    tk.Button(main_frame, text="Webcam Emotion Detector",
              font=("Arial", 16, "bold"), fg="white", bg="#9b59b6",
              width=25, height=2,
              command=lambda: (stop_animation.update({"stop": True}),
                               threading.Thread(target=detect_webcam_emotion_with_song_interface).start())
              ).pack(pady=5)

    tk.Button(main_frame, text="Play Your Choice",
              font=("Arial", 16, "bold"), fg="white", bg="#1abc9c",
              width=25, height=2,
              command=play_your_choice).pack(pady=5)

    tk.Button(main_frame, text="Exit",
              font=("Arial", 16, "bold"), fg="white", bg="#e74c3c",
              width=25, height=2,
              command=lambda: (stop_animation.update({"stop": True}), root.quit())
              ).pack(pady=10)



def show_mood_grid(prev):
    if prev and prev.winfo_exists():
        prev.destroy()

    frame = tk.Frame(root, bg="#ffe6f0")  # Light pink
    frame.place(relwidth=1, relheight=1)

    canvas = tk.Canvas(frame, bg="#ffe6f0", highlightthickness=0)
    canvas.place(relwidth=1, relheight=1)

# Blue music notes
    emojik = []
    for _ in range(15):
        x = random.randint(0, 950)
        y = random.randint(0, 500)
        nmoji = canvas.create_text(x, y, text="🎵", font=("Arial", 24), fill="#3498db")  # Blue
        emojik.append((nmoji, random.choice([-2, -1, 1, 2]), random.choice([-2, -1, 1, 2])))

    def animate_emojik():
        for i, (nmoji, dx, dy) in enumerate(emojik):
            x, y = canvas.coords(nmoji)
            if x < 0 or x > 1000: dx *= -1
            if y < 0 or y > 500: dy *= -1
            canvas.move(nmoji, dx, dy)
            emojik[i] = (nmoji, dx, dy)
        root.after(50, animate_emojik)

    animate_emojik()

    frame.place(relwidth=1, relheight=1)

    row, col = 0, 0
    for mood in moods:
        try:
            img = Image.open(f"{mood.lower()}.png")
            img = img.resize((200, 130))
            img_tk = ImageTk.PhotoImage(img)
            image_refs.append(img_tk)

            box = tk.Frame(frame, bg="black")
            box.grid(row=row, column=col, padx=20, pady=10)

            tk.Label(box, image=img_tk).pack()
            tk.Label(box, text=mood, font=("Arial", 14, "bold"), fg="white", bg="black").pack()

            tk.Button(box, text="Select", command=lambda m=mood: show_song_interface(frame, m),
                      bg="#00fd6a", fg="white", font=("Arial", 10)).pack(pady=5)

            col += 1
            if col > 2:
                col = 0
                row += 1
        except Exception as e:
            print(f"Missing image for {mood}: {e}")

    tk.Button(frame, text="⬅ Back", font=("Arial", 12), bg="#95a5a6", fg="white",
            command=lambda: show_main_menu(frame)).grid(row=row+1, column=1, pady=10)
def play_song_with_video(song_path, parent_frame):
    global current_mood
    # Pause the current UI and create a fullscreen-like Toplevel
    video_window = tk.Toplevel(root)
    video_window.geometry("1019x512")
    video_window.title("Now Playing")
    video_window.transient(root)
    video_window.grab_set()

    canvas = tk.Canvas(video_window, width=1019, height=512)
    canvas.pack()

    stop_flag = {"stop": False}

    def on_close():
        stop_flag["stop"] = True
        pygame.mixer.music.stop()
        if video_window.winfo_exists():
            video_window.destroy()
        show_song_interface(parent_frame, current_mood)  # Back to song list

    back_button = tk.Button(video_window, text="⬅ Back", font=("Arial", 12),
                            bg="#e74c3c", fg="white", command=on_close)
    back_button.place(x=10, y=10)

    def video_loop():
        cap = cv2.VideoCapture("music.mp4")
        if not cap.isOpened():
            print("Could not open music.mp4")
            return

        pygame.mixer.music.load(song_path)
        pygame.mixer.music.play()

        while not stop_flag["stop"]:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = cv2.resize(frame, (1019, 512))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(img)

            if canvas.winfo_exists():
                canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
                canvas.imgtk = imgtk

            # Exit video window once song ends
            if not pygame.mixer.music.get_busy():
                break

            time.sleep(0.03)  # ~30fps

        cap.release()
        if not stop_flag["stop"]:
            on_close()

    threading.Thread(target=video_loop, daemon=True).start()

def show_song_interface(prev, mood):
    global current_mood
    current_mood = mood
    if prev and prev.winfo_exists():
        prev.destroy()

    frame = tk.Frame(root, bg="white")
    frame.place(relwidth=1, relheight=1)

    tk.Label(frame, text=f"{mood} Songs", font=("Arial", 20, "bold"), fg="black", bg="white").pack(pady=10)

    def open_online_and_pause():
        global app_paused_due_to_online
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            app_paused_due_to_online = True
        webbrowser.open(f"https://www.youtube.com/results?search_query={mood.lower()}+songs")

    top_controls = tk.Frame(frame, bg="white")
    top_controls.pack(pady=10)


    tk.Button(top_controls, text="Play Online", font=("Arial", 12, "bold"), bg="#9b59b6", fg="white",
              command=open_online_and_pause).grid(row=0, column=1, padx=10)

    container = tk.Frame(frame, bg="white")
    container.pack(pady=10)

    def display_songs():
        for widget in container.winfo_children():
            widget.destroy()

        songs = [s for s in song_library[mood] if s not in temp_removed_songs[mood]] + user_added_songs[mood]

        for idx, song in enumerate(songs):
            color = random_color()
            btn = tk.Button(container, text=f"Song#{idx+1}", bg=color, fg="black", width=20, height=2,
                            command=lambda s=song: play_song_with_video(s, prev))
            btn.grid(row=idx // 3, column=idx % 3, padx=10, pady=10)

            btn.bind("<Button-3>", lambda e, s=song: remove_song_ui(s))

    def remove_song_ui(song):
        if song in user_added_songs[mood]:
            user_added_songs[mood].remove(song)
        elif song in song_library[mood] and song not in temp_removed_songs[mood]:
            temp_removed_songs[mood].append(song)
        display_songs()

    def add_song():
        file = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3")])
        if file:
            user_added_songs[mood].append(file)
            display_songs()

    def restart_app():
        for m in moods:
            temp_removed_songs[m] = []
            user_added_songs[m] = []
        show_splash()

    display_songs()

    controls = tk.Frame(frame, bg="white")
    controls.pack(pady=20)

    tk.Button(controls, text="Add Song", font=("Arial", 12), bg="#27ae60", fg="white",
              command=add_song).grid(row=0, column=0, padx=10)

    tk.Button(controls, text="Restart", font=("Arial", 12), bg="#e67e22", fg="white",
              command=restart_app).grid(row=0, column=1, padx=10)

    tk.Button(controls, text="Back", font=("Arial", 12), bg="#95a5a6", fg="white",
              command=lambda: show_mood_grid(frame)).grid(row=0, column=2, padx=10)

def play_your_choice():
    input_win = tk.Toplevel(root)
    input_win.title("Search Your Song")
    input_win.geometry("400x200")
    input_win.configure(bg="black")
    input_win.transient(root)

    tk.Label(input_win, text="Enter Song Name:", font=("Arial", 14), fg="white", bg="black").pack(pady=10)
    entry = tk.Entry(input_win, font=("Arial", 14), width=30)
    entry.pack(pady=5)

    def submit():
        song_name = entry.get().strip()
        if song_name:
            url = f"https://www.youtube.com/results?search_query={song_name.replace(' ', '+')}+song"
            webbrowser.open(url)
            input_win.destroy()
        else:
            messagebox.showwarning("Warning", "Please enter a song name.")

    tk.Button(input_win, text="Submit", font=("Arial", 12), bg="#2ecc71", fg="white", command=submit).pack(pady=15)

def detect_webcam_emotion_with_song_interface():
    # Create a new Tkinter Toplevel window for the webcam feed
    webcam_window = tk.Toplevel(root)
    webcam_window.title("Webcam Emotion Detector")
    # Make the Toplevel window a transient window for the root window
    # This keeps it on top of the root window and closes with it
    webcam_window.transient(root)
    webcam_window.geometry("800x600")
    webcam_window.protocol("WM_DELETE_WINDOW", lambda: on_webcam_window_close(webcam_window)) # Handle window close

    canvas = tk.Canvas(webcam_window, width=640, height=480, bg="black")
    canvas.pack(pady=10)

    status_label = tk.Label(webcam_window, text="Initializing webcam...", font=("Arial", 14), fg="white", bg="black")
    status_label.pack(pady=5)

    detected_emotion_label = tk.Label(webcam_window, text="", font=("Arial", 16, "bold"), fg="yellow", bg="black")
    detected_emotion_label.pack(pady=5)

    back_button = tk.Button(webcam_window, text="⬅ Back to Main Menu", font=("Arial", 12), bg="#95a5a6", fg="white",
                            command=lambda: on_webcam_window_close(webcam_window))
    back_button.pack(pady=10)

    webcam_stop_event.clear() # Clear the stop event before starting

    # Start the webcam feed in a new thread
    threading.Thread(target=detect_webcam_emotion_logic, args=(canvas, status_label, detected_emotion_label, webcam_window)).start()


def on_webcam_window_close(window):
    global webcam_stop_event
    webcam_stop_event.set() # Set the stop event to signal the webcam thread to stop
    # Destroy the window after a short delay to allow the thread to potentially finish its last loop iteration
    root.after(100, lambda: destroy_window_and_go_back(window))

def destroy_window_and_go_back(window):
    if window.winfo_exists(): # Check if the window still exists before destroying
        window.destroy()
    show_main_menu() # Go back to the main menu when the webcam window is closed

def detect_webcam_emotion_logic(canvas, status_label, detected_emotion_label, webcam_window):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        root.after(0, lambda: status_label.config(text="Error: Could not access the webcam.", fg="red"))
        return

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    mood_map = {
        'Angry': 'Anger',
        'Disgust': 'Sad',
        'Fear': 'Sad',
        'Happy': 'Happy',
        'Sad': 'Sad',
        'Surprise': 'Energetic',
        'Neutral': 'Relaxed'
    }

    detected_song_played = False
    countdown_started = False
    countdown = 5
    countdown_start_time = None
    last_detected_emotion = "None" # To store and display the last detected emotion

    while not webcam_stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break

        frame_flipped = cv2.flip(frame, 1)  # Flip horizontally for mirror effect
        gray = cv2.cvtColor(frame_flipped, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        current_status_text = ""
        current_detected_emotion_text = ""

        if len(faces) > 0 and not detected_song_played:
            if not countdown_started:
                countdown_start_time = cv2.getTickCount()
                countdown_started = True

            elapsed_time = (cv2.getTickCount() - countdown_start_time) / cv2.getTickFrequency()

            seconds_left = countdown - int(elapsed_time)
            if seconds_left > 0:
                current_status_text = f"Detecting emotion in {seconds_left}s"
                cv2.putText(frame_flipped, current_status_text, (30, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            else:
                try:
                    result = DeepFace.analyze(frame_flipped, actions=['emotion'], enforce_detection=False)
                    emotion_label = result[0]['dominant_emotion'].capitalize()
                    last_detected_emotion = emotion_label # Update last detected emotion

                    if emotion_label in mood_map:
                        mood = mood_map[emotion_label]
                        song = random.choice(song_library[mood])
                        play_song(song)
                        detected_song_played = True
                        current_status_text = f"Detected: {emotion_label} → Playing {mood}"
                        cv2.putText(frame_flipped, current_status_text, (30, 80),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    else:
                        current_status_text = "Unknown emotion detected"
                        cv2.putText(frame_flipped, current_status_text, (30, 80),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                        detected_song_played = True
                except Exception as e:
                    print("DeepFace error:", e)
                    current_status_text = "Emotion detection failed"
                    cv2.putText(frame_flipped, current_status_text, (30, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                    detected_song_played = True

        elif detected_song_played:
            current_status_text = "Enjoy your music 🎵"
            current_detected_emotion_text = f"Last Detected Emotion: {last_detected_emotion}"
            cv2.putText(frame_flipped, current_status_text, (30, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        else:
            current_status_text = "Show your face to start detection"
            cv2.putText(frame_flipped, current_status_text, (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        # Update Tkinter labels and canvas from the main thread
        root.after(0, lambda: update_webcam_ui(canvas, status_label, detected_emotion_label, frame_flipped, current_status_text, current_detected_emotion_text))

    cap.release()
    cv2.destroyAllWindows()


def update_webcam_ui(canvas, status_label, detected_emotion_label, frame, status_text, emotion_text):
    if not canvas.winfo_exists(): # Check if widgets still exist before updating
        return

    # Update labels
    status_label.config(text=status_text)
    detected_emotion_label.config(text=emotion_text)

    # Update canvas image
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    imgtk = ImageTk.PhotoImage(image=img)
    canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
    canvas.imgtk = imgtk # Keep a reference!


def show_ai_music_mode(prev):
    # Only destroy 'prev' if it's a valid widget and exists
    if prev and prev.winfo_exists():
        prev.destroy()
    frame = tk.Frame(root, bg="#f2f2f2")  # Light gray
    frame.place(relwidth=1, relheight=1)

    canvas = tk.Canvas(frame, bg="#f2f2f2", highlightthickness=0)
    canvas.place(relwidth=1, relheight=1)

    emojit = []
    for _ in range(12):
        x = random.randint(0, 950)
        y = random.randint(0, 500)
        bmoji = canvas.create_text(x, y, text="🎵", font=("Arial", 20), fill="#e74c3c")  # Red
        emojit.append((bmoji, random.choice([-2, -1, 1, 2]), random.choice([-2, -1, 1, 2])))

    def animate_emojit():
        for i, (bmoji, dx, dy) in enumerate(emojit):
            x, y = canvas.coords(bmoji)
            if x < 0 or x > 1000: dx *= -1
            if y < 0 or y > 500: dy *= -1
            canvas.move(bmoji, dx, dy)
            emojit[i] = (bmoji, dx, dy)
        root.after(50, animate_emojit)

    animate_emojit()

    frame.place(relwidth=1, relheight=1)

    tk.Label(frame, text="AI Music Assistant", font=("Arial", 22), fg="white", bg="black").pack(pady=10)
    tk.Button(frame, text="Vibe Chat", font=("Arial", 14), command=lambda: show_vibe_chat(frame)).pack(pady=5)
    tk.Button(frame, text="Voice Zone", font=("Arial", 14), command=lambda: threading.Thread(target=voice_zone).start()).pack(pady=5)
    tk.Button(frame, text="⬅ Back", font=("Arial", 12), bg="#95a5a6", fg="white",
          command=lambda: show_main_menu(frame)).pack(pady=10)


def show_vibe_chat(prev):
    if prev and prev.winfo_exists():
        prev.destroy()

    frame = tk.Toplevel(root)
    frame.title("Vibe Chat")
    frame.geometry("800x600")
    frame.transient(root)
    frame.configure(bg="black")

    mood_map = {
        'Angry': 'Anger', 'angry': 'Anger', 'mad': 'Anger', 'furious': 'Anger',
        'Sad': 'Sad', 'sad': 'Sad', 'depressed': 'Sad', 'unhappy': 'Sad', 'disgust': 'Sad', 'fear': 'Sad',
        'Happy': 'Happy', 'happy': 'Happy', 'joyful': 'Happy', 'excited': 'Happy',
        'Energetic': 'Energetic', 'surprise': 'Energetic', 'energetic': 'Energetic', 'surprised': 'Energetic',
        'Relaxed': 'Relaxed', 'neutral': 'Relaxed', 'calm': 'Relaxed', 'relax': 'Relaxed', 'relaxed': 'Relaxed', 'chill': 'Relaxed'
    }

    mood_songs = {
        "Sad": [
            "1) Tadap Tadap Ke (KK)", "2) Channa Mereya (Arijit Singh)", "3) Agar Tum Saath Ho",
            "4) Bhula Dena", "5) Phir Le Aaya Dil", "6) Hamari Adhuri Kahani", "7) Tujhe Bhula Diya",
            "8) Yaad Hai Na", "9) Kabira (Encore)", "10) Dard Dilo Ke"
        ],
        "Happy": [
            "1) Ude Dil Befikre", "2) Gallan Goodiyan", "3) London Thumakda", "4) Kar Gayi Chull",
            "5) Desi Girl", "6) Aankh Marey", "7) The Breakup Song", "8) Dil Dhadakne Do",
            "9) Abhi Toh Party Shuru Hui Hai", "10) Sweety Tera Drama"
        ],
        "Relaxed": [
            "1) Tum Mile (Slow)", "2) Raabta", "3) Jeene Laga Hoon", "4) Tera Yaar Hoon Main",
            "5) Sun Saathiya", "6) Khairiyat", "7) Laung Da Lashkara", "8) Kabira",
            "9) Phir Kabhi", "10) Tujh Mein Rab Dikhta Hai"
        ],
        "Energetic": [
            "1) Malhari", "2) Zinda", "3) Sher Aaya Sher", "4) Jashn-e-Ishqa", "5) Sultan Title Track",
            "6) Jai Jai Shivshankar", "7) Apna Time Aayega", "8) Saudagar Sauda Kar", "9) Chak Lein De",
            "10) Lakshya Title"
        ],
        "Anger": [
            "1) Bulleya", "2) Khoon Chala", "3) Ziddi Dil", "4) Azadi", "5) Sadda Haq",
            "6) Kar Har Maidaan Fateh", "7) Josh Mein", "8) Teri Mitti", "9) Aala Re Aala", "10) Baap Se"
        ]
    }

    def speak(text):
        engine.say(text)
        engine.runAndWait()

    def play_emotion_song(emotion):
        filename = f"{emotion.lower()}{random.randint(1, 5)}.mp3"
        try:
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
        except:
            messagebox.showerror("Error", f"Cannot play file: {filename}")

    def process_user_message(event=None):
        user_text = entry.get()
        if not user_text.strip():
            return "break"
        chat_box.insert(tk.END, f"🧑: {user_text}\n")
        entry.delete(0, tk.END)

        lower_text = user_text.lower()

        # Pause / Resume
        if "pause" in lower_text:
            pygame.mixer.music.pause()
            chat_box.insert(tk.END, "🤖: Music paused.\n")
            return "break"
        elif "resume" in lower_text:
            pygame.mixer.music.unpause()
            chat_box.insert(tk.END, "🤖: Music resumed.\n")
            return "break"

        # [YouTube Song]
        import re
        match = re.search(r'\[(.*?)\]', user_text)
        if match:
            song_name = match.group(1).strip()
            if song_name:
                pygame.mixer.music.pause()
                url = f"https://www.youtube.com/results?search_query={song_name.replace(' ', '+')}+song"
                chat_box.insert(tk.END, f"🤖: Opening YouTube for '{song_name}'...\n")
                webbrowser.open(url)
                return "break"

        # Detect {emotion} for recommendation
        curly_match = re.search(r'\{(.*?)\}', user_text)
        if curly_match:
            mood_keyword = curly_match.group(1).strip().lower()
            mapped_mood = mood_map.get(mood_keyword)
            if mapped_mood and mapped_mood in mood_songs:
                chat_box.insert(
                    tk.END, 
                    f"🤖: I have Recommended top {mood_keyword} songs for you:\n🤖: Want more? Just say another emotion like happy, sad, etc. in Curly Braces\n"
                )
            for song in mood_songs[mapped_mood]:
                chat_box.insert(tk.END, f"🎵 {song}\n")    
            return "break"


        # Fallback: detect keyword and play song
        found_emotions = []
        for key in mood_map:
            if key in lower_text:
                found_emotions.append(key)

        if len(found_emotions) == 0:
            chat_box.insert(tk.END, "🤖: Sir, enter a valid emotion like happy, sad, angry etc.\n")
        elif len(found_emotions) > 1:
            chat_box.insert(tk.END, "🤖: You can not play the two songs of two emotions at one time.\n")
        else:
            detected_keyword = found_emotions[0]
            mapped_mood = mood_map[detected_keyword]
            play_emotion_song(mapped_mood)
            chat_box.insert(tk.END, f"🤖: Ok Sir, I am playing a {detected_keyword} song for you.\n")
            chat_box.insert(tk.END, "🤖: So Sir! Which emotion type of song should I play now?\n")

        return "break"

    chat_box = scrolledtext.ScrolledText(frame, width=70, height=18, font=("Arial", 12), wrap=tk.WORD)
    chat_box.pack(pady=10)

    entry = tk.Entry(frame, font=("Arial", 14), width=45)
    entry.pack(side=tk.LEFT, padx=5)
    entry.bind("<Return>", process_user_message)

    tk.Button(frame, text="Send", command=process_user_message).pack(side=tk.LEFT)
    tk.Button(frame, text="⬅ Back", font=("Arial", 12), bg="#95a5a6", fg="white",
              command=lambda: show_ai_music_mode(frame)).pack(pady=10)

    chat_box.insert(tk.END,
        "🤖: Welcome to the Vibe Chat, your AI music assistant.\n"
        "What's on your mind?\n"
        "Tell me which emotion song you want to listen.\n"
        "Try: Recommend SONGS BY {sad} songs\n"
        "Try: Online Search by [Song Name]\n"   
    )

def voice_zone():
    stop_flag = {"stop": False}
    detected_emotion_name = {"emotion": ""}
    mid_screen_text = {"text": ""}

    voice_zone_window = tk.Toplevel(root)
    voice_zone_window.title("Voice Zone")
    voice_zone_window.geometry("1019x512")
    voice_zone_window.transient(root)

    canvas = tk.Canvas(voice_zone_window, width=1019, height=512, highlightthickness=0)
    canvas.place(x=0, y=0)

    import time

    def display_mid_text_word_by_word(text, delay=0.3):
        if not isinstance(text, str) or not text.strip():
            return
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        mid_screen_text["text"] = ""
        for line_index, line in enumerate(lines):
            words = line.split()
            current_display = ""
            for word in words:
                current_display = f"{current_display} {word}".strip()
                animated_text = "\n".join(lines[:line_index]) + ("\n" if line_index > 0 else "") + current_display
                mid_screen_text["text"] = animated_text
                time.sleep(delay)
            mid_screen_text["text"] = "\n".join(lines[:line_index + 1])
            time.sleep(0.5)
        time.sleep(1)
        mid_screen_text["text"] = ""

    def go_back_to_ai_music_mode():
        stop_flag["stop"] = True
        pygame.mixer.music.stop()
        if voice_zone_window.winfo_exists():
            voice_zone_window.destroy()
        show_ai_music_mode(None)

    def toggle_music():
        if current_audio["playing"]:
            if current_audio["paused"]:
                pygame.mixer.music.unpause()
                current_audio["paused"] = False
                toggle_btn.config(text="⏸ Pause")
            else:
                pygame.mixer.music.pause()
                current_audio["paused"] = True
                toggle_btn.config(text="▶ Resume")

    def skip_to_next_song():
        if song_queue and current_song_index["index"] < len(song_queue):
            current_song_index["index"] += 1
            play_song(song_queue[current_song_index["index"] - 1])

    next_btn = tk.Button(voice_zone_window, text="▶ Next", font=("Arial", 12, "bold"),
                         bg="#c0392b", fg="white", command=skip_to_next_song)
    next_btn.place(x=450, y=10)

    toggle_btn = tk.Button(voice_zone_window, text="⏸ Pause", font=("Arial", 12, "bold"),
                           bg="#27ae60", fg="white", command=toggle_music)
    toggle_btn.place(x=850, y=10)

    back_btn = tk.Button(voice_zone_window, text="⬅ Back", font=("Arial", 12),
                         bg="#95a5a6", fg="white", command=go_back_to_ai_music_mode)
    back_btn.place(x=10, y=10)

    def video_loop():
        cap = cv2.VideoCapture("voicezone.mp4")
        if not cap.isOpened():
            print("Error: Cannot open video file")
            return
        while not stop_flag["stop"]:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            if detected_emotion_name["emotion"]:
                cv2.putText(frame, f"{detected_emotion_name['emotion']} Song Playing", (100, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            if mid_screen_text["text"]:
                color = tuple(np.random.randint(0, 255, size=3).tolist())
                y0 = 250
                for i, line in enumerate(mid_screen_text["text"].split("\n")):
                    cv2.putText(frame, line, (150, y0 + i * 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3, cv2.LINE_AA)
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            if canvas.winfo_exists():
                canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
                canvas.imgtk = imgtk
        cap.release()

    threading.Thread(target=video_loop, daemon=True).start()

    mood_map = {
        'angry': 'Anger',
        'disgust': 'Sad',
        'fear': 'Sad',
        'happy': 'Happy',
        'sad': 'Sad',
        'surprise': 'Energetic',
        'neutral': 'Relaxed',
        'relaxed': 'Relaxed',
        'motivated': 'Motivated'
    }

    def speak_text(text):
        def run():
            engine.setProperty('rate', 170)
            engine.setProperty('volume', 1.0)
            engine.say(text)
            engine.runAndWait()
        threading.Thread(target=run).start()

    def monitor_songs():
        while not stop_flag["stop"]:
            if current_audio["playing"] and not pygame.mixer.music.get_busy() and not current_audio["paused"]:
                if current_song_index["index"] < len(song_queue):
                    current_song_index["index"] += 1
                    play_song(song_queue[current_song_index["index"] - 1])
                else:
                    current_audio["playing"] = False
                    speak_text("Waiting for your next mood.")
                    display_mid_text_word_by_word("Waiting for your next mood", 0.3)
            time.sleep(1)

    def play_song(file):
        try:
            announce = f"Sir, I am playing {detected_emotion_name['emotion']} song for you."
            speak_text(announce)
            display_mid_text_word_by_word(announce, 0.4)
            pygame.mixer.music.load(file)
            pygame.mixer.music.play()
            current_audio["playing"] = True
            current_audio["paused"] = False
            toggle_btn.config(text="⏸ Pause")
        except:
            speak_text("Sorry, I could not play the song.")
            display_mid_text_word_by_word("Sorry, could not play song", 0.4)

    def recognize_voice():
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            while not stop_flag["stop"]:
                try:
                    audio = recognizer.listen(source, timeout=5)
                    text = recognizer.recognize_google(audio).lower()
                    print("User said:", text)
                    detected_emotion = None
                    for key in mood_map:
                        if key in text:
                            detected_emotion = mood_map[key]
                            detected_emotion_name["emotion"] = key.capitalize()
                            break
                    if detected_emotion:
                        song_queue.clear()
                        for i in range(1, 6):
                            song_queue.append(f"{detected_emotion.lower()}{i}.mp3")
                        current_song_index["index"] = 1
                        play_song(song_queue[0])
                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    print("Error:", str(e))

    speak_text("Welcome to the Voice Zone. Please tell me your mood.")
    display_mid_text_word_by_word("Welcome to the Voice Zone.\nPlease tell me your mood", 0.4)
    threading.Thread(target=recognize_voice, daemon=True).start()
    threading.Thread(target=monitor_songs, daemon=True).start()

show_splash()
root.mainloop()