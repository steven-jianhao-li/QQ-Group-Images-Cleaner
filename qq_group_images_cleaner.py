#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import os
import sys
import threading
import random
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, ttk, Frame, Label, Button, Scrollbar, Spinbox, StringVar, Canvas, Menu, Toplevel, W, E, N, S, simpledialog

# --- 关键修复 1: 将 ctypes 相关的导入移至文件顶部 ---
# 这可以确保 PyInstaller 能够正确地将这些模块打包进去
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

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
        'select_folder_btn': "手动选择...",
        'auto_select_folder_btn': "自动选择",
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
        'error_invalid_date': "请输入有效的年份和月份。",
        'prompt_qq_number': "请输入您的QQ号",
        'qq_number_title': "输入QQ号",
        'error_find_qq_folder_title': "自动查找失败",
        'error_find_qq_folder_msg': "未找到对应的QQ图片文件夹, 请手动选择。",
        'thumb_viewer_title': "缩略图预览 - {} 年 {} 月",
        'items_per_page': "每页显示:",
        'sort_by': "排序:",
        'page_label': "第 {} / {} 页",
        'sort_time_asc': "时间 (从早到晚)",
        'sort_time_desc': "时间 (从晚到早)",
        'sort_size_asc': "大小 (从小到大)",
        'sort_size_desc': "大小 (从大到小)",
        'context_delete': "删除",
        'context_open': "打开",
        'context_open_dir': "打开所在目录",
        'prev_page': "上一页",
        'next_page': "下一页"
    },
    'en': {
        'window_title': "QQ Group Images Cleaner",
        'folder_label': "QQ Group Folder:",
        'select_folder_btn': "Manual Select...",
        'auto_select_folder_btn': "Auto Select",
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
        'error_invalid_date': "Please enter valid numbers for year and month.",
        'prompt_qq_number': "Please enter your QQ number",
        'qq_number_title': "Enter QQ Number",
        'error_find_qq_folder_title': "Auto-Select Failed",
        'error_find_qq_folder_msg': "Could not find the corresponding QQ image folder. Please select it manually.",
        'thumb_viewer_title': "Thumbnail Viewer - {}-{:02d}",
        'items_per_page': "Items per page:",
        'sort_by': "Sort by:",
        'page_label': "Page {} of {}",
        'sort_time_asc': "Time (Ascending)",
        'sort_time_desc': "Time (Descending)",
        'sort_size_asc': "Size (Ascending)",
        'sort_size_desc': "Size (Descending)",
        'context_delete': "Delete",
        'context_open': "Open",
        'context_open_dir': "Open Containing Folder",
        'prev_page': "Prev",
        'next_page': "Next"
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


if __name__ == "__main__":
    root = Tk()
    app = QQCleanerApp(root)
    root.mainloop()