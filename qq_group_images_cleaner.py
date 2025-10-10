#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import os
import threading
import random
from datetime import datetime
from collections import defaultdict
from tkinter import Tk, filedialog, messagebox, ttk, Frame, Label, Button, Scrollbar, Spinbox, StringVar, Canvas, Menu, Toplevel, W, E, N, S

# Pillow is required for image thumbnail generation
try:
    from PIL import Image, ImageTk
except ImportError:
    messagebox.showerror("Dependency Missing", "Pillow library not found.\nPlease install it by running: pip install Pillow")
    exit()

# --- Language Configuration ---
I18N_STRINGS = {
    'zh': {
        'window_title': "QQ群聊图像清理",
        'folder_label': "QQ群文件夹:",
        'select_folder_btn': "选择文件夹...",
        'scan_files_btn': "扫描文件",
        'delete_prompt': "删除此日期及之前的文件:",
        'delete_files_btn': "删除文件",
        'status_select_folder': "请选择一个文件夹以开始。",
        'status_folder_selected': "已选择文件夹: {}",
        'status_scanning': "正在扫描... 这可能需要一段时间。",
        'status_scan_complete': "扫描完成。共找到 {} 个月份的文件。",
        'status_deletion_cancelled': "用户取消了删除操作。",
        'status_deleting': "正在删除... ({}/{})",
        'status_delete_complete': "删除完成。删除了 {} 个文件，失败 {} 个。",
        'tree_month': "月份",
        'tree_size': "总大小 (MB)",
        'tree_count': "文件数量",
        'year_prefix': "年份: {}",
        'confirm_delete_title': "确认删除",
        'confirm_delete_msg': "您确定要永久删除 {} 年 {} 月及之前的所有文件吗？\n\n此操作无法撤销。\n\n以下是待删除图片的部分随机预览：",
        'confirm_btn': "确认删除",
        'cancel_btn': "取消",
        'language_menu': "语言 (Language)",
        'error_title': "错误",
        'error_no_folder': "未选择文件夹。",
        'error_invalid_date': "请输入有效的年份和月份。"
    },
    'en': {
        'window_title': "QQ Group Images Cleaner",
        'folder_label': "QQ Group Folder:",
        'select_folder_btn': "Select Folder...",
        'scan_files_btn': "Scan Files",
        'delete_prompt': "Delete files from and before:",
        'delete_files_btn': "Delete Files",
        'status_select_folder': "Please select a folder to begin.",
        'status_folder_selected': "Folder selected: {}",
        'status_scanning': "Scanning... this may take a while.",
        'status_scan_complete': "Scan complete. Found files grouped into {} months.",
        'status_deletion_cancelled': "Deletion cancelled by user.",
        'status_deleting': "Deleting... ({}/{})",
        'status_delete_complete': "Deletion complete. Deleted {} files, failed {} files.",
        'tree_month': "Month",
        'tree_size': "Total Size (MB)",
        'tree_count': "File Count",
        'year_prefix': "Year: {}",
        'confirm_delete_title': "Confirm Deletion",
        'confirm_delete_msg': "Are you sure you want to permanently delete all files from and before {month:02d}-{year}?\n\nThis action CANNOT be undone.\n\nA random sample of images to be deleted is shown below:",
        'confirm_btn': "Confirm Deletion",
        'cancel_btn': "Cancel",
        'language_menu': "Language",
        'error_title': "Error",
        'error_no_folder': "No folder selected.",
        'error_invalid_date': "Please enter valid numbers for year and month."
    }
}

class QQCleanerApp:
    def __init__(self, root):
        self.root = root
        self.lang = 'zh'  # Default language is Chinese

        # --- Data Storage ---
        self.file_data = defaultdict(lambda: defaultdict(lambda: {'size': 0, 'paths': []}))
        self.root_path = StringVar()

        self.setup_ui()
        self.update_ui_language()

    def _(self, key, *args):
        """Simple text translation helper."""
        return I18N_STRINGS[self.lang].get(key, key).format(*args)

    def set_language(self, lang_code):
        """Set the application language and update UI."""
        self.lang = lang_code
        self.update_ui_language()

    def setup_ui(self):
        """Initialize the GUI application."""
        # --- Menu Bar ---
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        language_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self._('language_menu'), menu=language_menu)
        language_menu.add_command(label="中文", command=lambda: self.set_language('zh'))
        language_menu.add_command(label="English", command=lambda: self.set_language('en'))
        
        self.root.minsize(600, 450)

        top_frame = Frame(self.root, padx=10, pady=10)
        top_frame.pack(fill='x')

        self.folder_label = Label(top_frame)
        self.folder_label.pack(side='left')
        ttk.Entry(top_frame, textvariable=self.root_path, state='readonly').pack(side='left', fill='x', expand=True, padx=5)
        self.select_folder_button = ttk.Button(top_frame, command=self.select_folder)
        self.select_folder_button.pack(side='left')

        mid_frame = Frame(self.root, padx=10, pady=5)
        mid_frame.pack(fill='both', expand=True)

        self.tree = ttk.Treeview(mid_frame, columns=('month', 'size', 'count'), show='headings')
        vsb = Scrollbar(mid_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky=N+S+W+E)
        vsb.grid(row=0, column=1, sticky=N+S)
        mid_frame.grid_rowconfigure(0, weight=1)
        mid_frame.grid_columnconfigure(0, weight=1)

        bottom_frame = Frame(self.root, padx=10, pady=10)
        bottom_frame.pack(fill='x')

        self.scan_button = ttk.Button(bottom_frame, command=self.start_scan, state='disabled')
        self.scan_button.pack(side='left')

        self.delete_label = Label(bottom_frame)
        self.delete_label.pack(side='left', padx=(20, 5))
        self.year_spinbox = Spinbox(bottom_frame, from_=2000, to=datetime.now().year, width=6)
        self.year_spinbox.pack(side='left')
        self.month_spinbox = Spinbox(bottom_frame, from_=1, to=12, width=4)
        self.month_spinbox.pack(side='left', padx=5)
        self.year_spinbox.delete(0, 'end'); self.year_spinbox.insert(0, str(datetime.now().year))
        self.month_spinbox.delete(0, 'end'); self.month_spinbox.insert(0, str(datetime.now().month))
        
        self.delete_button = ttk.Button(bottom_frame, command=self.start_delete, state='disabled')
        self.delete_button.pack(side='left', padx=5)

        status_frame = Frame(self.root, padx=10, pady=5, bd=1, relief='sunken')
        status_frame.pack(fill='x', side='bottom')
        self.progress = ttk.Progressbar(status_frame, orient='horizontal', mode='determinate')
        self.progress.pack(side='right')
        self.status_label = Label(status_frame, text="", anchor='w')
        self.status_label.pack(fill='x')

    def update_ui_language(self):
        """Update all text elements in the UI to the current language."""
        self.root.title(self._('window_title'))
        self.root.nametowidget(self.root.cget('menu')).entryconfig(1, label=self._('language_menu'))
        
        self.folder_label.config(text=self._('folder_label'))
        self.select_folder_button.config(text=self._('select_folder_btn'))
        self.scan_button.config(text=self._('scan_files_btn'))
        self.delete_label.config(text=self._('delete_prompt'))
        self.delete_button.config(text=self._('delete_files_btn'))
        
        self.tree.heading('month', text=self._('tree_month'))
        self.tree.heading('size', text=self._('tree_size'))
        self.tree.heading('count', text=self._('tree_count'))

        if not self.root_path.get():
            self.status_label.config(text=self._('status_select_folder'))
        
        # Redraw treeview with translated strings if data exists
        if self.file_data:
            self.update_treeview()


    def select_folder(self):
        """Open a dialog to select the root folder."""
        path = filedialog.askdirectory(title="Select the QQ Group folder")
        if path:
            self.root_path.set(path)
            self.status_label.config(text=self._('status_folder_selected', path))
            self.scan_button.config(state='normal')
            self.delete_button.config(state='disabled')
            self.file_data.clear()
            self.update_treeview()

    def start_scan(self):
        """Start the file scanning process in a new thread."""
        if not self.root_path.get():
            messagebox.showerror(self._('error_title'), self._('error_no_folder'))
            return
        
        self.scan_button.config(state='disabled')
        self.delete_button.config(state='disabled')
        self.status_label.config(text=self._('status_scanning'))
        self.progress.start()
        threading.Thread(target=self.scan_thread, daemon=True).start()

    def scan_thread(self):
        """The actual scanning logic that runs in the background."""
        self.file_data.clear()
        path_to_scan = self.root_path.get()
        try:
            for root, _, files in os.walk(path_to_scan):
                for name in files:
                    full_path = os.path.join(root, name)
                    try:
                        # NEW: Get the earliest of ctime, mtime, atime
                        ctime = os.path.getctime(full_path)
                        mtime = os.path.getmtime(full_path)
                        atime = os.path.getatime(full_path)
                        file_time = min(ctime, mtime, atime)
                        
                        file_size = os.path.getsize(full_path)
                        dt_object = datetime.fromtimestamp(file_time)
                        
                        year, month = dt_object.year, dt_object.month
                        self.file_data[year][month]['size'] += file_size
                        self.file_data[year][month]['paths'].append(full_path)
                    except (FileNotFoundError, PermissionError):
                        continue
        finally:
            self.root.after(0, self.finish_scan)
    
    def finish_scan(self):
        """Update the GUI after the scan is complete."""
        self.progress.stop()
        self.progress['value'] = 0
        self.update_treeview()
        month_count = sum(len(m) for m in self.file_data.values())
        self.status_label.config(text=self._('status_scan_complete', month_count))
        self.scan_button.config(state='normal')
        if self.file_data:
            self.delete_button.config(state='normal')

    def update_treeview(self):
        """Clear and repopulate the treeview with the latest file data."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        sorted_years = sorted(self.file_data.keys(), reverse=True)
        for year in sorted_years:
            year_node = self.tree.insert('', 'end', values=(self._('year_prefix', year), "", ""), open=True)
            sorted_months = sorted(self.file_data[year].keys(), reverse=True)
            for month in sorted_months:
                data = self.file_data[year][month]
                size_mb = round(data['size'] / (1024 * 1024), 2)
                file_count = len(data['paths'])
                self.tree.insert(year_node, 'end', values=(f"  └ {month:02d}", f"{size_mb:,.2f}", f"{file_count:,}"))

    def start_delete(self):
        """Confirm and start the deletion process."""
        try:
            target_year = int(self.year_spinbox.get())
            target_month = int(self.month_spinbox.get())
        except ValueError:
            messagebox.showerror(self._('error_title'), self._('error_invalid_date'))
            return

        paths_to_delete = []
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp')
        image_paths_to_preview = []
        
        for year, months in self.file_data.items():
            for month, data in months.items():
                if year < target_year or (year == target_year and month <= target_month):
                    paths_to_delete.extend(data['paths'])
                    # Collect image paths for preview
                    for path in data['paths']:
                        if path.lower().endswith(image_extensions):
                            image_paths_to_preview.append(path)
        
        if not paths_to_delete:
            self.status_label.config(text="No files to delete for the selected period.")
            return

        # --- NEW: Show confirmation dialog with thumbnails ---
        dialog = ConfirmationDialog(self.root, self, target_year, target_month, image_paths_to_preview)
        self.root.wait_window(dialog.top) # Wait until the dialog is closed

        if dialog.confirmed:
            self.scan_button.config(state='disabled')
            self.delete_button.config(state='disabled')
            self.status_label.config(text=self._('status_deleting', '0', len(paths_to_delete)))
            threading.Thread(target=self.delete_thread, args=(paths_to_delete,), daemon=True).start()
        else:
            self.status_label.config(text=self._('status_deletion_cancelled'))

    def delete_thread(self, paths_to_delete):
        """The actual deletion logic that runs in the background."""
        total_files = len(paths_to_delete)
        deleted_count, error_count = 0, 0
        
        self.root.after(0, lambda: self.progress.config(maximum=total_files, value=0))

        for i, path in enumerate(paths_to_delete):
            try:
                os.remove(path)
                deleted_count += 1
            except (OSError, PermissionError) as e:
                print(f"Could not delete {path}: {e}")
                error_count += 1
            
            if (i + 1) % 50 == 0 or (i + 1) == total_files:
                self.root.after(0, lambda i=i: self.update_delete_progress(i + 1, total_files))

        self.root.after(0, lambda: self.finish_delete(deleted_count, error_count))

    def update_delete_progress(self, current, total):
        self.progress['value'] = current
        self.status_label.config(text=self._('status_deleting', current, total))

    def finish_delete(self, deleted_count, error_count):
        """Update the GUI after deletion is complete."""
        self.status_label.config(text=self._('status_delete_complete', deleted_count, error_count))
        self.progress['value'] = 0
        self.start_scan()

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

class ToolTip:
    """Create a tooltip for a given widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        widget.bind("<Enter>", self.enter)
        widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        self.tooltip_window = Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        label = Label(self.tooltip_window, text=self.text, justify='left',
                      background="#ffffe0", relief='solid', borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def leave(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None


if __name__ == "__main__":
    root = Tk()
    app = QQCleanerApp(root)
    root.mainloop()