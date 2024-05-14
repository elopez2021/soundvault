from PyQt5.QtWidgets import QLabel
from queue import Queue
from threading import Thread
import requests
from PyQt5.QtGui import QPixmap

class CustomWidget(QWidget):
    def _init_(self, imagePath):
        super()._init_()
        global pool
        global limit
        self.layout = QHBoxLayout(self)
        self.cover = ImageLabel(self)
        self.layout.addWidget(self.cover)
        self.image_queue = Queue()  # Initialize the image download queue
        self.start_worker_threads()  # Start worker threads for image downloading
        self.add_image_download_task(imagePath, self.cover)  # Add image download task

    def start_worker_threads(self):
        for _ in range(4):  # Limit to 4 concurrent downloads
            worker_thread = Thread(target=self.worker, args=(self.image_queue,))
            worker_thread.daemon = True
            worker_thread.start()

    def worker(self, image_queue):
        while True:
            url, cover = image_queue.get()
            self.download_and_set_image(url, cover)
            image_queue.task_done()

    def download_and_set_image(self, url, cover):
        response = requests.get(url)
        image_data = response.content
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        cover.setPixmap(pixmap)

    def add_image_download_task(self, url, cover):
        self.image_queue.put((url, cover))

# Example usage
# Assuming 'cover' is an instance of a QLabel or similar widget
custom_widget = CustomWidget('image_url_1')