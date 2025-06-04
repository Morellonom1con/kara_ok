from PyQt5.QtWidgets import QApplication,QMainWindow,QPushButton,QStyle,QFrame,QSlider,QLabel,QOpenGLWidget
from PyQt5.QtCore import Qt,QPropertyAnimation,QPoint,QTimer,QUrl,QTime
from PyQt5.QtGui import QPainter,QColor,QFont,QPolygon
from PyQt5.QtMultimedia import QMediaPlayer,QMediaContent
from OpenGL.GL import *
import numpy as np
import sys
import time

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
    def initializeGL(self):
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

        uniform vec2 u_resolution;
        uniform float u_time;
        uniform float u_spin_amount;
        uniform float u_contrast;
        uniform vec4 u_colour_1;
        uniform vec4 u_colour_2;
        uniform vec4 u_colour_3;

        void main()
        {
            float spin_time = u_time;
            float SPIN_EASE = 0.4; // controlls strength of swirl  

            vec2 screen_coords = uv * u_resolution; // to scale properly

            vec2 pos = (screen_coords - 0.5 * u_resolution) / length(u_resolution) - vec2(0.0, 0.0); // last part is the center offset
            float uv_len = length(pos);

            float speed = (spin_time * SPIN_EASE * 0.2) + 302.2;
            float angle = atan(pos.y, pos.x) + speed - SPIN_EASE * 20.0 * (u_spin_amount * uv_len + (1.0 - u_spin_amount));
            vec2 mid = (u_resolution / length(u_resolution)) / 2.0;

            pos = vec2(uv_len * cos(angle) + mid.x, uv_len * sin(angle) + mid.y) - mid;

            // Paint swirl
            pos *= 30.0;
            speed = u_time * 2.0;
            vec2 uv2 = vec2(pos.x + pos.y);

            for (int i = 0; i < 5; ++i) {
                uv2 += sin(max(pos.x, pos.y)) + pos;
                pos += 0.5 * vec2(cos(5.1123314 + 0.353 * uv2.y + speed * 0.131121), sin(uv2.x - 0.113 * speed));
                pos -= cos(pos.x + pos.y) - sin(pos.x * 0.711 - pos.y);
            }

            float contrast_mod = (0.25 * u_contrast + 0.5 * u_spin_amount + 1.2);
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

        # Check for compile errors
        if glGetShaderiv(shader, GL_COMPILE_STATUS) != GL_TRUE:
            raise RuntimeError(glGetShaderInfoLog(shader).decode())
        return shader

    def paintGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self.shader_program)

        # time and resolution
        elapsed=time.time()-self.start_time
        glUniform1f(glGetUniformLocation(self.shader_program, "u_time"), elapsed)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_spin_amount"), 0.6)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_contrast"),3)
        glUniform2f(glGetUniformLocation(self.shader_program, "u_resolution"), self.width(), self.height())

        # your 3 color inputs
        glUniform4f(glGetUniformLocation(self.shader_program, "u_colour_1"), 0.5, 1.0, 0.7, 1.0)#outer color
        glUniform4f(glGetUniformLocation(self.shader_program, "u_colour_2"), 0.1, 0.1, 0.1, 1.0)#center color
        glUniform4f(glGetUniformLocation(self.shader_program, "u_colour_3"), 0.0, 0.2, 0.9, 1.0)#dominant middle color

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
        
        self.viewport=GLviewport(self)
        self.music_player=QMediaPlayer(self)
        self.music_player.setVolume(50)
        self.music_player.setMedia(QMediaContent(QUrl.fromLocalFile("/home/bhargav/Downloads/Syn Cole - Feel Good.mp3")))


        self.toggle_btn=TrapezoidButton(self)
        self.toggle_btn.move(self.width()-self.toggle_btn.width(),int(self.height()/2)-50)
        self.toggle_btn.clicked.connect(self.toggle_menu)

        self.menu_width=200
        self.side_menu=QFrame(self)
        self.side_menu.setGeometry(self.width(),0,self.menu_width,self.height())
        self.side_menu.setStyleSheet("background-color: #444;")

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

    def toggle_play(self):
        self.isplaying=not (self.isplaying)
        if(self.isplaying==False):
            self.music_player.pause()
            self.play_button.setText("⏵")
        else:
            self.music_player.play()
            self.play_button.setText("⏸")
            
    def on_duration_change(self, dur):
        self.player_duration = QTime(0, 0).addMSecs(dur)
        self.play_slider.setMaximum(dur)
        self.update_play_time_label()

    def on_position_change(self, pos):
        self.player_position = QTime(0, 0).addMSecs(pos)
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
        self.viewport.setGeometry(0,0,self.width(),self.height()-15)
        if self.menu_visible:
            self.side_menu.setGeometry(self.width() - self.menu_width, 0, self.menu_width, self.height())
            x = self.width() - self.menu_width - self.toggle_btn.width()
        else:
            self.side_menu.setGeometry(self.width(), 0, self.menu_width, self.height())
            x = self.width() - self.toggle_btn.width()

        self.toggle_btn.move(x, int(self.height() / 2) - self.toggle_btn.height() // 2)
        
        self.player_menu.setGeometry(0, self.height() - self.player_height, self.width(), self.player_height)
        self.play_slider.setGeometry(50,15,self.player_menu.width()-50-10-100-40,20)
        self.play_time.setGeometry(50+10+self.play_slider.width(),15,100,20)

        self.volume_button.move(self.width() - 40, 10)
        self.volume_slider_frame.move(self.width() - 42, self.player_menu.y() - 123)

        super().resizeEvent(event)


app=QApplication(sys.argv)
window=MainWindow()
window.show()
sys.exit(app.exec())

