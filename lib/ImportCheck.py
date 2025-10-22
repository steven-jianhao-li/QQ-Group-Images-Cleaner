from tkinter import messagebox
def import_PIL():
    try:
        from PIL import Image, ImageTk
    except ImportError:
        messagebox.showerror("Dependency Missing", "Pillow library not found.\nPlease install it by running: pip install Pillow")
        exit()
    return Image, ImageTk
    
        
