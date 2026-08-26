from PyQt5.QtWidgets import QMenu,QActionGroup,QApplication,QMainWindow,QLineEdit,QPushButton,QStyle,QFrame,QSlider,QLabel,QOpenGLWidget,QListWidget,QListWidgetItem,QProgressBar
from PyQt5.QtCore import Qt,QPropertyAnimation,QPoint,QTimer,QUrl,QObject,QTime,Qt,QRunnable, QThreadPool, pyqtSlot,pyqtSignal
from PyQt5.QtGui import QPainter,QColor,QFont,QPolygon
from PyQt5.QtMultimedia import QMediaPlayer,QMediaContent
from OpenGL.GL import *
import numpy as np
import sys
import time
import soundcard as sc
import os
from pathlib import Path
import subprocess
import shutil
from SpotiFLAC import SpotiFLAC



class SongDownloaderSignals(QObject):
    finished = pyqtSignal(str, str, str)  # title, wav_path, lrc_path
    error = pyqtSignal(str)

class SongDownloader(QRunnable):
    def __init__(self, song_url: str, max_retries: int = 3):
        super().__init__()
        self.song_url = song_url
        self.max_retries = max_retries
        self.signals = SongDownloaderSignals()

    @pyqtSlot()
    def run(self):
        current_dir = os.getcwd()
        Path(current_dir, "current_queue").mkdir(exist_ok=True)

        # STEP 0 ── fetch lyrics
        lyr_proc = subprocess.run([
            "node", "lyrics_fetcher.js", self.song_url
        ], check=False)

        if lyr_proc.returncode == 2:
            self.signals.error.emit("🫥 No lyrics available for this track.")
            return
        if lyr_proc.returncode != 0:
            print("💥 Warning: lyrics_fetcher crashed but continuing since JSON likely exists.")

        # Convert JSON ➜ LRC
        try:
            subprocess.run(["node", "json_to_lrc.js"], check=True)
        except subprocess.CalledProcessError:
            self.signals.error.emit("❌ Unable to convert JSON to LRC.")
            return

        # Save list of MP3s before
        prev_mp3s = set(f for f in os.listdir(current_dir) if f.lower().endswith(".mp3"))

        # Retry logic for downloading
        download_success = False
        for attempt in range(1, self.max_retries + 1):
            print(f"📥 Download attempt {attempt}")
            try:
                SpotiFLAC(
                    url=self.song_url,
                    output_dir=current_dir,
                    services=["ext:tidal-web"],
                    transcode_to="mp3",
                    transcode_bitrate="320k",
                )
            except subprocess.CalledProcessError:
                continue

            # Check if a new MP3 has appeared
            new_mp3s = set(f for f in os.listdir(current_dir) if f.lower().endswith(".mp3"))
            diff = new_mp3s - prev_mp3s
            if diff:
                song_mp3 = diff.pop()
                download_success = True
                break
            time.sleep(1)

        if not download_success:
            self.signals.error.emit("❌ Download attempts failed.")
            return

        song_title = Path(song_mp3).stem

        # move LRC to unique file
        # Count existing numbered folders in queue
        queue_dir = Path(current_dir) / "current_queue"
        # Highest slot in use + 1. Counting folders instead would reuse a number
        # after a middle entry is deleted and overwrite a song still in the queue.
        used = [int(f.name) for f in queue_dir.iterdir() if f.is_dir() and f.name.isdigit()]
        counter = (max(used) + 1) if used else 1
        target_dir = queue_dir / str(counter)
        target_dir.mkdir(parents=True, exist_ok=True)

        # The folder is just a slot number, so keep the real name beside it.
        (target_dir / "title.txt").write_text(song_title, encoding="utf-8")

        # Move lyrics.lrc
        src_lrc = Path(current_dir) / "lyrics.lrc"
        dest_lrc = target_dir / "lyrics.lrc"
        if src_lrc.exists():
            src_lrc.rename(dest_lrc)
        else:
            dest_lrc = ""

        # Move original MP3
        src_mp3 = Path(current_dir)/song_mp3
        dest_mp3 = target_dir/"original.mp3"
        src_mp3.rename(dest_mp3)

        # Run spleeter to split vocals + accompaniment into target_dir
        spleeter_cmd = [
            "python3", "-m", "spleeter", "separate",
            "-p", "spleeter:2stems",
            "-o", str(target_dir),
            str(dest_mp3)
        ]
        try:
            subprocess.run(spleeter_cmd,check=True)
        except subprocess.CalledProcessError:
            self.signals.error.emit("❌ Spleeter failed.")
            return

        wav_path = str(target_dir / "original"/"accompaniment.wav")
        self.signals.finished.emit(song_title, wav_path, str(dest_lrc))



if sys.platform.startswith("linux"):
    wayland_display = os.environ.get("WAYLAND_DISPLAY")
    if wayland_display:
        os.environ["QT_QPA_PLATFORM"] = "wayland"
    else:
        os.environ["QT_QPA_PLATFORM"] = "xcb"

samplerate = 48000
blocksize = 1024

loopback = sc.get_microphone(sc.default_speaker().name, include_loopback=True)

mic = loopback.recorder(samplerate=samplerate, blocksize=blocksize)
mic.__enter__()  

def get_volume():
    data = mic.record(numframes=blocksize)
    return np.linalg.norm(data)


class TrapezoidButton(QPushButton):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setFixedSize(20,80)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background-color: transparent; border: none;")
        self.Flipped=False

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width=self.width()
        height=self.height()
        polygon=QPolygon([
            QPoint(0,10),
            QPoint(width,0),
            QPoint(width,height),
            QPoint(0,height-10)
        ])

        painter.setBrush(QColor(68,68,68))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(polygon)

        painter.setPen(QColor(255,255,255))
        painter.setFont(QFont("Arial",12,QFont.Bold))
        if(self.Flipped):
            painter.drawText(self.rect(),Qt.AlignCenter,"›")
        else:
            painter.drawText(self.rect(),Qt.AlignCenter,"‹")    

class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            val = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), event.x(), self.width())
            self.setValue(val)
            self.sliderMoved.emit(val)
        super().mousePressEvent(event)

class GLviewport(QOpenGLWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)
        self.start_time=time.time()
        self.prev_volume = 0.0

    def initializeGL(self):
        if not self.context().isValid():
            print("OpenGL context is not valid!")
            return
        glEnable(GL_DEPTH_TEST)
        self.quad=np.array([
            -1.0, -1.0,
            1.0, -1.0,
            -1.0,  1.0,
            1.0,  1.0,
        ],dtype=np.float32)
        self.VAO=glGenVertexArrays(1)
        self.VBO=glGenBuffers(1)
        glBindVertexArray(self.VAO)
        glBindBuffer(GL_ARRAY_BUFFER,self.VBO)
        glBufferData(GL_ARRAY_BUFFER,self.quad.nbytes,self.quad,GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
        self.vertshader_src = """#version 330 core
        layout(location = 0) in vec2 aPos;
        out vec2 uv;
        void main()
        {
            gl_Position = vec4(aPos, 0.0, 1.0);
            uv = aPos * 0.5 + 0.5;
        }
        """

        self.fragshader_src = """#version 330 core
        in vec2 uv;
        out vec4 FragColor;

        uniform float u_volume;
        uniform vec2 u_resolution;
        uniform float u_time;
        uniform float u_spin_amount;
        uniform float u_contrast;
        uniform vec4 u_colour_1;
        uniform vec4 u_colour_2;
        uniform vec4 u_colour_3;


        float sigmoid(float x) 
        {
            return 1.0 / (1.0 + exp(-x));
        }

        void main()
        {
            float spin_time = u_time;
            float SPIN_EASE = 0.4; // controls strength of swirl  

            vec2 screen_coords = uv * u_resolution; // to scale properly

            vec2 pos = (screen_coords - 0.5 * u_resolution) / length(u_resolution) - vec2(0.0, 0.0); // last part is the center offset
            float uv_len = length(pos);

            float speed = (spin_time * SPIN_EASE * 0.2) + 302.2;
            float angle = atan(pos.y, pos.x) + speed - SPIN_EASE * 20.0 * (u_spin_amount * uv_len + (1.0 - u_spin_amount));
            vec2 mid = (u_resolution / length(u_resolution)) / 2;

            pos = vec2(uv_len * cos(angle) + mid.x, uv_len * sin(angle) + mid.y) - mid;

            // Paint swirl
            pos *= 30.0;
            speed = u_time * 2.0;
            vec2 uv2 = vec2(pos.x + pos.y);

            for (int i = 0; i < 5; ++i) {
                uv2 += sin(max(pos.x, pos.y)) + pos;
                pos += 0.5 * vec2(cos(5.1123314 + 0.353 * uv2.y + speed * 0.131121), sin(uv2.x- 0.113 * speed));
                pos -= cos(pos.x + pos.y) - sin(pos.x * 0.711  - pos.y);
            }

            float contrast_mod = (0.25 * u_contrast + 0.5 * u_spin_amount + 1.2+pow(1.08,u_volume)/8);
            float paint_res = min(2.0, max(0.0, length(pos) * 0.035 * contrast_mod));
            float c1p = max(0.0, 1.0 - contrast_mod * abs(1.0 - paint_res));
            float c2p = max(0.0, 1.0 - contrast_mod * abs(paint_res));
            float c3p = 1.0 - min(1.0, c1p + c2p);

            vec4 col = (0.3 / u_contrast) * u_colour_1 +
                    (1.0 - 0.3 / u_contrast) *
                    (u_colour_1 * c1p + u_colour_2 * c2p + vec4(c3p * u_colour_3.rgb, c3p * u_colour_1.a));

            FragColor = col;
        }

        """

        vert =self.compile_shader(self.vertshader_src, GL_VERTEX_SHADER)
        frag =self.compile_shader(self.fragshader_src, GL_FRAGMENT_SHADER)

        self.shader_program = glCreateProgram()
        glAttachShader(self.shader_program, vert)
        glAttachShader(self.shader_program, frag)
        glLinkProgram(self.shader_program)
    
        glDeleteShader(vert)
        glDeleteShader(frag)

    def compile_shader(self,source, shader_type):
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)

        if glGetShaderiv(shader, GL_COMPILE_STATUS) != GL_TRUE:
            raise RuntimeError(glGetShaderInfoLog(shader).decode())
        return shader

    def paintGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self.shader_program)

        # time and resolution
        elapsed=time.time()-self.start_time
        raw_volume = get_volume()
        alpha=0.5
        smoothed = (1 - alpha) * self.prev_volume + alpha * raw_volume
        self.prev_volume = smoothed  # Store for next frame
        
        glUniform1f(glGetUniformLocation(self.shader_program, "u_volume"), smoothed)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_time"), elapsed)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_spin_amount"), 0.6)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_contrast"),2)
        glUniform2f(glGetUniformLocation(self.shader_program, "u_resolution"), self.width(), self.height())

        glUniform4f(glGetUniformLocation(self.shader_program, "u_colour_1"), 0.2, 1.0, 0.7, 1.0)
        glUniform4f(glGetUniformLocation(self.shader_program, "u_colour_2"), 0.1, 0.1, 0.1, 1.0)
        glUniform4f(glGetUniformLocation(self.shader_program, "u_colour_3"), 0.0, 0.2, 0.7, 1.0)


        glBindVertexArray(self.VAO)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        glBindVertexArray(0)
        glUseProgram(0)

    def resizeGL(self, w, h):
        pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Kara_ok")
        self.setGeometry(500,250,800,600)

        self.lyrics_font_size = None  # None -> scale with the window
        self.lyrics_delay = 0         # ms, positive shows lyrics earlier
        self.lyrics = []  # Store list of (time_ms, text)
        self.current_lyric_index = 0
        self.music_queue = []
        self.active_downloads = 0
        self.threadpool = QThreadPool()
        self.viewport=GLviewport(self)
        self.setCentralWidget(self.viewport)
        self.music_player=QMediaPlayer(self)
        self.music_player.setVolume(50)
        self.music_player.positionChanged.connect(self.update_lyrics)
        self.music_player.stateChanged.connect(self.on_state_change)
       
        self.toggle_btn=TrapezoidButton(self)
        self.toggle_btn.move(self.width()-self.toggle_btn.width(),int(self.height()/2)-50)
        self.toggle_btn.clicked.connect(self.toggle_menu)
        self.toggle_btn.raise_()

        self.lyric_window=QLabel(self)
        self.lyric_window.setText("Lyrics go here")
        self.lyric_window.setAlignment(Qt.AlignCenter)
        self.lyric_window.setWordWrap(True)

        self.menu_width=300
        self.side_menu=QFrame(self)
        self.side_menu.setGeometry(self.width(),self.menuBar().height(),self.menu_width,self.height())
        self.side_menu.setStyleSheet("background-color: #444;")
        
        self.add_button=QPushButton(self.side_menu)
        self.add_button.setText("+")
        self.link_field=QLineEdit(self.side_menu)
        self.link_field.setPlaceholderText("Paste a Spotify track link")
        self.link_field.setStyleSheet("background-color:white;")
        self.link_field.returnPressed.connect(self.on_add)
        self.add_button.clicked.connect(self.on_add)

        self.progress_bar = QProgressBar(self.side_menu)
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.hide()

        self.queue_list = QListWidget(self.side_menu)
        self.queue_list.setTextElideMode(Qt.ElideRight)  # song names are long
        self.queue_list.setStyleSheet("""
        QListWidget {
            background-color: #333;
            color: white;
            border: none;
            outline: none;
        }
        QListWidget::item { padding: 6px 4px; }
        QListWidget::item:selected { background-color: #666; }
        QListWidget::item:hover { background-color: #555; }
        """)
        self.queue_list.itemClicked.connect(self.load_from_queue)

        self.player_menu=QFrame(self)

        self.play_button=QPushButton(self.player_menu)
        self.play_button.setText("⏵")
        self.play_button.clicked.connect(self.toggle_play)
        self.play_button.setStyleSheet("font-size: 14px;color:white;font-weight:bold")

        self.play_slider=ClickableSlider(Qt.Horizontal,self.player_menu)
        self.play_slider.sliderMoved.connect(self.music_player.setPosition)

        self.player_position = QTime(0, 0)
        self.player_duration = QTime(0, 0)
        self.music_player.durationChanged.connect(self.on_duration_change)
        self.music_player.positionChanged.connect(self.on_position_change)
        self.play_time=QLabel(f"{self.player_position.toString('mm:ss')} / {self.player_duration.toString('mm:ss')}",self.player_menu)
        self.play_time.setStyleSheet("color: white")
        self.player_height=50

        self.player_menu.setGeometry(0,self.height()-self.player_height,self.width(),self.player_height)
        self.play_button.setGeometry(10,10,30,30)
        self.play_slider.setGeometry(50,15,self.player_menu.width()-50-10-100-40,20)
        self.play_time.setGeometry(50+10+self.play_slider.width(),15,100,20)
        
        self.player_menu.setStyleSheet("background-color: #444")
        self.isplaying=False

        self.volume_button = QPushButton("🔊", self.player_menu)
        self.volume_button.setGeometry(self.width() - 40, 10, 30, 30)
        self.volume_button.setStyleSheet("color: white; font-size: 14px;")
        self.volume_button.clicked.connect(self.toggle_volume_slider)

        self.volume_slider_frame=QFrame(self)
        self.volume_slider = QSlider(Qt.Vertical, self.volume_slider_frame)
        self.volume_slider.setStyleSheet("""
        QSlider::groove:vertical {
            background: #666;
            width: 6px;
            border-radius: 3px;
        }

        QSlider::handle:vertical {
            background: white;
            border: 1px solid #000;
            height: 4px;
            margin: -1px;
            border-radius: 8px;
        }

        QSlider::sub-page:vertical {
            background: #333;
            border-radius: 3px;
        }

        QSlider::add-page:vertical {
            background: #bbb;
            border-radius: 3px;
        }
        """)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.music_player.volume())
        self.volume_slider_frame.setGeometry(self.width() - 40, 10, 34, 120) 
        self.volume_slider_frame.setStyleSheet("background-color: #666;border-radius:12px;") 
        self.volume_slider_frame.hide()
        self.volume_slider.setGeometry(2,10,30,100)
        self.volume_slider.valueChanged.connect(self.music_player.setVolume)

        self.btn_anim=QPropertyAnimation(self.toggle_btn,b"geometry")
        self.btn_anim.setDuration(150)
        self.menu_anim=QPropertyAnimation(self.side_menu,b"geometry")
        self.menu_anim.setDuration(150)
        
        self.menu_visible=False
        self.build_menus()
        self.sync_queue_from_disk()

    def build_menus(self):
        options_menu = self.menuBar().addMenu("Options")

        # Font size: "Auto" tracks the window, the rest are fixed pixel sizes.
        font_menu = options_menu.addMenu("Lyrics Size")
        font_group = QActionGroup(self)
        font_group.setExclusive(True)
        for label, size in [("Auto (fit window)", None), ("Small", 48),
                            ("Medium", 72), ("Large", 96), ("Huge", 128)]:
            action = font_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(size == self.lyrics_font_size)
            action.triggered.connect(lambda checked, s=size: self.set_lyrics_font_size(s))
            font_group.addAction(action)

        # Offset: positive values pull the lyrics ahead of the audio.
        offset_menu = options_menu.addMenu("Lyrics Offset")
        offset_group = QActionGroup(self)
        offset_group.setExclusive(True)
        for label, ms in [("Later 500 ms", -500), ("Later 250 ms", -250),
                          ("In sync", 0),
                          ("Earlier 250 ms", 250), ("Earlier 500 ms", 500),
                          ("Earlier 750 ms", 750), ("Earlier 1000 ms", 1000)]:
            action = offset_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(ms == self.lyrics_delay)
            action.triggered.connect(lambda checked, d=ms: self.set_lyrics_delay(d))
            offset_group.addAction(action)

    def apply_lyrics_style(self):
        size = self.lyrics_font_size or int(self.height() / 8)
        self.lyric_window.setStyleSheet(f"color:white;font-size:{size}px;")

    def set_lyrics_font_size(self, size):
        self.lyrics_font_size = size
        self.apply_lyrics_style()
        print(f"🎵 Lyrics size set to {size or 'auto'}")

    def set_lyrics_delay(self, delay_ms):
        self.lyrics_delay = delay_ms
        print(f"⏱ Lyrics offset set to {delay_ms}ms")

    def sync_queue_from_disk(self):
        self.queue_list.clear()
        self.music_queue.clear()
        
        queue_dir = Path(os.getcwd()) / "current_queue"
        if not queue_dir.exists():
            return
        
        # Numbered slots first and in order, anything else last, never crashing.
        def slot(folder):
            return (0, int(folder.name)) if folder.name.isdigit() else (1, 0)

        for folder in sorted((f for f in queue_dir.iterdir() if f.is_dir()), key=slot):
            wav_path = folder / "original" / "accompaniment.wav"
            lrc_path = folder / "lyrics.lrc"
            if not wav_path.exists():
                continue

            title_file = folder / "title.txt"
            title = ""
            if title_file.exists():
                title = title_file.read_text(encoding="utf-8").strip()
            self.add_queue_item(title or folder.name, str(wav_path), str(lrc_path), str(folder))

    def add_queue_item(self, title, wav_path, lrc_path, folder_path):
        item = QListWidgetItem(title)
        item.setToolTip(title)  # the panel elides long names
        item.setData(Qt.UserRole, (wav_path, lrc_path, folder_path))
        self.queue_list.addItem(item)
        self.music_queue.append({"title": title, "wav": wav_path, "lrc": lrc_path})

    def start_download(self, song_url):
        if not song_url:
            return
        downloader = SongDownloader(song_url)
        downloader.signals.finished.connect(self.on_download_complete)
        downloader.signals.error.connect(self.on_download_error)
        self.threadpool.start(downloader)
        self.active_downloads += 1
        self.progress_bar.show()
        self.link_field.clear()

    def download_finished(self):
        # Keep the bar up while any other download is still running.
        self.active_downloads = max(0, self.active_downloads - 1)
        if self.active_downloads == 0:
            self.progress_bar.hide()

    def on_download_error(self, msg):
        print(msg)
        self.download_finished()

    def on_download_complete(self, title, wav_path, lrc_path):
        self.download_finished()
        self.add_queue_item(title, wav_path, lrc_path, str(Path(wav_path).parent.parent))
        print(f"✅ Added '{title}' to queue.")

    def update_lyrics(self, pos):
        if not self.lyrics:
            return

        pos += self.lyrics_delay  # Apply delay

        # backward scrub
        while self.current_lyric_index > 0 and self.lyrics[self.current_lyric_index][0] > pos:
            self.current_lyric_index -= 1

        # forward
        while (self.current_lyric_index + 1 < len(self.lyrics) and
               self.lyrics[self.current_lyric_index + 1][0] <= pos):
            self.current_lyric_index += 1

        self.lyric_window.setText(self.lyrics[self.current_lyric_index][1])

    def load_from_queue(self, item):
        wav_path, lrc_path, _ = item.data(Qt.UserRole)
        self.music_player.setMedia(QMediaContent(QUrl.fromLocalFile(wav_path)))

        self.lyrics.clear()
        self.current_lyric_index = 0
        self.lyric_window.setText("♪")

        try:
            with open(lrc_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("[") and "]" in line:
                        parts = line.strip().split("]")
                        for i in range(len(parts) - 1):
                            timestamp = parts[i][1:]
                            lyric_text = parts[-1]
                            time_parts = timestamp.split(":")
                            if len(time_parts) == 2:
                                minutes = int(time_parts[0])
                                seconds = float(time_parts[1])
                                time_ms = int((minutes * 60 + seconds) * 1000)
                                self.lyrics.append((time_ms, lyric_text))
            self.lyrics.sort()
        except (FileNotFoundError, OSError):
            pass

        if not self.lyrics:
            self.lyric_window.setText("Lyrics not found.")

        self.music_player.play()

    def toggle_play(self):
        if self.music_player.state() == QMediaPlayer.PlayingState:
            self.music_player.pause()
        else:
            self.music_player.play()

    def on_state_change(self, state):
        # The button mirrors the player, so picking a song from the queue or a
        # track ending on its own keeps the icon honest.
        self.isplaying = state == QMediaPlayer.PlayingState
        self.play_button.setText("⏸" if self.isplaying else "⏵")

    def on_add(self):
        self.start_download(self.link_field.text())
            
    def on_duration_change(self, dur):
        self.player_duration = QTime(0, 0).addMSecs(dur)
        self.play_slider.setMaximum(dur)
        self.update_play_time_label()

    def on_position_change(self, pos):
        self.player_position = QTime(0, 0).addMSecs(pos)
        if not self.play_slider.isSliderDown():  # don't fight an active drag
            self.play_slider.setValue(pos)
        self.update_play_time_label()
    
    def toggle_volume_slider(self):
        if self.volume_slider.isVisible():
            self.volume_slider_frame.hide()
        else:
            self.volume_slider_frame.show()


    def update_play_time_label(self):
        current = self.player_position.toString('mm:ss') if hasattr(self, 'player_position') else "00:00"
        total = self.player_duration.toString('mm:ss') if hasattr(self, 'player_duration') else "00:00"
        self.play_time.setText(f"{current} / {total}")


    def toggle_menu(self):
        if self.menu_visible:
            self.menu_anim.setStartValue(self.side_menu.geometry())
            self.menu_anim.setEndValue(self.side_menu.geometry().translated(self.menu_width,0))
            self.btn_anim.setStartValue(self.toggle_btn.geometry())
            self.btn_anim.setEndValue(self.toggle_btn.geometry().translated(self.menu_width,0))
        else:
            self.menu_anim.setStartValue(self.side_menu.geometry())
            self.menu_anim.setEndValue(self.side_menu.geometry().translated(-self.menu_width,0))
            self.btn_anim.setStartValue(self.toggle_btn.geometry())
            self.btn_anim.setEndValue(self.toggle_btn.geometry().translated(-self.menu_width,0))
        
        self.menu_anim.start()
        self.btn_anim.start()
        self.toggle_btn.Flipped=not self.toggle_btn.Flipped
        self.menu_visible= not self.menu_visible
    
    def resizeEvent(self, event):
        # The panel is a child of the window, not the central widget, so it has
        # to start below the menu bar or the menu bar covers its first row.
        top = self.menuBar().height()
        panel_height = self.height() - top
        if self.menu_visible:
            self.side_menu.setGeometry(self.width() - self.menu_width, top, self.menu_width, panel_height)
            x = self.width() - self.menu_width - self.toggle_btn.width()
        else:
            self.side_menu.setGeometry(self.width(), top, self.menu_width, panel_height)
            x = self.width() - self.toggle_btn.width()

        self.toggle_btn.move(x, int(self.height() / 2) - self.toggle_btn.height() // 2)
        
        self.player_menu.setGeometry(0, self.height() - self.player_height, self.width(), self.player_height)
        self.play_slider.setGeometry(50,15,self.player_menu.width()-50-10-100-40,20)
        self.play_time.setGeometry(50+10+self.play_slider.width(),15,100,20)
        self.lyric_window.setGeometry((self.width() - int(self.width() * 2 / 3)) // 2,int((self.height()-self.player_height) / 4),int(self.width() * 2 / 3),int(self.height() / 2))
        self.apply_lyrics_style()
        self.volume_button.move(self.width() - 40, 10)
        self.volume_slider_frame.move(self.width() - 42, self.player_menu.y() - 123)
        self.toggle_btn.raise_()   
        self.link_field.setGeometry(0, 0, 250, 25)
        self.add_button.setGeometry(255, 0, 40, 25)
        self.progress_bar.setGeometry(0, 30, 295, 10)
        self.queue_list.setGeometry(0, 45, 295, self.side_menu.height() - 45 - self.player_height)
        super().resizeEvent(event)


    def contextMenuEvent(self, event):
        item = self.queue_list.itemAt(self.queue_list.mapFromGlobal(event.globalPos()))
        if item:
            menu = QMenu(self)
            delete_action = menu.addAction("Delete from Queue")
            action = menu.exec_(event.globalPos())
            if action == delete_action:
                _, _, folder_path = item.data(Qt.UserRole)
                try:
                    shutil.rmtree(folder_path)
                    print(f"🗑️ Deleted {folder_path}")
                except Exception as e:
                    print(f"❌ Could not delete: {e}")
                self.sync_queue_from_disk()


app=QApplication(sys.argv)
window=MainWindow()
window.show()
sys.exit(app.exec())

