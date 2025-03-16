import glob
import socket
import threading
from collections import defaultdict
import os

# Diccionario para almacenar las conexiones (sockets) de cada sala
salas = {}
# Diccionario para guardar el historial de cada sala (en memoria)
historial_salas = defaultdict(list)
# Diccionario para mapear socket -> nombre de usuario
usuarios = {}

lock = threading.Lock()  # Para evitar condiciones de carrera

# Ruta de carpeta donde guardaremos archivos
CARPETA_HISTORIAL = "historial_data"

# 1. Función para asegurar que exista la carpeta de historiales
def asegurar_carpeta():
    if not os.path.exists(CARPETA_HISTORIAL):
        os.makedirs(CARPETA_HISTORIAL)

def listar_usuarios_en_sala(nombre_sala):
    """Devuelve la lista de nombres de usuario conectados en esa sala."""
    if nombre_sala not in salas:
        return []
    lista_nombres = []
    for sock in salas[nombre_sala]:
        if sock in usuarios:
            lista_nombres.append(usuarios[sock])
    return lista_nombres

# 2. Función para guardar un mensaje en el archivo de historial de la sala
def guardar_mensaje_en_archivo(nombre_sala, mensaje):
    """
    Guarda la 'línea' de mensaje en un archivo asociado a 'nombre_sala'.
    """
    asegurar_carpeta()
    ruta_archivo = os.path.join(CARPETA_HISTORIAL, f"historial_{nombre_sala}.txt")
    with open(ruta_archivo, "a", encoding="utf-8") as f:
        f.write(mensaje + "\n")

def manejar_cliente(cliente_socket, nombre_usuario, sala_actual):
    global salas, historial_salas, usuarios

    # Enviamos todo el historial de la sala actual (en memoria) al nuevo usuario
    with lock:
        for msg in historial_salas[sala_actual]:
            cliente_socket.send((msg + "\n").encode())

    while True:
        try:
            mensaje = cliente_socket.recv(1024).decode()
            if not mensaje:
                break

            # Procesar comandos
            if mensaje.startswith("/salas"):
                with lock:
                    if salas:
                        lista_salas = ", ".join(salas.keys())
                    else:
                        lista_salas = "No hay salas disponibles."
                cliente_socket.send(f"Salas disponibles: {lista_salas}\n".encode())

            elif mensaje.startswith("/crear"):
                partes = mensaje.split(" ", 1)
                if len(partes) < 2:
                    cliente_socket.send("Uso: /crear NOMBRE_DE_SALA\n".encode())
                    continue
                nombre_sala = partes[1].strip()

                with lock:
                    if nombre_sala not in salas:
                        salas[nombre_sala] = []
                        historial_salas[nombre_sala] = []
                        cliente_socket.send(f"Sala '{nombre_sala}' creada!\n".encode())

                        # Opcional: Crear un archivo vacío para su historial
                        ruta_archivo = os.path.join(CARPETA_HISTORIAL, f"historial_{nombre_sala}.txt")
                        asegurar_carpeta()
                        if not os.path.exists(ruta_archivo):
                            open(ruta_archivo, "w").close()

                    else:
                        cliente_socket.send(f"La sala '{nombre_sala}' ya existe.\n".encode())

            elif mensaje.startswith("/unir"):
                partes = mensaje.split(" ", 1)
                if len(partes) < 2:
                    cliente_socket.send("Uso: /unir NOMBRE_DE_SALA\n".encode())
                    continue
                nombre_sala = partes[1].strip()

                with lock:
                    if nombre_sala in salas:
                        # Retirar al cliente de la sala anterior
                        if cliente_socket in salas[sala_actual]:
                            salas[sala_actual].remove(cliente_socket)
                        # Añadir a la nueva sala
                        salas[nombre_sala].append(cliente_socket)
                        sala_actual = nombre_sala
                        cliente_socket.send(f"Te has unido a la sala '{nombre_sala}'\n".encode())

                        # Enviar historial de esa sala en memoria
                        for msg in historial_salas[nombre_sala]:
                            cliente_socket.send((msg + "\n").encode())
                    else:
                        cliente_socket.send(f"La sala '{nombre_sala}' no existe.\n".encode())

            elif mensaje.startswith("/usuarios"):
                with lock:
                    lista_nombres = listar_usuarios_en_sala(sala_actual)
                respuesta = f"Usuarios en sala '{sala_actual}': " + ", ".join(lista_nombres) + "\n"
                cliente_socket.send(respuesta.encode())

            elif mensaje.startswith("/salir"):
                with lock:
                    cliente_socket.send("Saliendo del chat...\n".encode())
                    if cliente_socket in salas[sala_actual]:
                        salas[sala_actual].remove(cliente_socket)
                cliente_socket.close()
                return

            else:
                # Difundir mensaje a los demás en la sala
                texto_formateado = f"{nombre_usuario}: {mensaje}"
                with lock:
                    # Guardar en memoria
                    historial_salas[sala_actual].append(texto_formateado)
                    # Guardar en archivo
                    guardar_mensaje_en_archivo(sala_actual, texto_formateado)

                    for cli in salas[sala_actual]:
                        if cli != cliente_socket:
                            cli.send((texto_formateado + "\n").encode())

        except Exception as e:
            print(f"Error con {nombre_usuario}: {e}")
            with lock:
                if cliente_socket in salas[sala_actual]:
                    salas[sala_actual].remove(cliente_socket)
            cliente_socket.close()
            break


def cargar_historial_inicial():
    asegurar_carpeta()

    # Leer todos los archivos historial_<sala>.txt
    for archivo in glob.glob(os.path.join(CARPETA_HISTORIAL, 'historial_*.txt')):
        # archivo = 'historial_data/historial_miSala.txt'
        nombre_basename = os.path.basename(archivo)  # 'historial_miSala.txt'
        # Extraer el nombre de la sala: 'miSala'
        nombre_sala = nombre_basename.replace("historial_", "").replace(".txt", "")

        # Crear la sala (si no existe)
        salas[nombre_sala] = []
        historial_salas[nombre_sala] = []

        # Cargar las líneas del archivo en el historial en memoria
        with open(archivo, 'r', encoding='utf-8') as f:
            lineas = f.read().splitlines()

        for linea in lineas:
            historial_salas[nombre_sala].append(linea)


def main():
    asegurar_carpeta()
    # Cargar historiales de salas (opcional)
    # cargar_historial_inicial()

    cargar_historial_inicial()

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("0.0.0.0", 5555))
    servidor.listen(5)
    print("Servidor iniciado en el puerto 5555")

    # Creamos la sala general por defecto
    salas["general"] = []
    historial_salas["general"] = []

    while True:
        cliente, addr = servidor.accept()
        try:
            # Pedir el nombre de usuario
            cliente.send("Ingrese su nombre: ".encode())
            nombre_usuario = cliente.recv(1024).decode().strip()
            if not nombre_usuario:
                cliente.close()
                continue

            with lock:
                usuarios[cliente] = nombre_usuario
                salas["general"].append(cliente)
            print(f"{nombre_usuario} se ha unido al chat desde {addr}")

            hilo = threading.Thread(
                target=manejar_cliente,
                args=(cliente, nombre_usuario, "general")
            )
            hilo.start()
        except:
            cliente.close()

if __name__ == "__main__":
    main()
