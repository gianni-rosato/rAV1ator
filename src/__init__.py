import logging
import sys
import threading
import subprocess
import gi
import json
import os
import time
import shutil

from pathlib import Path
from gettext import gettext as _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio

Adw.init()

from . import info

BASE_DIR = Path(__file__).resolve().parent

app_id = "net.natesales.rAV1ator"

def humanize(seconds):
    seconds = round(seconds)
    words = ["year", "day", "hour", "minute", "second"]

    if not seconds:
        return "now"
    else:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        y, d = divmod(d, 365)

        time = [y, d, h, m, s]

        duration = []

        for x, i in enumerate(time):
            if i == 1:
                duration.append(f"{i} {words[x]}")
            elif i > 1:
                duration.append(f"{i} {words[x]}s")

        if len(duration) == 1:
            return duration[0]
        elif len(duration) == 2:
            return f"{duration[0]} and {duration[1]}"
        else:
            return ", ".join(duration[:-1]) + " and " + duration[-1]

# metadata returns the file's resolution and audio bitrate
def metadata(file): 
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file,
        ]
        logging.debug("Running ffprobe: " + " ".join(cmd))
        x = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
        m = json.loads(x)
        streams = m["streams"]
        video = streams[0]

        return video["width"], video["height"]
    except Exception as e:
        logging.error("Get metadata:", e)
        return None, None
    
def notify(text):
    application = Gtk.Application.get_default()
    notification = Gio.Notification.new(title="rAV1ator")
    notification.set_body(text)
    application.send_notification(None, notification)


def first_open():
    startup_file = os.path.join(Path.home(), ".var/app/net.natesales.rAV1ator/startup.dat")
    if os.path.exists(startup_file):
        return False
    else:
        with open(startup_file, "w") as f:
            f.write("\n")
        return True


class FileSelectDialog(Gtk.FileChooserDialog):
    home = Path.home()

    def __init__(self, parent, select_multiple, label, selection_text, open_only, callback=None):
        super().__init__(transient_for=parent, use_header_bar=True)
        self.select_multiple = select_multiple
        self.label = label
        self.callback = callback
        self.set_action(action=Gtk.FileChooserAction.OPEN if open_only else Gtk.FileChooserAction.SAVE)
        self.set_title(title="Select " + selection_text + " files" if self.select_multiple else "Select " + selection_text + " file")
        self.set_modal(modal=True)
        self.set_select_multiple(select_multiple=self.select_multiple)
        self.connect("response", self.dialog_response)
        self.set_current_folder(Gio.File.new_for_path(path=str(self.home)))

        self.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Select", Gtk.ResponseType.OK
        )
        btn_select = self.get_widget_for_response(response_id=Gtk.ResponseType.OK)
        btn_select.get_style_context().add_class(class_name="suggested-action")
        btn_cancel = self.get_widget_for_response(response_id=Gtk.ResponseType.CANCEL)
        btn_cancel.get_style_context().add_class(class_name="destructive-action")

        self.show()

    def dialog_response(self, widget, response):
        if response == Gtk.ResponseType.OK:
            if self.select_multiple:
                gliststore = self.get_files()
                for glocalfile in gliststore:
                    print(glocalfile.get_path())
            else:
                glocalfile = self.get_file()
                # print(glocalfile.get_path())
                self.label.set_label(glocalfile.get_path())
        if self.callback is not None:
            self.callback()
        widget.close()

@Gtk.Template(filename=str(BASE_DIR.joinpath('startup.ui')))
class OnboardWindow(Adw.Window):
    __gtype_name__ = "OnboardWindow"

    image = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image.set_from_file(
            filename=str(
                BASE_DIR.joinpath('net.natesales.rAV1ator-splash.png')
            )
        )

    @Gtk.Template.Callback()
    def go(self, button):
        app.win = MainWindow(application=app)
        app.win.present()
        self.destroy()


@Gtk.Template(filename=str(BASE_DIR.joinpath("window.ui")))
class MainWindow(Adw.Window):
    __gtype_name__ = "rAV1atorWindow"

    # Video page
    source_file_label = Gtk.Template.Child()
    resolution_width_entry = Gtk.Template.Child()
    resolution_height_entry = Gtk.Template.Child()
    scaling_method = Gtk.Template.Child()
    warning_image = Gtk.Template.Child()
    quantizer_scale = Gtk.Template.Child()
    speed_scale = Gtk.Template.Child()
    chroma_switch = Gtk.Template.Child()
    grain_scale = Gtk.Template.Child()

    # Audio page
    bitrate_entry = Gtk.Template.Child()
    vbr_switch = Gtk.Template.Child()
    downmix_switch = Gtk.Template.Child()

    # Advanced page
    av1an_entry = Gtk.Template.Child()
    rav1e_entry = Gtk.Template.Child()
    workers_entry = Gtk.Template.Child()

    # Export page
    output_file_label = Gtk.Template.Child()
    container_mkv_button = Gtk.Template.Child()
    container_webm_button = Gtk.Template.Child()
    container = "mkv"
    encode_button = Gtk.Template.Child()
    encoding_spinner = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    progress_bar = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Default to MKV
        self.container_webm_button.set_has_frame(False)
        self.container_mkv_button.set_has_frame(True)
        self.container = "mkv"

        # Reset value to remove extra decimal
        self.speed_scale.set_value(0)
        self.speed_scale.set_value(8)
        self.quantizer_scale.set_value(0)
        self.quantizer_scale.set_value(80)
        self.grain_scale.set_value(0)
        self.grain_scale.set_value(2)

        # resolution and audio bitrate
        self.metadata: (float, float) = ()

        # Absolute source path file
        self.source_file_absolute = ""

        # Set progress bar to 0
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_text("0%")
        self.process = None

    def load_metadata(self):
        self.metadata = metadata(self.source_file_absolute)

    @Gtk.Template.Callback()
    def on_scale_value_changed(self, scale):
        value = int(scale.get_value())
        if value > 100:
            self.warning_image.set_visible(True)
        else:
            self.warning_image.set_visible(False)

    @Gtk.Template.Callback()
    def empty_or_not_empty(self, entry):
        if self.bitrate_entry.get_text() == "":
            self.container_webm_button.set_sensitive(False)
        else:
            self.container_webm_button.set_sensitive(True)

    def handle_file_select(self):

        # Trim file path
        if "/" in self.source_file_label.get_text():
            self.source_file_absolute = self.source_file_label.get_text()
            self.source_file_label.set_text(os.path.basename(self.source_file_absolute))
            self.load_metadata()

    # Video

    @Gtk.Template.Callback()
    def open_source_file(self, button):
        FileSelectDialog(
            parent=self,
            select_multiple=False,
            label=self.source_file_label,
            selection_text="source",
            open_only=True,
            callback=self.handle_file_select
        )

    # Export

    @Gtk.Template.Callback()
    def open_output_file(self, button):
        FileSelectDialog(
            parent=self,
            select_multiple=False,
            label=self.output_file_label,
            selection_text="output",
            open_only=False,
        )

    @Gtk.Template.Callback()
    def container_mkv(self, button):
        self.container_webm_button.set_has_frame(False)
        self.container_mkv_button.set_has_frame(True)
        self.container = "mkv"

    @Gtk.Template.Callback()
    def container_webm(self, button):
        self.container_mkv_button.set_has_frame(False)
        self.container_webm_button.set_has_frame(True)
        self.container = "webm"

    @Gtk.Template.Callback()
    def start_export(self, button):
        self.encode_button.set_visible(False)
        self.encoding_spinner.set_visible(True)
        self.stop_button.set_visible(True)

        output = self.output_file_label.get_text()
        if self.container == "mkv" and not output.endswith(".mkv"):
            output += ".mkv"
        elif self.container == "webm" and not output.endswith(".webm"):
            output += ".webm"

        def run_in_thread():
            encode_start = time.time()

            try:
                workers_specified = int(self.workers_entry.get_text())
                workers = f"{workers_specified}"
            except ValueError:
                workers = "0"

            try:
                audioparams1 = f"-c:a libopus -b:a {self.bitrate_entry.get_text()}K -compression_level 10 -vbr " + "on" if self.vbr_switch.get_state() else "off"
                audioparams2 = "-ac 2" if self.downmix_switch.get_state() else ""

                audioparams = " ".join([audioparams1, audioparams2])
            except:
                audioparams = "-c:a copy"

            width = height = None

            try:
                width = int(self.resolution_width_entry.get_text())
            except ValueError:
                pass

            try:
                height = int(self.resolution_height_entry.get_text())
            except ValueError:
                pass

            if width is not None and height is None:
                height = -1
            elif width is None and height is not None:
                width = -1

            if self.scaling_method.get_selected_item() == "Lanczos":
                method = "lanczos"
            elif self.scaling_method.get_selected_item() == "Mitchell":
                method = "bicubic:param0=1/3:param1=1/3"
            elif self.scaling_method.get_selected_item() == "Catrom":
                method = "bicubic:param0=0:param1=1/2"
            else:
                method = "bicubic:param0=-1/2:param1=1/4"

            try:
                rav1e_custom = self.rav1e_entry.get_text()
            except:
                rav1e_custom = ""

            try:
                if 0 < height < 1920:
                    tiles = " --tiles 4 " 
            except:
                try:
                    if 0 < int(self.metadata[1]) < 1920:
                        tiles = " --tiles 4 "
                except:
                    tiles = " --tiles 8 "
                
            rav1e_params = f"--speed {int(self.speed_scale.get_value())} --quantizer {int(self.quantizer_scale.get_value())} --threads 2 --keyint 0 --no-scene-detection" + tiles + rav1e_custom

            cmd = [
                "av1an",
                "-i", self.source_file_absolute,
                "-y",
                "--temp", "av1an-cache",
                "--split-method", "av-scenechange",
                "-m", "hybrid",
                "-c", "ffmpeg",
                "-e", "rav1e",
                "--photon-noise", f"{int(self.grain_scale.get_value())}",
                "--force",
                "--video-params", rav1e_params,
                "--pix-format", "yuv420p10le",
                "--audio-params", audioparams,
                "-w", workers,
                "-o", output,
            ]

            if self.chroma_switch.get_active():
                cmd.append("--chroma-noise")
            
            if width is not None or height is not None:
                cmd.append("-f")
                cmd.append(f'-vf scale={width}:{height}:flags={method}')

            try:
                cmd.extend(str(self.av1an_entry.get_text()).split())
            except:
                pass
            
            print(" ".join(cmd))
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                     universal_newlines=True)
            last_update = time.time_ns()
            for line in self.process.stdout:
                print(line.strip())
                tokens = line.strip().split(":")
                if len(tokens) == 2 and (tokens[0] == "Scene Detection" or tokens[0] == "Encoding"):
                    step = tokens[0]
                    frac = tokens[1].split("/")
                    progress = int(frac[0])/int(frac[1])
                    progress = round(progress,2)
                    if time.time_ns() - last_update > 300000000:
                        self.progress_bar.set_fraction(progress)
                        self.progress_bar.set_text(f"{step} ~ {int(progress*100)}%")
                        last_update = time.time_ns()
            self.process.wait()
            self.progress_bar.set_fraction(0)
            if self.process.returncode == 0:
                encode_end = time.time() - encode_start
                notify(f"Encode finished in {humanize(encode_end)}! ✈️")
                self.progress_bar.set_text(f"Encode finished in {humanize(encode_end)}! ✈️ ~ 0%")
                self.stop_button.set_visible(False)
            else:
                notify(f"Encode Stopped")
                self.progress_bar.set_text("Encode Stopped ~ 0%")
                self.stop_button.set_visible(False)

            self.encode_button.set_visible(True)
            self.encoding_spinner.set_visible(False)

        thread = threading.Thread(target=run_in_thread)
        thread.start()

    @Gtk.Template.Callback()
    def stop_encode(self, button):
        print("Killing av1an...")
        if self.process is not None:
            self.process.terminate()
            shutil.rmtree("av1an-cache")
            print("Killed av1an")


class App(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)

        about_action = Gio.SimpleAction(name="about")
        about_action.connect("activate", self.about_dialog)
        self.add_action(about_action)

        quit_action = Gio.SimpleAction(name="quit")
        quit_action.connect("activate", self.quit)
        self.add_action(quit_action)
        #os.system("rav1e --version")

    def on_activate(self, app):
        if first_open():
            startup_window = OnboardWindow(application=self)
            startup_window.present()
        else:
            self.win = MainWindow(application=app)
            self.win.present()

    def about_dialog(self, action, user_data):
        about = Adw.AboutWindow(transient_for=self.win,
                                application_name="rAV1ator",
                                application_icon="net.natesales.rAV1ator",
                                developer_name="Nate Sales, Gianni Rosato & Trix",
                                version=info.version,
                                copyright="Copyright © 2023 Nate Sales &amp; Gianni Rosato",
                                license_type=Gtk.License.GPL_3_0,
                                website="https://github.com/gianni-rosato/rAV1ator/issues",
                                issue_url="https://github.com/gianni-rosato/rAV1ator/issues")
        # about.set_translator_credits(translators())
        about.set_developers(["Nate Sales <nate@natesales.net>","Gianni Rosato <grosatowork@proton.me>", "Trix <>"])
        about.set_designers(["Gianni Rosato <grosatowork@proton.me>", "Trix <>"])
        about.add_acknowledgement_section(
            ("Special thanks to the AV1 Community"),
            [
                "AV1 Discord https://discord.gg/SjumTJEsFD",
            ]
        )
        about.add_acknowledgement_section(
            ("Special thanks to the Av1an dev team"),
            [
                "Av1an Discord https://discord.gg/BwyQp2QX9h",
            ]
        )
        about.add_acknowledgement_section(
            ("Special thanks to the rav1e dev team"),
            [
                "rav1e repository https://github.com/xiph/rav1e",
            ]
        )
        about.add_acknowledgement_section(
            ("Software versions:"),
            [
                str(subprocess.check_output(["av1an", "--version"]).decode("utf-8").strip().splitlines()[0])+f"\n\n"+str(subprocess.check_output(["rav1e", "--version"]).decode("utf-8").strip().splitlines()[0]),
            ]
        )
        about.add_legal_section(
            title='Av1an',
            copyright='Copyright © 2023 Av1an',
            license_type=Gtk.License.GPL_3_0,
        )
        about.add_legal_section(
            title='FFmpeg',
            copyright='Copyright © 2023 FFmpeg',
            license_type=Gtk.License.GPL_3_0,
        )
        about.add_legal_section(
            title='rav1e',
            copyright='Copyright © 2023 xiph.org',
            license_type=Gtk.License.BSD,
        )
        about.present()

    def quit(self, action=None, user_data=None):
        exit()


app = App(application_id=app_id)
app.run(sys.argv)
