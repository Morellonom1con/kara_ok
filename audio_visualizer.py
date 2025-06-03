from PyQt5.QtWidgets import QApplication,QMainWindow,QPushButton,QFrame,QSlider,QLabel
from PyQt5.QtCore import Qt,QPropertyAnimation,QPoint
from PyQt5.QtGui import QPainter,QColor,QFont,QPolygon
import sys

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
            painter.drawText(self.rect(),Qt.AlignCenter,">")
        else:
            painter.drawText(self.rect(),Qt.AlignCenter,"<")    

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Kara_ok")
        self.setGeometry(500,250,800,600)

        self.toggle_btn=TrapezoidButton(self)
        self.toggle_btn.move(self.width()-self.toggle_btn.width(),int(self.height()/2)-50)
        self.toggle_btn.clicked.connect(self.toggle_menu)

        self.menu_width=200
        self.side_menu=QFrame(self)
        self.side_menu.setGeometry(self.width(),0,self.menu_width,self.height())
        self.side_menu.setStyleSheet("background-color: #444;")

        self.player_menu=QFrame(self)
        self.play_button=QPushButton(self.player_menu)
        self.play_slider=QSlider(Qt.Horizontal,self.player_menu)
        self.play_time=QLabel("00:00 / 00:00",self.player_menu)
        self.play_time.setStyleSheet("color: white")
        self.player_height=50
        self.player_menu.setGeometry(0,self.height()-self.player_height,self.width(),self.player_height)
        self.play_button.setGeometry(10,10,30,30)
        self.play_slider.setGeometry(50,15,self.player_menu.width()-50-10-100,20)
        self.play_time.setGeometry(50+10+self.play_slider.width(),15,100,20)
        
        self.player_menu.setStyleSheet("background-color: #444")

        self.btn_anim=QPropertyAnimation(self.toggle_btn,b"geometry")
        self.btn_anim.setDuration(150)
        self.menu_anim=QPropertyAnimation(self.side_menu,b"geometry")
        self.menu_anim.setDuration(150)
        
        self.menu_visible=False

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
        if self.menu_visible:
            self.side_menu.setGeometry(self.width() - self.menu_width, 0, self.menu_width, self.height())
            x = self.width() - self.menu_width - self.toggle_btn.width()
        else:
            self.side_menu.setGeometry(self.width(), 0, self.menu_width, self.height())
            x = self.width() - self.toggle_btn.width()

        self.toggle_btn.move(x, int(self.height() / 2) - self.toggle_btn.height() // 2)

        self.player_menu.setGeometry(0, self.height() - self.player_height, self.width(), self.player_height)
        self.play_slider.setGeometry(50,15,self.player_menu.width()-50-10-100,20)
        self.play_time.setGeometry(50+10+self.play_slider.width(),15,100,20)

        super().resizeEvent(event)


app=QApplication(sys.argv)
window=MainWindow()
window.show()
sys.exit(app.exec())

