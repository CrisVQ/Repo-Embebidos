import cv2
import math
import cvzone
import threading
import sqlite3
from ultralytics import YOLO
import tkinter as tk
from tkinter import ttk
import random
from PIL import Image, ImageTk
import serial
import time
from datetime import datetime

class YOLODetectionApp:
    def __init__(self):
        # Inicialización del hardware, modelo y base de datos
        self.serial_port = serial.Serial('/dev/ttyACM0', baudrate=9600, timeout=1)
        self.yolo_model = YOLO("Weights/best.pt")
        self.class_labels = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

        self.frame = None
        self.running = False
        self.detected_number = ''
        self.operation = ""
        self.operation_result = 0
        self.video_capture = None
        self.lock = threading.Lock()
        self.operation_type = "Random"
        self.default_bg = "lightgrey"

        self.app = tk.Tk()
        self.canvas = None
        self.operation_label = None
        self.result_label = None
        self.operation_selector = None
        self.student_selector = None

        self.initialize_database()
        self.setup_gui()
        self.generate_operation()

    # Generar una operación matemática
    def generate_operation(self):
        num1 = random.randint(1, 50)
        num2 = random.randint(1, 50)

        if self.operation_type == "Random":
            operator = random.choice(['+', '-', '*', '/'])
        else:
            operator = self.operation_type

        if operator == '+':
            self.operation_result = num1 + num2
        elif operator == '-':
            self.operation_result = num1 - num2
        elif operator == '*':
            self.operation_result = num1 * num2
        elif operator == '/':
            while num2 == 0 or num1 % num2 != 0:
                num2 = random.randint(1, 50)
            self.operation_result = num1 // num2

        if 0 <= self.operation_result <= 99:
            self.operation = f"{num1} {operator} {num2}"
        else:
            self.generate_operation()

    # Base de datos: inicializar tablas
    def initialize_database(self):
        connection = sqlite3.connect('students.db')
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                correct INTEGER NOT NULL,
                incorrect INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id)
            )
        """)
        connection.commit()
        connection.close()

    # Registrar un nuevo alumno
    def register_student(self, name):
        if name.strip():
            connection = sqlite3.connect('students.db')
            cursor = connection.cursor()
            cursor.execute("INSERT INTO students (name) VALUES (?)", (name,))
            connection.commit()
            connection.close()
            self.update_student_selector()
        else:
            print("El nombre del alumno no puede estar vacío.")

    # Obtener la lista de alumnos
    def get_students(self):
        connection = sqlite3.connect('students.db')
        cursor = connection.cursor()
        cursor.execute("SELECT id, name FROM students")
        students = cursor.fetchall()
        connection.close()
        return students

    # Actualizar el selector de alumnos
    def update_student_selector(self):
        students = self.get_students()
        self.student_selector['values'] = [f"{s[0]} - {s[1]}" for s in students]

    # Registrar estadísticas de un alumno (acumular datos por fecha)
    def update_stats(self, student_id, correct, incorrect):
        today_date = datetime.now().strftime("%Y-%m-%d")  # Fecha actual (solo día)
        connection = sqlite3.connect('students.db')
        cursor = connection.cursor()

        # Verificar si ya existe un registro para el alumno y la fecha actual
        cursor.execute("""
            SELECT id, correct, incorrect FROM stats 
            WHERE student_id = ? AND DATE(datetime) = ?
        """, (student_id, today_date))
        existing_record = cursor.fetchone()

        if existing_record:
            # Actualizar los valores de aciertos y desaciertos
            record_id, existing_correct, existing_incorrect = existing_record
            new_correct = existing_correct + correct
            new_incorrect = existing_incorrect + incorrect
            cursor.execute("""
                UPDATE stats 
                SET correct = ?, incorrect = ?, datetime = ? 
                WHERE id = ?
            """, (new_correct, new_incorrect, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), record_id))
        else:
            # Insertar un nuevo registro si no existe
            cursor.execute("""
                INSERT INTO stats (student_id, correct, incorrect, datetime) 
                VALUES (?, ?, ?, ?)
            """, (student_id, correct, incorrect, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        connection.commit()
        connection.close()

    # Obtener estadísticas acumuladas
    def get_stats(self):
        connection = sqlite3.connect('students.db')
        cursor = connection.cursor()
        query = """
            SELECT s.name, st.correct, st.incorrect, DATE(st.datetime) AS date
            FROM stats st
            JOIN students s ON s.id = st.student_id
            ORDER BY st.datetime DESC
        """
        cursor.execute(query)
        stats = cursor.fetchall()
        connection.close()
        return stats

    # Mostrar ventana de estadísticas
    def show_stats_window(self):
        stats_window = tk.Toplevel(self.app)
        stats_window.title("Estadísticas de Alumnos")
        stats_window.geometry("600x400")
       
        tk.Label(stats_window, text="Estadísticas de Alumnos", font=("Arial", 14, "bold")).pack(pady=10)

        tree = ttk.Treeview(stats_window, columns=("Alumno", "Aciertos", "Errores", "Fecha"), show="headings")
        tree.heading("Alumno", text="Alumno")
        tree.heading("Aciertos", text="Aciertos")
        tree.heading("Errores", text="Errores")
        tree.heading("Fecha", text="Fecha")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        stats = self.get_stats()
        for stat in stats:
            tree.insert("", "end", values=(stat[0], stat[1], stat[2], stat[3]))

    def start_detection(self):
        if not self.running:
            self.running = True

            # Si usas una cámara local:
            self.video_capture = cv2.VideoCapture(2)  # Índice de la cámara local (0 para la predeterminada)

            # Si usas una cámara IP:
            # self.video_capture = cv2.VideoCapture("http://192.168.31.47:4747/video")

            if not self.video_capture.isOpened():
                print("Error: No se pudo conectar a la cámara.")
                return

            threading.Thread(target=self.capture_video, daemon=True).start()
            threading.Thread(target=self.process_detections, daemon=True).start()


    # Capturar video
    def capture_video(self):
        while self.running:
            success, img = self.video_capture.read()
            if success:
                img_resized = cv2.resize(img, (840, 680))
                with self.lock:
                    self.frame = img_resized

    # Procesar detecciones
    def process_detections(self):
        while self.running:
            if self.frame is not None:
                with self.lock:
                    img_copy = self.frame.copy()

                results = self.yolo_model(img_copy)

                detected_digits = []
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                        w, h = x2 - x1, y2 - y1
                        conf = math.ceil((box.conf[0].cpu().numpy() * 100)) / 100
                        cls = int(box.cls[0].cpu().numpy())

                        if conf > 0.3:
                            detected_digits.append((x1, cls))
                            cvzone.cornerRect(img_copy, (x1, y1, w, h), l=20, t=2)
                            cvzone.putTextRect(img_copy, f'{self.class_labels[cls]} {conf}', (x1, y1 - 10), scale=0.8, thickness=1, colorR=(255, 0, 0))

                detected_digits.sort(key=lambda x: x[0])
                self.detected_number = ''.join([self.class_labels[d[1]] for d in detected_digits])

                if self.detected_number:
                    cvzone.putTextRect(img_copy, f'Numero Detectado: {self.detected_number}', (50, 50), scale=1.2, thickness=2, colorR=(0, 255, 0))

                img_rgb = cv2.cvtColor(img_copy, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(img_rgb)
                img_tk = ImageTk.PhotoImage(image=img_pil)

                self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
                self.canvas.image = img_tk

            time.sleep(0.03)

    # Detener detección
    def stop_detection(self):
        self.running = False
        if self.video_capture:
            self.video_capture.release()

    # Comparar número detectado con el resultado
    def compare_numbers(self):
        if self.detected_number:
            is_correct = self.detected_number == str(self.operation_result)
            comparison_result = "Correcto!" if is_correct else "Incorrecto!"

            self.result_label.config(text=f"Detectado: {self.detected_number}\nResultado: {comparison_result}")

            self.serial_port.write(b'T' if is_correct else b'F')

            if is_correct:
                self.app.configure(bg="green")
            else:
                self.app.configure(bg="red")

            self.app.after(1000, lambda: self.app.configure(bg=self.default_bg))

            # Registrar estadísticas
            selected_student = self.student_selector.get()
            if selected_student and " - " in selected_student:
                student_id = int(selected_student.split(" - ")[0])
                self.update_stats(student_id, int(is_correct), int(not is_correct))

            if is_correct:
                self.generate_operation()
                self.operation_label.config(text=f"Operación:\n{self.operation}", font=("Arial", 24, "bold"))
        else:
            self.result_label.config(text="No se ha detectado ningún número.")
            self.serial_port.write(b'F')

    # Configurar GUI
    def setup_gui(self):
        self.app.title("Detección de Números con YOLO")
        self.app.geometry("1140x700")
        self.app.resizable(False, False)

        # Área de visualización de video
        self.canvas = tk.Canvas(self.app, width=840, height=680, bg="black")
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)

        # Panel derecho para botones
        frame_buttons = tk.Frame(self.app)
        frame_buttons.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 40), pady=10)

        # Título de la sección de detección
        tk.Label(frame_buttons, text="Control de Detección", font=("Arial", 14, "bold")).pack(pady=5)

        # Botones de detección
        start_button = ttk.Button(frame_buttons, text="Iniciar Detección", command=self.start_detection)
        start_button.pack(fill='both', expand=True, pady=5)

        stop_button = ttk.Button(frame_buttons, text="Detener Detección", command=self.stop_detection)
        stop_button.pack(fill='both', expand=True, pady=5)

        verify_button = ttk.Button(frame_buttons, text="Verificar", command=self.compare_numbers)
        verify_button.pack(fill='both', expand=True, pady=5)

        # Separador visual
        tk.Label(frame_buttons, text="").pack(pady=10)  # Espaciado

        # Selector de alumnos
        tk.Label(frame_buttons, text="Seleccionar Alumno:", font=("Arial", 12)).pack(pady=5)
        self.student_selector = ttk.Combobox(frame_buttons)
        self.student_selector.pack(fill='both', expand=True, pady=5)
        self.update_student_selector()

        # Botón para abrir la ventana de gestión de alumnos
        manage_students_button = ttk.Button(frame_buttons, text="Gestión de Alumnos", command=self.open_manage_students_window)
        manage_students_button.pack(fill='both', expand=True, pady=10)

        # Espaciado adicional
        tk.Label(frame_buttons, text="").pack(pady=10)

        # Área de operación matemática
        self.operation_label = tk.Label(frame_buttons, text=f"Operación:\n{self.operation}", font=("Arial", 24, "bold"), anchor="center", relief="solid")
        self.operation_label.pack(fill='both', expand=True, pady=10)

        # Resultado de la detección
        self.result_label = tk.Label(frame_buttons, text="Esperando detección...", font=("Arial", 12), anchor="center", relief="solid")
        self.result_label.pack(fill='both', expand=True, pady=10)

    # Ventana de gestión de alumnos
    def open_manage_students_window(self):
        manage_window = tk.Toplevel(self.app)
        manage_window.title("Gestión de Alumnos")
        manage_window.geometry("800x600")

        # Título
        tk.Label(manage_window, text="Gestión de Alumnos", font=("Arial", 16, "bold")).pack(pady=10)

        # Tabla de estadísticas
        tree = ttk.Treeview(manage_window, columns=("Alumno", "Aciertos", "Errores", "Fecha"), show="headings")
        tree.heading("Alumno", text="Alumno")
        tree.heading("Aciertos", text="Aciertos")
        tree.heading("Errores", text="Errores")
        tree.heading("Fecha", text="Fecha")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Cargar estadísticas en la tabla
        self.load_student_stats(tree)

        # Botón para registrar un nuevo alumno
        register_button = ttk.Button(manage_window, text="Registrar Alumno", command=self.open_register_window)
        register_button.pack(fill='both', expand=True, pady=5)

        # Botón para editar un alumno
        edit_button = ttk.Button(manage_window, text="Editar Alumno", command=lambda: self.edit_student(tree))
        edit_button.pack(fill='both', expand=True, pady=5)

    def load_student_stats(self, tree):
        # Limpiar la tabla antes de cargar datos
        for row in tree.get_children():
            tree.delete(row)

        # Cargar estadísticas en la tabla
        stats = self.get_stats()
        for stat in stats:
            tree.insert("", "end", values=(stat[0], stat[1], stat[2], stat[3]))

    def edit_student(self, tree):
        # Obtener el alumno seleccionado
        selected_item = tree.selection()
        if not selected_item:
            tk.messagebox.showwarning("Advertencia", "Por favor, selecciona un alumno para editar.")
            return

        # Obtener datos del alumno seleccionado
        selected_data = tree.item(selected_item)["values"]
        if not selected_data:
            return

        selected_name = selected_data[0]

        # Crear una ventana para editar el nombre del alumno
        edit_window = tk.Toplevel(self.app)
        edit_window.title("Editar Alumno")
        edit_window.geometry("400x200")

        tk.Label(edit_window, text="Editar Nombre del Alumno:", font=("Arial", 12)).pack(pady=10)
        name_entry = tk.Entry(edit_window)
        name_entry.insert(0, selected_name)
        name_entry.pack(pady=10)

        save_button = ttk.Button(edit_window, text="Guardar", command=lambda: self.save_edited_student(selected_name, name_entry.get(), edit_window, tree))
        save_button.pack(pady=10)

    def save_edited_student(self, old_name, new_name, edit_window, tree):
        if not new_name.strip():
            tk.messagebox.showwarning("Advertencia", "El nombre no puede estar vacío.")
            return

        # Actualizar el nombre del alumno en la base de datos
        connection = sqlite3.connect('students.db')
        cursor = connection.cursor()
        cursor.execute("UPDATE students SET name = ? WHERE name = ?", (new_name, old_name))
        connection.commit()
        connection.close()

        # Actualizar la tabla
        self.load_student_stats(tree)

        # Cerrar la ventana de edición
        edit_window.destroy()

        tk.messagebox.showinfo("Éxito", "El nombre del alumno ha sido actualizado.")




    # Ventana de registro de alumnos
    def open_register_window(self):
        register_window = tk.Toplevel(self.app)
        register_window.title("Registrar Alumno")
        tk.Label(register_window, text="Nombre del Alumno:").pack(pady=5)
        name_entry = tk.Entry(register_window)
        name_entry.pack(pady=5)
        register_button = ttk.Button(register_window, text="Registrar", command=lambda: [self.register_student(name_entry.get()), register_window.destroy()])
        register_button.pack(pady=10)

    # Ejecutar aplicación
    def run(self):
        self.operation_label.config(text=f"Operación:\n{self.operation}", font=("Arial", 24, "bold"))
        self.app.protocol("WM_DELETE_WINDOW", self.on_close)
        self.app.mainloop()

    def on_close(self):
        self.stop_detection()
        self.serial_port.close()
        self.app.destroy()


if __name__ == "__main__":
    app = YOLODetectionApp()
    app.run()
