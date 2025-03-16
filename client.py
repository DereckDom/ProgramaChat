import socket
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext

# -------------------------
#  CONFIGURACIÓN DEL CLIENTE
# -------------------------
IP_SERVIDOR = "192.168.1.13"  # Cambia a la IP de tu servidor
PUERTO = 5555

cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    cliente.connect((IP_SERVIDOR, PUERTO))
except:
    messagebox.showerror("Error", "No se pudo conectar con el servidor.")
    exit()

# -------------------------
#  PEDIR NOMBRE DE USUARIO
# -------------------------
nombre_usuario = simpledialog.askstring("Nombre de usuario", "Ingrese su nombre:")
if not nombre_usuario:
    messagebox.showerror("Error", "Debe ingresar un nombre de usuario.")
    exit()
cliente.send(nombre_usuario.encode())

# Al inicio, el servidor nos meterá en la sala 'general'
current_room_name = "general"

# -------------------------
#   FUNCIÓN PARA MOSTRAR VENTANA DE TUTORIAL
# -------------------------
def mostrar_ventana_ayuda():
    # Creamos una nueva ventana Toplevel
    ventana_ayuda = tk.Toplevel(root)
    ventana_ayuda.title("Tutorial y Comandos")
    ventana_ayuda.geometry("500x300")

    # Texto con explicaciones
    tutorial_texto = (
        "===== TUTORIAL DE COMANDOS =====\n\n"
        "Puedes escribir estos comandos en la ventana 'Controles de la sala actual':\n\n"
        "/help\n"
        "    - Muestra la lista de comandos disponibles.\n\n"
        "/salas\n"
        "    - Muestra todas las salas disponibles en el servidor.\n\n"
        "/crear <sala>\n"
        "    - Crea una nueva sala (si no existe).\n\n"
        "/unir <sala>\n"
        "    - Te une (o cambia) a la sala especificada.\n\n"
        "/usuarios\n"
        "    - Muestra los usuarios que están en la sala actual.\n\n"
        "/privado <usuario> <mensaje>\n"
        "    - Envía un mensaje privado al usuario en tu misma sala.\n\n"
        "/salir\n"
        "    - Cierra tu sesión y te desconecta del chat.\n\n"
        "Además, puedes escribir mensajes normales (sin '/') para que todos en tu sala los vean.\n\n"
        "===== Fin del Tutorial ====="
    )

    # ScrolledText para mostrar el tutorial
    text_area = scrolledtext.ScrolledText(ventana_ayuda, wrap=tk.WORD)
    text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    text_area.insert(tk.END, tutorial_texto)
    text_area.config(state=tk.DISABLED)  # Solo lectura

# -------------------------
#    VENTANA LOBBY
# -------------------------
root = tk.Tk()
root.title(f"Lobby - {nombre_usuario}")
root.geometry("500x200")

info_label = tk.Label(root, text="Bienvenido al Lobby. Usa los botones para listar, crear o unirte a salas.")
info_label.pack(pady=10)

rooms_frame = tk.Frame(root)
rooms_frame.pack(pady=5)

room_name_entry = tk.Entry(rooms_frame, width=20)
room_name_entry.grid(row=0, column=0, padx=5)

def listar_salas():
    """Solicita la lista de salas al servidor."""
    try:
        cliente.send("/salas".encode())
    except:
        messagebox.showerror("Error", "No se pudo solicitar la lista de salas.")

def crear_sala():
    """Crea una sala con el nombre ingresado en room_name_entry."""
    sala = room_name_entry.get().strip()
    if sala:
        comando = f"/crear {sala}"
        try:
            cliente.send(comando.encode())
        except:
            messagebox.showerror("Error", "No se pudo crear la sala.")
        room_name_entry.delete(0, tk.END)

def unirse_sala():
    """Se une a la sala con el nombre ingresado en room_name_entry."""
    sala = room_name_entry.get().strip()
    if sala:
        comando = f"/unir {sala}"
        try:
            cliente.send(comando.encode())
        except:
            messagebox.showerror("Error", "No se pudo unir a la sala.")
        room_name_entry.delete(0, tk.END)

btn_listar = tk.Button(rooms_frame, text="Listar Salas", command=listar_salas)
btn_listar.grid(row=0, column=1, padx=5)

btn_crear = tk.Button(rooms_frame, text="Crear Sala", command=crear_sala)
btn_crear.grid(row=0, column=2, padx=5)

btn_unir = tk.Button(rooms_frame, text="Unirse Sala", command=unirse_sala)
btn_unir.grid(row=0, column=3, padx=5)

# NUEVO: Botón para ver Tutorial/Comandos
btn_ayuda = tk.Button(root, text="Ver Comandos/Tutorial", command=mostrar_ventana_ayuda)
btn_ayuda.pack(pady=5)

# -------------------------
#   ALMACENAR VENTANAS DE SALA
# -------------------------
rooms_windows = {}  # dict: { room_name: (Toplevel, chat_area, users_list) }

def open_room_window(room_name: str):
    """
    Crea (o reusa) una ventana Toplevel para la sala dada, con:
    - ScrolledText para los mensajes
    - Listbox para los usuarios de la sala
    """
    if room_name in rooms_windows:
        # si ya existe la ventana, la mostramos
        win, chat_area, users_list = rooms_windows[room_name]
        if not win.winfo_exists():
            # Fue cerrada, crearla de nuevo
            win = tk.Toplevel(root)
            win.title(f"Sala - {room_name}")
            win.geometry("500x400")

            # Área de chat
            chat_area = scrolledtext.ScrolledText(win, wrap=tk.WORD)
            chat_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            chat_area.config(state=tk.DISABLED)

            # ListBox de usuarios
            users_list = tk.Listbox(win)
            users_list.pack(side=tk.RIGHT, fill=tk.Y)

            rooms_windows[room_name] = (win, chat_area, users_list)
        else:
            win.deiconify()  # volver a mostrar si estaba minimizada
        return rooms_windows[room_name]
    else:
        # Crear nueva ventana
        win = tk.Toplevel(root)
        win.title(f"Sala - {room_name}")
        win.geometry("500x400")

        chat_area = scrolledtext.ScrolledText(win, wrap=tk.WORD)
        chat_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_area.config(state=tk.DISABLED)

        users_list = tk.Listbox(win)
        users_list.pack(side=tk.RIGHT, fill=tk.Y)

        rooms_windows[room_name] = (win, chat_area, users_list)
        return rooms_windows[room_name]

# ------------------------------------------------
#  Ventana de control para enviar mensajes a la sala actual
# ------------------------------------------------
sala_control = tk.Toplevel(root)
sala_control.title("Controles de la sala actual (general)")
sala_control.geometry("400x100")

label_sala_msg = tk.Label(sala_control, text="Mensaje:")
label_sala_msg.pack()
entry_sala_msg = tk.Entry(sala_control, width=30)
entry_sala_msg.pack(pady=5)

def enviar_mensaje_sala(event=None):
    """Envia un mensaje a la sala actual."""
    global current_room_name
    if current_room_name not in rooms_windows:
        return
    _, tchat_area, _ = rooms_windows[current_room_name]

    mensaje = entry_sala_msg.get().strip()
    if mensaje:
        try:
            cliente.send(mensaje.encode())
        except:
            tchat_area.config(state=tk.NORMAL)
            tchat_area.insert(tk.END, "Error al enviar mensaje.\n")
            tchat_area.config(state=tk.DISABLED)
        # Muestra local si no es comando
        if not mensaje.startswith("/"):
            tchat_area.config(state=tk.NORMAL)
            tchat_area.insert(tk.END, f"Tú: {mensaje}\n")
            tchat_area.config(state=tk.DISABLED)
            tchat_area.yview(tk.END)
        entry_sala_msg.delete(0, tk.END)

        if mensaje.lower() == "/salir":
            cliente.close()
            for room, (w, ca, ul) in rooms_windows.items():
                if w.winfo_exists():
                    w.destroy()
            root.quit()

btn_enviar_sala = tk.Button(sala_control, text="Enviar", command=enviar_mensaje_sala)
btn_enviar_sala.pack()

sala_control.bind("<Return>", enviar_mensaje_sala)

# ------------------------------------------------
#  Hilo receptor de mensajes del servidor
# ------------------------------------------------
def recibir_mensajes():
    global current_room_name
    while True:
        try:
            mensaje = cliente.recv(1024).decode()
            if not mensaje:
                break

            # Si el servidor avisa que nos unimos a una nueva sala
            if mensaje.startswith("Te has unido a la sala"):
                ini = mensaje.find("'")
                fin = mensaje.rfind("'")
                if ini != -1 and fin != -1 and fin > ini:
                    new_room = mensaje[ini+1:fin]

                    # Ocultar la ventana anterior si existe
                    if current_room_name in rooms_windows:
                        old_win, _, _ = rooms_windows[current_room_name]
                        if old_win.winfo_exists():
                            old_win.withdraw()

                    # Actualizar la sala actual
                    current_room_name = new_room
                    sala_control.title(f"Controles de la sala actual ({new_room})")

                    # Abrir o mostrar la nueva ventana
                    open_room_window(new_room)
                    # Pedir usuarios de la sala
                    cliente.send("/usuarios".encode())

            elif mensaje.startswith("Usuarios en sala"):
                # Ej: "Usuarios en sala 'myroom': user1, user2"
                # Actualizar la listbox de la sala actual
                if current_room_name in rooms_windows:
                    _, tchat_area, tusers_list = rooms_windows[current_room_name]
                    partes = mensaje.split(":")
                    if len(partes) == 2:
                        users_str = partes[1].strip()
                        tusers_list.delete(0, tk.END)
                        if users_str:
                            userlist = users_str.split(",")
                            for u in userlist:
                                tusers_list.insert(tk.END, u.strip())
            else:
                # Mensaje normal
                if current_room_name in rooms_windows:
                    _, tchat_area, _ = rooms_windows[current_room_name]
                    tchat_area.config(state=tk.NORMAL)
                    tchat_area.insert(tk.END, mensaje + "\n")
                    tchat_area.config(state=tk.DISABLED)
                    tchat_area.yview(tk.END)
        except:
            break
    cliente.close()
    root.quit()

# Iniciar un hilo para escuchar mensajes del servidor
hilo_receptor = threading.Thread(target=recibir_mensajes, daemon=True)
hilo_receptor.start()

# Crear ya la ventana de la sala 'general' por si llega historial
open_room_window("general")

# -------------------------
#  EJECUTAR LA INTERFAZ
# -------------------------
root.mainloop()
