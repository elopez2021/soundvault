<div align="center">
  <img src="resource/logo.png" alt="Logo" width="300">
  <h1>SoundVault</h1>
</div>

## About

This project is a PyQt5 application designed to enhance your music listening experience. It includes features for downloading songs, sorting them based on your preferences, and normalizing their audio levels for a consistent and enjoyable listening experience. The user interface is simple and intuitive.

## Installation

This project requires Python 3.11. If you don't have Python installed, you can download it from [python.org](https://www.python.org/downloads/).

Once you have Python installed, you can install the project as follows:

```bash
git clone https://github.com/elopez2021/soundvault.git
cd soundvault
pip install -r requirements.txt
```

This tool also requires `ffmpeg` to be installed on your system. You can install it using the following commands:

### On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install ffmpeg
```

### On macOS:
```bash
brew install ffmpeg
```

### On Windows:

You can download `ffmpeg` from the official website [here](https://ffmpeg.org/download.html). After downloading, extract the files and add the `bin` directory to your system's PATH.

The tool can also install `ffmpeg` for you. Just run the program and it will check if `ffmpeg` is installed. If not, it will automatically download and install it for you in the project directory. This feature is currently only available for Windows users.


## Usage

Once you have installed the project, you can run it as follows:

```bash
python main.py
```

## Demo

Here are some screenshots of the application in action:

Home Section:

![image](demo/home.png)

Download Section:

![image](demo/download.png)

Normalize Section:

![image](demo/normalize.png)
![image](demo/normalizing.png)

Sort Section:

![image](demo/sort.png)
![image](demo/sorting.png)

## Disclaimer

This tool is provided for personal use only. As the author of this tool, I do not support the downloading of copyrighted content without the permission of the copyright holder. The user is solely responsible for any use of the tool. I am not responsible for any infringements on the rights of the copyright holders resulting from the use of this tool.

## Credits

This project was made possible just because of the following libraries:

- [spotDL](https://github.com/spotDL/spotify-downloader): A library to download Spotify songs.
- [FluentWidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets.git): A library to create fluent design widgets in PyQt5.
