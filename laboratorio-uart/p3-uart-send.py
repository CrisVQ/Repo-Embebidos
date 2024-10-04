import serial
from time import sleep

# Configura el puerto serial y la velocidad
ser = serial.Serial('/dev/ttyACM0', 9600)  # Cambia al puerto correcto si es necesario

while True:
    # Envía un carácter a la Tiva C para encender el LED
    ser.write(b'A')  # Envía 'A' para encender el LED
    print("Enviado desde Python: A - Encender LED")

    sleep(2)

    # Envía un carácter a la Tiva C para apagar el LED
    ser.write(b'B')  # Envía 'B' para apagar el LED
    print("Enviado desde Python: B - Apagar LED")

    sleep(2)


    if ser.in_waiting > 0:
            value = ser.readline().decode('utf-8').rstrip()
            print(value)

# Cierra el puerto
ser.close()