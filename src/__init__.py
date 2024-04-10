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
    crop_toggle = Gtk.Template.Child()
    crf_scale = Gtk.Template.Child()
    warning_image_speed = Gtk.Template.Child()
    speed_scale = Gtk.Template.Child()
    toggle_denoise = Gtk.Template.Child()
    grain_scale = Gtk.Template.Child()

    # Advanced page
    workers_entry = Gtk.Template.Child()
    toggle_tune_vq = Gtk.Template.Child()
    toggle_tune_psnr = Gtk.Template.Child()
    toggle_tune_ssim = Gtk.Template.Child()
    toggle_tune_psy = Gtk.Template.Child()
    sharpness_scale = Gtk.Template.Child()
    gop_entry = Gtk.Template.Child()
    toggle_ogop = Gtk.Template.Child()
    varboost_scale = Gtk.Template.Child()
    octile_scale = Gtk.Template.Child()
    toggle_altcurve = Gtk.Template.Child()
    toggle_dlf2 = Gtk.Template.Child()
    qpcomp_scale = Gtk.Template.Child()
    toggle_qm = Gtk.Template.Child()
    qm_min_scale = Gtk.Template.Child()
    qm_max_scale = Gtk.Template.Child()
    toggle_overlays = Gtk.Template.Child()
    toggle_tf = Gtk.Template.Child()
    toggle_cdef = Gtk.Template.Child()
    tile_rows_entry = Gtk.Template.Child()
    tile_cols_entry = Gtk.Template.Child()

    # Audio page
    bitrate_entry = Gtk.Template.Child()
    downmix_switch = Gtk.Template.Child()
    audio_copy_switch = Gtk.Template.Child()
    loudnorm_toggle = Gtk.Template.Child()
    volume_scale = Gtk.Template.Child()

    # Export page
    output_file_label = Gtk.Template.Child()
    container_mkv_button = Gtk.Template.Child()
    container = "mkv"
    encode_button = Gtk.Template.Child()
    encoding_spinner = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    progress_bar = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Add the radio buttons to the group
        self.toggle_tune_psnr.set_group(self.toggle_tune_vq)
        self.toggle_tune_ssim.set_group(self.toggle_tune_vq)
        self.toggle_tune_psy.set_group(self.toggle_tune_vq)

        # Set the initial active radio button & default to Tune 3
        self.toggle_tune_psy.set_active(True)
        self.tune = 3

        # Default to MKV
        self.container_mkv_button.set_has_frame(True)
        self.container = "mkv"

        # Reset value to remove extra decimal
        self.speed_scale.set_value(0)
        self.speed_scale.set_value(6)
        self.crf_scale.set_value(0)
        self.crf_scale.set_value(32)
        self.grain_scale.set_value(0)
        self.grain_scale.set_value(6)
        self.grain_scale.set_value(0)
        self.volume_scale.set_value(0)
        self.volume_scale.set_value(6)
        self.volume_scale.set_value(0)

        # resolution and audio bitrate
        self.metadata: (float, float, float) = ()

        # Absolute source path file
        self.source_file_absolute = ""
        self.output_file_absolute = ""

        # Set progress bar to 0
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_text("0%")
        self.process = None
        self.encode_start = None

    def load_metadata(self):
        self.metadata = metadata(self.source_file_absolute)

    def handle_file_select(self):
        # Trim file path
        if "/" in self.source_file_label.get_text():
            self.source_file_absolute = self.source_file_label.get_text()
            self.source_file_label.set_text(os.path.basename(self.source_file_absolute))

    # Video

    @Gtk.Template.Callback()
    def open_source_file(self, button):
        self.bitrate_entry.set_text(str(112))
        self.gop_entry.set_text(str(240))
        self.tile_cols_entry.set_text(str(1))
        self.tile_rows_entry.set_text(str(1))
        FileSelectDialog(
            parent=self,
            select_multiple=False,
            label=self.source_file_label,
            selection_text="source",
            open_only=True,
            callback=self.handle_file_select
        )

    @Gtk.Template.Callback()
    def speed_changed(self, button):
        if self.speed_scale.get_value() < 3:
            self.warning_image_speed.set_visible(True)
        elif self.speed_scale.get_value() > 2:
            self.warning_image_speed.set_visible(False)
        else:
            self.warning_image_speed.set_visible(True)

    @Gtk.Template.Callback()
    def open_output_file(self, button):
        FileSelectDialog(
            parent=self,
            select_multiple=False,
            label=self.output_file_label,
            selection_text="output",
            open_only=False,
        )

    # Advanced

    @Gtk.Template.Callback()
    def on_tune_vq(self, button):
        self.toggle_tune_vq.set_active(True)
        self.toggle_tune_psnr.set_active(False)
        self.toggle_tune_ssim.set_active(False)
        self.toggle_tune_psy.set_active(False)
        self.tune = 0

    @Gtk.Template.Callback()
    def on_tune_psnr(self, button):
        self.toggle_tune_vq.set_active(False)
        self.toggle_tune_psnr.set_active(True)
        self.toggle_tune_ssim.set_active(False)
        self.toggle_tune_psy.set_active(False)
        self.tune = 1

    @Gtk.Template.Callback()
    def on_tune_ssim(self, button):
        self.toggle_tune_vq.set_active(False)
        self.toggle_tune_psnr.set_active(False)
        self.toggle_tune_ssim.set_active(True)
        self.toggle_tune_psy.set_active(False)
        self.tune = 2

    @Gtk.Template.Callback()
    def on_tune_psy(self, button):
        self.toggle_tune_vq.set_active(False)
        self.toggle_tune_psnr.set_active(False)
        self.toggle_tune_ssim.set_active(False)
        self.toggle_tune_psy.set_active(True)
        self.tune = 3

    # Export

    container = "mkv"

    @Gtk.Template.Callback()
    def start_export(self, button):
        self.encode_button.set_visible(False)
        self.encoding_spinner.set_visible(True)
        self.stop_button.set_visible(True)

        output = self.output_file_label.get_text()
        if not output.endswith(".mkv"):
            output += ".mkv"

        def run_in_thread():
            encode_start = time.time()

            try:
                workers = str(int(self.workers_entry.get_text()))
            except ValueError:
                workers = "0"

            width = height = None

            try:
                width = int(self.resolution_width_entry.get_text())
            except ValueError:
                pass

            try:
                height = int(self.resolution_height_entry.get_text())
            except ValueError:
                pass

            if self.crop_toggle.get_active():
                if width is not None and height is None:
                    height = "ih"
                elif width is None and height is not None:
                    width = "iw"
            else:
                if width is not None and height is None:
                    height = -2
                elif width is None and height is not None:
                    width = -2

            method = "bicubic:param0=0:param1=1/2"

            if width is not None and height is not None:
                resolution = "crop" + f"={width}:{height}" if self.crop_toggle.get_active() else "scale" + f"={width}:{height}:flags={method}"
            else:
                resolution = "-y"

            if self.volume_scale.get_value() == 0:
                if self.loudnorm_toggle.get_active():
                    audio_filters = "loudnorm,aformat=channel_layouts=7.1|6.1|5.1|stereo"
                else:
                    audio_filters = "aformat=channel_layouts=7.1|6.1|5.1|stereo"
            else:
                if self.loudnorm_toggle.get_active():
                    audio_filters = f"loudnorm,volume={int(self.volume_scale.get_value())}dB,aformat=channel_layouts=7.1|6.1|5.1|stereo"
                else:
                    audio_filters = f"volume={int(self.volume_scale.get_value())}dB,aformat=channel_layouts=7.1|6.1|5.1|stereo"

            if self.audio_copy_switch.get_state():
                audiosettings = " ".join([
                    "-c:a", "copy"
                ])
            else:
                audiosettings = " ".join([
                    "-c:a", "libopus",
                    "-mapping_family", "1",
                    "-b:a", self.bitrate_entry.get_text() + "K",
                    "-af", audio_filters,
                    "-ac", "2" if self.downmix_switch.get_state() else "0"
                ])

            crf_value = f"{int(self.crf_scale.get_value())}"
            speed_value = f"{int(self.speed_scale.get_value())}"

            if self.toggle_denoise.get_active():
                grain_denoise = "1"
            else:
                grain_denoise = "0"

            grain_value = str(int(self.grain_scale.get_value()))

            sharpness_lvl = int(self.sharpness_scale.get_value())
            
            if self.toggle_ogop.get_active():
                encoder_opengop = "1"
            else:
                encoder_opengop = "2"

            if self.toggle_altcurve.get_active():
                enc_alt_curve = "1"
            else:
                enc_alt_curve = "0"

            if self.toggle_dlf2.get_active():
                dlf_value = "2"
            else:
                dlf_value = "1"

            varboost_strength = str(int(self.varboost_scale.get_value()))
            octile_lvl = str(int(self.octile_scale.get_value()))
            qp_comp_strength = str(int(self.qpcomp_scale.get_value()))

            if self.toggle_qm.get_state():
                qm_enabled = "1"
            else:
                qm_enabled = "0"

            qm_min_value = str(int(self.qm_min_scale.get_value()))
            qm_max_value = str(int(self.qm_max_scale.get_value()))

            if self.toggle_overlays.get_active():
                overlays_enabled = "1"
            else:
                overlays_enabled = "0"

            if self.toggle_tf.get_active():
                tf_enabled = "1"
            else:
                tf_enabled = "0"

            if self.tile_rows_entry.get_text() == "0":
                tile_rows = "0"
            elif self.tile_rows_entry.get_text() == "1":
                tile_rows = "1"
            elif self.tile_rows_entry.get_text() == "2":
                tile_rows = "2"
            elif self.tile_rows_entry.get_text() == "3":
                tile_rows = "3"
            elif self.tile_rows_entry.get_text() == "4":
                tile_rows = "4"
            elif self.tile_rows_entry.get_text() == "5":
                tile_rows = "5"
            elif self.tile_rows_entry.get_text() == "6":
                tile_rows = "6"
            else:
                tile_rows = "1"
            
            if self.toggle_cdef.get_active():
                cdef_enabled = "1"
            else:
                cdef_enabled = "0"

            if self.tile_cols_entry.get_text() == "0":
                tile_cols = "0"
            elif self.tile_cols_entry.get_text() == "1":
                tile_cols = "1"
            elif self.tile_cols_entry.get_text() == "2":
                tile_cols = "2"
            elif self.tile_cols_entry.get_text() == "3":
                tile_cols = "3"
            elif self.tile_cols_entry.get_text() == "4":
                tile_cols = "4"
            elif self.tile_cols_entry.get_text() == "5":
                tile_cols = "5"
            elif self.tile_cols_entry.get_text() == "6":
                tile_cols = "6"
            else:
                tile_cols = "1"

            if self.gop_entry.get_text == "":
                av1an_gop_size = "240"
            else:
                av1an_gop_size = str(int(self.gop_entry.get_text()))

            videosettings = " ".join([
                "--tune", str(self.tune),
                "--sharpness", str(sharpness_lvl),
                "--keyint", "-1",
                "--lp", "2",
                "--irefresh-type", str(encoder_opengop),
                "--crf", str(crf_value),
                "--preset", str(speed_value),
                "--film-grain", str(grain_value),
                "--film-grain-denoise", str(grain_denoise),
                "--variance-boost-strength", str(varboost_strength),
                "--variance-octile", str(octile_lvl),
                "--enable-alt-curve", str(enc_alt_curve),
                "--qp-scale-compress-strength", str(qp_comp_strength),
                "--enable-dlf", str(dlf_value),
                "--enable-qm", str(qm_enabled),
                "--qm-min", str(qm_min_value),
                "--qm-max", str(qm_max_value),
                "--enable-tf", str(tf_enabled),
                "--enable-cdef", str(cdef_enabled),
                "--enable-overlays", str(overlays_enabled),
                "--tile-rows", str(tile_rows),
                "--tile-columns", str(tile_cols),
            ])

            cmd = [
                "av1an",
                "-y",
                "-i", f"{self.source_file_absolute}",
                "--temp", "av1an-cache",
                "--split-method", "av-scenechange",
                "-m", "hybrid",
                "-c", "ffmpeg",
                "--sc-downscale-height", "1080",
                "-e", "svt-av1",
                "--force",
                "--pix-format", "yuv420p10le",
                "-w", str(workers),
                "-f", f"\"-vf {resolution}\"" if width is not None or height is not None  else "\"-y\"",
                "-a", f"\"{audiosettings}\"",
                "-v", f"\"{videosettings}\"",
                "-x", f"{int(av1an_gop_size)}",
                "-o", str(output),
            ]

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
                notify("Encode Stopped")
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
                                developer_name="AV1 Hypertuning GUI",
                                version=info.version,
                                copyright="Copyright © 2024 Nate Sales &amp; Gianni Rosato",
                                license_type=Gtk.License.GPL_3_0,
                                website="https://github.com/gianni-rosato/rAV1ator",
                                issue_url="https://github.com/gianni-rosato/rAV1ator/issues")
        about.set_developers(["Nate Sales https://natesales.net","Gianni Rosato https://giannirosato.com", "Trix <>"])
        about.set_designers(["Gianni Rosato https://giannirosato.com", "Trix <>"])
        about.add_acknowledgement_section(
            ("Special thanks to the encoding community!"),
            [
                "AV1 For Dummies https://discord.gg/bbQD5MjDr3", "SVT-AV1-PSY Fork https://github.com/gianni-rosato/svt-av1-psy", "Codec Wiki https://wiki.x266.mov/", "Av1an Discord https://discord.gg/BwyQp2QX9h",
            ]
        )
        about.add_legal_section(
            title='Av1an',
            copyright='Copyright © 2024 Av1an',
            license_type=Gtk.License.GPL_3_0,
        )
        about.add_legal_section(
            title='FFmpeg',
            copyright='Copyright © 2024 FFmpeg',
            license_type=Gtk.License.GPL_3_0,
        )
        about.add_legal_section(
            title='SVT-AV1',
            copyright='Copyright © 2024 Alliance for Open Media',
            license_type=Gtk.License.BSD,
        )
        about.present()

    def quit(self, action=None, user_data=None):
        exit()


app = App(application_id=app_id)
app.run(sys.argv)
