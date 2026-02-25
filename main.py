import tkinter as tk
from PIL import Image, ImageTk
from strips import *
from langageNaturel import *
import tkinter.font as tkFont
from tkinter import messagebox
from tkinter import ttk
import webbrowser
from tkinter import PhotoImage


def split_text(text, max_words):
    """Découpe un texte en lignes de max_words mots."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line.split()) + len(word.split()) <= max_words:
            current_line += word + " "
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    if current_line.strip():
        lines.append(current_line.strip())
    return lines


class Cube:
    def __init__(self, canvas, name, x, y, size=50):
        self.canvas = canvas
        self.name = name
        self.size = size
        self.image = Image.open(f"img/{name}.jpeg")
        self.image = self.image.resize((size, size), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.image)
        self.id = canvas.create_image(x + size / 2, y + size / 2, image=self.photo)
        self.x = x
        self.y = y

    def move_to(self, x, y):
        dx = x - self.x
        dy = y - self.y
        self.canvas.move(self.id, dx, dy)
        self.x = x
        self.y = y


class RobotHand:
    # FIX: passage de la référence app en paramètre au lieu d'utiliser une variable globale
    def __init__(self, canvas, app, x, y, size=20, color="black"):
        self.canvas = canvas
        self.app = app
        self.size = size
        self.color = color
        self.id = canvas.create_oval(x - size/2, y, x + size/2, y + size, fill=color)
        self.cord = canvas.create_line(x, 0, x, y, width=3, fill=color)
        self.holding = None
        self.x = x
        self.y = y

    def update_cord(self):
        self.canvas.coords(self.cord, self.x, 0, self.x, self.y)

    def prendre(self, cube):
        if self.holding is None:
            self.move_horizontally(cube.x + 25, callback=lambda: self._descendre_vers_cube(cube))

    def _descendre_vers_cube(self, cube):
        self.move_vertically(cube.y - self.size, steps=10, callback=lambda: self._prendre_cube(cube))

    def _prendre_cube(self, cube):
        self.holding = cube
        self.app.update_place_status(cube.x, cube.y, True)
        max_y = self.app.get_highest_cube_position()
        self.move_vertically(max_y - self.size, steps=10, callback=self.app.execute_next_action)

    def deposer(self):
        if self.holding:
            free_place = self.app.get_free_place(self.holding.x)
            if free_place is not None:
                free_x, free_y = free_place
                self.move_horizontally(free_x + 25, callback=lambda: self._descendre_pour_deposer(free_x, free_y))

    def _descendre_pour_deposer(self, x, y):
        self.move_vertically(y - self.size, steps=10, callback=lambda: self._deposer_cube(x, y))

    def _deposer_cube(self, x, y):
        if self.holding:
            cube = self.holding
            cube.move_to(x, y)
            self.holding = None
            self.app.update_place_status(x, y, False)
            max_y = self.app.get_highest_cube_position()
            self.move_vertically(max_y - self.size, steps=10, callback=self.app.execute_next_action)

    def empiler(self, cube, target_cube):
        if self.holding == cube:
            self.move_horizontally(target_cube.x + 25, callback=lambda: self._descendre_sur_cube(target_cube))

    def _descendre_sur_cube(self, target_cube):
        self.move_vertically(target_cube.y - target_cube.size - self.size, steps=2, callback=lambda: self._placer_cube(target_cube))

    def _placer_cube(self, target_cube):
        if self.holding:
            cube = self.holding
            cube.move_to(target_cube.x, target_cube.y - target_cube.size)
            self.holding = None
            max_y = self.app.get_highest_cube_position()
            self.move_vertically(max_y - self.size, delay=10, callback=self.app.execute_next_action)

    def depiler(self, cube):
        self.move_horizontally(cube.x + 25, callback=lambda: self._descendre_vers_cube(cube))

    def move_horizontally(self, x, steps=35, delay=20, callback=None):
        dx = (x - self.x) / steps

        def step(i):
            if i < steps:
                self.canvas.move(self.id, dx, 0)
                self.x += dx
                self.update_cord()
                if self.holding:
                    self.holding.move_to(self.holding.x + dx, self.holding.y)
                self.canvas.after(delay, step, i + 1)
            else:
                if callback:
                    callback()

        step(0)

    def move_vertically(self, y, steps=35, delay=20, callback=None):
        dy = (y - self.y) / steps

        def step(i):
            if i < steps:
                self.canvas.move(self.id, 0, dy)
                self.y += dy
                self.update_cord()
                if self.holding:
                    self.holding.move_to(self.holding.x, self.y + self.size)
                self.canvas.after(delay, step, i + 1)
            else:
                if callback:
                    callback()

        step(0)


class Application(tk.Tk):

    # Constantes de l'interface
    TABLE_Y = 400
    BG_COLOR = "#091821"
    FRAME_COLOR = "#DCB48C"
    TABLE_COLOR = "#8B4513"
    CUBE_SIZE = 50
    CUBE_POSITIONS_X = [150, 250, 350, 450, 550, 650]
    CUBE_NAMES = ['A', 'B', 'C', 'D', 'E', 'F']

    def __init__(self):
        super().__init__()
        self.title("Monde de cubes")
        self.iconbitmap('img/logo.ico')
        self.state('zoomed')
        self.configure(bg=self.BG_COLOR)

        # État d'exécution
        self.actions = []
        self.action_index = 0
        self.is_executing = False  # FIX: empêcher les doubles exécutions

        # Canvas principal
        self.canvas = tk.Canvas(self, width=1200, height=600, bg=self.BG_COLOR)
        self.canvas.pack()

        self._draw_grid()
        self._draw_simulation_frame()
        self._draw_table()
        self._init_cubes()
        self._draw_plan_panel()
        self._draw_nlp_interface()

        # Initialisation du bras robot
        self.robot_hand = RobotHand(self.canvas, self, 175, 50)

        # Écrire l'état initial dans le fichier
        initial = [
            ONTABLE('A'), ONTABLE('B'), ONTABLE('C'),
            ONTABLE('D'), ONTABLE('E'), ONTABLE('F'),
            CLEAR('A'), CLEAR('B'), CLEAR('C'),
            CLEAR('D'), CLEAR('E'), CLEAR('F'), ARMEMPTY()
        ]
        write_state_to_file('initial.tx', transform_goal(str(initial)))

    # =========================================================================
    # DESSIN DE L'INTERFACE
    # =========================================================================

    def _draw_grid(self):
        """Dessine le quadrillage de l'environnement de simulation."""
        for x in range(50, 800, 50):
            for y in range(0, 500, 50):
                self.canvas.create_rectangle(x, y, x+50, y+50, fill="lightgray", outline="gray")

    def _draw_simulation_frame(self):
        """Dessine les cadres autour de l'environnement de simulation."""
        titre_font = tkFont.Font(family="Times New Roman", size=18, weight="bold", slant="italic")

        # FIX: noms uniques pour chaque bordure au lieu d'écraser self.world_border
        self.border_top = tk.Label(
            self.canvas, text="Environnement de simulation", justify='center',
            relief='sunken', bg=self.FRAME_COLOR, font=titre_font, borderwidth=2
        )
        self.border_top.place(x=50, y=0, width=750, height=30)

        self.border_left = tk.Label(self.canvas, relief='sunken', bg=self.FRAME_COLOR, borderwidth=2)
        self.border_left.place(x=50, y=30, width=20, height=(self.TABLE_Y + 80))

        self.border_right = tk.Label(self.canvas, relief='sunken', bg=self.FRAME_COLOR, borderwidth=2)
        self.border_right.place(x=780, y=30, width=20, height=(self.TABLE_Y + 80))

        self.border_bottom = tk.Label(self.canvas, relief='sunken', bg=self.FRAME_COLOR, borderwidth=2)
        self.border_bottom.place(x=50, y=(self.TABLE_Y + 100), width=750, height=20)

    def _draw_table(self):
        """Dessine la table et ses pieds."""
        # Plateau de la table
        self.canvas.create_rectangle(
            100, (self.TABLE_Y + 50),
            750, (self.TABLE_Y + 65),
            fill=self.TABLE_COLOR, outline='black'
        )
        # Pied gauche
        self.canvas.create_rectangle(
            150, (self.TABLE_Y + 65),
            165, (self.TABLE_Y + 120),
            fill=self.TABLE_COLOR
        )
        # Pied droit
        self.canvas.create_rectangle(
            685, (self.TABLE_Y + 65),
            700, (self.TABLE_Y + 120),
            fill=self.TABLE_COLOR
        )

    def _init_cubes(self):
        """Initialise les cubes et les places sur la table."""
        self.cubes = {}
        self.places = []
        for name, x in zip(self.CUBE_NAMES, self.CUBE_POSITIONS_X):
            self.cubes[name] = Cube(self.canvas, name, x, self.TABLE_Y)
            # status=False signifie "occupé", True signifie "libre"
            self.places.append({'x': x, 'y': self.TABLE_Y, 'free': False})

    def _draw_plan_panel(self):
        """Dessine le panneau d'affichage du plan d'actions (côté droit)."""
        titre_font = tkFont.Font(family="Times New Roman", size=18, weight="bold", slant="italic")
        plan_font = tkFont.Font(family="Times New Roman", size=20, weight="bold", slant="italic")

        # Boutons
        self.btn_team = tk.Button(
            self.canvas, text='Equipe', font=('Arial', 12),
            relief='sunken', bg='gray', command=self.team_view
        )
        self.btn_team.place(x=850, y=50, width=100)

        self.btn_help = tk.Button(
            self.canvas, text='Aide', font=('Arial', 12),
            relief='sunken', bg='yellow', command=self.help_view
        )
        self.btn_help.place(x=1050, y=50, width=100)

        # Zone de texte du plan
        self.text_area = tk.Text(self.canvas, bg='#D3D3D3', font=plan_font)
        self.text_area.place(x=870, y=130, height=330, width=258)
        self.text_area.tag_configure("center", justify='center')
        self.text_area.config(state=tk.DISABLED)

        # Cadre du plan
        self.plan_title = tk.Label(
            self.canvas, text="Plan d'actions", justify='center',
            relief='sunken', bg=self.FRAME_COLOR, font=titre_font, borderwidth=2
        )
        self.plan_title.place(x=850, y=100, width=280, height=30)

        # Bordures droite, gauche et bas du cadre plan
        self.canvas.create_rectangle(1130, 100, 1150, 480, fill=self.FRAME_COLOR)
        self.canvas.create_rectangle(850, 100, 870, 480, fill=self.FRAME_COLOR)
        self.canvas.create_rectangle(850, 460, 1130, 480, fill=self.FRAME_COLOR, outline='black')

    def _draw_nlp_interface(self):
        """Dessine l'interface de saisie des commandes utilisateur."""
        haut_nlp = self.TABLE_Y + 140

        self.command_label = tk.Label(
            self.canvas, text="Interface Utilisateur >>", justify='center',
            relief='groove', bg='gray', font=("Sans Serif", 15), borderwidth=2, fg='white'
        )
        self.command_label.place(x=100, y=haut_nlp, width=200, height=35)

        entry_font = tkFont.Font(family="Times New Roman", size=15, weight="bold")
        self.command_entry = tk.Text(self.canvas, font=entry_font, highlightcolor="black", highlightthickness=2)
        self.command_entry.place(x=305, y=haut_nlp, width=300, height=50)

        # Exécuter avec la touche Entrée
        self.command_entry.bind("<Return>", self.start_actions)

        self.btn_execute = tk.Button(
            self.canvas, bg='green', text="Executer",
            font=("Arial", 16), command=self.start_actions
        )
        self.btn_execute.place(x=605, y=haut_nlp, width=100, height=35)

    # =========================================================================
    # LOGIQUE D'EXÉCUTION
    # =========================================================================

    def set_plan(self, actions):
        """Affiche le plan d'actions dans la zone de texte dédiée."""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)
        for i, element in enumerate(actions, 1):
            self.text_area.insert(tk.END, f"{i}. {element}\n")
        self.text_area.config(state=tk.DISABLED)

    def update_goal(self, goal):
        """Supprime les HOLDING redondants quand un ON existe pour le même bloc."""
        holding_indices = [i for i, item in enumerate(goal) if isinstance(item, HOLDING)]
        to_delete = set(
            i for i in holding_indices
            if any(isinstance(item, ON) and item.X == goal[i].X for item in goal)
        )
        return [item for i, item in enumerate(goal) if i not in to_delete]

    def set_ui_enabled(self, enabled):
        """Active ou désactive les contrôles pendant l'exécution."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.btn_execute.config(state=state)
        self.command_entry.config(state=state)

    def start_actions(self, event=None):
        """Lance l'interprétation de la commande et l'exécution du plan."""
        # FIX: empêcher les doubles exécutions pendant qu'un plan est en cours
        if self.is_executing:
            return

        command_text = self.command_entry.get("1.0", tk.END).strip()
        if not command_text:
            return

        # Empêcher l'insertion du retour à la ligne par la touche Entrée
        if event:
            self.after(1, lambda: self.command_entry.delete("end-2c", "end-1c"))

        # Appeler le NLP pour interpréter la commande
        but_str, nlp_ok, nlp_msg = ask_for_goal(command_text)

        if not nlp_ok:
            messagebox.showinfo("Alerte", nlp_msg)
            return

        # FIX: gestion d'erreur explicite au lieu de try/except nu
        try:
            but = eval(but_str)
        except (SyntaxError, NameError, TypeError) as e:
            messagebox.showinfo("Alerte", f"Erreur d'interprétation du but: {e}")
            return

        # Nettoyer les redondances (HOLDING + ON pour le même bloc)
        but = self.update_goal(but)

        # Lire l'état courant et générer le plan
        initial = read_goal_from_file("initial.tx")
        if not initial:
            messagebox.showinfo("Alerte", "Erreur: impossible de lire l'état initial")
            return

        plan_ok, plan, plan_msg = ask_for_plan(initial, but)

        if not plan_ok:
            messagebox.showinfo("Alerte", plan_msg)
            return

        # Exécuter le plan
        self.set_plan(plan)
        self.command_entry.delete("1.0", tk.END)
        self.actions = plan
        self.action_index = 0
        self.is_executing = True
        self.set_ui_enabled(False)
        self.execute_next_action()

    # =========================================================================
    # GESTION DES PLACES ET CUBES
    # =========================================================================

    def update_place_status(self, x, y, free):
        """Met à jour le statut d'une place (free=True si libre, False si occupée)."""
        for place in self.places:
            if abs(place['x'] - x) < 5 and abs(place['y'] - y) < 5:
                place['free'] = free
                break

    def get_free_place(self, current_x):
        """Trouve la place libre la plus proche de current_x.
        Retourne un tuple (x, y) ou None si aucune place n'est libre."""
        best_place = None
        min_distance = float('inf')

        for place in self.places:
            if place['free']:
                distance = abs(place['x'] - current_x)
                if distance < min_distance:
                    min_distance = distance
                    best_place = (place['x'], place['y'])

        if best_place is None:
            # Fallback: utiliser la première place (ne devrait pas arriver en usage normal)
            best_place = (self.places[0]['x'], self.places[0]['y'])

        return best_place

    def get_highest_cube_position(self):
        """Retourne la position Y au-dessus du cube le plus haut."""
        min_y = float('inf')
        for cube in self.cubes.values():
            if cube.y < min_y:
                min_y = cube.y
        if min_y < float('inf'):
            return min_y - self.CUBE_SIZE
        return 50

    # =========================================================================
    # EXÉCUTION DES ACTIONS
    # =========================================================================

    def execute_next_action(self):
        """Exécute la prochaine action du plan, ou termine l'exécution."""
        if self.action_index < len(self.actions):
            action = self.actions[self.action_index]
            self.action_index += 1
            self.execute_action(action)
        else:
            # Plan terminé, réactiver l'interface
            self.is_executing = False
            self.set_ui_enabled(True)

    def execute_action(self, action):
        """Dispatch une action STRIPS vers la méthode d'animation correspondante."""
        if isinstance(action, PickupOp):
            cube = self.cubes[action.X]
            self.robot_hand.prendre(cube)
            self.update_place_status(cube.x, cube.y, True)

        elif isinstance(action, PutdownOp):
            self.robot_hand.deposer()

        elif isinstance(action, StackOp):
            cube = self.cubes[action.X]
            target_cube = self.cubes[action.Y]
            self.robot_hand.empiler(cube, target_cube)

        elif isinstance(action, UnstackOp):
            cube = self.cubes[action.X]
            self.robot_hand.depiler(cube)

    # =========================================================================
    # FENÊTRE ÉQUIPE
    # =========================================================================

    def team_view(self):
        """Affiche la fenêtre avec les membres de l'équipe."""
        team = tk.Toplevel(self)
        team.state('zoomed')
        team.grab_set()
        team.focus_set()
        team.config(bg='gray')

        titre = tk.Label(team, text="MEMBRE DU GROUPE", font=("time new roman", 20, "bold"), bg='gray', fg='white')
        titre.pack(pady=5)

        def create_label(frame, text, row):
            label = tk.Label(frame, text=text, font=("time new roman", 10, "bold"), bg="#f0f0f0", fg="#333333")
            label.grid(row=row, column=0, sticky="w")

        def add_social_icon(frame, icon_path, link, col):
            try:
                icon = PhotoImage(file=icon_path).subsample(4)
                button = tk.Button(
                    frame, image=icon, borderwidth=0, bg="#f0f0f0",
                    activebackground="#f0f0f0", command=lambda: webbrowser.open_new(link)
                )
                button.photo = icon  # Garder une référence pour éviter le garbage collection
                button.grid(row=0, column=col, padx=(5, 5), pady=10)
            except Exception as e:
                print(f"Erreur lors du chargement de l'icône {icon_path}: {e}")

        def create_team_card(root, photo_path, name, firstname, email, phone,
                             function, departement, specialite,
                             facebook_link=None, twitter_link=None,
                             linkdln_link=None, instagram_link=None):
            card = tk.Frame(root, bg="#f0f0f0", bd=2, relief="groove", width=200)

            try:
                image = Image.open(photo_path)
                size = (200, 190) if departement == "" else (200, 210)
                image = image.resize(size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
            except Exception as e:
                print(f"Erreur lors du chargement de l'image {photo_path}: {e}")
                photo = None

            photo_label = tk.Label(card, image=photo, bg="#f0f0f0")
            if photo:
                photo_label.photo = photo
            photo_label.grid(row=0, column=0, padx=10, pady=0, rowspan=5)

            info_frame = tk.Frame(card, bg="#f0f0f0")
            info_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="w")

            if departement != "":
                create_label(info_frame, f"Nom: {name}", 0)
                create_label(info_frame, f"Prénom: {firstname}", 1)
                create_label(info_frame, f"Email: {email}", 2)
                create_label(info_frame, f"Tél: +224 {phone}", 3)
                create_label(info_frame, f"Fonction: {function}", 4)
                create_label(info_frame, f"Département: {departement}", 5)
                create_label(info_frame, f"Spécialité: {specialite}", 6)
            else:
                create_label(info_frame, f"Nom: Pr. {firstname} {name}", 0)
                create_label(info_frame, f"Email: {email}", 1)
                create_label(info_frame, f"Tél: +224 {phone}", 2)
                create_label(info_frame, f"Spécialité: {specialite}", 3)
                create_label(info_frame, f"Recteur de l'Université Kofi Annan de Guinée", 4)

            social_frame = tk.Frame(info_frame, bg="#f0f0f0")
            social_frame.grid(row=7, column=0, columnspan=2, padx=(10, 0), pady=(2, 2), sticky="w")

            if facebook_link:
                add_social_icon(social_frame, "img/fb.png", facebook_link, 0)
            if twitter_link:
                add_social_icon(social_frame, "img/X.png", twitter_link, 1)
            if linkdln_link:
                add_social_icon(social_frame, "img/L.png", linkdln_link, 2)
            if instagram_link:
                add_social_icon(social_frame, "img/in.png", instagram_link, 3)

            return card

        # Contenu de la page
        description_label = tk.Label(
            team,
            text="Cette page présente les membres de l'équipe et l'encadreur qui ont travaillé sur ce thème de memoire:",
            font=("time new roman", 16, "bold"), bg="#f0f0f0", fg="#333333"
        )
        description_label.pack(side="top", pady=5)

        description_intermediate = tk.Label(
            team,
            text="Ci-dessous l'equipe d'Ingenieurs qui ont conçu l'application:",
            font=("time new roman", 12, "italic"), bg="#f0f0f0", fg="#333333"
        )
        description_intermediate.pack(side="top", pady=5)

        container_top = tk.Frame(team, bg="#f0f0f0")
        container_top.pack(side="top", pady=0)

        card1 = create_team_card(
            container_top, "img/profilePro.png", "Fofana", "Elhadj Moussa", "Moussaf654@gmail.com",
            "629 657 647", "Etudiant de l'EPI (UKAG)", "Génie Informatique", "Développement logiciel",
            "https://www.facebook.com/Elmousaf?mibextid=LQQJ4d", "https://www.twitter.com/elmousaf",
            "http://linkedin.com/in/fofana-elhadj-moussa-834502249",
            "https://www.instagram.com/elhadj_moussa_fofana"
        )
        card1.pack(side="left", padx=10, pady=8)

        card2 = create_team_card(
            container_top, "img/guezz.png", "Barry", "Elhadj Ibrahima", "igb.barry@gmail.com",
            "621 041 311", "Etudiant de l'EPI (UKAG)", "Génie Informatique", "Développement logiciel",
            "https://www.facebook.com/ibrahimguezz.barry?mibextid=LQQJ4d",
            "https://www.twitter.com/membre2", "https://www.linkdln.com/membre2",
            "https://www.instagram.com/membre2"
        )
        card2.pack(side="left", padx=10, pady=8)

        description_intermediate2 = tk.Label(
            team, text="Ci-dessous l'encadreur du memoire:",
            font=("time new roman", 12, "italic"), bg="#f0f0f0", fg="#333333"
        )
        description_intermediate2.pack(side="top", pady=5)

        container_bottom = tk.Frame(team, bg="#f0f0f0")
        container_bottom.pack(side="top", pady=10)

        card3 = create_team_card(
            container_bottom, "img/rect.png", "Laskri", "Mohamed Tayeb",
            "mtlaskri12@gmail.com", "620 988 928/ +213 5 42226594",
            "", "", "Expert en Intelligence Artificielle",
            "https://www.facebook.com/mohamedtayeb.laskri?mibextid=LQQJ4d",
            "https://www.twitter.com/membre3",
            "http://linkedin.com/in/pr-mohamed-tayeb-laskri-2610aa204",
            "https://www.instagram.com/membre3"
        )
        card3.pack(side="top", padx=10, pady=10)

    # =========================================================================
    # FENÊTRE D'AIDE
    # =========================================================================

    # FIX: une seule version de help_view (fusion de la version simple et détaillée)
    def help_view(self):
        """Affiche la fenêtre d'aide avec la documentation complète."""
        help_window = tk.Toplevel(self)
        help_window.title("Aide")
        help_window.state("zoomed")
        help_window.configure(bg="#f0f0f0")

        # Rendre la fenêtre modale
        help_window.grab_set()
        help_window.focus_force()

        # Frame pour contenir le canvas et la scrollbar
        canvas_frame = tk.Frame(help_window, bg="#f0f0f0")
        canvas_frame.grid(row=0, column=0, sticky="nsew")

        help_window.grid_rowconfigure(0, weight=1)
        help_window.grid_columnconfigure(0, weight=1)

        # Canvas pour le contenu scrollable
        canvas = tk.Canvas(canvas_frame, bg="#f0f0f0", width=1200, height=600)
        canvas.pack(side="left", fill="both", expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Conteneur scrollable
        scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        scrollable_frame.bind("<Configure>", on_frame_configure)

        # Titre
        title_label = tk.Label(
            scrollable_frame, text="Bienvenue dans la page d'aide",
            font=("Arial", 24, "bold"), bg="#f0f0f0", fg="blue"
        )
        title_label.pack(pady=(20, 10))

        frame_width = 1200

        # --- Sections d'aide ---
        help_sections = [
            (
                "À propos de l'application",
                """Cette application a été conçue lors d'un projet de mémoire pour l'obtention d'un diplôme d'ingénieur d'État en génie informatique à l'Université Kofi Annan de Guinée, sur le thème "Modélisation et Simulation d'un Robot pour la génération et l'exécution de plans d'actions dans un environnement de manipulation de blocs variés", par: Elhadj Ibrahima Barry et Elhadj Moussa Fofana, encadrés par le Professeur Mohamed Tayeb Laskri, expert en intelligence artificielle et Recteur de l'Université Kofi Annan de Guinée. Le mémoire a été élaboré en 2023-2024."""
            ),
            (
                "Fonctionnalités de l'application",
                """Cette application est conçue en suivant trois étapes essentielles : le traitement de langage naturel, STRIPS avec la génération de plan d'action et l'interface graphique."""
            ),
            (
                "Comment utiliser l'application",
                """Une fois lancée, tous les blocs se trouvent sur la table, et vous pouvez donner des instructions au robot pour qu'il les exécute. Ces instructions sont données en langage naturel et le robot les exécute. Tout un ensemble de processus est mis en place dans la partie traitement de langage naturel pour que le robot comprenne le langage naturel qui lui est envoyé. Une fois la commande saisie, il l'exécute."""
            ),
        ]

        for section_title, section_text in help_sections:
            section_frame = tk.Frame(scrollable_frame, bg="#ffffff", bd=2, relief="groove", width=frame_width)
            section_frame.pack(pady=10, padx=50, fill="x", expand=True)

            tk.Label(
                section_frame, text=section_title,
                font=("Arial", 18, "bold"), bg="#ffffff", fg="#333333"
            ).pack(pady=(10, 5))

            for line in split_text(section_text, 60):
                tk.Label(
                    section_frame, text=line, font=("Arial", 14),
                    bg="#ffffff", fg="#333333", wraplength=frame_width-50, justify="left"
                ).pack(pady=1, anchor="w")

        # Section exemples
        examples_frame = tk.Frame(scrollable_frame, bg="#ffffff", bd=2, relief="groove", width=frame_width)
        examples_frame.pack(pady=10, padx=50, fill="x", expand=True)

        tk.Label(
            examples_frame, text="Exemples d'utilisation",
            font=("Arial", 18, "bold"), bg="#ffffff", fg="#333333"
        ).pack(pady=(10, 5))

        examples = [
            "1) Prendre le cube A",
            "2) Déposer A",
            "3) Empiler le bloc C sur le bloc B",
            "4) Désempiler C de B",
            "5) Mets A sur B et Empiler C sur le bloc D"
        ]
        for example in examples:
            tk.Label(
                examples_frame, text=example, font=("Arial", 14),
                bg="#ffffff", fg="#333333", wraplength=frame_width-50, justify="left"
            ).pack(pady=1, anchor="w")

        # Défilement à la molette
        def _on_mouse_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mouse_wheel)

        # FIX: nettoyer le bind global quand la fenêtre est fermée
        def on_close():
            canvas.unbind_all("<MouseWheel>")
            help_window.destroy()

        help_window.protocol("WM_DELETE_CLOSE", on_close)


if __name__ == "__main__":
    app = Application()
    app.mainloop()