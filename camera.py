import cv2

def main():
    # Usa 0 si es una cámara USB. Si usas la cámara oficial de la Raspberry (CSI), puede ser necesario usar el backend adecuado
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Error al abrir la cámara")
        return

    print("✅ Cámara iniciada. Presiona 'q' para salir.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("⚠️ No se pudo leer el frame")
            break

        # Muestra el frame en una ventana
        cv2.imshow('Raspberry Cam', frame)

        # Salir con la tecla 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Libera la cámara y cierra la ventana
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
