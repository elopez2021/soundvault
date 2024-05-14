import json
import subprocess
import sys
import random
import traceback

from PyQt5.QtCore import Qt, pyqtSignal, QThread, QRunnable, QThreadPool, pyqtSlot
from PyQt5.QtGui import QMovie, QIcon, QPixmap,QFont
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, \
    QListWidgetItem, QLabel, QFileDialog, QTableWidgetItem, QSizePolicy, QHeaderView, QFrame

from qfluentwidgets import (SearchLineEdit, PushButton, MessageBox, TableWidget, ImageLabel, StrongBodyLabel, ProgressBar, BodyLabel, InfoBar, InfoBarPosition, TitleLabel)



from qfluentwidgets import FluentIcon as FIF

from functools import partial
from spotdl import Spotdl
from spotdl.download.progress_handler import ProgressHandler, SongTracker
from spotdl.types.options import DownloaderOptionalOptions

import tracemalloc
tracemalloc.start()

import requests

from queue import Queue
from threading import Thread



# Global thread pool and image queue
image_queue = Queue() #receives a tuple of (url, cover)

def worker(image_queue):
    while True:
        url, cover = image_queue.get()
        download_and_set_image(url, cover)
        image_queue.task_done()

for _ in range(4):  # Limit to 4 concurrent downloads
    worker_thread = Thread(target=worker, args=(image_queue,))
    worker_thread.daemon = True
    worker_thread.start()

def download_and_set_image(url, cover):
    response = requests.get(url)
    image_data = response.content
    pixmap = QPixmap()
    pixmap.loadFromData(image_data)
    cover.setPixmap(pixmap)
    cover.scaledToWidth(64)
    cover.setBorderRadius(8, 8, 8, 8)


class CustomWidget(QWidget):
    # Add a class attribute for the QThreadPool
    def __init__(self, imagePath):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.cover = ImageLabel(self)
        
        self.layout.addWidget(self.cover)
        try:
            self.add_image_download_task(imagePath, self.cover)
        except Exception as e:
            print(f"Failed to load image: {e}")

    def add_image_download_task(self, url, cover):
        image_queue.put((url, cover))

class DownloaderThread(QThread):
    progress_update = pyqtSignal(dict)  # Emit both song_id and song_progress
    finished = pyqtSignal(str)

    def __init__(self, query, downloader_settings):
        super().__init__()
        self.query = query
        self.custom_directory = downloader_settings['output']
        self.format = downloader_settings['format']
        self.process = None
        self.stopped = False
    
    def run(self):
        try:

            self.process = subprocess.Popen([
                sys.executable, "-u",
                "src/download.py",
                '--song_url',
                self.query,
                '--output', self.custom_directory,
                '--format', self.format
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            
            if self.process.stdout is None:
                print("No output from process")
            else:
                print("Output from process:", self.process.stdout)



            # Read from self.process.stdout line by line
            for line in iter(self.process.stdout.readline, ''):
                line = line.strip()
                try:
                    data = json.loads(line)
                    self.progress_update.emit(data)
                    #print(f"Parsed JSON: {data}")
                except json.JSONDecodeError:
                    print(f"Failed to parse line as JSON: {line}")
            
            print("passed the loop")

            # Read from self.process.stderr line by line
            
            for line in iter(self.process.stderr.readline, ''):
                line = line.strip()
                print(f"Error from process: {line}")
            
            if self.process:            
                return_code = self.process.wait()
            else:
                print("Process is None")
                self.stopped = True

            if self.stopped == True:
                self.finished.emit("Download has been stopped!")
            elif return_code == 0:
                self.finished.emit("Download Completed!")
            else:
                print(f"Download failed with return code: {return_code}")
                self.finished.emit("Download Failed!")

        except Exception as e:
            print("Error:", e)  # Print the error for debugging
            """
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')

            for stat in top_stats:
                print(stat)
            """
            self.finished.emit("Download Failed!")
        finally:
            self.process.stdout.close()
            

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            self.process = None
            self.stopped = True




class SearchThread(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self, spotdl, query):
        QThread.__init__(self)
        self.spotdl = spotdl
        self.query = query

    def run(self):
        try:
            songs = self.spotdl.search([self.query])
            if songs:
                self.signal.emit(songs)
            else:
                self.signal.emit(None)
        except Exception as e:
            print(f"Failed to search for songs: {e}")
            self.signal.emit(None)
                    

class Song(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.downloader_thread = None  # Initialize downloader thread
        self.spotdl = self.connect_to_spotdl() # Initialize spotdl object
        self.songsData = None  # A dictionary to store song data
        self.songs = None # A list of Song objects for spotdl
        self.downloading = False # Add a flag to track whether downloads are happening

    def connect_to_spotdl(self):
        try:
            spotdl = Spotdl(client_id='5f573c9620494bae87890c0f08a60293', client_secret='212476d9b0f3472eaa762d90b19b0ba8')
            print("Connected to Spotdl")
            return spotdl
        except Exception as e:
            print(f"Failed to connect to Spotdl: {e}")
            InfoBar.error(
                title='Connection Error',
                content="Failed to connect to Spotdl. Please check your internet connection and try again.",
                orient=Qt.Horizontal,  # Use vertical layout when the content is too long
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,
                parent=self
            )

            return None
        
    def set_downloader_settings(self, download_folder, output_format):
        try:
            # Check if spotdl object is initialized
            if self.spotdl is not None:
                self.spotdl.downloader_settings = {'output': download_folder, 'format': output_format}
            else:
                print("Spotdl object is not initialized.")
        except Exception as e:
            print(f"Failed to set downloader settings: {e}")

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)
        self.HBoxLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.HBoxLayout)

        # Search box for entering Spotify track URL
        self.searchBox = SearchLineEdit(self)
        self.searchBox.setPlaceholderText("Enter Spotify Track URL")
        self.HBoxLayout.addWidget(self.searchBox, 8, Qt.AlignTop)

        self.searchBox.returnPressed.connect(self.start_lookup)

        self.searchBox.searchSignal.connect(self.start_lookup)

        # Add QLabel for loading
        self.loading_label = TitleLabel(self)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setVisible(False)  # Initially hide the loading label
        self.mainLayout.addWidget(self.loading_label)

        # Button to initiate download
        self.download_button_all = PushButton(self)
        self.download_button_all.setText("Download All")
        self.download_button_all.setEnabled(False)
        self.download_button_all.clicked.connect(self.toggle_download_all)
        self.HBoxLayout.addWidget(self.download_button_all, 1, Qt.AlignTop)

        # Set up the table to display song information
        self.songTable = TableWidget(self)
        self.songTable.setBorderVisible(True)
        self.songTable.setBorderRadius(8)
        self.songTable.setWordWrap(False)
        self.songTable.setRowCount(3)
        self.songTable.setColumnCount(3)
        self.songTable.setHorizontalHeaderLabels(['Cover','title', 'Progress'])

        self.songTable.verticalHeader().hide()
        self.songTable.horizontalHeader().hide()
        self.songTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.songTable.setVisible(False)

        self.mainLayout.addWidget(self.songTable, 1)
    
    def toggle_download_all(self):
        try:
            if self.downloading:
                self.stop_all_downloads()
            else:
                self.start_download_multiple_song()
        except Exception as e:
            print("Error: ", e) 

    def start_lookup(self):
        # Get the text from the search box
        query = self.searchBox.text()

        # Show the loading label
        self.loading_label.setText("Searching for songs...")
        self.loading_label.setVisible(True)
        
        # Define the update_ui function inside start_lookup
        def update_ui(result):
            # Show the table
            self.songTable.setVisible(True)
            if result:
                self.songs = result
                self.songsData = {f"{song.name} - {song.artists[0]}": song for song in result}

                print(self.songsData)
                self.loading_label.setText(f"Total: {len(self.songs)} songs")
                
                self.download_button_all.setEnabled(True)
                self.songTable.setRowCount(len(self.songs))
                for i, song in enumerate(self.songs):
                    # Create the custom widget with the image path
                    widget = CustomWidget(song.cover_url)
                    self.songTable.setCellWidget(i, 0, widget)

                    songLabel = BodyLabel(f"{song.name}\n{', '.join(song.artists)}")
                    font = QFont()
                    font.setBold(True)  # Make font bold
                    font.setPointSize(11)
                    self.songTable.setCellWidget(i, 1, songLabel)

                    # Create a download button for the song
                    downloadButton = PushButton(FIF.DOWNLOAD,"Download")

                    progress_bar_id = f"{song.name} - {song.artists[0]}"
                    
                    downloadButton.setObjectName(f"downloadButton{progress_bar_id}")
                
                    

                    downloadButton.clicked.connect(partial(self.start_download_song, i, 2, progress_bar_id))
                    self.songTable.setCellWidget(i, 2, downloadButton)

                    # Set the row height
                    self.songTable.setRowHeight(i, 80)
            else:
                w = MessageBox(
                    'Oops!😢',
                    'No songs found. Please enter a valid song name or Spotify URL.',
                    self
                )
                w.exec()
                self.searchBox.clear()

        # Create a new thread and connect its signal to the update_ui function
        self.search_thread = SearchThread(self.spotdl, query)
        self.search_thread.signal.connect(update_ui)
        self.search_thread.start()
               
    def stop_all_downloads(self):
        # Reset the flag and button text
        self.downloading = False
        self.download_button_all.setText("Download All")

        # Stop the downloader thread
        if self.downloader_thread is not None:
            self.downloader_thread.stop()

    
    def start_download_multiple_song(self):
        query = self.searchBox.text()
        if not query:
            return
        custom_directory = QFileDialog.getExistingDirectory(self, "Select Directory", "/")
        if not custom_directory:
            return
        
        format = 'mp3'
        downloader_settings: DownloaderOptionalOptions = {'output': custom_directory, 'format': format}

        self.spotdl.downloader_settings = downloader_settings
        self.downloading = True
        self.download_button_all.setText("Stop All")

        # Get the existing stylesheet
        #stylesheet = self.download_button_all.styleSheet()
        # Append the new background color setting
        #stylesheet += "background-color: #dc3545;"

        # Apply the updated stylesheet
        #self.download_button_all.setStyleSheet(stylesheet)

        try:

            # Convert the keys of the result dictionary to a list
            songRows = list(self.songsData.keys())

            if songRows is None:
                raise ValueError("No songs rows found.")

            # Iterate over all rows in the songTable
            for songId, song in self.songsData.items():
                # Get the row number from the list of song IDs
                row = songRows.index(songId)
                self.create_progress_bar(row, 2, songId)
        except Exception as e:
            print(f"Failed to create progress bars: {e}")
        
        self.downloader_thread = DownloaderThread(query, downloader_settings)
        self.downloader_thread.finished.connect(self.finish_download)
        self.downloader_thread.progress_update.connect(self.update_progress_bar)
        self.downloader_thread.start()
        self.loading_label.setText("Starting download. Please wait...")
        self.loading_label.setVisible(True)

        

    def start_download_song(self, row, column, song_id):

        custom_directory = QFileDialog.getExistingDirectory(self, "Select Directory", "/")

        if not custom_directory:
            return    
        
        self.create_progress_bar(row, column, song_id)

        format = 'mp3'
        downloader_settings: DownloaderOptionalOptions = {'output': custom_directory, 'format': format}

        self.spotdl.downloader_settings = downloader_settings                

        self.downloader_thread = DownloaderThread(song_id, downloader_settings)
        self.downloader_thread.finished.connect(self.finish_download)
        self.downloader_thread.progress_update.connect(self.update_progress_bar)
        self.downloader_thread.start()
        self.loading_label.setText("Starting download. Please wait...")
        self.loading_label.setVisible(True)

    def create_progress_bar(self, row, column, id):
        
        progressBar = ProgressBar()
        # Set the object name (ID)
        progressBar.setObjectName(f'progressBar{id}')
        # Set the range of values
        progressBar.setRange(0, 100)

        # Set the current value
        progressBar.setValue(0)

        # Set the alignment
        progressBar.setAlignment(Qt.AlignCenter)

        # Set the widget containing the progress bar as the cell widget
        self.songTable.setCellWidget(row, column, progressBar)

        

    def update_progress_bar(self, song_dict): #song_id = song.name - song.artists[0]
        
        self.loading_label.setText("Downloading songs...")

        try:
            # Find the progress bar by its object name and update its value
            self.findChild(ProgressBar, f'progressBar{song_dict["song_id"]}').setValue(song_dict['song_progress'])
        except Exception as e:
            print(f"Failed to update progress bar: {e}")
            print(f"Unexpected error: {traceback.format_exc()}")
    
    def finish_download(self, message):
        self.loading_label.setVisible(False)  # Hide the loading label after download completes
        self.download_button_all.setText("Download All")
        
        w = MessageBox(
            'Message Info',
            message,
            self
        )

        
        #w.cancelButton.setText("Let's goooo")

        if w.exec():
            pass
            
    
        