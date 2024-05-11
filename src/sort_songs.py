import json
import subprocess
import sys
import random
import traceback

from PyQt5.QtCore import Qt, pyqtSignal, QThread, QRunnable, QThreadPool, pyqtSlot
from PyQt5.QtGui import QMovie, QIcon, QPixmap,QFont
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, \
    QListWidgetItem, QLabel, QFileDialog, QTableWidgetItem, QSizePolicy, QHeaderView, QFrame

from qfluentwidgets import (ListWidget, TitleLabel, PrimaryPushButton, PushButton, MessageBox, CheckBox, ProgressBar)



from qfluentwidgets import FluentIcon as FIF

from functools import partial
from spotdl import Spotdl
from spotdl.download.progress_handler import ProgressHandler, SongTracker
from spotdl.types.options import DownloaderOptionalOptions

import tracemalloc
tracemalloc.start()


import os
import shutil
import sys
from pydub.utils import mediainfo
from colorama import Fore, Style

class SortThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool)
    sorted_song = pyqtSignal(str)
    def __init__(self, folder_path, sort_options):
        super().__init__()
        self.folder_path = folder_path
        self.sort_options = sort_options
        
    def run(self):
        if self.sort_and_organize():
            print("Files have been successfully organized.")
            self.finished.emit(True)
        else:
            print("Failed to organize files due to invalid input.")
            self.finished.emit(False)
            
    def list_audio_files(self, directory):
        """ List all audio files in a directory. """
        supported_formats = ('mp3', 'm4a', 'flac', 'wav', 'opus')
        return [f for f in os.listdir(directory) if f.endswith(supported_formats)]

    def read_metadata(self, file_path):
        """ Read metadata from an audio file using Mutagen. """
        extension = os.path.splitext(file_path)[1]
        try:
            return mediainfo(file_path)
        except Exception as e:
            print(f"Error reading metadata for {file_path}: {e}")
            return None


    def create_nested_folders(self, directory, attributes):
        """ Create nested folders based on a list of attributes and return the final path. """
        for attribute in attributes:
            directory = os.path.join(directory, attribute)
            os.makedirs(directory, exist_ok=True)
        return directory

    def sort_and_organize(self):
        """ Sort and organize audio files into folders based on multiple metadata attributes. """        
        audio_files = self.list_audio_files(self.folder_path)
        total_audio_files = len(audio_files)
        total_audio_sorted = 0
        for file_name in audio_files:
            file_path = os.path.join(self.folder_path, file_name)
            extension = os.path.splitext(file_path)[1]
            metadata = self.read_metadata(file_path)
            
            if metadata:
                # Extract folder names based on sort criteria
                folder_names = [metadata['TAG'].get(attr, ['Unknown']) for attr in self.sort_options if attr in metadata['TAG']]
                try:
                    if folder_names:
                        target_folder = self.create_nested_folders(self.folder_path, folder_names)
                        # Move file to the new folder
                        shutil.move(file_path, os.path.join(target_folder, file_name))
                        #print(f"Moved {file_name} to {target_folder}")
                        total_audio_sorted += 1
                        self.sorted_song.emit(f"Moved {file_name} to {target_folder}")
                        self.progress.emit(int((total_audio_sorted / total_audio_files) * 100))
                    else:
                        print(f"{Fore.RED}Failed to sort {file_name} {Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Error: {e} {Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to read metadata for {file_name} {Style.RESET_ALL}")

        return True
class SortSongs(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.isSorting = False
        self.sort_thread = None
        self.setAcceptDrops(True)  # Enable drag and drop
        self.folder_path = None
        self.checkboxes = None
        self.listWidget = None

        self.initUI()
        
    def initUI(self):
        # Clear the QVBoxLayout
        self.clear_layout(self.vBoxLayout)
        self.drop_enabled = True
        text = "Drag and drop your music folder"
        self.label = TitleLabel(text, self)
        self.label.setAlignment(Qt.AlignCenter)
        
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(25, 25, 25, 25)
        self.vBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
        self.setObjectName("sort_songs_frame")
        
        self.setStyleSheet("#sort_songs_frame { border: 2px dashed #4285F4; }")
        
    def clear_layout(self,layout):
        if self.isSorting and self.sort_thread is not None:
            self.sort_thread.terminate()
            self.isSorting = False
            print("Terminated thread")
        while layout.count():
            child = layout.takeAt(0)
            # If the child is a layout, clear it
            if child.layout():
                self.clear_layout(child.layout())
            # If the child is a widget, delete it
            if child.widget():
                child.widget().deleteLater()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        try:
            if event.mimeData().hasUrls() and self.drop_enabled:
                urls = event.mimeData().urls()
                for url in urls:
                    if url.isLocalFile():
                        self.folder_path = url.toLocalFile()
                        # Process the dropped folder path
                        print("Dropped folder path:", self.folder_path)
                        self.showList()
            else:
                event.ignore()
        except Exception as e:
            print("Error",e)

    def mousePressEvent(self, event):
        try:

            if event.button() == Qt.LeftButton and self.drop_enabled:
                self.folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
                # Process the selected folder path
                print("Selected folder path:", self.folder_path)
                self.showList()
        except Exception as e:
            print("Error",e)       
    
    def showList(self):
        if self.folder_path is None or not self.folder_path:
            return
        self.drop_enabled = False
        self.setStyleSheet("")

        self.listWidget = ListWidget()   

        self.label.setVisible(False)
        self.label_path = TitleLabel(f"Selected Folder: {self.folder_path}", self)

        # Create the checkboxes
        chxGenre = CheckBox("Genre")
        chxGenre.setObjectName("genre")
        chxArtist = CheckBox("Artist")
        chxArtist.setObjectName("artist")
        chxAlbum = CheckBox("Album")
        chxAlbum.setObjectName("album")

        # Store checkboxes in a list
        self.checkboxes = [chxGenre, chxArtist, chxAlbum]

        # Create a horizontal layout named checkboxLayout
        checkboxLayout = QHBoxLayout()
        # Set the margins
        checkboxLayout.setContentsMargins(0, 0, 0, 10)

        # Add a stretchable space on the left side of the checkboxes
        checkboxLayout.addStretch(1)

        # Add the checkboxes to the layout with a gap between them
        checkboxLayout.addWidget(chxGenre)
        checkboxLayout.addSpacing(10)  # Adjust the size of the gap as needed
        checkboxLayout.addWidget(chxArtist)
        checkboxLayout.addSpacing(10)  # Adjust the size of the gap as needed
        checkboxLayout.addWidget(chxAlbum)

        # Add a stretchable space on the right side of the checkboxes
        checkboxLayout.addStretch(1)        

        self.start_button = PrimaryPushButton('Start Sorting')
        self.start_button.clicked.connect(self.startSorting)
        self.reset_button = PushButton('Reset') 
        self.reset_button.clicked.connect(self.initUI)
        # Create a QHBoxLayout for the buttons
        self.buttonBoxLayout = QHBoxLayout()      


        # Add stretches and the buttons to the QHBoxLayout
        self.buttonBoxLayout.addStretch(1)  # Add a stretch on the left
        self.buttonBoxLayout.addWidget(self.start_button)  # Add the start button
        self.buttonBoxLayout.addSpacing(10)  # Add a small gap
        self.buttonBoxLayout.addWidget(self.reset_button)  # Add the reset button
        self.buttonBoxLayout.addStretch(1)  # Add a stretch on the right             
        
        

        self.progressBar = ProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)

        self.vBoxLayout.addWidget(self.label_path,1,Qt.AlignCenter)
        self.vBoxLayout.addLayout(checkboxLayout)
        self.vBoxLayout.addLayout(self.buttonBoxLayout)
        self.vBoxLayout.addWidget(self.progressBar, 1,Qt.AlignCenter)
        

        self.vBoxLayout.addWidget(self.listWidget,6)
    
    def startSorting(self):        
        # Get all checkboxes that are checked
        sort_options = [checkbox.objectName() for checkbox in self.checkboxes if checkbox.isChecked()]
        if not sort_options:
            print("Please select at least one sorting option.")
            w = MessageBox("Message Info", "Please select at least one sorting option.", self)
            w.exec()
            return

        self.isSorting = True
        self.label_path.setText("Sorting files. Please wait...")
        try:
            self.sort_thread = SortThread(self.folder_path, sort_options)
            self.sort_thread.progress.connect(self.updateProgress)
            self.sort_thread.finished.connect(self.sortFinished)
            self.sort_thread.sorted_song.connect(self.show_sorted_audio)
            self.sort_thread.start()
        except Exception as e:
            print("Error",e)
    
    def show_sorted_audio(self, message):
        self.listWidget.addItem(QListWidgetItem(message))
        self.listWidget.scrollToBottom()
    
    def updateProgress(self, value):
        self.progressBar.setValue(value)
    
    def sortFinished(self, success):
        self.isSorting = False
        if success:
            self.label_path.setText("Sorting completed successfully.")
        else:
            self.label_path.setText("Sorting failed.")        