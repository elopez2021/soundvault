# coding:utf-8
import os
from pathlib import Path
import sys
import platform

from PyQt5.QtCore import Qt, QRect, QUrl, QSize
from PyQt5.QtGui import QIcon, QPainter, QImage, QBrush, QColor, QFont, QDesktopServices, QPixmap
from PyQt5.QtWidgets import QApplication, QFrame, QStackedWidget, QHBoxLayout, QLabel, QVBoxLayout

from qfluentwidgets import (NavigationInterface, NavigationItemPosition, NavigationWidget, MessageBox,
                            isDarkTheme, setTheme, Theme, setThemeColor, qrouter, FluentWindow, NavigationAvatarWidget, ImageLabel)
from qfluentwidgets import FluentIcon as FIF
from qframelesswindow import FramelessWindow, StandardTitleBar
from qfluentwidgets import SplashScreen
from src.song_downloader import Song
from src.sort_songs import SortSongs
from src.normalize_audio import NormalizeAudio


from spotdl.utils.ffmpeg import is_ffmpeg_installed
from src.ffmpeg_utils import download_ffmpeg, download_ffprobe, is_ffprobe_installed


class Widget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)

        # Create a QLabel for the logo
        self.logo = ImageLabel('resource/logo.png')
        self.logo.scaledToHeight(500)

        # Create a QLabel for the text
        self.label = QLabel(text, self)
        self.label.setAlignment(Qt.AlignCenter)

        # Use a QVBoxLayout and add the logo and label to it
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.addWidget(self.logo, 5, Qt.AlignCenter)
        self.vBoxLayout.addWidget(self.label, 10, Qt.AlignCenter)

        self.setObjectName(text.replace(' ', '-'))



class Window(FramelessWindow):

    def __init__(self):
        super().__init__()
        self.setTitleBar(StandardTitleBar(self))

        # use dark theme mode
        setTheme(Theme.DARK)

        # change the theme color
        #setThemeColor('#0078d4')

        self.hBoxLayout = QHBoxLayout(self)
        self.navigationInterface = NavigationInterface(self, showMenuButton=True)
        self.stackWidget = QStackedWidget(self)

        # create sub interface
        self.songInterface = Song(self)
        self.musicInterface =  NormalizeAudio(self)
        self.folderInterface = SortSongs(self)
        self.homeInterface = Widget('Welcome to SoundVault!', self)
        #self.settingInterface = Widget('Setting Interface', self)

        # initialize layout
        self.initLayout()

        # add items to navigation interface
        self.initNavigation()

        self.initWindow()

        # 4. Hide the splash screen
        self.splashScreen.finish()

    def initLayout(self):
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, self.titleBar.height(), 0, 0)
        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addWidget(self.stackWidget)
        self.hBoxLayout.setStretchFactor(self.stackWidget, 1)

    def initNavigation(self):
        # enable acrylic effect
        # self.navigationInterface.setAcrylicEnabled(True)
        
        self.addSubInterface(self.songInterface, FIF.DOWNLOAD, 'Download Songs')
        self.addSubInterface(self.homeInterface, FIF.HOME, 'Home')
        self.addSubInterface(self.musicInterface, FIF.MUSIC, 'Normalize Audio')        
        self.addSubInterface(self.folderInterface, FIF.FOLDER, 'Sort Songs')

        #self.addSubInterface(self.settingInterface, FIF.SETTING, 'Settings', NavigationItemPosition.BOTTOM)

        # add navigation items to scroll area

        
        # for i in range(1, 21):
        #     self.navigationInterface.addItem(
        #         f'folder{i}',
        #         FIF.FOLDER,
        #         f'Folder {i}',
        #         lambda: print('Folder clicked'),
        #         position=NavigationItemPosition.SCROLL
        #     )

        # add custom widget to bottom

        

        #!IMPORTANT: don't forget to set the default route key if you enable the return button
        # qrouter.setDefaultRouteKey(self.stackWidget, self.musicInterface.objectName())

        # set the maximum width
        # self.navigationInterface.setExpandWidth(300)

        self.stackWidget.currentChanged.connect(self.onCurrentInterfaceChanged)
        self.stackWidget.setCurrentIndex(1)

        # always expand
        #self.navigationInterface.setCollapsible(False)

    def initWindow(self):
        self.resize(900, 700)
        self.setWindowIcon(QIcon('resource/logo.png'))
        self.setWindowTitle('SoundVault')
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(102, 102))

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

        # NOTE: set the minimum window width that allows the navigation panel to be expanded
        # self.navigationInterface.setMinimumExpandWidth(900)
        # self.navigationInterface.expand(useAni=False)

        self.setQss()

    def addSubInterface(self, interface, icon, text: str, position=NavigationItemPosition.TOP, parent=None):
        """ add sub interface """
        self.stackWidget.addWidget(interface)
        self.navigationInterface.addItem(
            routeKey=interface.objectName(),
            icon=icon,
            text=text,
            onClick=lambda: self.switchTo(interface),
            position=position,
            tooltip=text,
            parentRouteKey=parent.objectName() if parent else None
        )

    def setQss(self):
        color = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/{color}/demo.qss', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def switchTo(self, widget):
        self.stackWidget.setCurrentWidget(widget)

    def onCurrentInterfaceChanged(self, index):
        widget = self.stackWidget.widget(index)
        self.navigationInterface.setCurrentItem(widget.objectName())

        #!IMPORTANT: This line of code needs to be uncommented if the return button is enabled
        # qrouter.push(self.stackWidget, widget.objectName())


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    if not is_ffmpeg_installed():
        os_name = platform.system().lower()
        print("FFmpeg is not installed.")
        if os_name == "windows":
            print("FFmpeg is going to be installed for you. Please wait...")
            try:
                path = download_ffmpeg()
                if path is not None:
                    print('FFmpeg has been installed successfully.')
                else:
                    print('Failed to install FFmpeg.')
                    sys.exit(1)
            except Exception as e:
                print(f'Failed to install FFmpeg: {e}')
                sys.exit(1)
        elif os_name == "linux":
            print("You need to run the following command on your terminal to install FFmpeg:")
            print("sudo apt update")
            print("sudo apt-get install ffmpeg")
        elif os_name == "darwin":
            print("You need to run the following command on your terminal to install FFmpeg:")
            print("brew install ffmpeg")
        else:
            print("FFmpeg is not available for your system.")
        
        print('FFmpeg is going to be installed. Please wait...')
    
    if not is_ffprobe_installed():
        print("FFprobe is not installed.")
        if platform.system().lower() == "windows":
            print("FFprobe is going to be installed for you. Please wait...")
            try:
                if download_ffprobe():
                    print('FFprobe has been installed successfully.')
                else:
                    print('Failed to install FFprobe.')
                    sys.exit(1)
            except Exception as e:
                print(f'Failed to install FFprobe: {e}')
                sys.exit(1)
        else:
            print("Please install it.")
            sys.exit(1)

            
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec_()