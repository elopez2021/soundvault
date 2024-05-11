import json
import subprocess
import sys
import random
import traceback

from PyQt5.QtCore import Qt, pyqtSignal, QThread, QRunnable, QThreadPool, pyqtSlot
from PyQt5.QtGui import QMovie, QIcon, QPixmap,QFont
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, \
    QListWidgetItem, QLabel, QFileDialog, QTableWidgetItem, QSizePolicy, QHeaderView, QFrame

from qfluentwidgets import (ListWidget, TitleLabel, PrimaryPushButton, PushButton, ProgressBar)



from qfluentwidgets import FluentIcon as FIF

from functools import partial
from spotdl import Spotdl
from spotdl.download.progress_handler import ProgressHandler, SongTracker
from spotdl.types.options import DownloaderOptionalOptions
from qfluentwidgets import DisplayLabel

import tracemalloc
tracemalloc.start()

import os
import sys
from pydub import AudioSegment
from pydub.utils import mediainfo
import mutagen
from mutagen.mp4 import MP4

from colorama import Fore, Style


class NormalizeThread(QThread):
    progress_update = pyqtSignal(int)
    normalized_audio = pyqtSignal(str)
    finished = pyqtSignal(bool)
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        try:
            supported_formats = ('mp3', 'm4a', 'flac', 'wav', 'opus')
            target_dBFS = -20.0
            if self.folder_path is None or not self.folder_path:
                print("No folder path selected")
                return
            total_files = sum(
                file_name.endswith(supported_formats)
                for subdir, dirs, files in os.walk(self.folder_path)
                for file_name in files
            )
            print("Total of songs: ",total_files)
            total_normalized_files = 0
            for subdir, dirs, files in os.walk(self.folder_path):
                for file_name in files: 
                    file_path = os.path.join(subdir, file_name)
                    if file_name.endswith(supported_formats):
                        print("Processing file: ", file_path)
                    
                        # Load audio file
                        file_extension = os.path.splitext(file_name)[1][1:]
                        if file_extension == 'm4a':
                            audio = AudioSegment.from_file(file_path, format='mp4')
                            audioM = MP4(file_path)
                        else:         
                            audio = AudioSegment.from_file(file_path, format=file_extension)
                            audioM = mutagen.File(file_path)                   

                        metadata_from_mutagen = audioM.tags       

                        metadata = mediainfo(file_path)
                        if file_extension == 'm4a':
                            metadata['format_name'] = 'mp4'

                        # Calculate the gain to apply
                        change_in_dBFS = target_dBFS - audio.dBFS

                        if change_in_dBFS == 0:
                            #print(f"{Fore.YELLOW}Volume is already normalized for {file_path}{Style.RESET_ALL}")
                            self.normalized_audio.emit(f"Volume is already normalized for {file_path}")
                            continue
                        
                        # Apply the gain
                        normalized_audio = audio.apply_gain(change_in_dBFS)
                        # Export normalized audio back to a temporary file
                        temp_file_path = file_path + ".temp"
                        normalized_audio.export(temp_file_path, format=metadata['format_name'], bitrate = metadata['bit_rate'])
                        # Replace original file with temporary file
                        os.remove(file_path)
                        os.rename(temp_file_path, file_path)
                        # Write metadata back
                        
                        if file_extension == 'm4a':
                            audioM = MP4(file_path)
                        else:         
                            audioM = mutagen.File(file_path)  
                        
                        for key, value in metadata_from_mutagen.items():
                            audioM[key] = value

                        audioM.save()

                        total_normalized_files += 1
                        self.progress_update.emit(int((total_normalized_files / total_files) * 100))
                        print("Percentage ",(total_normalized_files / total_files) * 100)

                        self.normalized_audio.emit(f"Normalized volume of {file_path}")

                        #print(f"{Fore.GREEN}Normalized volume of {file_path}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}Unsupported format for {file_path}{Style.RESET_ALL}")

            self.finished.emit(True)

        except Exception as e:
            self.finished.emit(False)
            print("Error",e)



class NormalizeAudio(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.setAcceptDrops(True)  # Enable drag and drop
        self.folder_path = None
        self.isNormalizing = False
        self.normalize_thread = None

        self.initUI()
        
        
    def initUI(self):
        # Clear the QVBoxLayout
        self.clear_layout(self.vBoxLayout)
        self.drop_enabled = True
        text = "Drag and drop your music folder"
        self.label = TitleLabel(text, self)        

        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(25, 25, 25, 25)

        self.vBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
        self.setObjectName("normalize-interface")


        
        self.setStyleSheet("#normalize-interface { border: 2px dashed #4285F4; }")
        
    def clear_layout(self,layout):
        if self.isNormalizing and self.normalize_thread is not None:
            self.normalize_thread.terminate()
            self.isNormalizing = False
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

        self.listWidget = ListWidget()   

        self.label.setVisible(False)
        self.label_path = TitleLabel(f"Selected Folder: {self.folder_path}", self)


        self.start_button = PrimaryPushButton('Start Normalization')
        self.start_button.clicked.connect(self.startNormalization)
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
        self.progressBar.setVisible(False)

        self.progressBar.setObjectName("progressBar")

        self.vBoxLayout.addWidget(self.label_path,1,alignment=Qt.AlignTop | Qt.AlignCenter)
        # Add the QHoBoxLayout to the QVBoxLayout
        self.vBoxLayout.addLayout(self.buttonBoxLayout)
        self.vBoxLayout.addWidget(self.progressBar, 1, alignment=Qt.AlignCenter)

        self.vBoxLayout.addWidget(self.listWidget,6)
        self.setStyleSheet("")
    
    def startNormalization(self):
        print("Starting normalization ", self.folder_path)
        self.isNormalizing = True
        self.normalize_thread = NormalizeThread(self.folder_path)
        self.progressBar.setVisible(True)
        self.normalize_thread.progress_update.connect(self.update_progress_bar)
        self.normalize_thread.normalized_audio.connect(self.show_normalized_audio)
        self.normalize_thread.finished.connect(self.finished_normalizing)
        self.normalize_thread.start()
        self.label_path.setText("Starting normalization. Please wait...")
    
    def finished_normalizing(self, value):
        if value:
            self.label_path.setText("Normalization completed.")
            self.isNormalizing = False
        else:
            self.label_path.setText("An error occurred during normalization.")
    
    def update_progress_bar(self, value):
        self.progressBar.setValue(value)

    def show_normalized_audio(self, file_path):
        self.label_path.setText("Normalizing. Please wait...")
        self.listWidget.addItem(QListWidgetItem(file_path))
        self.listWidget.scrollToBottom()

