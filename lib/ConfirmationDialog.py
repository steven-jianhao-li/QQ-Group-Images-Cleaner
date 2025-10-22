import os
import random
from tkinter import ttk, Frame, Label, Scrollbar, Canvas, Toplevel
from lib.ToolTip import ToolTip
from lib.ImportCheck import import_PIL

Image, ImageTk = import_PIL()

class ConfirmationDialog:
    """A custom dialog to confirm deletion with image previews."""
    def __init__(self, parent, app, year, month, image_paths):
        self.parent = parent
        self.app = app
        self.confirmed = False
        
        self.top = Toplevel(parent)
        self.top.title(self.app._('confirm_delete_title'))
        self.top.transient(parent)
        self.top.grab_set()

        # Message
        if self.app.lang == 'zh':
            msg = self.app._('confirm_delete_msg', year, month)
        else:
            msg = self.app._('confirm_delete_msg', year=year, month=month)
        Label(self.top, text=msg, justify='left', padx=10, pady=10).pack()

        # Thumbnails Frame
        thumb_frame = Frame(self.top, bd=2, relief='sunken')
        thumb_frame.pack(padx=10, pady=10, fill='both', expand=True)
        self.canvas = Canvas(thumb_frame, width=480, height=250)
        
        scrollbar = Scrollbar(thumb_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.photo_references = [] # IMPORTANT: Keep reference to avoid garbage collection
        self.load_thumbnails(image_paths)

        # Buttons
        button_frame = Frame(self.top, pady=5)
        button_frame.pack()
        ttk.Button(button_frame, text=self.app._('cancel_btn'), command=self.cancel).pack(side='right', padx=10)
        ttk.Button(button_frame, text=self.app._('confirm_btn'), command=self.confirm).pack(side='right')

    def load_thumbnails(self, image_paths):
        """Load a sample of images and display them."""
        sample_size = 20
        paths_to_show = random.sample(image_paths, min(len(image_paths), sample_size))
        
        for i, path in enumerate(paths_to_show):
            try:
                image = Image.open(path)
                image.thumbnail((100, 100)) # Resize in-place
                photo = ImageTk.PhotoImage(image)
                self.photo_references.append(photo)

                row, col = divmod(i, 4)
                item_frame = Frame(self.scrollable_frame)
                item_frame.grid(row=row, column=col, padx=5, pady=5)
                
                img_label = Label(item_frame, image=photo)
                img_label.pack()
                
                # Show filename as a tooltip
                ToolTip(img_label, os.path.basename(path))

            except Exception as e:
                print(f"Could not load thumbnail for {path}: {e}")

    def confirm(self):
        self.confirmed = True
        self.top.destroy()

    def cancel(self):
        self.confirmed = False
        self.top.destroy()
