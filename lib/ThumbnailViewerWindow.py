import os
import sys
import threading
from tkinter import messagebox, ttk, Frame, Label, Scrollbar, StringVar, Canvas, Menu, Toplevel
from lib.ToolTip import ToolTip
from lib.ImportCheck import import_PIL

Image, ImageTk = import_PIL()

class ThumbnailViewerWindow:
    def __init__(self, parent, app, image_paths, year, month):
        self.parent = parent
        self.app = app
        self.year = year
        self.month = month
        
        self.top = Toplevel(parent)
        self.top.title(self.app._('thumb_viewer_title', self.year, self.month))
        self.top.minsize(800, 600)
        self.top.transient(parent)
        self.top.grab_set()

        self.all_images = [] # Will store tuples of (path, size, mtime)
        self.photo_references = {} # path -> PhotoImage
        self.thumb_labels = {} # path -> Label widget
        
        self.current_page = 1
        self.items_per_page = StringVar(value='20')
        self.sort_option = StringVar()
        self.columns = 4
        self.last_width = 0
        
        self.setup_ui()
        self.load_image_data(image_paths)

    def setup_ui(self):
        # --- Top Control Frame ---
        control_frame = Frame(self.top, padx=10, pady=5)
        control_frame.pack(fill='x')

        Label(control_frame, text=self.app._('items_per_page')).pack(side='left', padx=(0, 5))
        per_page_combo = ttk.Combobox(control_frame, textvariable=self.items_per_page, state='readonly', width=5)
        per_page_combo['values'] = ['5', '10', '20', '50', '100']
        per_page_combo.bind('<<ComboboxSelected>>', lambda e: self.update_view())
        per_page_combo.pack(side='left')

        Label(control_frame, text=self.app._('sort_by')).pack(side='left', padx=(20, 5))
        sort_menu = ttk.Combobox(control_frame, textvariable=self.sort_option, state='readonly', width=20)
        sort_menu['values'] = [
            self.app._('sort_time_desc'), self.app._('sort_time_asc'),
            self.app._('sort_size_desc'), self.app._('sort_size_asc')
        ]
        sort_menu.set(self.app._('sort_time_desc'))
        sort_menu.pack(side='left')
        sort_menu.bind('<<ComboboxSelected>>', self.sort_and_update)

        self.page_label = Label(control_frame, text="")
        self.page_label.pack(side='right', padx=10)
        self.next_button = ttk.Button(control_frame, text=self.app._('next_page'), command=lambda: self.change_page(1))
        self.next_button.pack(side='right')
        self.prev_button = ttk.Button(control_frame, text=self.app._('prev_page'), command=lambda: self.change_page(-1))
        self.prev_button.pack(side='right', padx=5)

        # --- Main Content (Canvas for thumbnails) ---
        main_frame = Frame(self.top, bd=1, relief='sunken')
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.canvas = Canvas(main_frame)
        scrollbar = Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Mouse Wheel Scrolling ---
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # --- Resize Handling ---
        self.top.bind('<Configure>', self.on_resize)

        # --- Context Menu ---
        self.context_menu = Menu(self.top, tearoff=0)
        self.context_menu.add_command(label=self.app._('context_delete'), command=self.delete_image)
        self.context_menu.add_command(label=self.app._('context_open'), command=self.open_image)
        self.context_menu.add_command(label=self.app._('context_open_dir'), command=self.open_image_directory)
        self.clicked_image_path = None

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling on the canvas."""
        if sys.platform == "win32":
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif sys.platform == "darwin":
            self.canvas.yview_scroll(int(-1 * event.delta), "units")
        else: # Linux
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")

    def on_resize(self, event):
        """Handle window resize to reflow thumbnails."""
        new_width = event.width
        if new_width != self.last_width:
            self.last_width = new_width
            new_columns = max(1, (self.canvas.winfo_width() - 20) // 180)
            if new_columns != self.columns:
                self.columns = new_columns
                self.update_view(force_reload=False)

    def load_image_data(self, image_paths):
        """Load image metadata in a separate thread."""
        threading.Thread(target=self._load_image_data_thread, args=(image_paths,), daemon=True).start()

    def _load_image_data_thread(self, image_paths):
        temp_list = []
        for path in image_paths:
            try:
                stat = os.stat(path)
                temp_list.append({'path': path, 'size': stat.st_size, 'time': stat.st_mtime})
            except FileNotFoundError:
                continue
        self.all_images = temp_list
        self.top.after(0, self.sort_and_update)

    def sort_and_update(self, event=None):
        """Sorts the master list of images and updates the view."""
        sort_key = self.sort_option.get()
        
        reverse = True
        if sort_key in [self.app._('sort_time_asc'), self.app._('sort_size_asc')]:
            reverse = False

        key_func = 'time'
        if sort_key in [self.app._('sort_size_asc'), self.app._('sort_size_desc')]:
            key_func = 'size'
            
        self.all_images.sort(key=lambda x: x[key_func], reverse=reverse)
        self.current_page = 1
        self.update_view()

    def update_view(self, force_reload=True):
        """Clears and repopulates the thumbnail view for the current page."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if force_reload:
            self.photo_references.clear()
            self.thumb_labels.clear()

        try:
            per_page = int(self.items_per_page.get())
        except ValueError:
            per_page = 20
        
        total_items = len(self.all_images)
        self.total_pages = (total_items + per_page - 1) // per_page
        if self.total_pages == 0: self.total_pages = 1

        start_index = (self.current_page - 1) * per_page
        end_index = start_index + per_page
        self.images_on_page = self.all_images[start_index:end_index]

        self.update_page_controls()
        
        if self.images_on_page:
            if force_reload:
                threading.Thread(target=self._load_thumbnails_thread, args=(self.images_on_page,), daemon=True).start()
            else:
                self.populate_thumbnails(self.images_on_page)

    def _load_thumbnails_thread(self, image_data):
        """Load thumbnail images in the background."""
        for data in image_data:
            path = data['path']
            if path in self.photo_references:
                continue
            try:
                image = Image.open(path)
                image.thumbnail((150, 150))
                photo = ImageTk.PhotoImage(image)
                self.photo_references[path] = photo
            except Exception as e:
                print(f"Error loading thumbnail for {path}: {e}")
        
        self.top.after(0, lambda: self.populate_thumbnails(image_data))

    def populate_thumbnails(self, image_data):
        """Place loaded thumbnails onto the canvas in a fixed grid."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        for i, data in enumerate(image_data):
            path = data['path']
            photo = self.photo_references.get(path)
            if not photo:
                continue
            
            row, col = divmod(i, self.columns)
            
            frame = Frame(self.scrollable_frame, width=170, height=170)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            frame.grid_propagate(False)
            
            label = Label(frame, image=photo)
            label.pack(expand=True)
            self.thumb_labels[path] = label

            label.bind("<Button-3>", lambda e, p=path: self.show_context_menu(e, p))
            ToolTip(label, os.path.basename(path))

        for col_index in range(self.columns):
            self.scrollable_frame.grid_columnconfigure(col_index, weight=1)

    def update_page_controls(self):
        """Update the state of pagination buttons and label."""
        self.page_label.config(text=self.app._('page_label', self.current_page, self.total_pages))
        self.prev_button.config(state='normal' if self.current_page > 1 else 'disabled')
        self.next_button.config(state='normal' if self.current_page < self.total_pages else 'disabled')

    def change_page(self, delta):
        """Navigate to the previous or next page."""
        new_page = self.current_page + delta
        if 1 <= new_page <= self.total_pages:
            self.current_page = new_page
            self.update_view()

    def show_context_menu(self, event, path):
        self.clicked_image_path = path
        self.context_menu.post(event.x_root, event.y_root)

    def delete_image(self):
        path = self.clicked_image_path
        if not path: return
        
        if messagebox.askyesno(self.app._('confirm_delete_title'), f"确认删除文件?\n{os.path.basename(path)}", parent=self.top):
            try:
                os.remove(path)
                self.thumb_labels[path].master.destroy()
                del self.thumb_labels[path]
                self.all_images = [img for img in self.all_images if img['path'] != path]
                self.images_on_page = [img for img in self.images_on_page if img['path'] != path]
                
                self.populate_thumbnails(self.images_on_page)
                self.update_page_controls()

                self.app.file_data[self.year][self.month]['paths'].remove(path)
            except Exception as e:
                messagebox.showerror(self.app._('error_title'), f"删除失败: {e}", parent=self.top)

    def open_image(self):
        if self.clicked_image_path:
            try:
                os.startfile(self.clicked_image_path)
            except AttributeError:
                import subprocess
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.call([opener, self.clicked_image_path])

    def open_image_directory(self):
        if self.clicked_image_path:
            try:
                os.startfile(os.path.dirname(self.clicked_image_path))
            except AttributeError:
                import subprocess
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.call([opener, os.path.dirname(self.clicked_image_path)])
