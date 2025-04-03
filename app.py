import sys
import os
import re
import time
import json
import queue
import threading
import multiprocessing
import subprocess
import webbrowser
import customtkinter as ctk
from tkinter import filedialog, messagebox, font
from PyQt6 import QtWidgets, QtWebEngineWidgets, QtCore
import requests
import tkinter as tk
from flask import Flask, render_template

class PreviewProcess(multiprocessing.Process):
    def __init__(self, comm_queue):
        super().__init__()
        self.comm_queue = comm_queue
        self.daemon = True

    def run(self):
        class PreviewWindow(QtWidgets.QMainWindow):
            def __init__(self, queue):
                super().__init__()
                self.queue = queue
                self.browser = QtWebEngineWidgets.QWebEngineView()
                self.setCentralWidget(self.browser)
                self.resize(1280, 720)
                self.setWindowTitle("Live Preview")
                self.timer = QtCore.QTimer()
                self.timer.timeout.connect(self.check_queue)
                self.timer.start(100)

            def check_queue(self):
                try:
                    if not self.queue.empty():
                        html = self.queue.get_nowait()
                        self.browser.setHtml(html)
                except:
                    pass

        app = QtWidgets.QApplication(sys.argv)
        window = PreviewWindow(self.comm_queue)
        window.show()
        app.exec()

class CodeBot(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Full-Stack Dev Studio")
        self.geometry("1400x900")
        self.api_key = "AIzaSyDVKIgfwT_1S-lzuS3mRW-ZPkgrxJT0pVY"
        
        # Server management
        self.server_process = None
        self.server_running = False
        self.current_port = 5000
        self.project_dir = None
        
        # Syntax highlighting theme
        self.vs_code_theme = {
            'background': '#1E1E1E',
            'foreground': '#D4D4D4',
            'html': {'tag': '#569CD6', 'attr': '#9CDCFE', 'string': '#CE9178'},
            'css': {'selector': '#D7BA7D', 'property': '#9CDCFE', 'value': '#CE9178'},
            'js': {'keyword': '#569CD6', 'function': '#DCDCAA', 'string': '#CE9178', 'number': '#B5CEA8'},
            'py': {'keyword': '#569CD6', 'function': '#DCDCAA', 'string': '#CE9178', 'class': '#4EC9B0'}
        }
        
        self.preview_queue = multiprocessing.Queue()
        self.preview_process = None
        
        self.setup_ui()
        self.setup_syntax_highlighting()
        self.setup_event_handlers()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Editor Area
        editor_frame = ctk.CTkFrame(self)
        editor_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.tabs = ctk.CTkTabview(editor_frame)
        self.tabs.pack(fill="both", expand=True)

        self.html_editor = self.create_editor_tab("HTML")
        self.css_editor = self.create_editor_tab("CSS")
        self.js_editor = self.create_editor_tab("JavaScript")
        self.py_editor = self.create_editor_tab("Python Backend")

        # Control Panel
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        # Left Side Controls
        left_control_frame = ctk.CTkFrame(control_frame)
        left_control_frame.pack(side="left", fill="x", expand=True)
        
        self.prompt_entry = ctk.CTkEntry(
            left_control_frame,
            placeholder_text="Describe your application...",
            font=("Roboto", 14),
            width=400
        )
        self.prompt_entry.pack(side="left", padx=5)

        ctk.CTkButton(
            left_control_frame,
            text="Generate",
            command=self.start_generation,
            fg_color="#2ECC71",
            hover_color="#27AE60",
            width=120
        ).pack(side="left", padx=5)

        # Right Side Controls
        right_control_frame = ctk.CTkFrame(control_frame)
        right_control_frame.pack(side="right")

        self.server_button = ctk.CTkButton(
            right_control_frame,
            text="Start Server",
            command=self.toggle_server,
            fg_color="#3498DB",
            hover_color="#2980B9",
            width=120
        )
        self.server_button.pack(side="right", padx=5)

        ctk.CTkButton(
            right_control_frame,
            text="Open Browser",
            command=self.open_browser,
            fg_color="#9B59B6",
            hover_color="#8E44AD",
            width=120
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            right_control_frame,
            text="Live Preview",
            command=self.toggle_preview,
            fg_color="#3498DB",
            hover_color="#2980B9",
            width=120
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            right_control_frame,
            text="Save Project",
            command=self.save_project,
            fg_color="#7F8C8D",
            hover_color="#95A5A6",
            width=120
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            right_control_frame,
            text="Load Project",
            command=self.load_project,
            fg_color="#7F8C8D",
            hover_color="#95A5A6",
            width=120
        ).pack(side="right", padx=5)

    def create_editor_tab(self, title):
        tab = self.tabs.add(title)
        frame = ctk.CTkFrame(tab)
        frame.pack(fill="both", expand=True)
        
        editor = tk.Text(
            frame,
            wrap="none",
            font=("Consolas", 14),
            bg=self.vs_code_theme['background'],
            fg=self.vs_code_theme['foreground'],
            insertbackground=self.vs_code_theme['foreground'],
            selectbackground='#264F78',
            relief="flat"
        )
        editor.pack(fill="both", expand=True, padx=2, pady=2)
        return editor

    def setup_syntax_highlighting(self):
        # HTML tags
        self.html_editor.tag_configure('tag', foreground=self.vs_code_theme['html']['tag'])
        self.html_editor.tag_configure('attr', foreground=self.vs_code_theme['html']['attr'])
        self.html_editor.tag_configure('string', foreground=self.vs_code_theme['html']['string'])

        # CSS tags
        self.css_editor.tag_configure('selector', foreground=self.vs_code_theme['css']['selector'])
        self.css_editor.tag_configure('property', foreground=self.vs_code_theme['css']['property'])
        self.css_editor.tag_configure('value', foreground=self.vs_code_theme['css']['value'])

        # JavaScript tags
        self.js_editor.tag_configure('keyword', foreground=self.vs_code_theme['js']['keyword'])
        self.js_editor.tag_configure('function', foreground=self.vs_code_theme['js']['function'])
        self.js_editor.tag_configure('string', foreground=self.vs_code_theme['js']['string'])
        self.js_editor.tag_configure('number', foreground=self.vs_code_theme['js']['number'])

        # Python tags
        self.py_editor.tag_configure('keyword', foreground=self.vs_code_theme['py']['keyword'])
        self.py_editor.tag_configure('function', foreground=self.vs_code_theme['py']['function'])
        self.py_editor.tag_configure('string', foreground=self.vs_code_theme['py']['string'])
        self.py_editor.tag_configure('class', foreground=self.vs_code_theme['py']['class'])

        threading.Thread(target=self.highlight_worker, daemon=True).start()

    def highlight_worker(self):
        while True:
            self.highlight_editor(self.html_editor, 'html')
            self.highlight_editor(self.css_editor, 'css')
            self.highlight_editor(self.js_editor, 'js')
            self.highlight_editor(self.py_editor, 'py')
            time.sleep(0.3)

    def highlight_editor(self, editor, lang):
        content = editor.get("1.0", "end-1c")
        editor.tag_remove("highlight", "1.0", "end")
        
        if lang == 'html':
            self.apply_regex(editor, r'<\/?[\w]+', 'tag')
            self.apply_regex(editor, r'\b[\w-]+(?=\=)', 'attr')
            self.apply_regex(editor, r'["\'].*?["\']', 'string')
        elif lang == 'css':
            self.apply_regex(editor, r'[\w-]+\s*(?={)', 'selector')
            self.apply_regex(editor, r'[\w-]+(?=\:)', 'property')
            self.apply_regex(editor, r':\s*.*?;', 'value')
        elif lang == 'js':
            keywords = ['function', 'const', 'let', 'if', 'else', 'return', 'class', 'export', 'import']
            self.apply_regex(editor, r'\b('+'|'.join(keywords)+r')\b', 'keyword')
            self.apply_regex(editor, r'\b\d+\b', 'number')
            self.apply_regex(editor, r'["\'].*?["\']', 'string')
            self.apply_regex(editor, r'function\s+([\w]+)', 'function')
        elif lang == 'py':
            keywords = ['import', 'from', 'class', 'def', 'if', 'else', 'elif', 'for', 'while', 'return']
            self.apply_regex(editor, r'\b(' + '|'.join(keywords) + r')\b', 'keyword')
            self.apply_regex(editor, r'def\s+([\w_]+)', 'function')
            self.apply_regex(editor, r'class\s+([\w_]+)', 'class')
            self.apply_regex(editor, r'["\'].*?["\']', 'string')

    def apply_regex(self, editor, pattern, tag):
        for match in re.finditer(pattern, editor.get("1.0", "end-1c")):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            editor.tag_add(tag, start, end)

    def setup_event_handlers(self):
        for editor in [self.html_editor, self.css_editor, self.js_editor, self.py_editor]:
            editor.bind("<KeyRelease>", lambda e: self.update_preview())

    def toggle_preview(self):
        if not self.preview_process or not self.preview_process.is_alive():
            self.preview_process = PreviewProcess(self.preview_queue)
            self.preview_process.start()
            time.sleep(1)
        self.update_preview()

    def update_preview(self):
        html_content = f"""<!DOCTYPE html>
        <html>
            <head><style>{self.css_editor.get("1.0", "end")}</style></head>
            <body>{self.html_editor.get("1.0", "end")}</body>
            <script>{self.js_editor.get("1.0", "end")}</script>
        </html>"""
        self.preview_queue.put(html_content)

    def start_generation(self):
        prompt = self.prompt_entry.get()
        if not prompt:
            messagebox.showwarning("Warning", "Please enter a description")
            return
            
        threading.Thread(target=self.generate_code, args=(prompt,), daemon=True).start()

    def generate_code(self, prompt):
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{
                            "text": f"{prompt}\n\nProvide complete HTML, CSS, JavaScript, and Python Flask code in separate code blocks."
                        }]
                    }]
                }
            )
            response.raise_for_status()
            
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            
            # Extract code from each language
            html = self.extract_code(content, "html")
            css = self.extract_code(content, "css")
            js = self.extract_code(content, "javascript")
            py = self.extract_code(content, "python")
            
            # Update editors
            self.html_editor.delete("1.0", "end")
            self.html_editor.insert("end", html or "<!-- Generated HTML -->")
            
            self.css_editor.delete("1.0", "end")
            self.css_editor.insert("end", css or "/* Generated CSS */")
            
            self.js_editor.delete("1.0", "end")
            self.js_editor.insert("end", js or "// Generated JavaScript")
            
            self.py_editor.delete("1.0", "end")
            self.py_editor.insert("end", py or "# Generated Python Flask Backend")
            
            messagebox.showinfo("Success", "Code generated successfully!")
            self.update_preview()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate code: {str(e)}")

    def extract_code(self, text, lang):
        match = re.search(rf"```{lang}.*?\n(.*?)```", text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def toggle_server(self):
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        try:
            if not self.project_dir:
                if not self.save_project():
                    return
            
            # Ensure required directories exist
            os.makedirs(os.path.join(self.project_dir, "templates"), exist_ok=True)
            os.makedirs(os.path.join(self.project_dir, "static/css"), exist_ok=True)
            os.makedirs(os.path.join(self.project_dir, "static/js"), exist_ok=True)
            
            # Save all files
            self.save_file(os.path.join(self.project_dir, "templates/index.html"), self.html_editor.get("1.0", "end"))
            self.save_file(os.path.join(self.project_dir, "static/css/style.css"), self.css_editor.get("1.0", "end"))
            self.save_file(os.path.join(self.project_dir, "static/js/script.js"), self.js_editor.get("1.0", "end"))
            
            # Save Python file
            py_content = self.py_editor.get("1.0", "end")
            if not py_content.strip():
                py_content = """from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
"""
            self.save_file(os.path.join(self.project_dir, "app.py"), py_content)
            
            # Set FLASK_APP environment variable
            os.environ['FLASK_APP'] = 'app.py'
            
            # Start Flask server
            self.server_process = subprocess.Popen(
                ['flask', 'run'],
                cwd=self.project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            self.server_running = True
            self.update_server_button()
            
            # Monitor server output
            threading.Thread(target=self.monitor_server_output, daemon=True).start()
            
            messagebox.showinfo("Server", f"Backend server started on http://localhost:{self.current_port}")
            
        except Exception as e:
            messagebox.showerror("Server Error", f"Failed to start server: {str(e)}")

    def stop_server(self):
        if self.server_process:
            try:
                if sys.platform == 'win32':
                    self.server_process.send_signal(subprocess.CTRL_BREAK_EVENT)
                else:
                    self.server_process.terminate()
                self.server_process.wait(timeout=3)
            except:
                self.server_process.kill()
            finally:
                self.server_running = False
                self.update_server_button()
                messagebox.showinfo("Server", "Backend server stopped")

    def monitor_server_output(self):
        while self.server_process.poll() is None:
            output = self.server_process.stdout.readline().decode()
            if output:
                print("[Server]", output.strip())

    def update_server_button(self):
        self.server_button.configure(
            text="Stop Server" if self.server_running else "Start Server",
            fg_color="#E74C3C" if self.server_running else "#3498DB",
            hover_color="#C0392B" if self.server_running else "#2980B9"
        )

    def open_browser(self):
        if self.server_running:
            webbrowser.open(f"http://localhost:{self.current_port}")
        else:
            messagebox.showwarning("Warning", "Server is not running")

    def save_project(self):
        try:
            directory = filedialog.askdirectory()
            if not directory:
                return False
            
            self.project_dir = directory
            
            # Create necessary directories
            os.makedirs(os.path.join(directory, "templates"), exist_ok=True)
            os.makedirs(os.path.join(directory, "static/css"), exist_ok=True)
            os.makedirs(os.path.join(directory, "static/js"), exist_ok=True)
            
            # Save files
            self.save_file(os.path.join(directory, "templates/index.html"), self.html_editor.get("1.0", "end"))
            self.save_file(os.path.join(directory, "static/css/style.css"), self.css_editor.get("1.0", "end"))
            self.save_file(os.path.join(directory, "static/js/script.js"), self.js_editor.get("1.0", "end"))
            
            # Save Python file with default content if empty
            py_content = self.py_editor.get("1.0", "end")
            if not py_content.strip():
                py_content = """from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
"""
            self.save_file(os.path.join(directory, "app.py"), py_content)
            
            messagebox.showinfo("Success", f"Project saved to {directory}")
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {str(e)}")
            return False

    def save_file(self, path, content):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())

    def load_project(self):
        try:
            directory = filedialog.askdirectory()
            if not directory:
                return
                
            self.project_dir = directory
            
            # Load HTML
            html_path = os.path.join(directory, "templates/index.html")
            if os.path.exists(html_path):
                with open(html_path, "r", encoding="utf-8") as f:
                    self.html_editor.delete("1.0", "end")
                    self.html_editor.insert("end", f.read())
            
            # Load CSS
            css_path = os.path.join(directory, "static/css/style.css")
            if os.path.exists(css_path):
                with open(css_path, "r", encoding="utf-8") as f:
                    self.css_editor.delete("1.0", "end")
                    self.css_editor.insert("end", f.read())
            
            # Load JavaScript
            js_path = os.path.join(directory, "static/js/script.js")
            if os.path.exists(js_path):
                with open(js_path, "r", encoding="utf-8") as f:
                    self.js_editor.delete("1.0", "end")
                    self.js_editor.insert("end", f.read())
            
            # Load Python
            py_path = os.path.join(directory, "app.py")
            if os.path.exists(py_path):
                with open(py_path, "r", encoding="utf-8") as f:
                    self.py_editor.delete("1.0", "end")
                    self.py_editor.insert("end", f.read())
            
            messagebox.showinfo("Success", "Project loaded successfully")
            self.update_preview()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project: {str(e)}")

    def on_closing(self):
        if self.server_running:
            self.stop_server()
        if self.preview_process and self.preview_process.is_alive():
            self.preview_process.terminate()
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("dark-blue")
    app = CodeBot()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()