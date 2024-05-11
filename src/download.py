import json
import os
import click
from spotdl import Spotdl
from spotdl.types.options import DownloaderOptionalOptions
from spotdl.download.downloader import Downloader
from spotdl.download.progress_handler import ProgressHandler, SongTracker
import logging
from spotdl import SpotifyClient


import asyncio

spotdl = None

from spotdl.types.song import Song

@click.command()
@click.option('--output', default=os.path.dirname(os.path.realpath(__file__)), help='The output directory for the downloaded songs.')
@click.option('--format', default='mp3', help='The format of the downloaded songs.')
@click.option('--song_url', prompt='Spotify song URL', help='The Spotify URL of the song to download.')
def download_song(output, format, song_url):
    """
    # Configure logging
    logger = logging.getLogger('spotdl')
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    """
    global spotdl

    downloader_settings: DownloaderOptionalOptions = {'output': output, 'format': format}

    spotdl = Spotdl(client_id='5f573c9620494bae87890c0f08a60293', client_secret='212476d9b0f3472eaa762d90b19b0ba8', downloader_settings=downloader_settings)

    
    spotdl.downloader.progress_handler = ProgressHandler(
        simple_tui=True,
        update_callback=song_update
    )   
    spotdl.downloader.progress_handler.web_ui = True
    try:
        # Fetch song metadata
        def download_song(url):
            print("Starting download")
            try:
                songs = spotdl.search([song_url])
            except Exception as exception:
                print(f"Error fetching song metadata! {exception}")
                return
            
            print("Songs fetched")
            

            # Download Song
            tuples = spotdl.downloader.download_multiple_songs(songs)

            if tuples is not None:
                return True

        download_song(song_url)
    except Exception as exception:
        print(f"Error downloading! {exception}")

    

async def send_update(update):
    """
    Send an update to the client.

    ### Arguments
    - update: The update to send.
    """
    song_id = f'{update["song"]["name"]} - {update["song"]["artists"][0]}'
    progress = update["progress"]
    message = update["message"]

    data = {'song_id' : song_id, 'song_progress' : progress, 'message' : message}
    print(json.dumps(data))

def song_update(progress_handler: SongTracker, message: str):
    """
    Called when a song updates.

    ### Arguments
    - progress_handler: The progress handler.
    - message: The message to send.
    """

    update_message = {
        "song": progress_handler.song.json,
        "progress": round(progress_handler.progress),
        "message": message,
    }

    global spotdl

    asyncio.run_coroutine_threadsafe(
        send_update(update_message), spotdl.downloader.loop
    )

if __name__ == '__main__':
    download_song()