import os
import sys
import threading
import ctypes
from pathlib import Path
from ctypes import wintypes
from datetime import datetime
from collections import defaultdict
from tkinter import filedialog, messagebox, ttk, Frame, Label, Scrollbar, Spinbox, StringVar, Menu, W, E, N, S, simpledialog
from lib.ImportCheck import import_PIL
from lib.ConfirmationDialog import ConfirmationDialog
from lib.ThumbnailViewerWindow import ThumbnailViewerWindow
from lib.i18n import I18N_STRINGS

Image, ImageTk = import_PIL()

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
        
        self.auto_select_button = ttk.Button(top_frame, command=self.auto_select_folder)
        self.auto_select_button.pack(side='left', padx=(0, 5))
        
        self.select_folder_button = ttk.Button(top_frame, command=self.select_folder)
        self.select_folder_button.pack(side='left')

        mid_frame = Frame(self.root, padx=10, pady=5)
        mid_frame.pack(fill='both', expand=True)

        self.tree = ttk.Treeview(mid_frame, columns=('month', 'size', 'count'), show='headings')
        vsb = Scrollbar(mid_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky=N+S+W+E)
        vsb.grid(row=0, column=1, sticky=N+S)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
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
        self.auto_select_button.config(text=self._('auto_select_folder_btn'))
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
            self.set_folder_path(path)

    def auto_select_folder(self):
        """Try to automatically find the QQ Group folder."""
        qq_number = simpledialog.askstring(self._('qq_number_title'), self._('prompt_qq_number'), parent=self.root)
        if not qq_number or not qq_number.isdigit():
            return

        documents_path = self.get_documents_path()
        if not documents_path:
              messagebox.showwarning(self._('error_find_qq_folder_title'), "Could not determine the Documents folder path.")
              return

        qq_folder_path = Path(documents_path) / 'Tencent Files' / qq_number / 'Image' / 'Group2'

        if qq_folder_path.is_dir():
            self.set_folder_path(str(qq_folder_path))
        else:
            messagebox.showwarning(self._('error_find_qq_folder_title'), self._('error_find_qq_folder_msg'))

    def get_documents_path(self):
        """Get the user's Documents folder path reliably on Windows."""
        if sys.platform == 'win32':
            # These modules are now imported at the top of the file
            CSIDL_PERSONAL = 5       # My Documents
            SHGFP_TYPE_CURRENT = 0   # Get current, not default value

            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            return buf.value
        else:
            # Fallback for non-Windows systems
            return str(Path.home() / 'Documents')

    def set_folder_path(self, path):
        """Sets the folder path and updates the UI."""
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
        
        # Switch to determinate progress bar
        self.progress.stop()
        self.progress.config(mode='determinate', value=0)
        
        threading.Thread(target=self.scan_thread, daemon=True).start()

    def scan_thread(self):
        """Optimized scanning logic using os.scandir."""
        self.file_data.clear()
        path_to_scan = self.root_path.get()
        
        # --- 关键修复 2: 增强错误捕获和报告 ---
        # 使用更广泛的 except Exception as e 来捕获所有可能的错误
        # 并使用 print() 将错误信息输出到控制台，以便调试
        print(f"Starting scan on: {path_to_scan}")

        try:
            # --- Progress Estimation ---
            all_entries = list(os.scandir(path_to_scan))
            total_entries = len(all_entries)
            print(f"Found {total_entries} top-level entries.")
            self.root.after(0, lambda: self.progress.config(maximum=total_entries if total_entries > 0 else 1))
        except Exception as e:
            print(f"!!! FATAL ERROR: Could not list directory '{path_to_scan}'.")
            print(f"!!! REASON: {e}")
            import traceback
            traceback.print_exc() # 打印完整的错误堆栈
            self.root.after(0, self.finish_scan)
            return

        def process_file(entry):
            """Processes a single file entry to avoid code duplication."""
            try:
                stat = entry.stat()
                # 使用 st_mtime 作为统一的时间戳来源，因为它最可靠
                file_time = stat.st_mtime
                file_size = stat.st_size
                
                dt_object = datetime.fromtimestamp(file_time)
                year, month = dt_object.year, dt_object.month
                
                self.file_data[year][month]['size'] += file_size
                self.file_data[year][month]['paths'].append(entry.path)
            except Exception as e:
                # 如果单个文件处理失败，打印警告但继续运行
                print(f"--- WARNING: Could not process file '{entry.path}'. Reason: {e}")
                
        def recursive_scan(path):
            try:
                for entry in os.scandir(path):
                    if entry.is_dir(follow_symlinks=False):
                        recursive_scan(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        process_file(entry)
            except Exception as e:
                print(f"--- WARNING: Could not scan sub-directory '{path}'. Reason: {e}")

        # --- Main Scan Loop ---
        try:
            for i, entry in enumerate(all_entries):
                try:
                    if entry.is_dir(follow_symlinks=False):
                        recursive_scan(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        process_file(entry)
                finally:
                    # Update progress after processing each top-level entry
                    self.root.after(0, lambda i=i: self.progress.config(value=i + 1))
        finally:
            print("Scan loop finished.")
            # Final call to ensure GUI is updated after the loop finishes
            self.root.after(0, self.finish_scan)
    
    def finish_scan(self):
        """Update the GUI after the scan is complete."""
        self.progress.stop()
        self.progress['value'] = 0
        self.update_treeview()
        month_count = sum(len(m) for m in self.file_data.values())
        self.status_label.config(text=self._('status_scan_complete', month_count))
        print(f"Scan complete. Found data for {month_count} months.")
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
                # Store year and month in the item's tags for later retrieval
                item_id = self.tree.insert(year_node, 'end', values=(f"  └ {month:02d}", f"{size_mb:,.2f}", f"{file_count:,}"))
                self.tree.item(item_id, tags=(str(year), str(month)))

    def on_tree_double_click(self, event):
        """Handle double-click event on the treeview to open thumbnail viewer."""
        item_id = self.tree.focus()
        if not item_id: return
        
        item = self.tree.item(item_id)
        tags = item.get('tags')

        if tags and len(tags) == 2:
            try:
                year, month = int(tags[0]), int(tags[1])
                paths = self.file_data.get(year, {}).get(month, {}).get('paths', [])
                if paths:
                    ThumbnailViewerWindow(self.root, self, paths, year, month)
            except (ValueError, IndexError):
                print(f"Could not parse year/month from tags: {tags}")

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

        dialog = ConfirmationDialog(self.root, self, target_year, target_month, image_paths_to_preview)
        self.root.wait_window(dialog.top)

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
