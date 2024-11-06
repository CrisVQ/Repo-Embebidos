import cv2
import serial
from abc import ABC, abstractmethod

class video_capture_abs(ABC):
    @abstractmethod
    def display_camera(self):
        pass

    @abstractmethod
    def stop_display(self):
        pass

    @abstractmethod
    def camera_visualization(self):
        pass

class VideoCapture(video_capture_abs):
    def __init__(self, camera) -> None:
        self.camera = cv2.VideoCapture(camera)
        self.displayed = True
        self.fgbg_knn = cv2.createBackgroundSubtractorKNN()  # Inicializa el sustractor de fondo KNN

        # Configurar el puerto serial
        self.serial_port = serial.Serial('/dev/ttyACM2', 9600)  # Reemplaza 'COM3' con tu puerto serial

    def display_camera(self):
        self.camera_visualization()

    def stop_display(self):
        self.displayed = False
        self.camera.release()
        cv2.destroyAllWindows()

    def camera_visualization(self):
        while self.displayed:
            check, frame = self.camera.read()
            if check:
                fgmask = self.fgbg_knn.apply(frame)
                contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                height, width, _ = frame.shape
                center_x, center_y = width // 2, height // 2

                for contour in contours:
                    if cv2.contourArea(contour) > 1000:  # Umbral para evitar detecciones pequeñas
                        x, y, w, h = cv2.boundingRect(contour)
                        object_center_x = x + w // 2

                        if object_center_x < center_x:
                            self.serial_port.write(b'I')  # Enviar 'I' si el objeto está a la izquierda
                            print("objeto en la inzquierda")
                        else:
                            self.serial_port.write(b'D')  # Enviar 'D' si el objeto está a la derecha
                            print("objeto en la derecha")
                        break

                cv2.circle(frame, (center_x, center_y), 5, (0, 255, 0), -1)
                cv2.imshow("Camera", frame)
                #cv2.imshow("Foreground Mask", fgmask)
            else:
                print("Error al capturar el frame.")

            key = cv2.waitKey(1)
            if key == 27:  # 27 es el código ASCII para la tecla 'Esc'
                self.stop_display()

if __name__ == "__main__":
    camera = "http://172.18.0.188:4747/video"  # Puedes usar 0 para la webcam local
    camera_object = VideoCapture(camera)
    camera_object.display_camera()
