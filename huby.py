import tkinter as tk
from tkinter import ttk, font, filedialog, messagebox, simpledialog
from types import SimpleNamespace
import csv
import json
import os
import random
from datetime import datetime
import locale
import requests
import threading

# ===================================================================
# CLASSE HELPER PARA TOOLTIPS
# ===================================================================
class Tooltip:
    """
    Cria uma tooltip (dica de ferramenta) para um widget tkinter.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def showtip(self):
        if self.tooltip_window:
            return
        
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 1
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("Arial", "9", "normal"), wraplength=200)
        label.pack(ipadx=5, ipady=3)

    def hidetip(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

# ===================================================================
# CLASSE PARA INTEGRAÇÃO COM WPPCONNECT
# ===================================================================
class WhatsAppConnector:
    def __init__(self, session_name):
        self.base_url = "http://localhost:21465"
        self.session_name = session_name
        self.secret_key = "THISISMYSECURETOKEN"
        self.is_connected = False
        self.token = None

    def generate_token(self):
        try:
            url = f"{self.base_url}/api/{self.session_name}/{self.secret_key}/generate-token"
            response = requests.post(url)
            if response.status_code in [200, 201]:
                data = response.json()
                if 'token' in data:
                    self.token = data['token']
                    return True, "Token gerado com sucesso"
                else:
                    return False, "Token não encontrado na resposta"
            else:
                return False, f"Erro ao gerar token: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Erro inesperado: {str(e)}"

    def _get_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        return {"Content-Type": "application/json"}

    def start_session(self):
        try:
            if not self.token:
                success, message = self.generate_token()
                if not success:
                    return False, f"Erro ao gerar token: {message}"
            headers = self._get_headers()
            response = requests.post(f"{self.base_url}/api/{self.session_name}/start-session", headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'qrcode' in data:
                    return True, "QR Code gerado. Escaneie no console do servidor."
                elif data.get('status') == 'CONNECTED':
                    self.is_connected = True
                    return True, "WhatsApp já conectado!"
                else:
                    return True, "Sessão em processo de inicialização..."
            else:
                error_msg = response.json().get('message', response.text)
                return False, f"Erro {response.status_code}: {error_msg}"
        except requests.exceptions.ConnectionError:
            return False, "Erro: Não foi possível conectar ao wppconnect na porta 21465."
        except Exception as e:
            return False, f"Erro inesperado: {str(e)}"

    def check_connection_status(self):
        try:
            if not self.token: return False
            headers = self._get_headers()
            response = requests.get(f"{self.base_url}/api/{self.session_name}/check-connection-session", headers=headers)
            if response.status_code == 200:
                data = response.json()
                connected = (
                    data.get('connected') == True or data.get('status') == 'CONNECTED' or
                    data.get('state') == 'CONNECTED' or data.get('status') == 'inChat' or
                    data.get('state') == 'OPENING' or 'connected' in str(data).lower()
                )
                self.is_connected = connected
                return self.is_connected
            self.is_connected = False
            return False
        except Exception:
            self.is_connected = False
            return False

    def close_session(self):
        try:
            if not self.token: return False, "Token não disponível"
            headers = self._get_headers()
            response = requests.post(f"{self.base_url}/api/{self.session_name}/close-session", headers=headers)
            if response.status_code == 200:
                self.is_connected = False
                return True, "Sessão fechada com sucesso"
            return False, f"Erro ao fechar sessão: {response.status_code}"
        except Exception as e:
            return False, f"Erro inesperado: {str(e)}"

    def logout_session(self):
        try:
            if not self.token:
                return False, "Token não disponível para deslogar"
            
            headers = self._get_headers()
            response = requests.post(f"{self.base_url}/api/{self.session_name}/logout-session", headers=headers)
            
            if response.status_code == 200:
                return True, "Sessão deslogada com sucesso."
            else:
                error_msg = response.json().get('message', response.text)
                return False, f"Erro ao deslogar sessão: {error_msg}"
        except Exception as e:
            return False, f"Erro inesperado ao deslogar: {str(e)}"

    def send_message(self, phone, message):
        try:
            if not self.token: return False, "Token não disponível. Conecte primeiro."
            clean_phone = ''.join(filter(str.isdigit, phone))
            if len(clean_phone) <= 11 and not clean_phone.startswith("55"):
                clean_phone = "55" + clean_phone
            payload = {"phone": clean_phone, "message": message}
            headers = self._get_headers()
            response = requests.post(f"{self.base_url}/api/{self.session_name}/send-message", json=payload, headers=headers)
            if response.status_code in [200, 201]:
                return True, "Mensagem enviada com sucesso"
            error_msg = response.json().get('message', response.text)
            return False, f"Erro ao enviar: {error_msg}"
        except Exception as e:
            return False, f"Erro inesperado: {str(e)}"

    def get_messages_for_contact(self, phone, include_me=True):
        """Busca as últimas mensagens de uma conversa."""
        try:
            if not self.token:
                return False, "Token não disponível."
            
            clean_phone = ''.join(filter(str.isdigit, phone))
            if len(clean_phone) <= 11 and not clean_phone.startswith("55"):
                clean_phone = "55" + clean_phone
            
            url = f"{self.base_url}/api/{self.session_name}/all-messages-in-chat/{clean_phone}"
            
            headers = self._get_headers()
            params = {'includeMe': str(include_me).lower()}
            
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                messages = response.json()
                return True, messages.get("response", [])
            else:
                error_msg = response.json().get('message', response.text)
                return False, f"Erro ao buscar mensagens: {error_msg}"
        except Exception as e:
            return False, f"Erro inesperado ao buscar mensagens: {str(e)}"

# ===================================================================
# CLASSE PRINCIPAL DA APLICAÇÃO (HUBY_APP)
# ===================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.config_filepath = os.path.join(script_dir, "config.json")
        self.comments_filepath = os.path.join(script_dir, "comentarios.json")
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        except locale.Error:
            print("Locale pt_BR.UTF-8 não encontrado.")
        
        self.title("Huby App - Gerenciador e Enviador")
        self.geometry("850x450")
        self.configure(bg="#F0F0F0")
        
        # --- LÓGICA DE MÚLTIPLOS PERFIS ---
        self.whatsapp_connectors = {}
        self.profile_names = []
        self.active_profile_name = tk.StringVar()
        
        self.current_filepath = None
        self.nome_var = tk.StringVar()
        self.telefone_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.min_interval_var = tk.StringVar(value="20")
        self.max_interval_var = tk.StringVar(value="45")
        
        self.all_contacts = []
        self.comments = {}
        self.after_id = None
        self.original_edit_value = None
        self.message_templates = []
        self.message_templates_paths = []
        self.auto_send_running = False
        self.auto_send_stop_requested = False
        self.current_auto_index = 0
        self.countdown_after_id = None
        
        self.custom_message_panel = None
        self.custom_message_text_widget = None
        self.is_custom_message_panel_visible = False
        
        # --- WIDGET DO HISTÓRICO DE CHAT ---
        self.chat_history_text = None

        self.wpp_button = None

        # --- Variáveis da Barra de Status ---
        self.status_list_var = tk.StringVar(value="Nenhuma lista carregada")
        self.status_txt_var = tk.StringVar(value="Templates: 0")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF", rowheight=25)
        style.map('Treeview', background=[('selected', '#E0E0E0')], foreground=[('selected', '#000000')])
        
        self._create_widgets()
        self._create_context_menu()
        self.bind("<Alt-w>", self._send_whatsapp_message)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._load_state()
        
        self._update_profile_menu()
        self.active_profile_name.trace_add("write", self._on_profile_change)
        
        # --- CONFIGURAÇÃO DO DESTAQUE DE ÚLTIMO ENVIO ---
        self.tree.tag_configure('last_sent', background='#d8e8ff') # Um azul bem claro
        self.tree.tag_configure('success', background='#d9f7d9')   # Verde claro
        self.tree.tag_configure('failed', background='#ffdddd')    # Vermelho claro
        self.last_sent_item_id = None # Armazena o ID do item na Treeview
        self.last_sent_contact_n = None # Armazena o número (N) do contato para persistência
        self.countdown_item_id = None # ID do item para o qual o countdown está rodando

        self._check_connection_periodically()

    def _get_active_connector(self):
        """Retorna a instância do conector para o perfil ativo."""
        profile_name = self.active_profile_name.get()
        return self.whatsapp_connectors.get(profile_name)

    def _check_connection_periodically(self):
        def check():
            connector = self._get_active_connector()
            if connector:
                old_status = connector.is_connected
                new_status = connector.check_connection_status()
                if old_status != new_status:
                    self._update_connection_button()
        
        threading.Thread(target=check, daemon=True).start()
        self.after(5000, self._check_connection_periodically)

    def _update_connection_button(self):
        connector = self._get_active_connector()
        if connector and connector.is_connected:
            self.connect_button.config(text="Desconectar", bg="#ffcccc")
        else:
            self.connect_button.config(text="Conectar", bg="#ccffcc")

    def _toggle_whatsapp_connection(self):
        connector = self._get_active_connector()
        if not connector:
            messagebox.showwarning("Nenhum Perfil", "Por favor, adicione e/ou selecione um perfil primeiro.")
            return

        if connector.is_connected:
            if messagebox.askyesno("Confirmar Desconexão Total",
                                   "Isso irá desconectar e limpar os dados da sessão atual no servidor, exigindo uma nova leitura de QR Code para reconectar.\n\nDeseja continuar?"):
                success, message = connector.logout_session()
                if success:
                    connector.token = None
                    connector.is_connected = False
                    self._update_connection_button()
                    messagebox.showinfo("Desconectado", "Sessão finalizada e limpa com sucesso.")
                else:
                    messagebox.showerror("Erro ao Deslogar", f"Não foi possível limpar a sessão no servidor.\nMotivo: {message}")
        else:
            success, message = connector.start_session()
            if success:
                self.after(2000, self._check_connection_and_update)
            else:
                messagebox.showerror("Erro", message)

    def _check_connection_and_update(self):
        connector = self._get_active_connector()
        if connector and connector.check_connection_status():
            self._update_connection_button()
        else:
            self.after(3000, self._check_connection_and_update)

    def _create_load_action_frame(self, parent):
        load_action_frame = tk.Frame(parent, bg="#F0F0F0")
        load_action_frame.pack(fill="x", pady=3)
        left_frame = tk.Frame(load_action_frame, bg="#F0F0F0")
        left_frame.pack(side="left")
        load_button = tk.Button(left_frame, text="LOAD", font=font.Font(family="Arial", size=10, weight="bold"), command=self._carregar_csv)
        load_button.pack(side="left")
        Tooltip(load_button, "Carregar uma nova lista de contatos (.csv)")
        status_buttons_frame = tk.Frame(left_frame, bg="#F0F0F0")
        status_buttons_frame.pack(side="left", padx=(5, 0))
        status_map = {"NA": "Não atendeu", "CP": "Caixa postal", "SI": "Sem interesse", "NE": "Não existe"}
        for key, value in status_map.items():
            b = tk.Button(status_buttons_frame, text=key, width=4, command=lambda v=value: self._set_status(v))
            b.pack(side="left", padx=1)
            Tooltip(b, f"Define o status do contato como '{value}'")
        
        action_buttons_frame = tk.Frame(load_action_frame, bg="#F0F0F0")
        action_buttons_frame.pack(side="right")
        
        self._create_profile_controls(action_buttons_frame)
        
        interval_frame = tk.Frame(action_buttons_frame, bg="#F0F0F0")
        interval_frame.pack(side="left", padx=(0, 10))
        tk.Label(interval_frame, text="Intervalo (s):", bg="#F0F0F0").pack(side="left", padx=(0,2))
        min_entry = tk.Entry(interval_frame, textvariable=self.min_interval_var, width=4, justify='center')
        min_entry.pack(side="left")
        Tooltip(min_entry, "Intervalo MÍNIMO em segundos")
        tk.Label(interval_frame, text="-", bg="#F0F0F0").pack(side="left", padx=(2,2))
        max_entry = tk.Entry(interval_frame, textvariable=self.max_interval_var, width=4, justify='center')
        max_entry.pack(side="left")
        Tooltip(max_entry, "Intervalo MÁXIMO em segundos")

        self.start_button = tk.Button(action_buttons_frame, text="START", width=6, command=self._toggle_auto_send, bg="#ccffcc")
        self.start_button.pack(side="left", padx=(0, 5))
        Tooltip(self.start_button, "Iniciar ou parar o envio automático")
        self.connect_button = tk.Button(action_buttons_frame, text="Conectar", width=10, command=self._toggle_whatsapp_connection, bg="#ccffcc")
        self.connect_button.pack(side="left", padx=(0, 5))
        Tooltip(self.connect_button, "Conectar/Desconectar do WhatsApp.\nDesconectar limpa a sessão atual.")
        txt_button = tk.Button(action_buttons_frame, text="TXT", width=3, command=self._load_message_templates)
        txt_button.pack(side="left", padx=1)
        Tooltip(txt_button, "Carregar modelos de mensagem de arquivos .txt")
        
        self.w_button = tk.Button(action_buttons_frame, text="W", width=3, command=self._send_whatsapp_message)
        self.w_button.pack(side="left", padx=1)
        Tooltip(self.w_button, "Enviar mensagem de template (Atalho: Alt+W)")
        
        self.wpp_button = tk.Button(action_buttons_frame, text="Wpp", width=4, command=self._toggle_custom_message_panel)
        self.wpp_button.pack(side="left", padx=1)
        Tooltip(self.wpp_button, "Mostrar/Ocultar painel de mensagem personalizada")

        l_button = tk.Button(action_buttons_frame, text="L", width=3)
        l_button.pack(side="left", padx=1)
        Tooltip(l_button, "Função de Ligar (a ser implementada)")
    
    def _create_profile_controls(self, parent):
        profile_frame = tk.Frame(parent, bg="#F0F0F0")
        profile_frame.pack(side="left", padx=(0, 10))

        tk.Label(profile_frame, text="Perfil WPP:", bg="#F0F0F0").pack(side="left")

        self.profile_menu = ttk.OptionMenu(profile_frame, self.active_profile_name, "Nenhum Perfil")
        self.profile_menu.pack(side="left", padx=5)

        add_button = tk.Button(profile_frame, text="+", command=self._add_new_profile, font=("Arial", 10, "bold"))
        add_button.pack(side="left")
        Tooltip(add_button, "Adicionar novo perfil de WhatsApp")

        remove_button = tk.Button(profile_frame, text="-", command=self._remove_profile, font=("Arial", 10, "bold"))
        remove_button.pack(side="left", padx=(2,0))
        Tooltip(remove_button, "Remover o perfil selecionado")

    def _add_new_profile(self):
        profile_name = simpledialog.askstring("Novo Perfil", "Digite um nome para o novo perfil (ex: 'Trabalho'):", parent=self)
        
        if profile_name and profile_name.strip():
            profile_name = profile_name.strip()
            if profile_name in self.whatsapp_connectors:
                messagebox.showwarning("Perfil Existente", "Um perfil com este nome já existe.")
                return
            
            self.whatsapp_connectors[profile_name] = WhatsAppConnector(session_name=profile_name)
            self.profile_names.append(profile_name)
            self._update_profile_menu()
            self.active_profile_name.set(profile_name)
            messagebox.showinfo("Sucesso", f"Perfil '{profile_name}' criado. Agora clique em 'Conectar' para logar.")

    def _remove_profile(self):
        connector = self._get_active_connector()
        if not connector:
            messagebox.showwarning("Nenhum Perfil", "Nenhum perfil selecionado para remover.")
            return

        profile_name = connector.session_name
        if messagebox.askyesno("Confirmar Remoção", f"Tem certeza que deseja remover o perfil '{profile_name}'?"):
            del self.whatsapp_connectors[profile_name]
            self.profile_names.remove(profile_name)
            self._update_profile_menu()
            if self.profile_names:
                self.active_profile_name.set(self.profile_names[0])
            else:
                self.active_profile_name.set("Nenhum Perfil")

    def _update_profile_menu(self):
        menu = self.profile_menu["menu"]
        menu.delete(0, "end")
        
        options = self.profile_names if self.profile_names else ["Nenhum Perfil"]
        
        for name in options:
            menu.add_command(label=name, command=lambda value=name: self.active_profile_name.set(value))
        
        if not self.active_profile_name.get() in self.profile_names:
             self.active_profile_name.set(options[0])

    def _on_profile_change(self, *args):
        connector = self._get_active_connector()
        if connector:
            threading.Thread(target=self._check_connection_and_update, daemon=True).start()
        else:
            self._update_connection_button()

    def _toggle_custom_message_panel(self):
        if self.is_custom_message_panel_visible:
            self.custom_message_panel.grid_forget()
            self.is_custom_message_panel_visible = False
            self.wpp_button.config(relief="raised")
        else:
            self.custom_message_panel.grid(row=1, column=0, sticky="ew")
            self.is_custom_message_panel_visible = True
            self.custom_message_text_widget.focus_set()
            self.wpp_button.config(relief="sunken")

    def _show_temporary_tooltip(self, widget, text):
        x = widget.winfo_rootx() + widget.winfo_width() + 5
        y = widget.winfo_rooty() + widget.winfo_height() + 5

        tooltip_window = tk.Toplevel(self)
        tooltip_window.wm_overrideredirect(True)
        tooltip_window.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tooltip_window, text=text, justify='left',
                         background="#e0f8e0", relief='solid', borderwidth=1,
                         font=("Arial", "9", "bold"), wraplength=200)
        label.pack(ipadx=10, ipady=5)
        
        tooltip_window.after(2500, tooltip_window.destroy)

    def _send_custom_message(self):
        message_content = self.custom_message_text_widget.get("1.0", tk.END).strip()
        if not message_content:
            messagebox.showwarning("Mensagem Vazia", "Por favor, digite uma mensagem para enviar.")
            return

        selected_id, _, full_contact_data = self._get_selected_contact_info()
        if not selected_id: return
        
        connector = self._get_active_connector()
        if not connector or not connector.is_connected:
            messagebox.showwarning("WhatsApp Desconectado", "Selecione um perfil e conecte ao WhatsApp antes de enviar.")
            return

        _, nome_completo, _, _, numero_telefone, _, _, _ = full_contact_data
        mensagem_filtrada = self._filtrar_caracteres_bmp(message_content)

        success, message = connector.send_message(numero_telefone, mensagem_filtrada)

        if success:
            self._show_temporary_tooltip(self.custom_message_text_widget, f"Mensagem enviada para {nome_completo}!")
            self.custom_message_text_widget.delete("1.0", tk.END)
        else:
            messagebox.showerror("Falha no Envio", f"Não foi possível enviar para {nome_completo}.\nMotivo: {message}")

    def _handle_custom_message_send_shortcut(self, event):
        self._send_custom_message()
        return "break"
    
    def _add_comment_to_contact(self, contact_number, telefone_id, comment_line):
        try:
            existing_comment = self.comments.get(telefone_id, "").strip()
            new_comment = f"{existing_comment}\n{comment_line}" if existing_comment else comment_line
            self.comments[telefone_id] = new_comment
            self._save_all_comments_to_file()
            
            if self.tree.selection() and self.tree.item(self.tree.selection()[0], 'values')[0] == contact_number:
                self.comment_text.config(state="normal")
                self.comment_text.delete("1.0", tk.END)
                self.comment_text.insert(tk.END, new_comment)
                self.comment_text.config(state="disabled")
        except Exception as e:
            print(f"Erro ao adicionar comentário: {e}")
    
    def _add_campaign_sent_comment(self, contact_number, telefone_id):
        timestamp = datetime.now().strftime("%d de %B, %H:%M de %Y")
        campaign_text = f"{timestamp} - Campanha enviada"
        self._add_comment_to_contact(contact_number, telefone_id, campaign_text)
    
    def _send_whatsapp_message(self, event=None):
        if self.auto_send_running:
            messagebox.showwarning("Modo Automático", "O envio automático está ativo. Use STOP para interromper primeiro.")
            return
        selected_id, contact_number, full_contact_data = self._get_selected_contact_info()
        if not selected_id: return

        connector = self._get_active_connector()
        if not connector or not connector.is_connected:
            messagebox.showwarning("WhatsApp Desconectado", "Selecione um perfil e conecte ao WhatsApp antes de enviar.")
            return

        if not self.message_templates:
            self._load_message_templates()
            if not self.message_templates: return
        
        template_aleatorio = random.choice(self.message_templates)
        _, nome_completo, _, _, numero_telefone, _, _, _ = full_contact_data
        nome_tratado = self._processar_nome(nome_completo)
        mensagem_personalizada = template_aleatorio.replace("[nome]", nome_tratado)
        mensagem_filtrada = self._filtrar_caracteres_bmp(mensagem_personalizada)
        
        self.update_idletasks()
        success, message = connector.send_message(numero_telefone, mensagem_filtrada)
        disparo_status = "Sucesso" if success else "Falhou"
        self._update_disparo_status(contact_number, disparo_status)
        
        if success:
            self._add_campaign_sent_comment(contact_number, numero_telefone)
            self._show_temporary_tooltip(self.w_button, f"Mensagem enviada para {nome_completo}!")
        else:
            messagebox.showerror("Falha no Envio", f"Não foi possível enviar para {nome_completo}.\nMotivo: {message}")

    def _update_countdown_in_list(self, item_id, remaining_time):
        if not self.auto_send_running or self.auto_send_stop_requested:
            # Limpa o status se o envio for interrompido
            if self.tree.exists(item_id):
                self.tree.set(item_id, "status_envio", "")
            return

        self.countdown_item_id = item_id
        if remaining_time > 0:
            if self.tree.exists(item_id):
                self.tree.set(item_id, "status_envio", f"Em {remaining_time}s...")
            self.countdown_after_id = self.after(1000, self._update_countdown_in_list, item_id, remaining_time - 1)
        else:
            if self.tree.exists(item_id):
                self.tree.set(item_id, "status_envio", "Enviando...")
            self.countdown_item_id = None

    def _toggle_auto_send(self):
        if not self.auto_send_running:
            connector = self._get_active_connector()
            if not connector or not connector.is_connected:
                messagebox.showwarning("WhatsApp Desconectado", "Selecione um perfil e conecte ao WhatsApp primeiro.")
                return

            if not self.all_contacts:
                messagebox.showwarning("Sem Contatos", "Carregue uma lista de contatos primeiro.")
                return
            if not self.message_templates:
                messagebox.showwarning("Sem Mensagens", "Carregue os templates de mensagem primeiro.")
                return

            selected_items = self.tree.selection()
            if not selected_items:
                messagebox.showwarning("Início Requerido", "Por favor, selecione um contato na lista para iniciar o envio automático.")
                return

            selected_n = self.tree.item(selected_items[0], 'values')[0]
            start_index = next((i for i, contact in enumerate(self.all_contacts) if contact[0] == selected_n), -1)

            if start_index == -1:
                messagebox.showerror("Erro", "Não foi possível encontrar o contato selecionado na lista de dados.")
                return

            self.auto_send_running = True
            self.auto_send_stop_requested = False
            self.current_auto_index = start_index
            self.start_button.config(text="STOP", bg="#ffcccc")
            self._start_auto_send()
        else:
            self._stop_auto_send()

    def _stop_auto_send(self):
        if self.countdown_after_id:
            self.after_cancel(self.countdown_after_id)
            self.countdown_after_id = None
        
        # Limpa a mensagem de contagem regressiva do item atual
        if self.countdown_item_id and self.tree.exists(self.countdown_item_id):
            self.tree.set(self.countdown_item_id, "status_envio", "")
            self.countdown_item_id = None

        self.auto_send_stop_requested = True
        self.auto_send_running = False
        self.start_button.config(text="START", bg="#ccffcc")
        self.title("Huby App - Gerenciador e Enviador")
        print("Envio automático interrompido pelo usuário")

    def _start_auto_send(self):
        if not self.auto_send_running or self.auto_send_stop_requested: return
        
        if self.current_auto_index >= len(self.all_contacts):
            self._generate_send_report()
            self._stop_auto_send()
            messagebox.showinfo("Concluído", "Todos os contatos foram processados!")
            return
        
        contact = self.all_contacts[self.current_auto_index]
        contact_id = contact[0]
        for item in self.tree.get_children():
            if self.tree.item(item, 'values')[0] == contact_id:
                self.tree.selection_set(item); self.tree.focus(item); self.tree.see(item)
                self.on_item_select(None)
                break
        self.after(1000, self._send_auto_message)

    def _send_auto_message(self):
        if self.auto_send_stop_requested: return
        
        selected_id, contact_number, full_contact_data = self._get_selected_contact_info()
        
        # --- LÓGICA DE ATUALIZAÇÃO DO DESTAQUE ---
        if self.last_sent_item_id:
            try:
                # Pega as tags existentes, remove 'last_sent' e reaplica as outras
                current_tags = list(self.tree.item(self.last_sent_item_id, 'tags'))
                if 'last_sent' in current_tags:
                    current_tags.remove('last_sent')
                self.tree.item(self.last_sent_item_id, tags=tuple(current_tags))
            except tk.TclError:
                pass # O item pode não existir mais, ignora o erro
        
        if selected_id:
            self.last_sent_item_id = selected_id
            self.last_sent_contact_n = contact_number
        # --- FIM DA LÓGICA DE DESTAQUE ---

        if not selected_id:
            self.current_auto_index += 1; self.after(100, self._start_auto_send)
            return
        
        connector = self._get_active_connector()
        if not connector or not connector.is_connected:
            self._stop_auto_send()
            messagebox.showwarning("Envio Parado", "O envio foi interrompido (WhatsApp desconectado).")
            return

        template_aleatorio = random.choice(self.message_templates)
        _, nome_completo, _, _, numero_telefone, _, _, _ = full_contact_data
        nome_tratado = self._processar_nome(nome_completo)
        mensagem_personalizada = template_aleatorio.replace("[nome]", nome_tratado)
        mensagem_filtrada = self._filtrar_caracteres_bmp(mensagem_personalizada)
        
        success, message = connector.send_message(numero_telefone, mensagem_filtrada)
        disparo_status = "Sucesso" if success else "Falhou"
        self._update_disparo_status(contact_number, disparo_status)
        
        # Define a cor e o status na lista baseado no sucesso ou falha
        if success:
            self._add_campaign_sent_comment(contact_number, numero_telefone)
            self.tree.item(selected_id, tags=('success',))
            self.tree.set(selected_id, "status_envio", "✓ Sucesso")
            print(f"Mensagem enviada com sucesso para {nome_completo}")
        else:
            self.tree.item(selected_id, tags=('failed',))
            self.tree.set(selected_id, "status_envio", "✗ Falhou")
            print(f"Erro ao enviar para {nome_completo}: {message}")
        
        # Aplica o destaque azul por cima da cor de status
        current_tags = list(self.tree.item(selected_id, 'tags'))
        if 'last_sent' not in current_tags:
            current_tags.append('last_sent')
        self.tree.item(selected_id, tags=tuple(current_tags))

        self.current_auto_index += 1
        if self.current_auto_index < len(self.all_contacts) and not self.auto_send_stop_requested:
            intervalo = 1 # Intervalo padrão de 1 segundo para falhas
            if success: # Se teve sucesso, calcula o intervalo aleatório
                try:
                    min_i = int(self.min_interval_var.get())
                    max_i = int(self.max_interval_var.get())
                    if min_i <= 0 or max_i < min_i: raise ValueError("Intervalo inválido")
                    intervalo = random.randint(min_i, max_i)
                except (ValueError, tk.TclError):
                    messagebox.showwarning("Intervalo Inválido", "Intervalo inválido. Usando padrão (20-45s).")
                    self.min_interval_var.set("20"); self.max_interval_var.set("45")
                    intervalo = random.randint(20, 45)

            print(f"Próximo envio em {intervalo} segundos...")
            
            # Encontra o ID do próximo item para exibir o contador
            proximo_contato = self.all_contacts[self.current_auto_index]
            proximo_contato_id_n = proximo_contato[0]
            proximo_item_id = None
            for item in self.tree.get_children():
                if self.tree.item(item, 'values')[0] == proximo_contato_id_n:
                    proximo_item_id = item
                    break
            
            if proximo_item_id:
                self._update_countdown_in_list(proximo_item_id, intervalo)

            self.after(intervalo * 1000, self._start_auto_send)
        else:
            if not self.auto_send_stop_requested: self._start_auto_send()
            else: self._stop_auto_send()

    def _add_contact_not_found_comment(self, contact_number, telefone_id, nome_completo):
        timestamp = datetime.now().strftime("%d de %B, %H:%M de %Y")
        comment_text = f"{timestamp} - Contato não encontrado no WhatsApp"
        self._add_comment_to_contact(contact_number, telefone_id, comment_text)
        for i, contact in enumerate(self.all_contacts):
            if contact[0] == contact_number:
                contact_list = list(contact); contact_list[3] = "Não encontrado"
                self.all_contacts[i] = tuple(contact_list)
                break
        for item in self.tree.get_children():
            if self.tree.item(item, 'values')[0] == contact_number:
                values = list(self.tree.item(item, 'values')); values[3] = "Não encontrado"
                self.tree.item(item, values=values)
                break

    def _load_messages_from_paths(self, filepaths):
        loaded_templates, loaded_paths, failed_files = [], [], []
        for path in filepaths:
            if not os.path.exists(path): failed_files.append(os.path.basename(path)); continue
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    loaded_templates.append(file.read()); loaded_paths.append(path)
            except Exception: failed_files.append(os.path.basename(path))
        
        if not loaded_templates:
            self.status_txt_var.set("Templates: 0") # Atualiza se falhar
            return False, failed_files
        
        self.message_templates, self.message_templates_paths = loaded_templates, loaded_paths
        
        # --- ATUALIZAÇÃO DA BARRA DE STATUS ---
        self.status_txt_var.set(f"Templates: {len(self.message_templates)}")
        # --- FIM DA ATUALIZAÇÃO ---
        
        return True, failed_files
    
    def _load_message_templates(self):
        filepaths = filedialog.askopenfilenames(title="Selecione até 10 arquivos de mensagem", filetypes=[("Arquivos de Texto", "*.txt")])
        if not filepaths: return
        filepaths = filepaths[:10]
        success, failed_files = self._load_messages_from_paths(filepaths)
        if success:
            msg = f"{len(self.message_templates)} templates carregados."
            if failed_files: msg += f"\nFalha ao carregar: {', '.join(failed_files)}"
            messagebox.showinfo("Sucesso", msg)
        else: messagebox.showerror("Erro", "Não foi possível carregar nenhum template.")

    def _processar_nome(self, nome_completo):
        if not isinstance(nome_completo, str) or not nome_completo.strip(): return ""
        palavras = nome_completo.split()
        return palavras[1] if palavras[0].lower() in ['doutor', 'dr.'] and len(palavras) > 1 else palavras[0]

    def _filtrar_caracteres_bmp(self, texto):
        return "".join(c for c in texto if ord(c) <= 0xFFFF)

    def _create_widgets(self):
        top_controls_frame = tk.Frame(self, bg="#F0F0F0", padx=5, pady=5)
        top_controls_frame.pack(fill="x")
        self._create_info_frame(parent=top_controls_frame)
        self._create_load_action_frame(parent=top_controls_frame)
        self._create_search_frame(parent=top_controls_frame)
        self._create_main_layout()
        self._create_status_bar()

    def _create_status_bar(self):
        status_bar = tk.Frame(self, relief="sunken", borderwidth=1, bg="#F0F0F0")
        status_bar.pack(side="bottom", fill="x", padx=2, pady=2)
        
        list_label = tk.Label(status_bar, textvariable=self.status_list_var, anchor='w', bg="#F0F0F0")
        list_label.pack(side="left", padx=5)
        
        txt_label = tk.Label(status_bar, textvariable=self.status_txt_var, anchor='e', bg="#F0F0F0")
        txt_label.pack(side="right", padx=5)

    def _create_info_frame(self, parent):
        info_frame = tk.Frame(parent, bg="#F0F0F0")
        info_frame.pack(fill="x", pady=(0, 3))
        load_entry_font = font.Font(family="Arial", size=16, weight="bold")
        self.nome_entry = tk.Entry(info_frame, textvariable=self.nome_var, font=load_entry_font, state="readonly", readonlybackground="#F0F0F0", fg="black", width=25)
        self.nome_entry.pack(side="left", ipady=5, expand=True, fill="x")
        self.telefone_entry = tk.Entry(info_frame, textvariable=self.telefone_var, font=load_entry_font, state="readonly", readonlybackground="#F0F0F0", fg="black", width=18)
        self.telefone_entry.pack(side="left", ipady=5, padx=(3, 0))
        for entry in [self.nome_entry, self.telefone_entry]:
            entry.bind("<Double-Button-1>", self._enable_entry_edit); entry.bind("<Return>", self._save_entry_edit)
            entry.bind("<Escape>", self._cancel_entry_edit); entry.bind("<FocusOut>", self._cancel_entry_edit)

    def _enable_entry_edit(self, event):
        entry = event.widget
        if not self.tree.selection(): return
        self.original_edit_value = entry.get()
        entry.config(state="normal", readonlybackground="white"); entry.focus_set(); entry.select_range(0, 'end')

    def _save_entry_edit(self, event):
        entry = event.widget; new_value = entry.get().strip()
        if new_value == self.original_edit_value or not new_value: self._cancel_entry_edit(event); return "break"
        selected_id, contact_number, _ = self._get_selected_contact_info()
        if not selected_id: self._cancel_entry_edit(event); return "break"
        if entry == self.nome_entry:
            new_value_formatted = new_value.title()
            self._update_contact_data(selected_id, contact_number, 1, new_value_formatted)
            self._save_edit_to_csv(contact_number, 0, new_value_formatted)
            self.nome_var.set((new_value_formatted[:20] + '...').upper() if len(new_value_formatted) > 20 else new_value_formatted.upper())
        elif entry == self.telefone_entry:
            new_phone_id = "".join(filter(str.isdigit, new_value))
            new_phone_formatted = self._formatar_telefone(new_phone_id)
            self._update_contact_data(selected_id, contact_number, 2, new_phone_formatted, phone_id=new_phone_id)
            self._save_edit_to_csv(contact_number, 2, new_phone_id)
        entry.config(state="readonly", readonlybackground="#F0F0F0"); self.tree.focus_set(); return "break"

    def _cancel_entry_edit(self, event):
        if event.widget.cget('state') == 'normal':
            event.widget.config(state="readonly", readonlybackground="#F0F0F0"); self.tree.focus_set()
        return "break"

    def _update_contact_data(self, selected_id, contact_number, value_index, new_value, phone_id=None):
        for i, contact in enumerate(self.all_contacts):
            if contact[0] == contact_number:
                cl = list(contact); cl[value_index] = new_value
                if phone_id is not None: cl[4] = phone_id
                self.all_contacts[i] = tuple(cl)
                break
        current_values = list(self.tree.item(selected_id, 'values')); current_values[value_index] = new_value
        self.tree.item(selected_id, values=current_values)

    def _get_selected_contact_info(self):
        if not (selected_items := self.tree.selection()):
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione um contato primeiro.")
            return None, None, None
        selected_id = selected_items[0]
        values = self.tree.item(selected_id, 'values')
        contact_number = values[0]
        full_contact_data = next((c for c in self.all_contacts if c[0] == contact_number), None)
        return selected_id, contact_number, full_contact_data

    def _create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Não atendeu", command=lambda: self._set_status("Não atendeu"))
        self.context_menu.add_command(label="Sem interesse", command=lambda: self._set_status("Sem interesse"))
        self.context_menu.add_command(label="Caixa postal", command=lambda: self._set_status("Caixa postal"))
        self.context_menu.add_command(label="Não existe", command=lambda: self._set_status("Não existe"))
        self.context_menu.add_command(label="Limpar Status", command=lambda: self._set_status(""))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Editar Nome", command=lambda: self._enable_entry_edit(SimpleNamespace(widget=self.nome_entry)))
        self.context_menu.add_command(label="Editar Telefone", command=lambda: self._enable_entry_edit(SimpleNamespace(widget=self.telefone_entry)))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Adicionar Novo Contato", command=self._add_new_contact)

    def _add_new_contact(self):
        if not self.current_filepath:
            messagebox.showwarning("Nenhum Arquivo", "Carregue um arquivo CSV antes de adicionar um novo contato.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Adicionar Novo Contato")
        
        dialog_width = 300
        dialog_height = 150

        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()

        position_x = main_window_x + (main_window_width // 2) - (dialog_width // 2)
        position_y = main_window_y + (main_window_height // 2) - (dialog_height // 2)

        dialog.geometry(f"{dialog_width}x{dialog_height}+{position_x}+{position_y}")
        dialog.resizable(False, False)
        
        tk.Label(dialog, text="Nome:").pack(pady=(10,0))
        nome_entry = tk.Entry(dialog, width=40)
        nome_entry.pack()
        
        tk.Label(dialog, text="Telefone:").pack(pady=(10,0))
        telefone_entry = tk.Entry(dialog, width=40)
        telefone_entry.pack()

        def save_contact():
            nome = nome_entry.get().strip()
            telefone = telefone_entry.get().strip()

            if not nome or not telefone:
                messagebox.showwarning("Campos Vazios", "Nome e telefone são obrigatórios.", parent=dialog)
                return

            telefone_padronizado = ''.join(filter(str.isdigit, telefone))

            try:
                new_row = [nome, '', telefone_padronizado]
                
                with open(self.current_filepath, 'a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(new_row)
                
                dialog.destroy()
                messagebox.showinfo("Sucesso", f"Contato '{nome}' adicionado com sucesso!\nA lista será recarregada.")
                self._load_data_from_path(self.current_filepath)

            except Exception as e:
                messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar o contato no arquivo CSV.\nErro: {e}", parent=dialog)

        save_button = tk.Button(dialog, text="Salvar", command=save_contact)
        save_button.pack(pady=10)
        dialog.transient(self)
        dialog.grab_set()
        nome_entry.focus_set()
        self.wait_window(dialog)

    def _save_edit_to_csv(self, contact_number, column_index, new_value):
        if not self.current_filepath: return False
        try:
            with open(self.current_filepath, 'r', encoding='utf-8', newline='') as file: lines = list(csv.reader(file))
            target_line_index = int(contact_number)
            if 0 < target_line_index < len(lines):
                target_row = lines[target_line_index]
                while len(target_row) <= column_index: target_row.append('')
                target_row[column_index] = new_value
                with open(self.current_filepath, 'w', encoding='utf-8', newline='') as file: csv.writer(file).writerows(lines)
                return True
            return False
        except Exception as e: print(f"ERRO ao editar CSV: {e}"); return False

    def _create_search_frame(self, parent):
        search_frame = tk.Frame(parent, bg="#F0F0F0"); search_frame.pack(fill="x", pady=(3, 0))
        tk.Label(search_frame, text="Pesquisar NOME:", bg="#F0F0F0").pack(side="left")
        search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", padx=3, fill="x", expand=True)
        self.search_var.trace_add("write", self._filter_contacts)
        search_entry.bind("<Down>", self._focus_list_and_select_first); search_entry.bind("<Up>", self._focus_list_and_select_first)

    def _create_main_layout(self):
        main_frame = tk.Frame(self, bg="#F0F0F0"); main_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self._create_list_frame(parent=main_frame)
        
        right_column_frame = tk.Frame(main_frame, width=220, bg="#F0F0F0")
        right_column_frame.pack(side="right", fill="y", padx=(5, 0))
        right_column_frame.pack_propagate(False)

        self._create_comment_frame(parent=right_column_frame)
        self._create_chat_history_frame(parent=right_column_frame)

    def _create_list_frame(self, parent):
        list_frame = tk.Frame(parent, bg="#F0F0F0")
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=0)
        list_frame.grid_columnconfigure(0, weight=1)

        tree_container = tk.Frame(list_frame)
        tree_container.grid(row=0, column=0, sticky="nsew")

        # Adicionada a coluna "status_envio"
        self.columns_display = ("n", "nome", "telefone", "status_envio", "status", "disparo")
        self.tree = ttk.Treeview(tree_container, columns=self.columns_display, show="headings")
        
        self.tree.heading("n", text="N")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("telefone", text="Telefone")
        self.tree.heading("status_envio", text="Status Envio")
        self.tree.heading("status", text="Status")
        self.tree.heading("disparo", text="Disparo")

        for col in self.columns_display:
            self.tree.heading(col, command=lambda _c=col: self._sort_column(_c, False))
            
        self.tree.column("n", width=40, anchor="center")
        self.tree.column("nome", width=150)
        self.tree.column("telefone", width=110)
        self.tree.column("status_envio", width=100, anchor="center") # Nova coluna
        self.tree.column("status", width=100)
        self.tree.column("disparo", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select); self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Up>", self._select_previous_item); self.tree.bind("<Down>", self._select_next_item)

        self.custom_message_panel = tk.Frame(list_frame, bg="#e0e0e0")
        
        self.custom_message_text_widget = tk.Text(self.custom_message_panel, height=3, wrap="word", font=("Arial", 10))
        self.custom_message_text_widget.pack(side="left", fill="both", expand=True, pady=5)
        self.custom_message_text_widget.bind("<Return>", self._handle_custom_message_send_shortcut)

        self.send_button = tk.Button(self.custom_message_panel, text=">", font=("Arial", 10, "bold"),
                                        command=self._send_custom_message, width=4)
        self.send_button.pack(side="right", fill="both", padx=(0, 5), pady=5)
        Tooltip(self.send_button, "Enviar (Enter)")

    def _create_comment_frame(self, parent):
        comment_panel = tk.Frame(parent, bg="#F0F0F0")
        comment_panel.pack(fill="x", expand=False)
        tk.Label(comment_panel, text="Observações:", bg="#F0F0F0", font=("Arial", 10, "bold")).pack(anchor="w")
        self.comment_text = tk.Text(comment_panel, width=25, height=5, wrap="word", relief="sunken", borderwidth=1, font=("Arial", 10))
        self.comment_text.pack(fill="both", expand=True, pady=(2,0))
        self.comment_text.bind("<KeyRelease>", self._schedule_comment_save); self.comment_text.config(state="disabled")
        tk.Button(comment_panel, text="Salvar (Ctrl + S)", command=self._save_comment).pack(fill="x", pady=(5, 0))

    def _create_chat_history_frame(self, parent):
        history_panel = tk.Frame(parent, bg="#F0F0F0")
        history_panel.pack(fill="both", expand=True, pady=(10, 0))

        tk.Label(history_panel, text="Histórico da Conversa:", bg="#F0F0F0", font=("Arial", 10, "bold")).pack(anchor="w")
        
        text_frame = tk.Frame(history_panel)
        text_frame.pack(fill="both", expand=True, pady=(2,0))

        self.chat_history_text = tk.Text(text_frame, width=25, wrap="word", relief="sunken",
                                         borderwidth=1, font=("Arial", 9), state="disabled",
                                         bg="#fdfdfd")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.chat_history_text.yview)
        self.chat_history_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.chat_history_text.pack(side="left", fill="both", expand=True)

        self.chat_history_text.tag_configure("contact_msg", foreground="#000080")
        self.chat_history_text.tag_configure("my_msg", foreground="#006400")
        self.chat_history_text.tag_configure("timestamp", foreground="#696969", font=("Arial", 7))

    def on_item_select(self, event):
        for entry in [self.nome_entry, self.telefone_entry]:
            if entry.cget('state') == 'normal': self._cancel_entry_edit(SimpleNamespace(widget=entry))
        if not (selected_items := self.tree.selection()):
            self.nome_var.set(""); self.telefone_var.set(""); self.comment_text.config(state="disabled")
            self.comment_text.delete("1.0", tk.END)
            return
        selected_n = self.tree.item(selected_items[0], 'values')[0]
        if full_contact_data := next((c for c in self.all_contacts if c[0] == selected_n), None):
            _, nome, tel_fmt, _, tel_id, _, _, _ = full_contact_data
            self.nome_var.set((nome[:20] + '...').upper() if len(nome) > 20 else nome.upper())
            self.telefone_var.set(tel_fmt)
            comment = self.comments.get(tel_id, "")
            self.comment_text.config(state="normal"); self.comment_text.delete("1.0", tk.END)
            self.comment_text.insert(tk.END, comment)
            
            self._clear_and_update_chat_history("Carregando mensagens...")
            threading.Thread(target=self._fetch_and_display_messages, args=(tel_id,), daemon=True).start()

    def _fetch_and_display_messages(self, phone_number):
        connector = self._get_active_connector()
        if not connector or not connector.is_connected:
            self.after(0, self._clear_and_update_chat_history, "Perfil desconectado.")
            return

        success, data = connector.get_messages_for_contact(phone_number)
        
        if success:
            self.after(0, self._display_messages, data)
        else:
            self.after(0, self._clear_and_update_chat_history, f"Erro:\n{data}")

    def _display_messages(self, messages):
        self.chat_history_text.config(state="normal")
        self.chat_history_text.delete("1.0", tk.END)

        if not messages:
            self.chat_history_text.insert(tk.END, "Nenhuma mensagem encontrada.")
            self.chat_history_text.config(state="disabled")
            return

        for msg in reversed(messages[-20:]):
            if 'body' in msg and msg['body']:
                sender_tag = "my_msg" if msg.get('fromMe') else "contact_msg"
                sender_name = "Eu: " if msg.get('fromMe') else "Contato: "
                
                try:
                    ts = datetime.fromtimestamp(msg['timestamp']).strftime('%d/%m/%Y %H:%M')
                    self.chat_history_text.insert(tk.END, f"{ts}\n", "timestamp")
                except Exception:
                    pass

                self.chat_history_text.insert(tk.END, f"{sender_name}", sender_tag)
                self.chat_history_text.insert(tk.END, f"{msg['body']}\n\n")

        self.chat_history_text.config(state="disabled")
        self.chat_history_text.see(tk.END)

    def _clear_and_update_chat_history(self, text):
        self.chat_history_text.config(state="normal")
        self.chat_history_text.delete("1.0", tk.END)
        self.chat_history_text.insert(tk.END, text)
        self.chat_history_text.config(state="disabled")
    
    def _schedule_comment_save(self, event=None):
        if self.after_id: self.after_cancel(self.after_id)
        self.after_id = self.after(1500, self._save_comment)

    def _save_comment(self):
        if not (selected_items := self.tree.selection()): return
        selected_n = self.tree.item(selected_items[0], 'values')[0]
        if telefone_id := next((c[4] for c in self.all_contacts if c[0] == selected_n), None):
            self.comments[telefone_id] = self.comment_text.get("1.0", tk.END).strip()
            self._save_all_comments_to_file()

    def _save_all_comments_to_file(self):
        try:
            with open(self.comments_filepath, "w", encoding='utf-8') as f: json.dump(self.comments, f, indent=4, ensure_ascii=False)
        except Exception as e: print(f"Erro ao salvar comentários: {e}")

    def _load_data_from_path(self, filepath):
        if self.last_sent_item_id:
            try:
                self.tree.item(self.last_sent_item_id, tags=())
            except tk.TclError:
                pass 
        self.last_sent_item_id = None
        self.last_sent_contact_n = None
        
        self.current_filepath = filepath
        try:
            with open(self.comments_filepath, "r", encoding='utf-8') as f: self.comments = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): self.comments = {}
        
        nova_lista_contatos_full = []
        try:
            with open(filepath, mode='r', encoding='utf-8') as file:
                csv_reader = csv.reader(file); next(csv_reader, None)
                for i, row in enumerate(csv_reader, 1):
                    if not row: continue
                    tel_id = row[2] if len(row) > 2 else ""
                    # Estrutura do tuple de 8 elementos
                    nova_lista_contatos_full.append((f"{i:03d}", row[0] if len(row) > 0 else "", 
                                                     self._formatar_telefone(tel_id), row[3] if len(row) > 3 else "",
                                                     tel_id, "", "", ""))
            self.all_contacts = nova_lista_contatos_full
            self.nome_var.set(""); self.telefone_var.set("")
            
            file_name = os.path.basename(filepath)
            self.status_list_var.set(f"Lista: {file_name}")

            # Estrutura de exibição com 6 colunas
            display_data = [(c[0], c[1], c[2], c[7], c[3], c[6]) for c in self.all_contacts]
            self._populate_treeview(display_data)
        except Exception as e:
            self.status_list_var.set("Erro ao carregar lista")
            messagebox.showerror("Erro ao ler arquivo", f"Ocorreu um erro: {e}")
    
    def _save_state(self):
        state = {
            "last_filepath": self.current_filepath,
            "last_selected_contact": self.tree.item(self.tree.selection()[0], 'values')[0] if self.tree.selection() else "",
            "last_geometry": self.geometry(),
            "last_message_files": self.message_templates_paths,
            "min_interval": self.min_interval_var.get(),
            "max_interval": self.max_interval_var.get(),
            "wpp_panel_visible": self.is_custom_message_panel_visible,
            "profile_names": self.profile_names,
            "active_profile": self.active_profile_name.get(),
            "last_sent_contact_n": self.last_sent_contact_n
        }
        try:
            with open(self.config_filepath, "w") as f: json.dump(state, f, indent=4)
        except Exception as e: print(f"Erro ao salvar estado: {e}")

    def _load_state(self):
        if not os.path.exists(self.config_filepath): return
        try:
            with open(self.config_filepath, "r") as f: state = json.load(f)
            if state.get("last_geometry"): self.geometry(state.get("last_geometry"))
            self.min_interval_var.set(state.get("min_interval", "20"))
            self.max_interval_var.set(state.get("max_interval", "45"))
            
            if message_files := state.get("last_message_files"): self._load_messages_from_paths(message_files)

            self.profile_names = state.get("profile_names", [])
            for name in self.profile_names:
                self.whatsapp_connectors[name] = WhatsAppConnector(session_name=name)
            
            active_prof = state.get("active_profile")
            if active_prof in self.profile_names:
                self.active_profile_name.set(active_prof)
            elif self.profile_names:
                self.active_profile_name.set(self.profile_names[0])

            if filepath := state.get("last_filepath"):
                if os.path.exists(filepath):
                    self._load_data_from_path(filepath)
                    
                    if last_sent_n := state.get("last_sent_contact_n"):
                        self.last_sent_contact_n = last_sent_n
                        for child_id in self.tree.get_children():
                            if self.tree.item(child_id, 'values')[0] == last_sent_n:
                                self.tree.item(child_id, tags=('last_sent',))
                                self.last_sent_item_id = child_id
                                break
                    
                    if last_contact := state.get("last_selected_contact"):
                        for child in self.tree.get_children():
                            if self.tree.item(child, 'values')[0] == last_contact:
                                self.tree.selection_set(child); self.tree.focus(child); self.tree.see(child)
                                break
                else:
                    warning_message = f"O arquivo da lista anterior não foi encontrado no caminho:\n\n{filepath}\n\nEle pode ter sido movido ou excluído."
                    messagebox.showwarning("Arquivo Não Encontrado", warning_message)
                    self.status_list_var.set("Lista anterior não encontrada")
                        
            if state.get("wpp_panel_visible"):
                self._toggle_custom_message_panel()

        except Exception as e: print(f"Erro ao carregar estado: {e}")

    def _on_closing(self):
        self._save_comment(); self._save_state(); self.destroy()

    def _focus_list_and_select_first(self, event):
        if visible_items := self.tree.get_children():
            self.tree.focus_set(); self.tree.selection_set(visible_items[0]); self.tree.focus(visible_items[0])
            return "break"

    def _filter_contacts(self, *args):
        search_term = self.search_var.get().lower()
        filtered = [c for c in self.all_contacts if not search_term or search_term in str(c[1]).lower()]
        display_data = [(c[0], c[1], c[2], c[7], c[3], c[6]) for c in filtered]
        self._populate_treeview(display_data)

    def _select_previous_item(self, event):
        if (ci := self.tree.focus()) and (pi := self.tree.prev(ci)):
            self.tree.selection_set(pi); self.tree.focus(pi); self.tree.see(pi)
        return "break"

    def _select_next_item(self, event):
        if (ci := self.tree.focus()) and (ni := self.tree.next(ci)):
            self.tree.selection_set(ni); self.tree.focus(ni); self.tree.see(ni)
        return "break"

    def _sort_column(self, col, reverse):
        col_map = {"n": 0, "nome": 1, "telefone": 2, "status": 3, "disparo": 6, "status_envio": 7}
        
        sort_index = col_map.get(col)
        if sort_index is None: return

        current_order_n = [self.tree.set(c, "n") for c in self.tree.get_children('')]
        data_to_sort = [c for n in current_order_n for c in self.all_contacts if c[0] == n]
        
        key_func = (lambda t: int(t[sort_index])) if col == 'n' else (lambda t: str(t[sort_index]).lower())
        data_to_sort.sort(key=key_func, reverse=reverse)
        
        display_data = [(c[0], c[1], c[2], c[7], c[3], c[6]) for c in data_to_sort]
        self._populate_treeview(display_data)
        
        self.tree.heading(col, command=lambda _c=col: self._sort_column(_c, not reverse))

    def _populate_treeview(self, data):
        self.tree.delete(*self.tree.get_children())
        for contact in data: self.tree.insert("", "end", values=contact)

    def _formatar_telefone(self, numero_str):
        n = ''.join(filter(str.isdigit, str(numero_str)))
        if len(n) == 13: return f"+{n[:2]} ({n[2:4]}) {n[4:9]}-{n[9:]}"
        if len(n) == 12: return f"+{n[:2]} ({n[2:4]}) {n[4:8]}-{n[8:]}"
        if len(n) == 11: return f"({n[:2]}) {n[2:7]}-{n[7:]}"
        if len(n) == 10: return f"({n[:2]}) {n[2:6]}-{n[6:]}"
        return numero_str

    # --- MÉTODO QUE ESTAVA FALTANDO ---
    def _carregar_csv(self):
        if filepath := filedialog.askopenfilename(filetypes=[("Arquivos CSV", "*.csv")]):
            self._load_data_from_path(filepath)

    def _show_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
        self.context_menu.post(event.x_root, event.y_root)

    def _set_status(self, new_status):
        if not (selected_items := self.tree.selection()):
            messagebox.showwarning("Nenhum Contato", "Selecione um contato para alterar o status."); return
        timestamp = datetime.now().strftime("%d de %B de %Y, %H:%M"); new_comment_line = f"{timestamp}\n{new_status}"
        for item_id in selected_items:
            contact_number = self.tree.item(item_id, 'values')[0]
            for i, contact in enumerate(self.all_contacts):
                if contact[0] == contact_number:
                    n, nome, tel, _, tel_id, o_s, d, s_e = contact
                    self.all_contacts[i] = (n, nome, tel, new_status, tel_id, o_s, d, s_e)
                    if new_status:
                        self._add_comment_to_contact(contact_number, tel_id, new_comment_line)
                    break
            v = list(self.tree.item(item_id, 'values')); v[4] = new_status; self.tree.item(item_id, values=v)
            if not self._save_status_to_csv(contact_number, new_status):
                messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar a alteração para {contact_number}.")
                self._load_data_from_path(self.current_filepath); return
        self.on_item_select(None)
    
    def _update_disparo_status(self, contact_number, new_disparo_status):
        for i, contact in enumerate(self.all_contacts):
            if contact[0] == contact_number:
                n, nome, tel, s, tel_id, o_s, _, s_e = contact
                self.all_contacts[i] = (n, nome, tel, s, tel_id, o_s, new_disparo_status, s_e); break
        for item in self.tree.get_children():
            if self.tree.item(item, 'values')[0] == contact_number:
                v = list(self.tree.item(item, 'values')); v[5] = new_disparo_status
                self.tree.item(item, values=tuple(v)); break

    def _generate_send_report(self):
        timestamp = datetime.now().strftime("%d de %B de %Y, %H:%M:%S")
        processed_contacts = [c for c in self.all_contacts if c[6]]
        if not processed_contacts: return
        success = [c for c in processed_contacts if c[6] == "Sucesso"]
        failed = [c for c in processed_contacts if c[6] == "Falhou"]
        content = [f"Relatório de Disparos - {timestamp}", "="*50, "Resumo:",
                   f"  - Envios Tentados: {len(processed_contacts)}", f"  - Sucessos: {len(success)}",
                   f"  - Falhas: {len(failed)}", "\n" + "="*50 + "\n"]
        if success:
            content.append("ENVIOS COM SUCESSO:"); content.extend([f"  - [{c[0]}] {c[1]} - {c[2]}" for c in success]); content.append("\n")
        if failed:
            content.append("ENVIOS QUE FALHARAM:"); content.extend([f"  - [{c[0]}] {c[1]} - {c[2]}" for c in failed]); content.append("\n")
        try:
            if fp := filedialog.asksaveasfilename(title="Salvar Relatório de Disparos", defaultextension=".txt",
                                                    filetypes=[("Arquivos de Texto", "*.txt")],
                                                    initialfile=f"Relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"):
                with open(fp, "w", encoding="utf-8") as f: f.write("\n".join(content))
                messagebox.showinfo("Relatório Salvo", f"O relatório foi salvo com sucesso em:\n{fp}")
        except Exception as e: messagebox.showerror("Erro ao Salvar Relatório", f"Não foi possível salvar.\nErro: {e}")

    def _save_status_to_csv(self, contact_number, new_status):
        if not self.current_filepath: return False
        try:
            with open(self.current_filepath, 'r', encoding='utf-8', newline='') as file: lines = list(csv.reader(file))
            if 0 < (idx := int(contact_number)) < len(lines):
                row = lines[idx]
                while len(row) <= 3: row.append('')
                row[3] = new_status
                with open(self.current_filepath, 'w', encoding='utf-8', newline='') as file: csv.writer(file).writerows(lines)
                return True
            return False
        except Exception as e: print(f"ERRO ao salvar status no CSV: {e}"); return False

if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        import traceback; root = tk.Tk(); root.withdraw()
        messagebox.showerror("Erro Crítico", f"Ocorreu um erro fatal:\n\n{e}\n\n{traceback.format_exc()}")