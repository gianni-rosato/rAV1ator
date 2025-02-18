# rAV1ator is End-of-life

Thanks for using rAV1ator! Unfortunately, I have decided to discontinue development on this project.

## Why?

For a couple of reasons:

- **rAV1e isn't as competitive as it used to be.** I've since been working on [SVT-AV1-PSY](https://github.com/gianni-rosato/svt-av1-psy/) which has combined rAV1e's usability with SVT-AV1's speed & aomenc's coding efficiency.
- **Granular control over settings isn't as crucial now.** Encoding efficiently with AV1 used to be a laborious process that involved a lot of custom configuration. rAV1ator aimed to bring the flexibility of medium complexity CLI workflows to a GUI, but now that AV1 is more mature, the need for this is lessened as encoders like SVT-AV1-PSY are designed to have strong, versatile defaults. Highly complex workflows involving Vapoursynth have never been in the scope of this project to capture.
- **Av1an isn't as important anymore.** Scene detection used to be considered very important, but SVT-AV1(-PSY) is fast enough where initializing new instances of the encoder for chunked encoding and waiting for scene detection to take place can meaningfully slow down the encoding process without a large quantity of threads. Scene detection also doesn't always offer meaningful compression efficiency gains.
- **Aviator exists.** Aviator is a more modern, efficient, & user-friendly version of rAV1ator that is available now on Flathub. It is based on SVT-AV1-PSY and FFmpeg, and through sustained development effort it has matured into a more complete solution for AV1 encoding than rAV1ator ever was. You can find more info [on the Codec Wiki](https://wiki.x266.mov/docs/utilities/Aviator) or the [GitHub repository](https://github.com/gianni-rosato/aviator).

## What now?

Go ahead and switch to Aviator. If you're looking into the command line, rAV1ator CLI is still maintained. I'll be around to answer questions about the transition, and I'm always open to feedback. Thanks for using rAV1ator <3

<div align="center">
<h1>rAV1ator</h1>

A Flatpak-first easy-to-use GUI for encoding with rav1e & libopus.

<img src="assets/rAV1ator_splash2.avif" alt="Splash" width=450/>
<br>
<br>

[![License](https://img.shields.io/github/license/natesales/q?style=for-the-badge)](https://raw.githubusercontent.com/natesales/q/main/LICENSE)

[![Please do not theme this app](https://stopthemingmy.app/badge.svg)](https://stopthemingmy.app)
</div>

## About

rAV1ator enables simple & easy video encoding for the word's most advanced open video codec, AV1. Encode your favorite media into super efficient files with incredible quality per bit, powered by the fast, memory-safe rav1e encoder with libopus for audio encoding. The sky's the limit for your old home video collection, large 4k smartphone videos, screen recordings, Blu-ray rips, you name it - take off with rAV1ator!

rAV1ator is designed to be a no frills, easy to use AV1 encoding GUI that any beginner can pick up and immediately understand how to use.

## Installation

### Repo

rAV1ator is available in my personal Flatpak repository. Given you have Flatpak on your system, you can install it by running:

```
flatpak --user remote-add --no-gpg-verify project-volo https://giannirosato.com/repo
flatpak --user install project-volo net.natesales.rAV1ator
```

### Building from Source

Make sure you have all required dependencies before building from source. This includes `flatpak-builder`, `python3` & `gcc`

```bash
git clone https://github.com/gianni-rosato/rAV1ator
cd rAV1ator
make
```

Third party packaging formats are not officially supported by rAV1ator, and if you encounter bugs while using them please do not submit them as issues.

## Why AV1?

AV1 aims to be more efficient than HEVC & VP9 by around 30%, and more efficient than h.264 by 50%. Traditionally, a lot of AV1 encoder implementations have been pretty slow compared to competing codecs' encoders, but the Rust-based [rav1e](https://github.com/xiph/rav1e) encoder has seen decent increases in speed recently and is improving more every day. We decided to use rav1e in order to give users a memory-safe AV1 encoder implementation that prioritizes visual quality &amp; "just works," for the most part.

One downside of rav1e is that despite being generally quicker than the libaom AV1 reference encoder, it is quite a bit slower than the SVT-AV1 production encoder. To combat this while maintaining high visual quality, rAV1ator utilizes a tool called [Av1an](https://github.com/master-of-zen/Av1an) that is capable of detecting scene changes in a video & splitting the video into multiple shorter videos (chunks) based on those scene changes, then encoding these chunks in parallel. This works especially well with longer videos. rAV1ator will determine the number of chunks to use based on Av1an's internal chunk allocator, which calculates the number of chunks your system can handle based on your logical CPU cores & the amount of RAM you have available. This can be manually specified as well, if you'd like to push your system harder or allow encoding to take up less system resources. Encoding speed scales with the number of chunks you have, so more chunks is faster but harder on your CPU & memory.

rAV1ator comes bundled with its own version of ffmpeg that is capable decoding videos to detect source information, upscaling & downscaling videos with a number of user configurable scaling algorithms, & encoding audio using the Opus audio codec via libopus.

## Why no Flathub?

Flathub doesn't allow us to use the network at build time to build our dependencies, which makes it impossible to build our app. If you'd prefer, our other app called [Aviator](https://github.com/gianni-rosato/aviator) is available on Flathub with a different encoding framework based on SVT-AV1 & FFmpeg instead of rav1e & Av1an. You can check it out [here](https://beta.flathub.org/apps/net.natesales.Aviator).

## rAV1ator's Defaults

Hovering over most user configurable options in rAV1ator will produce a helpful tooltip that you can look at to make things more clear.

### Video

<img src="assets/rAV1ator_video.webp" alt="rAV1ator Video Settings" width=480/>

When you load a video file into rAV1ator, resolution & audio bitrate are set to match the source as closely as possible. rAV1ator's rav1e speed preset is set to 8 by default, with a default Quantizer level of 80. You can set the Quantizer level from 1 to 255 using the slider, with larger numerical values indicating smaller filesize at the expense of visual quality. Speed 8 offers a good balance between speed & compression efficiency at any Quantizer level; higher values will encode faster at the expense of visual quality, while lower values will encode more efficiently but slower.

The Photon Noise slider allows you to add artifical grain to your video to mimic its natural grain, which applies the artificial grain at decode time as a filter which makes it easier to encode grainy videos at high fidelity. The grain levels are based on ISO noise, so 1 would be equal to ISO 100, 24 equal to ISO 2400, etc.

### Audio

<img src="assets/rAV1ator_audio.webp" alt="rAV1ator Audio Settings" width=480/>

Audio is only reencoded if a bitrate is specified; otherwise it is copied. Audio can be encoded to Opus, which is a highly efficient free audio codec that is often more efficient than competitors like AAC & MP3 audio. Opus reaches audio transparency at around 128kbps for stereo audio.

### Advanced

<img src="assets/rAV1ator_advanced.webp" alt="rAV1ator Advanced Settings" width=480/>

Av1an is a complex tool, and rav1e is a complex encoder. There are probably certain settings that you'd prefer to set manually if you're well versed in either utility, so the option to do so for both is offered here. Your custom settings will override the GUI's parameters & defaults. The amount of workers can also be manually specified here.

### Output

<img src="assets/rAV1ator_output.webp" alt="rAV1ator Output UI" width=480/>

The container your video is stored in is associated with the file extension. rAV1ator offers two options for video output: the Matroska video container & the WebM container. The open-source Matroska container (.MKV) is rAV1ator's default container, a universal multimedia container with widespread video &amp; audio support. WebM is designed for web compatibility &amp; may break subtitles. Both work out of the box with rAV1ator's AV1 video & Opus audio formats, although WebM is disabled if no audio bitrate is set due to the fact that copying the audio stream doesn't guarantee its compatibility with the WebM container.

## Roadmap & Limitations

Currently, rAV1ator may encounter issues with:
- Video streams with subtitles encoding to .webm

These are considered bugs, and we are working on fixing them ASAP. In the meantime, we'd prefer you choose the .mkv container if you are having trouble with subtitles.

In the future, we would like to:
- Add a queue, potentially
- Revamp outputting a file
- Get extra progress &amp error info
- Implement Av1an's --resume and --zones functionality

Let us know if you have any issues in our Issues section. Thank you for using rAV1ator!

## Credits

Actively developed by [Gianni Rosato](https://github.com/gianni-rosato/), and [Trix](https://discordapp.com/users/237665944942411777)
