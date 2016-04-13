# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from colorama import Fore
from spotify_ripper.utils import *
import os
import time
import spotify
import codecs
import shutil


class PostActions(object):
    tracks_to_remove = []
    fail_log_file = None
    success_tracks = []
    failure_tracks = []

    def __init__(self, args, ripper):
        self.args = args
        self.ripper = ripper

        # create a log file for rip failures
        if args.fail_log is not None:
            _base_dir = base_dir()
            if not path_exists(_base_dir):
                os.makedirs(enc_str(_base_dir))

            encoding = "ascii" if args.ascii else "utf-8"
            self.fail_log_file = codecs.open(os.path.join(
                _base_dir, args.fail_log[0]), 'w', encoding)

    def log_success(self, track):
        self.success_tracks.append(track)

    def log_failure(self, track):
        self.failure_tracks.append(track)
        if self.fail_log_file is not None:
            self.fail_log_file.write(track.link.uri + "\n")

    def end_failure_log(self):
        if self.fail_log_file is not None:
            file_name = self.fail_log_file.name
            self.fail_log_file.flush()
            os.fsync(self.fail_log_file.fileno())
            self.fail_log_file.close()
            self.fail_log_file = None

            if os.path.getsize(enc_str(file_name)) == 0:
                rm_file(file_name)

    def print_summary(self):
        if len(self.success_tracks) + len(self.failure_tracks) <= 1:
            return

        def print_with_bullet(_str):
            if self.args.ascii:
                print(" * " + _str)
            else:
                print(" • " + _str)

        def log_tracks(tracks):
            for track in tracks:
                try:
                    track.load()
                    if (len(track.artists) > 0 and track.artists[0].name
                            is not None and track.name is not None):
                        print_with_bullet(track.artists[0].name + " - " +
                                          track.name)
                    else:
                        print_with_bullet(track.link.uri)
                except spotify.Error as e:
                    print_with_bullet(track.link.uri)
            print("")

        if len(self.success_tracks) > 0:
            print(Fore.GREEN + "\nSuccess Summary (" +
                  str(len(self.success_tracks)) +
                  ")\n" + ("-" * 79) + Fore.RESET)
            log_tracks(self.success_tracks)
        if len(self.failure_tracks) > 0:
            print(Fore.RED + "\nFailure Summary (" +
                  str(len(self.failure_tracks)) +
                  ")\n" + ("-" * 79) + Fore.RESET)
            log_tracks(self.failure_tracks)

    def get_chart_name(self, chart):
        region_mapping = {
            "global": "Global",
            "us": "United States",
            "gb": "United Kingdom",
            "ad": "Andorra",
            "ar": "Argentina",
            "au": "Australia",
            "at": "Austria",
            "be": "Belgium",
            "bo": "Bolivia",
            "br": "Brazil",
            "bg": "Bulgaria",
            "ca": "Canada",
            "cl": "Chile",
            "co": "Colombia",
            "cr": "Costa Rica",
            "cy": "Cyprus",
            "cz": "Czech Republic",
            "dk": "Denmark",
            "do": "Dominican Republic",
            "ec": "Ecuador",
            "sv": "El Salvador",
            "ee": "Estonia",
            "fi": "Finland",
            "fr": "France",
            "de": "Germany",
            "gr": "Greece",
            "gt": "Guatemala",
            "hn": "Honduras",
            "hk": "Hong Kong",
            "hu": "Hungary",
            "is": "Iceland",
            "ie": "Ireland",
            "it": "Italy",
            "lv": "Latvia",
            "lt": "Lithuania",
            "lu": "Luxembourg",
            "my": "Malaysia",
            "mt": "Malta",
            "mx": "Mexico",
            "nl": "Netherlands",
            "nz": "New Zealand",
            "ni": "Nicaragua",
            "no": "Norway",
            "pa": "Panama",
            "py": "Paraguay",
            "pe": "Peru",
            "ph": "Philippines",
            "pl": "Poland",
            "pt": "Portugal",
            "sg": "Singapore",
            "sk": "Slovakia",
            "es": "Spain",
            "se": "Sweden",
            "ch": "Switzerland",
            "tw": "Taiwan",
            "tr": "Turkey",
            "uy": "Uruguay"
        }
        return (chart["recurrence"].title() + " " +
                region_mapping.get(chart["country"], "") + " " +
                ("Top" if chart["type"] == "regional" else "Viral") + " " +
                ("200" if chart["type"] == "regional" else "50"))

    def get_playlist_name(self):
        ripper = self.ripper

        if ripper.current_playlist is not None:
            return ripper.current_playlist.name
        elif ripper.current_album is not None:
            return (ripper.current_album.artist.name + " - " + ripper.current_album.name)
        elif ripper.current_chart is not None:
            return self.get_chart_name(ripper.current_chart)
        else:
            return None

    def create_playlist_m3u(self, tracks):
        args = self.args
        ripper = self.ripper

        name = self.get_playlist_name()
        if name is not None and args.playlist_m3u:
            name = sanitize_playlist_name(to_ascii(name))
            _base_dir = base_dir()
            playlist_path = to_ascii(
                os.path.join(_base_dir, name + '.m3u'))

            print(Fore.GREEN + "Creating playlist m3u file " +
                  playlist_path + Fore.RESET)

            encoding = "ascii" if args.ascii else "utf-8"
            with codecs.open(playlist_path, 'w', encoding) as playlist:
                for idx, track in enumerate(tracks):
                    track.load()
                    if track.is_local:
                        continue
                    _file = ripper.format_track_path(idx, track)
                    if path_exists(_file):
                        playlist.write(os.path.relpath(_file, _base_dir) +
                                       "\n")

    def create_playlist_wpl(self, tracks):
        args = self.args
        ripper = self.ripper

        name = self.get_playlist_name()
        if name is not None and args.playlist_wpl:
            name = sanitize_playlist_name(to_ascii(name))
            _base_dir = base_dir()
            playlist_path = to_ascii(
                os.path.join(_base_dir, name + '.wpl'))

            print(Fore.GREEN + "Creating playlist wpl file " +
                  playlist_path + Fore.RESET)

            encoding = "ascii" if args.ascii else "utf-8"
            with codecs.open(playlist_path, 'w', encoding) as playlist:
                # to get an accurate track count
                track_paths = []
                for idx, track in enumerate(tracks):
                    track.load()
                    if track.is_local:
                        continue
                    _file = ripper.format_track_path(idx, track)
                    if path_exists(_file):
                        track_paths.append(_file)

                playlist.write('<?wpl version="1.0"?>\n')
                playlist.write('<smil>\n')
                playlist.write('\t<head>\n')
                playlist.write('\t\t<meta name="Generator" '
                               'content="Microsoft Windows Media Player -- '
                               '12.0.7601.18526"/>\n')
                playlist.write('\t\t<meta name="ItemCount" content="' +
                               str(len(track_paths)) + '"/>\n')
                playlist.write('\t\t<author>' +
                               ripper.session.user.display_name +
                               '</author>\n')
                playlist.write('\t\t<title>' + name + '</title>\n')
                playlist.write('\t</head>\n')
                playlist.write('\t<body>\n')
                playlist.write('\t\t<seq>\n')
                for _file in track_paths:
                    _file.replace("&", "&amp;")
                    _file.replace("'", "&apos;")
                    playlist.write('\t\t\t<media src="' +
                                   os.path.relpath(_file, _base_dir) +
                                   "\"/>\n")
                playlist.write('\t\t</seq>\n')
                playlist.write('\t</body>\n')
                playlist.write('</smil>\n')

    def clean_up_partial(self):
        ripper = self.ripper

        if ripper.audio_file is not None and path_exists(ripper.audio_file):
            print(Fore.YELLOW + "Deleting partially ripped file" + Fore.RESET)
            rm_file(ripper.audio_file)

    def queue_remove_from_playlist(self, idx):
        ripper = self.ripper

        if self.args.remove_from_playlist:
            if ripper.current_playlist:
                if ripper.current_playlist.owner.canonical_name == \
                        ripper.session.user.canonical_name:
                    self.tracks_to_remove.append(idx)
                else:
                    print(Fore.RED +
                          "This track will not be removed from playlist " +
                          ripper.current_playlist.name + " since " +
                          ripper.session.user.canonical_name +
                          " is not the playlist owner..." + Fore.RESET)
            else:
                print(Fore.RED +
                      "No playlist specified to remove this track from. " +
                      "Did you use '-r' without a playlist link?" + Fore.RESET)

    def remove_tracks_from_playlist(self):
        ripper = self.ripper

        if self.args.remove_from_playlist and \
                ripper.current_playlist and len(self.tracks_to_remove) > 0:
            print(Fore.YELLOW +
                  "Removing successfully ripped tracks from playlist " +
                  ripper.current_playlist.name + "..." + Fore.RESET)

            ripper.current_playlist.remove_tracks(self.tracks_to_remove)

            while ripper.current_playlist.has_pending_changes:
                time.sleep(0.1)

    def remove_offline_cache(self):
        ripper = self.ripper

        if self.args.remove_offline_cache:
            storage_dir = os.path.join(ripper.session.config.settings_location,
                "Storage")
            if path_exists(storage_dir):
                shutil.rmtree(enc_str(storage_dir))

