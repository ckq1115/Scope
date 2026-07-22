import sys
import os
import shutil
import time
import queue
import socket
import numpy as np  
import serial
import serial.tools.list_ports
import csv
from collections import deque
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, \
                             QHBoxLayout, QGridLayout, QComboBox, QPushButton, QLabel, QCheckBox, \
                             QScrollArea, QSpinBox, QDoubleSpinBox, QMessageBox, QLineEdit, QColorDialog, \
                             QSplitter, QFileDialog, QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, \
                             QSizePolicy)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt, QPoint, QPointF, QRectF, QSettings, QByteArray
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QTransform, QPolygonF, QIcon, QPixmap, QMatrix4x4, QVector3D
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt6.QtWidgets import QMdiArea, QMdiSubWindow

if getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

try:
    import OpenGL
    from PyQt6.QtOpenGLWidgets import QOpenGLWidget 
    pg.setConfigOptions(useOpenGL=True)
    GL_STATUS = "   [GPU硬件加速: 开启]"
except Exception as e:
    pg.setConfigOptions(useOpenGL=False)
    GL_STATUS = f"   [警告: CPU渲染模式 ({e})]"

pg.setConfigOption('background', '#151515')
pg.setConfigOption('foreground', '#B0B0B0')
pg.setConfigOptions(antialias=False) 

DARK_STYLE = """
    QMainWindow { background-color: #121212; }
    QWidget { background-color: #1e1e1e; color: #e0e0e0; font-family: 'Microsoft YaHei', Helvetica; }
    QPushButton { background-color: #007acc; border: none; color: white; padding: 6px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    QPushButton:hover { background-color: #0098ff; }
    QPushButton:pressed { background-color: #005999; }
    QPushButton[active="true"] { background-color: #28a745; }
    QPushButton[active="false"] { background-color: #555555; }
    QComboBox { background-color: #2d2d2d; border: 1px solid #3d3d3d; padding: 3px; color: white; border-radius: 4px; min-height: 22px; }
    
    QSpinBox, QDoubleSpinBox { 
        background-color: #2d2d2d; border: 1px solid #3d3d3d; padding: 3px; padding-right: 24px; color: white; border-radius: 4px; min-height: 22px; width: 85px; 
    }
    
    QLineEdit { background-color: #2d2d2d; border: 1px solid #3d3d3d; padding: 2px 4px; color: white; border-radius: 4px; font-size: 12px; }
    QLabel { font-size: 12px; font-weight: bold; }
    QCheckBox { spacing: 4px; font-size: 12px; }
    QScrollArea { border: 1px solid #2d2d2d; background-color: #141414; }
    QSplitter::handle { background-color: #282828; }
    QSplitter::handle:horizontal { width: 5px; }
    
    QTabWidget::pane { border: 1px solid #3d3d3d; background-color: #1a1a1a; border-radius: 4px; }
    QTabBar::tab { background: #2d2d2d; color: #aaaaaa; padding: 6px 12px; border: 1px solid #3d3d3d; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
    QTabBar::tab:selected { background: #1a1a1a; color: #ffffff; font-weight: bold; border-top: 2px solid #007acc; }
    QTextEdit { background-color: #141414; color: #e0e0e0; border: 1px solid #3d3d3d; font-family: 'Consolas'; }
"""
DARK_STYLE += """
    QMdiSubWindow {
        border: 1px solid #3d3d3d;
    }
    QMdiSubWindow::handle {
        background: transparent;
        width: 15px;
        height: 15px;
    }
"""

class MdiTitleBar(QWidget):
    def __init__(self, sub_window):
        super().__init__(sub_window)
        self.sub_window = sub_window
        self._drag_start_global = None
        self._drag_start_pos = None
        self.setObjectName("mdiTitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(26)
        self.setStyleSheet("""
            QWidget#mdiTitleBar {
                background-color: #242424;
                color: #dddddd;
                font-family: 'Microsoft YaHei', Helvetica;
                font-size: 12px;
            }
            QLabel#mdiTitleLabel {
                background: transparent;
                font-weight: bold;
                padding-left: 82px;
                padding-right: 82px;
            }
            QPushButton#titleButton,
            QPushButton#closeButton {
                background-color: transparent;
                border: none;
                color: #cccccc;
                padding: 0;
                border-radius: 0;
                font-size: 12px;
                font-weight: normal;
            }
            QPushButton#titleButton:hover,
            QPushButton#closeButton:hover {
                background-color: #3a3a3a;
                color: #ffffff;
            }
            QPushButton#closeButton:hover {
                background-color: #c42b1c;
                color: #ffffff;
            }
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(0)
        self.title_label = QLabel(sub_window.windowTitle())
        self.title_label.setObjectName("mdiTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.title_label, 0, 0)

        self.btn_min = QPushButton("─")
        self.btn_max = QPushButton("□")
        self.btn_close = QPushButton("×")
        self.btn_close.setObjectName("closeButton")
        buttons = QWidget()
        buttons.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 2, 0, 2)
        buttons_layout.setSpacing(2)
        for btn in (self.btn_min, self.btn_max, self.btn_close):
            if btn is not self.btn_close:
                btn.setObjectName("titleButton")
            btn.setFixedSize(24, 22)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            buttons_layout.addWidget(btn)
        layout.addWidget(buttons, 0, 0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.btn_min.clicked.connect(sub_window.showMinimized)
        self.btn_max.clicked.connect(self.toggle_maximized)
        self.btn_close.clicked.connect(sub_window.close)

    def set_title(self, title):
        self.title_label.setText(title)

    def toggle_maximized(self):
        if self.sub_window.isMaximized():
            self.sub_window.showNormal()
        else:
            self.sub_window.showMaximized()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.sub_window.isMaximized():
            # 如果点击在顶部边缘 GRIP 范围内 → 交给子窗口缩放句柄处理
            if hasattr(self.sub_window, '_get_resize_edge'):
                local_y = event.position().toPoint().y()
                local_x = event.position().toPoint().x()
                w = self.sub_window.width()
                g = self.sub_window.GRIP_SIZE
                edge = None
                if local_y < g:
                    if local_x < g:       edge = 'topleft'
                    elif local_x > w - g: edge = 'topright'
                    else:                 edge = 'top'
                elif local_x < g:          edge = 'left'
                elif local_x > w - g:      edge = 'right'
                if edge is not None:
                    sub = self.sub_window
                    sub._resize_edge = edge
                    sub._resize_start_geo = sub.geometry()
                    sub._resize_start_global = event.globalPosition().toPoint()
                    sub._resizing = True
                    sub._snap_enabled = False
                    event.accept()
                    return
            self._drag_start_global = event.globalPosition().toPoint()
            self._drag_start_pos = self.sub_window.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        sub = self.sub_window
        # 如果子窗口正在被缩放（从标题栏区域发起的边缘缩放）
        if hasattr(sub, '_resize_edge') and sub._resize_edge is not None \
                and hasattr(sub, '_resize_start_geo') and sub._resize_start_geo is not None:
            delta = event.globalPosition().toPoint() - sub._resize_start_global
            geo = QRectF(sub._resize_start_geo)
            edge = sub._resize_edge
            min_w, min_h = sub.minimumWidth(), sub.minimumHeight()
            if 'left' in edge:
                geo.setLeft(min(geo.left() + delta.x(), geo.right() - min_w))
            if 'right' in edge:
                geo.setRight(max(geo.right() + delta.x(), geo.left() + min_w))
            if 'top' in edge:
                geo.setTop(min(geo.top() + delta.y(), geo.bottom() - min_h))
            if 'bottom' in edge:
                geo.setBottom(max(geo.bottom() + delta.y(), geo.top() + min_h))
            snapped = sub._snap_resize_geometry(geo, edge)
            new_geo = snapped.toRect()
            sub._updating_geometry = True
            sub.setGeometry(new_geo)
            sub._updating_geometry = False
            event.accept()
            return

        # 非拖拽/缩放状态：更新光标形状
        if not sub.isMaximized() and hasattr(sub, '_get_resize_edge'):
            local = event.position().toPoint()
            edge = sub._get_resize_edge(QPoint(local.x(), local.y()))
            cursor_map = {
                'left': Qt.CursorShape.SizeHorCursor,
                'right': Qt.CursorShape.SizeHorCursor,
                'top': Qt.CursorShape.SizeVerCursor,
                'bottom': Qt.CursorShape.SizeVerCursor,
                'topleft': Qt.CursorShape.SizeFDiagCursor,
                'bottomright': Qt.CursorShape.SizeFDiagCursor,
                'topright': Qt.CursorShape.SizeBDiagCursor,
                'bottomleft': Qt.CursorShape.SizeBDiagCursor,
            }
            self.setCursor(cursor_map.get(edge, Qt.CursorShape.ArrowCursor))
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if self._drag_start_global is not None and self._drag_start_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_start_global
            self.sub_window.move(self._drag_start_pos + delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        sub = self.sub_window
        if hasattr(sub, '_resize_edge') and sub._resize_edge is not None:
            sub._resize_edge = None
            sub._resize_start_geo = None
            sub._resize_start_global = None
            sub._resizing = False
            sub._snap_enabled = True
            sub._constrain_geometry()
            sub.update_frac_geometry()
        self._drag_start_global = None
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

class SnapMdiSubWindow(QMdiSubWindow):
    _all_windows = []
    _parent_resizing = False       # 类级别标志：主窗口正在缩放时，所有子窗口跳过约束
    GRIP_SIZE = 8                  # 边缘缩放感应区宽度 (px)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._snapping = False
        self._resizing = False
        self._snap_enabled = True          # 实例级别：仅控制自身吸附，不影响其他窗口
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._on_resize_finished)
        self._move_timer = QTimer()
        self._move_timer.setSingleShot(True)
        self._move_timer.timeout.connect(self._on_move_finished)
        self._updating_geometry = False    # 防止递归
        self._frac_geometry = None         # (x_frac, y_frac, w_frac, h_frac) 比例坐标
        # 自定义缩放句柄状态
        self._resize_edge = None           # None / 边名字符串
        self._resize_start_geo = None      # QRect: 缩放前的窗口几何
        self._resize_start_global = None   # QPoint: 缩放前的全局鼠标位置
        self.setMinimumSize(50, 50)
        transparent_icon = QPixmap(1, 1)
        transparent_icon.fill(Qt.GlobalColor.transparent)
        self.setWindowIcon(QIcon(transparent_icon))
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setMouseTracking(True)
        self._title_bar = MdiTitleBar(self)
        self._content_widget = None
        self._wrapper_widget = None
        SnapMdiSubWindow._all_windows.append(self)
        # 安装全局事件过滤器，捕获所有子孙 widget 的鼠标事件用于边缘缩放
        QApplication.instance().installEventFilter(self)

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, '_title_bar'):
            self._title_bar.set_title(title)

    def setWidget(self, widget):
        self._content_widget = widget
        wrapper = QWidget()
        wrapper.setMouseTracking(True)
        wrapper.setObjectName("mdiWindowFrame")
        wrapper.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        wrapper.setStyleSheet("""
            QWidget#mdiWindowFrame {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
            }
        """)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(1, 1, 1, 1)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(self._title_bar)
        wrapper_layout.addWidget(widget, stretch=1)
        self._wrapper_widget = wrapper
        super().setWidget(wrapper)

    def widget(self):
        return self._content_widget if self._content_widget is not None else super().widget()

    def eventFilter(self, obj, event):
        """全局事件过滤器：拦截属于本子窗口的鼠标事件，处理边缘缩放和光标切换。"""
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtWidgets import QWidget
        from PyQt6.QtCore import QRectF

        if not isinstance(obj, QWidget):
            return super().eventFilter(obj, event)

        etype = event.type()
        if etype not in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove,
                        QEvent.Type.MouseButtonRelease):
            return super().eventFilter(obj, event)
        if self.isMaximized() or not self.isVisible():
            return super().eventFilter(obj, event)

        # 跳过标题栏（标题栏自己处理鼠标）
        if obj is self._title_bar:
            return super().eventFilter(obj, event)

        if obj is not self and not self.isAncestorOf(obj):
            return super().eventFilter(obj, event)

        if etype == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            sub_local = self._map_to_sub_window(obj, event.position().toPoint())
            if sub_local is not None:
                edge = self._get_resize_edge(sub_local)
                if edge is not None and self._title_bar is not None \
                        and self._title_bar._drag_start_global is None:
                    self._resize_edge = edge
                    self._resize_start_geo = self.geometry()
                    self._resize_start_global = event.globalPosition().toPoint()
                    self._resizing = True
                    self._snap_enabled = False
                    return True

        elif etype == QEvent.Type.MouseMove:
            if self._resize_edge is not None and self._resize_start_geo is not None:
                delta = event.globalPosition().toPoint() - self._resize_start_global
                geo = QRectF(self._resize_start_geo)
                edge = self._resize_edge
                min_w, min_h = self.minimumWidth(), self.minimumHeight()
                if 'left' in edge:
                    geo.setLeft(min(geo.left() + delta.x(), geo.right() - min_w))
                if 'right' in edge:
                    geo.setRight(max(geo.right() + delta.x(), geo.left() + min_w))
                if 'top' in edge:
                    geo.setTop(min(geo.top() + delta.y(), geo.bottom() - min_h))
                if 'bottom' in edge:
                    geo.setBottom(max(geo.bottom() + delta.y(), geo.top() + min_h))
                snapped = self._snap_resize_geometry(geo, edge)
                new_geo = snapped.toRect()
                self._updating_geometry = True
                self.setGeometry(new_geo)
                self._updating_geometry = False
                return True

            sub_local = self._map_to_sub_window(obj, event.position().toPoint())
            if sub_local is not None:
                edge = self._get_resize_edge(sub_local)
                if edge is not None:
                    self.setCursor(self._RESIZE_CURSORS.get(edge, Qt.CursorShape.ArrowCursor))
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)

        elif etype == QEvent.Type.MouseButtonRelease:
            if self._resize_edge is not None:
                self._resize_edge = None
                self._resize_start_geo = None
                self._resize_start_global = None
                self._resizing = False
                self._snap_enabled = True
                self._constrain_geometry()
                self.update_frac_geometry()
                return True

        return super().eventFilter(obj, event)

    def _map_to_sub_window(self, obj, local_pos):
        """将某个子孙 widget 内的局部坐标映射到 SnapMdiSubWindow 的坐标。"""
        try:
            return obj.mapTo(self, local_pos)
        except RuntimeError:
            return None

    def _get_resize_edge(self, pos):
        """根据窗口内局部坐标 pos 判断鼠标落在哪个缩放边/角。"""
        if self.isMaximized():
            return None
        w, h = self.width(), self.height()
        g = self.GRIP_SIZE
        left = pos.x() < g
        right = pos.x() > w - g
        top = pos.y() < g
        bottom = pos.y() > h - g
        if top and left:     return 'topleft'
        if top and right:    return 'topright'
        if bottom and left:  return 'bottomleft'
        if bottom and right: return 'bottomright'
        if left:             return 'left'
        if right:            return 'right'
        if top:              return 'top'
        if bottom:           return 'bottom'
        return None

    _RESIZE_CURSORS = {
        'left': Qt.CursorShape.SizeHorCursor,
        'right': Qt.CursorShape.SizeHorCursor,
        'top': Qt.CursorShape.SizeVerCursor,
        'bottom': Qt.CursorShape.SizeVerCursor,
        'topleft': Qt.CursorShape.SizeFDiagCursor,
        'bottomright': Qt.CursorShape.SizeFDiagCursor,
        'topright': Qt.CursorShape.SizeBDiagCursor,
        'bottomleft': Qt.CursorShape.SizeBDiagCursor,
    }

    def _snap_resize_geometry(self, geo, edge, threshold=15):
        """缩放时对拖拽边做邻窗吸附，返回调整后的 QRect。"""
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        neighbor_edges = self._get_neighbor_edges(geo)

        if 'left' in edge:
            for etype, val in neighbor_edges:
                if etype in ('left', 'right') and abs(x - val) < threshold:
                    x = val
                    break
            for etype, val in neighbor_edges:
                if etype in ('left', 'right') and abs(x + w - val) < threshold:
                    pass  # 拖左边缘时右边缘不动

        if 'right' in edge:
            right_edge = x + w
            for etype, val in neighbor_edges:
                if etype in ('left', 'right') and abs(right_edge - val) < threshold:
                    w = val - x
                    break

        if 'top' in edge:
            for etype, val in neighbor_edges:
                if etype in ('top', 'bottom') and abs(y - val) < threshold:
                    y = val
                    break

        if 'bottom' in edge:
            bottom_edge = y + h
            for etype, val in neighbor_edges:
                if etype in ('top', 'bottom') and abs(bottom_edge - val) < threshold:
                    h = val - y
                    break

        parent_rect = self._get_parent_rect()
        if parent_rect:
            new_w = max(50, min(w, parent_rect.width()))
            new_h = max(50, min(h, parent_rect.height()))
            if 'left' in edge and w != new_w:
                x = x + w - new_w
            new_x = max(0, min(x, parent_rect.width() - new_w))
            new_y = max(0, min(y, parent_rect.height() - new_h))
            w, h = new_w, new_h
            x, y = new_x, new_y

        return QRectF(x, y, w, h) if isinstance(geo, QRectF) else geo.__class__(int(x), int(y), int(w), int(h))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            edge = self._get_resize_edge(event.position().toPoint())
            if edge is not None:
                self._resize_edge = edge
                self._resize_start_geo = self.geometry()
                self._resize_start_global = event.globalPosition().toPoint()
                self._resizing = True
                self._snap_enabled = False
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_edge is not None and self._resize_start_geo is not None:
            delta = event.globalPosition().toPoint() - self._resize_start_global
            geo = QRectF(self._resize_start_geo)
            edge = self._resize_edge
            if 'left' in edge:
                geo.setLeft(min(geo.left() + delta.x(), geo.right() - self.minimumWidth()))
            if 'right' in edge:
                geo.setRight(max(geo.right() + delta.x(), geo.left() + self.minimumWidth()))
            if 'top' in edge:
                geo.setTop(min(geo.top() + delta.y(), geo.bottom() - self.minimumHeight()))
            if 'bottom' in edge:
                geo.setBottom(max(geo.bottom() + delta.y(), geo.top() + self.minimumHeight()))
            snapped = self._snap_resize_geometry(geo, edge)
            new_geo = snapped.toRect()
            self._updating_geometry = True
            self.setGeometry(new_geo)
            self._updating_geometry = False
            event.accept()
            return

        if not self.isMaximized():
            edge = self._get_resize_edge(event.position().toPoint())
            if edge is not None:
                self.setCursor(self._RESIZE_CURSORS.get(edge, Qt.CursorShape.ArrowCursor))
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_edge is not None:
            self._resize_edge = None
            self._resize_start_geo = None
            self._resize_start_global = None
            self._resizing = False
            self._snap_enabled = True
            self._constrain_geometry()
            self.update_frac_geometry()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _get_parent_rect(self):
        """获取父窗口（QMdiArea）的可见视口矩形。

        子窗口的 geometry() 坐标是相对于 QMdiArea 的 viewport 的，
        所以必须用 viewport().rect() 而非 contentsRect()。
        contentsRect() 在有滚动条时坐标原点会偏移，导致坐标系不一致。
        """
        parent = self.parent()
        if parent is None:
            return None
        # QMdiArea 继承自 QAbstractScrollArea，子窗口坐标基于 viewport
        try:
            return parent.viewport().rect()
        except AttributeError:
            return parent.rect()

    def _get_neighbor_edges(self, current_geo):
        """获取其他可见子窗口的边沿位置，用于吸附对齐"""
        edges = []
        for win in SnapMdiSubWindow._all_windows:
            if win is self:
                continue
            try:
                if not win.isVisible():
                    continue
            except RuntimeError:
                continue
            geo = win.geometry()
            edges.append(('left', geo.left()))
            edges.append(('right', geo.right()))
            edges.append(('top', geo.top()))
            edges.append(('bottom', geo.bottom()))
        return edges

    def _snap_move_position(self, current_geo, threshold=15):
        """计算吸附后的位置，同时约束在父窗口边界内"""
        x, y = current_geo.x(), current_geo.y()
        w, h = current_geo.width(), current_geo.height()
        neighbor_edges = self._get_neighbor_edges(current_geo)

        # 第一步：吸附到相邻窗口边沿
        for edge_type, val in neighbor_edges:
            if edge_type == 'right':
                if abs(x - val) < threshold:
                    x = val
            elif edge_type == 'left':
                if abs(x + w - val) < threshold:
                    x = val - w
            elif edge_type == 'bottom':
                if abs(y - val) < threshold:
                    y = val
            elif edge_type == 'top':
                if abs(y + h - val) < threshold:
                    y = val - h

        # 第二步：约束在父窗口边界内
        parent_rect = self._get_parent_rect()
        if parent_rect:
            if w > parent_rect.width():
                x = 0
            else:
                max_x = parent_rect.width() - w
                x = max(0, min(x, max_x))
            if h > parent_rect.height():
                y = 0
            else:
                max_y = parent_rect.height() - h
                y = max(0, min(y, max_y))
        return int(x), int(y)

    def _constrain_geometry(self):
        """同时约束位置和大小，使其完全位于父窗口内"""
        if self.isMaximized():
            return
        # 父窗口缩放期间不单独约束，等缩放结束后统一处理
        if SnapMdiSubWindow._parent_resizing:
            return
        parent_rect = self._get_parent_rect()
        if parent_rect is None:
            return
        geo = self.geometry()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()

        # 限制宽度和高度不超过父窗口
        new_w = min(w, parent_rect.width())
        new_h = min(h, parent_rect.height())
        # 限制位置不超出父窗口（考虑子窗口宽度可能等于父窗口宽度的情况）
        if new_w >= parent_rect.width():
            new_x = 0
        else:
            new_x = max(0, min(x, parent_rect.width() - new_w))
        if new_h >= parent_rect.height():
            new_y = 0
        else:
            new_y = max(0, min(y, parent_rect.height() - new_h))

        if (new_x, new_y, new_w, new_h) != (x, y, w, h):
            self._updating_geometry = True
            self.setGeometry(new_x, new_y, new_w, new_h)
            self._updating_geometry = False

    def moveEvent(self, event):
        # 主窗口缩放期间：跳过所有吸附和约束，交给批量处理
        if SnapMdiSubWindow._parent_resizing:
            super().moveEvent(event)
            return
        # 由 _constrain_geometry 或 apply_frac_geometry 触发的递归移动：直接放行
        if self._updating_geometry:
            super().moveEvent(event)
            return
        # 自身正在执行吸附移动：防止递归
        if self._snapping:
            super().moveEvent(event)
            return
        # 自身缩放中或 snap 被禁用：跳过吸附
        if self._resizing or not self._snap_enabled:
            super().moveEvent(event)
            return
        super().moveEvent(event)
        x, y = self._snap_move_position(self.geometry())
        if x != self.x() or y != self.y():
            self._snapping = True
            self.move(x, y)
            self._snapping = False
        # 用户手动拖拽移动结束后，更新比例坐标
        self._move_timer.stop()
        self._move_timer.start(120)

    def resizeEvent(self, event):
        # 主窗口缩放期间：跳过所有逻辑，直接放行
        if SnapMdiSubWindow._parent_resizing:
            super().resizeEvent(event)
            return
        # 由 _constrain_geometry 触发的递归缩放：直接放行
        if self._updating_geometry:
            super().resizeEvent(event)
            return
        super().resizeEvent(event)
        # 用户拖拽子窗口边缘缩放时，禁用自身吸附，缩放结束后恢复
        self._resizing = True
        self._snap_enabled = False
        self._resize_timer.stop()
        self._resize_timer.start(100)

    def _on_resize_finished(self):
        """子窗口缩放结束：恢复吸附，约束位置，更新比例坐标"""
        self._resizing = False
        self._snap_enabled = True
        self._constrain_geometry()
        self.update_frac_geometry()

    def _on_move_finished(self):
        """子窗口移动结束：更新比例坐标"""
        self.update_frac_geometry()

    def update_frac_geometry(self):
        """根据当前绝对坐标计算并存储比例坐标 (0~1)"""
        if self.isMaximized():
            self._frac_geometry = None
            return
        parent_rect = self._get_parent_rect()
        if parent_rect is None or parent_rect.width() <= 0 or parent_rect.height() <= 0:
            return
        geo = self.geometry()
        self._frac_geometry = (
            geo.x() / parent_rect.width(),
            geo.y() / parent_rect.height(),
            geo.width() / parent_rect.width(),
            geo.height() / parent_rect.height(),
        )

    def apply_frac_geometry(self):
        """根据存储的比例坐标和当前父窗口大小，等比缩放子窗口并约束边界。
        合并计算，只调用一次 setGeometry，且变化小于 2px 时跳过。"""
        if self.isMaximized():
            return
        parent_rect = self._get_parent_rect()
        if parent_rect is None or parent_rect.width() <= 0 or parent_rect.height() <= 0:
            return

        if self._frac_geometry is not None:
            fx, fy, fw, fh = self._frac_geometry
            new_w = int(fw * parent_rect.width())
            new_h = int(fh * parent_rect.height())
            new_x = int(fx * parent_rect.width())
            new_y = int(fy * parent_rect.height())
        else:
            geo = self.geometry()
            new_x, new_y, new_w, new_h = geo.x(), geo.y(), geo.width(), geo.height()

        # 约束在父窗口内
        new_w = max(50, min(new_w, parent_rect.width()))
        new_h = max(50, min(new_h, parent_rect.height()))
        new_x = max(0, min(new_x, parent_rect.width() - new_w))
        new_y = max(0, min(new_y, parent_rect.height() - new_h))

        # 只有实际变化超过阈值才 setGeometry（避免无谓的 pyqtgraph 重绘）
        geo = self.geometry()
        if abs(new_x - geo.x()) < 2 and abs(new_y - geo.y()) < 2 \
                and abs(new_w - geo.width()) < 2 and abs(new_h - geo.height()) < 2:
            return

        self._updating_geometry = True
        self.setGeometry(new_x, new_y, new_w, new_h)
        self._updating_geometry = False

    def set_frac_geometry(self, fx, fy, fw, fh):
        """外部设置比例坐标（从 config 恢复时使用）"""
        self._frac_geometry = (fx, fy, fw, fh)

    def get_frac_geometry(self):
        """获取当前比例坐标，用于保存到 config"""
        # 优先返回最新的比例坐标；若未设置则即时计算
        if self._frac_geometry is None and not self.isMaximized():
            self.update_frac_geometry()
        return self._frac_geometry

    def constrain(self):
        """外部调用的约束接口（供 MainWindow._constrain_all_windows 使用）"""
        self._constrain_geometry()

    def closeEvent(self, event):
        if self in SnapMdiSubWindow._all_windows:
            SnapMdiSubWindow._all_windows.remove(self)
        super().closeEvent(event)

class CircularBuffer:
    def __init__(self, max_len=100000, dtype=np.float32):
        self.max_len = max_len
        self.buffer = np.zeros(max_len, dtype=dtype)
        self.head = 0
        self.total_count = 0

    def resize_buffer(self, new_len):
        if new_len == self.max_len:
            return
        new_buf = np.zeros(new_len, dtype=self.buffer.dtype)
        current_valid = min(self.total_count, self.max_len)
        if current_valid > 0:
            start_abs = max(0, self.total_count - current_valid)
            take_len = min(current_valid, new_len)
            take_start = self.total_count - take_len
            start_idx = (self.head - (self.total_count - take_start)) % self.max_len
            end_idx = start_idx + take_len
            if end_idx <= self.max_len:
                y_data = self.buffer[start_idx:end_idx]
            else:
                y_data = np.concatenate([self.buffer[start_idx:], self.buffer[0:(end_idx % self.max_len)]])
            new_buf[0:take_len] = y_data
            self.head = take_len % new_len
            self.total_count = take_len
        else:
            self.head = 0
            self.total_count = 0
        self.buffer = new_buf
        self.max_len = new_len

    def extend(self, np_array):
        n = len(np_array)
        if n == 0:
            return
        if n >= self.max_len:
            self.buffer[:] = np_array[-self.max_len:]
            self.head = 0
            self.total_count += n
            return
        end1 = min(self.head + n, self.max_len)
        len1 = end1 - self.head
        self.buffer[self.head:end1] = np_array[:len1]
        if len1 < n:
            len2 = n - len1
            self.buffer[0:len2] = np_array[len1:]
            self.head = len2
        else:
            self.head = end1 % self.max_len
        self.total_count += n

    def get_data_slice(self, start_abs, end_abs):
        if self.total_count == 0:
            return np.array([], dtype=self.buffer.dtype)
        earliest_abs = max(0, self.total_count - self.max_len)
        start_abs = max(start_abs, earliest_abs)
        end_abs = min(end_abs, self.total_count)
        if start_abs >= end_abs:
            return np.array([], dtype=self.buffer.dtype)
        start_idx = (self.head - (self.total_count - start_abs)) % self.max_len
        length = end_abs - start_abs
        end_idx = start_idx + length
        if end_idx <= self.max_len:
            return self.buffer[start_idx:end_idx]
        else:
            return np.concatenate([self.buffer[start_idx:], self.buffer[0:(end_idx % self.max_len)]])

    def get_val_at_abs(self, abs_idx):
        earliest_abs = max(0, self.total_count - self.max_len)
        if abs_idx < earliest_abs or abs_idx >= self.total_count:
            return None
        idx = (self.head - (self.total_count - abs_idx)) % self.max_len
        return self.buffer[idx]

    def clear(self):
        self.buffer.fill(0)
        self.head = 0
        self.total_count = 0

class PrecisionAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.precision = 2

    def tickStrings(self, values, scale, spacing):
        return [f"{v:.{self.precision}f}" for v in values]
          
# ==================== 通信基类 ====================
class DataThread(QThread):
    data_received = pyqtSignal(np.ndarray, np.ndarray)  # 矩阵 (channels, frames), 时间轴
    connection_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.TAIL = b'\x00\x00\x80\x7f'
        self.start_time = time.perf_counter() * 1000.0
        self.last_t = None
        self.tx_queue = queue.Queue()

    def parse_frames(self, rx_buffer: bytearray) -> bytearray:
        """提取以 TAIL 分隔的有效帧，返回未完成的尾部字节"""
        if len(rx_buffer) > 512 * 1024:
            rx_buffer = rx_buffer[-4096:]

        chunks = rx_buffer.split(self.TAIL)
        rx_buffer = bytearray(chunks[-1])  # 未完成的尾巴留着下次用

        valid_frames = []
        num_channels = -1
        for chunk in chunks[:-1]:
            if len(chunk) > 0 and len(chunk) % 4 == 0:
                ch = len(chunk) // 4
                if num_channels == -1:
                    num_channels = ch
                if ch == num_channels:
                    valid_frames.append(chunk)

        if valid_frames and num_channels > 0:
            all_bytes = b"".join(valid_frames)
            matrix = np.frombuffer(all_bytes, dtype=np.float32).reshape(len(valid_frames), num_channels)
            frames = len(valid_frames)
            t_now = time.perf_counter() * 1000.0 - self.start_time
            if self.last_t is None:
                t_array = np.linspace(max(0, t_now - frames), t_now, frames, endpoint=True)
            else:
                t_array = np.linspace(self.last_t, t_now, frames + 1, endpoint=True)[1:]
            self.last_t = t_now
            self.data_received.emit(matrix.T, t_array)

        return rx_buffer

    def send_data(self, data):
        self.tx_queue.put(data)

    def stop(self):
        self.running = False
        self.wait()


# ==================== 串口线程 ====================
class SerialThread(DataThread):
    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.01, write_timeout=0.1)
            self.ser.flushInput()
            rx_buffer = bytearray()
            self.start_time = time.perf_counter() * 1000.0

            while self.running:
                while not self.tx_queue.empty():
                    try:
                        data_to_send = self.tx_queue.get_nowait()
                        self.ser.write(data_to_send)
                    except Exception:
                        pass

                try:
                    waiting = self.ser.in_waiting
                except Exception as se:
                    self.connection_error.emit(f"串口设备异常断开: {se}")
                    break

                if waiting > 0:
                    rx_buffer.extend(self.ser.read(waiting))
                    rx_buffer = self.parse_frames(rx_buffer)   # 调用基类解析
                else:
                    time.sleep(0.001)
        except Exception as e:
            self.connection_error.emit(f"串口初始化失败: {e}")
        finally:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass


# ==================== UDP 线程 ====================
class UDPThread(DataThread):
    def __init__(self, local_ip='0.0.0.0', local_port=12345, remote_ip=None, remote_port=None):
        super().__init__()
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.sock = None

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.local_ip, self.local_port))
            self.sock.settimeout(0.01)
            rx_buffer = bytearray()
            self.start_time = time.perf_counter() * 1000.0

            while self.running:
                while not self.tx_queue.empty():
                    try:
                        data = self.tx_queue.get_nowait()
                        if self.remote_ip and self.remote_port:
                            self.sock.sendto(data, (self.remote_ip, self.remote_port))
                    except Exception:
                        pass

                try:
                    data, addr = self.sock.recvfrom(65536)
                    rx_buffer.extend(data)
                    rx_buffer = self.parse_frames(rx_buffer)
                except socket.timeout:
                    pass
                except Exception as e:
                    self.connection_error.emit(f"UDP 异常: {e}")
                    break
        except Exception as e:
            self.connection_error.emit(f"UDP 初始化失败: {e}")
        finally:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass

    def send_data(self, data):
        if self.remote_ip and self.remote_port:
            self.tx_queue.put(data)


# ==================== TCP 线程 ====================
class TCPThread(DataThread):
    def __init__(self, mode='client', host='127.0.0.1', port=12345):
        super().__init__()
        self.mode = mode
        self.host = host
        self.port = port
        self.conn = None
        self.server_sock = None

    def run(self):
        try:
            if self.mode == 'server':
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_sock.bind((self.host, self.port))
                self.server_sock.listen(1)
                self.server_sock.settimeout(1.0)
                while self.running:
                    try:
                        self.conn, addr = self.server_sock.accept()
                        break
                    except socket.timeout:
                        continue
                if not self.running:
                    return
            else:  # client
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect((self.host, self.port))

            self.conn.settimeout(0.01)
            rx_buffer = bytearray()
            self.start_time = time.perf_counter() * 1000.0

            while self.running:
                while not self.tx_queue.empty():
                    try:
                        self.conn.sendall(self.tx_queue.get_nowait())
                    except Exception:
                        pass

                try:
                    data = self.conn.recv(65536)
                    if not data:
                        self.connection_error.emit("TCP 连接已断开")
                        break
                    rx_buffer.extend(data)
                    rx_buffer = self.parse_frames(rx_buffer)
                except socket.timeout:
                    pass
                except Exception as e:
                    self.connection_error.emit(f"TCP 异常: {e}")
                    break
        except Exception as e:
            self.connection_error.emit(f"TCP 初始化失败: {e}")
        finally:
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
            if self.server_sock:
                try:
                    self.server_sock.close()
                except Exception:
                    pass


class VofaTimeline(QWidget):
    range_changed = pyqtSignal(int, int) 
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.max_len, self.total_count, self.view_start, self.view_width = 100000, 0, 0, 5000      
        self.auto_follow = True     
        self.drag_mode, self.drag_start_x, self.drag_start_view_start, self.drag_start_view_width = None, 0, 0, 0
    def update_state(self, total_count, view_start, view_width, auto_follow, max_len):
        self.total_count, self.view_start, self.view_width, self.auto_follow, self.max_len = total_count, view_start, view_width, auto_follow, max_len
        self.update()
    def _get_geometry(self):
        W = self.width()
        if self.max_len <= 0: return 0, 0, 0, 0, 0
        valid_len = min(self.total_count, self.max_len)
        valid_w = int((valid_len / self.max_len) * W)
        earliest_abs = max(0, self.total_count - self.max_len)
        vs = max(earliest_abs, min(self.view_start, self.total_count))
        vw = max(10, min(self.view_width, self.total_count - vs))
        green_x = int(((vs - earliest_abs) / self.max_len) * W)
        green_w = max(6, int((vw / self.max_len) * W))
        return valid_w, green_x, green_w, green_x, valid_w - 2 
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        valid_w, green_x, green_w, red_x, purple_x = self._get_geometry()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor('#333333')))
        painter.drawRect(0, 4, W, H - 8)
        if valid_w > 0:
            painter.setBrush(QBrush(QColor('#555555')))
            painter.drawRect(0, 4, valid_w, H - 8)
        if self.total_count > 0:
            painter.setBrush(QBrush(QColor(40, 167, 69, 180))) 
            painter.drawRect(green_x, 4, green_w, H - 8)
            painter.setBrush(QBrush(QColor('#28a745')))
            painter.drawEllipse(QPoint(green_x + green_w // 2, 4), 4, 4)
            painter.setBrush(QBrush(QColor('#dc3545')))
            painter.drawEllipse(QPoint(red_x, H // 2), 4, 4)
            if purple_x >= 0:
                painter.setBrush(QBrush(QColor('#b388ff')))
                painter.drawEllipse(QPoint(purple_x, H // 2), 3, 3)
    def mousePressEvent(self, event):
        if self.total_count == 0: return
        x = event.pos().x()
        valid_w, green_x, green_w, red_x, purple_x = self._get_geometry()
        if abs(x - red_x) <= 6:
            self.drag_mode, self.drag_start_x = 'red_dot', x
            self.drag_start_view_start, self.drag_start_view_width = self.view_start, self.view_width
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif green_x <= x <= (green_x + green_w):
            self.drag_mode, self.drag_start_x, self.drag_start_view_start = 'green_block', x, self.view_start
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            earliest_abs = max(0, self.total_count - self.max_len)
            clicked_abs = earliest_abs + int((x / self.width()) * self.max_len)
            new_start = max(earliest_abs, min(clicked_abs - self.view_width // 2, max(0, self.total_count - self.view_width)))
            self.range_changed.emit(new_start, self.view_width)
    def mouseMoveEvent(self, event):
        if self.drag_mode is None: return
        delta_abs = int(((event.pos().x() - self.drag_start_x) / self.width()) * self.max_len)
        earliest_abs = max(0, self.total_count - self.max_len)
        if self.drag_mode == 'green_block':
            new_start = max(earliest_abs, min(self.drag_start_view_start + delta_abs, max(earliest_abs, self.total_count - self.view_width)))
            self.range_changed.emit(new_start, self.view_width)
        elif self.drag_mode == 'red_dot':
            new_width = max(10, self.drag_start_view_width - delta_abs)
            new_start = self.drag_start_view_start + self.drag_start_view_width - new_width if new_width == 10 else self.drag_start_view_start + delta_abs
            new_start = max(earliest_abs, min(new_start, max(earliest_abs, self.total_count - new_width)))
            self.range_changed.emit(new_start, new_width)
    def mouseReleaseEvent(self, event):
        self.drag_mode = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

class OscilloscopeCursor(pg.InfiniteLine):
    def __init__(self, *args, label_text="", **kwargs):
        super().__init__(*args, **kwargs)
        self.label_text = label_text
        self.is_pressed = False         
        self._click_offset = 0
        
    def paint(self, painter, option, widget):
        tr = painter.transform()
        pixel_x = tr.map(QPointF(0, 0)).x()
        super().paint(painter, option, widget)
        
        if widget is not None:
            painter.save()
            pen = self.currentPen
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(pen.color()))
            painter.setTransform(QTransform())
            
            top_y, bot_y = 0, widget.height()
            
            painter.drawPolygon(QPolygonF([
                QPointF(pixel_x, top_y + 12), QPointF(pixel_x - 6, top_y + 2), QPointF(pixel_x + 6, top_y + 2)
            ]))
            painter.drawPolygon(QPolygonF([
                QPointF(pixel_x, bot_y - 12), QPointF(pixel_x - 6, bot_y - 2), QPointF(pixel_x + 6, bot_y - 2)
            ]))
            
            painter.setPen(QPen(pen.color()))
            font = painter.font()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            
            painter.drawText(int(pixel_x + 8), int(top_y + 13), self.label_text)
            painter.drawText(int(pixel_x + 8), int(bot_y - 4), self.label_text)
            painter.restore()

    def mouseDragEvent(self, ev):
        if not self.movable or ev.button() != Qt.MouseButton.LeftButton: return
        ev.accept()
        
        if ev.isStart():
            self.moving = True
            self.is_pressed = True
            vb = self.getViewBox()
            if vb is not None:
                mouse_x = ev.scenePos().x()
                line_x = vb.mapViewToScene(QPointF(self.value(), 0)).x()
                self._click_offset = line_x - mouse_x
        elif ev.isFinish():
            self.moving = False
            self.is_pressed = False
            
        if self.moving:
            vb = self.getViewBox()
            if vb is not None:
                target_scene_x = ev.scenePos().x() + self._click_offset
                target_data_x = vb.mapSceneToView(QPointF(target_scene_x, 0)).x()
                
                xr = vb.viewRange()[0]
                span = xr[1] - xr[0]
                margin = span * 0.005 
                
                target_data_x = max(xr[0] + margin, min(xr[1] - margin, target_data_x))
                self.setValue(target_data_x)
        

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scope V3.0" + GL_STATUS)
        self.resize(1400, 900)
        self.setStyleSheet(DARK_STYLE)
        self.last_crosshair_idx = -1
        # 首次启动时从模板复制默认配置
        if not os.path.exists("config.ini") and os.path.exists("config.default.ini"):
            shutil.copy("config.default.ini", "config.ini")
        self.settings = QSettings("config.ini", QSettings.Format.IniFormat)
        self.setWindowIcon(QIcon("favicon.ico"))
        self._pending_splitter_state = None   # showEvent 中用于恢复侧栏宽度

        self.max_memory_points = 100000  
        self.visible_points = 5000       
        self.data_history = []
        self.time_history = CircularBuffer(self.max_memory_points, dtype=np.float64)           
        self.curves = []
        self.fft_curves = []  
        self.hud_labels = []             
        
        self.default_colors = [
            '#FF3366', '#33CCFF', '#33FF66', '#FFFF33', '#FF9933', '#FF33FF', '#00FFFF',
            '#99FF33', '#FF66CC', '#CC99FF', '#FF5050', '#00FFCC', '#FFCC00', '#3399FF',
            '#A0E040', '#E6A23C', '#409EFF', '#67C23A', '#F56C6C', '#B388FF', '#FF8A80', '#84FFFF'
        ] 
        self.channel_colors = []
        self.channel_widgets = [] 

        self.constrain_timer = QTimer()
        self.constrain_timer.setSingleShot(True)
        self.constrain_timer.timeout.connect(self._constrain_all_windows)
        
        self.auto_scale_y = True     
        self.auto_follow_x = True        
        self.is_display_paused = False
        self.paused_length = 0           
        self.view_start_abs = 0          
        self.last_mouse_pos = None  
        self.render_frame_counter = 0
        self.last_precision = -1 
        self._setting_range = False      
        
        self.last_draw_mode = -1
        self.last_line_width = -1
        self.last_show_symbols = None
        self.last_stacked_mode = False
        
        self.total_frames_received = 0
        self.total_bytes_received = 0
        self.last_stat_frames = 0
        self.last_stat_bytes = 0
        self.current_fps = 0.0
        self.current_kbps = 0.0
        self.configured_interval_ms = 1.0
        self._updating_interval_display = False
        self.dynamic_time_window_s = 3.0
        self.dynamic_interval_ms = 1.0
        self.dynamic_fps = 1000.0
        self.dynamic_time_samples = deque()
        self.dynamic_last_time_ms = None
        
        self.is_meas_active = False
        self.time_offset = 0.0
        self.meas_frac_A = 0.33          
        self.meas_frac_B = 0.66

        left_axis = PrecisionAxisItem(orientation='left')
        left_axis.setStyle(autoExpandTextSpace=False, tickTextWidth=60)
        right_axis = PrecisionAxisItem(orientation='right')
        right_axis.setStyle(autoExpandTextSpace=False, tickTextWidth=60)
        bottom_axis = PrecisionAxisItem(orientation='bottom')

        self.init_ui(left_axis, right_axis, bottom_axis)
        self.load_saved_configurations() 
        self.refresh_ports()
        
        self.port_timer = QTimer()
        self.port_timer.timeout.connect(self.update_stats_only)
        self.port_timer.timeout.connect(self.auto_check_ports)
        self.port_timer.start(1000)
        
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plot_display)
        self.plot_timer.start(32) 
        
        if not self.is_meas_active:
            self.toggle_measurement_lines()
            
        self.comm_thread = None
        self.main_time_sub = None
        self.main_fft_sub = None
        # 窗口管理
        self.window_counter = {'time': 0, 'fft': 0, 'imu': 0}
        self.window_factories = {
            '时域波形': self.create_time_widget,
            '频域频谱': self.create_fft_widget,
            'IMU姿态': self.create_imu_widget,
        }
        self.window_type_map = {'时域波形': 'time', '频域频谱': 'fft', 'IMU姿态': 'imu'}

    def init_ui(self, left_axis, right_axis, bottom_axis):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        outer_layout = QHBoxLayout(main_widget)
        outer_layout.setContentsMargins(4, 4, 4, 4)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        outer_layout.addWidget(self.splitter)

        # ========== 左侧控制面板 ==========
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        # 通信配置顶栏（串口/UDP/TCP）
        serial_group = QWidget()
        serial_layout = QGridLayout(serial_group)
        serial_layout.setContentsMargins(4, 4, 4, 4)

        # --- 协议选择 ---
        serial_layout.addWidget(QLabel("协议:"), 0, 0)
        self.combo_protocol = QComboBox()
        self.combo_protocol.addItems(["串口", "UDP", "TCP 客户端", "TCP 服务端"])
        self.combo_protocol.currentIndexChanged.connect(self.on_protocol_changed)
        serial_layout.addWidget(self.combo_protocol, 0, 1, 1, 2)

        # --- 串口参数（端口、波特率）---
        serial_layout.addWidget(QLabel("串口:"), 1, 0)
        self.port_combo = QComboBox()
        serial_layout.addWidget(self.port_combo, 1, 1)
        self.btn_refresh_ports = QPushButton("刷新")
        self.btn_refresh_ports.setFixedWidth(40)
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)
        serial_layout.addWidget(self.btn_refresh_ports, 1, 2)

        serial_layout.addWidget(QLabel("波特率:"), 2, 0)
        self.baud_combo = QComboBox()
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems(["9600", "115200", "460800", "921600", "1500000", "2000000"])
        self.baud_combo.setCurrentText("115200")
        serial_layout.addWidget(self.baud_combo, 2, 1, 1, 2)

        # --- UDP/TCP 参数（IP/端口） ---
        self.edit_host = QLineEdit("127.0.0.1")
        self.edit_host.setVisible(False)
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(12345)
        self.spin_port.setVisible(False)

        serial_layout.addWidget(QLabel("IP/主机:"), 3, 0)
        serial_layout.addWidget(self.edit_host, 3, 1, 1, 2)
        serial_layout.addWidget(QLabel("端口:"), 4, 0)
        serial_layout.addWidget(self.spin_port, 4, 1, 1, 2)

        # 连接按钮
        self.btn_connect = QPushButton("打开连接")
        self.btn_connect.clicked.connect(self.toggle_connection)
        serial_layout.addWidget(self.btn_connect, 5, 0, 1, 3)

        left_layout.addWidget(serial_group)

        ctrl_group = QWidget()
        ctrl_layout = QGridLayout(ctrl_group)
        ctrl_layout.setContentsMargins(4, 0, 4, 4)

        self.btn_pause = QPushButton("暂停显示")
        self.btn_pause.clicked.connect(self.toggle_display_pause)
        self.btn_clear = QPushButton("清空波形")
        self.btn_clear.clicked.connect(self.clear_data)

        self.btn_autoscale = QPushButton("Y轴自适应: 开")
        self.btn_autoscale.setProperty("active", "true")
        self.btn_autoscale.clicked.connect(self.toggle_auto_scale_y)

        self.btn_meas = QPushButton("双线测量: 关")
        self.btn_meas.setProperty("active", "false")
        self.btn_meas.clicked.connect(self.toggle_measurement_lines)

        self.cb_stacked_mode = QCheckBox("波形分离")
        self.cb_stacked_mode.stateChanged.connect(lambda: self.update_curves_style(force=True))

        self.combo_draw_mode = QComboBox()
        self.combo_draw_mode.addItems(["阶梯线", "曲线", "散点", "连线+散点"])
        self.combo_draw_mode.currentIndexChanged.connect(lambda: self.update_curves_style(force=True))

        ctrl_layout.addWidget(self.btn_pause, 0, 0)
        ctrl_layout.addWidget(self.btn_clear, 0, 1)
        ctrl_layout.addWidget(self.btn_autoscale, 1, 0)
        ctrl_layout.addWidget(self.btn_meas, 1, 1)
        ctrl_layout.addWidget(self.cb_stacked_mode, 2, 0)
        ctrl_layout.addWidget(self.combo_draw_mode, 2, 1)
        left_layout.addWidget(ctrl_group)

        # 分类功能标签页
        self.left_tabs = QTabWidget()

        # --- TAB 1: 通道 ---
        tab_ch = QWidget()
        tab_ch_layout = QVBoxLayout(tab_ch)
        tab_ch_layout.setContentsMargins(2, 4, 2, 4)

        ch_ctrl_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.clicked.connect(lambda: self.bulk_channel_checkbox(True))
        self.btn_clear_all = QPushButton("全清")
        self.btn_clear_all.clicked.connect(lambda: self.bulk_channel_checkbox(False))
        ch_ctrl_layout.addWidget(self.btn_select_all)
        ch_ctrl_layout.addWidget(self.btn_clear_all)
        tab_ch_layout.addLayout(ch_ctrl_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.channel_container = QWidget()
        self.channel_layout = QVBoxLayout(self.channel_container)
        self.channel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.channel_layout.setContentsMargins(2, 4, 2, 4)
        scroll.setWidget(self.channel_container)
        tab_ch_layout.addWidget(scroll, stretch=1)
        self.left_tabs.addTab(tab_ch, "通道")

        # --- TAB 2: 统计 ---
        tab_stats = QWidget()
        tab_stats_layout = QVBoxLayout(tab_stats)
        tab_stats_layout.setContentsMargins(4, 4, 4, 4)

        self.table_stats = QTableWidget()
        self.table_stats.setColumnCount(6)
        self.table_stats.setHorizontalHeaderLabels(["通道", "Max", "Min", "Vpp", "Mean", "RMS"])
        self.table_stats.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_stats.verticalHeader().setVisible(False)
        self.table_stats.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_stats.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table_stats.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_stats.setShowGrid(False)
        self.table_stats.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_stats.setWordWrap(False)
        self.table_stats.setStyleSheet("""
            QTableWidget {
                background-color: #141414;
                color: #e0e0e0;
                border: none;
                font-family: 'Consolas';
                font-size: 12px;
            }
            QTableWidget::item {
                border-bottom: 1px solid #222222;
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #aaaaaa;
                padding: 6px;
                border: none;
                border-bottom: 2px solid #333333;
                font-weight: bold;
                font-family: 'Microsoft YaHei';
            }
        """)
        tab_stats_layout.addWidget(self.table_stats)
        self.left_tabs.addTab(tab_stats, "统计")

        # --- TAB 3: 设置 ---
        tab_settings = QWidget()
        tab_settings_layout = QVBoxLayout(tab_settings)
        tab_settings_layout.setContentsMargins(8, 8, 8, 8)

        # ===== 新增：添加窗口控件 =====
        add_window_group = QWidget()
        add_window_layout = QHBoxLayout(add_window_group)
        add_window_layout.setContentsMargins(0, 0, 0, 0)
        self.combo_add_window = QComboBox()
        self.combo_add_window.addItems(['时域波形', '频域频谱', 'IMU姿态'])
        self.btn_add_window = QPushButton("添加窗口")
        self.btn_add_window.clicked.connect(self.add_window)
        add_window_layout.addWidget(QLabel("添加窗口:"))
        add_window_layout.addWidget(self.combo_add_window)
        add_window_layout.addWidget(self.btn_add_window)
        tab_settings_layout.insertWidget(0, add_window_group)  # 放在最上面

        set_form = QGridLayout()
        set_form.addWidget(QLabel("X轴基准:"), 0, 0)
        self.combo_x_axis = QComboBox()
        self.combo_x_axis.addItems(["动态平均间隔", "理论点间隔"])
        self.combo_x_axis.setCurrentIndex(0)
        self.combo_x_axis.currentIndexChanged.connect(self.on_x_axis_mode_changed)
        set_form.addWidget(self.combo_x_axis, 0, 1)

        set_form.addWidget(QLabel("平均窗口(s):"), 1, 0)
        self.spin_dynamic_time_window = QDoubleSpinBox()
        self.spin_dynamic_time_window.setRange(0.2, 30.0)
        self.spin_dynamic_time_window.setSingleStep(0.5)
        self.spin_dynamic_time_window.setDecimals(1)
        self.spin_dynamic_time_window.setValue(self.dynamic_time_window_s)
        self.spin_dynamic_time_window.valueChanged.connect(self.on_dynamic_time_window_changed)
        set_form.addWidget(self.spin_dynamic_time_window, 1, 1)

        set_form.addWidget(QLabel("数据精度:"), 2, 0)
        self.spin_precision = QSpinBox()
        self.spin_precision.setRange(0, 20);
        self.spin_precision.setValue(5)
        set_form.addWidget(self.spin_precision, 2, 1)

        set_form.addWidget(QLabel("波形线宽:"), 3, 0)
        self.spin_linewidth = QDoubleSpinBox()
        self.spin_linewidth.setRange(0.0, 10.0); self.spin_linewidth.setSingleStep(0.5); self.spin_linewidth.setDecimals(1); self.spin_linewidth.setValue(1.0)
        self.spin_linewidth.valueChanged.connect(lambda: self.update_curves_style(force=True))
        set_form.addWidget(self.spin_linewidth, 3, 1)
        tab_settings_layout.addLayout(set_form)

        tab_settings_layout.addWidget(QLabel("离线数据:"))
        csv_layout = QHBoxLayout()
        self.btn_export = QPushButton("导出CSV")
        self.btn_export.clicked.connect(self.export_to_csv)
        self.btn_import = QPushButton("导入CSV")
        self.btn_import.clicked.connect(self.import_from_csv)
        csv_layout.addWidget(self.btn_export)
        csv_layout.addWidget(self.btn_import)
        tab_settings_layout.addLayout(csv_layout)
        tab_settings_layout.addStretch()
        self.left_tabs.addTab(tab_settings, "设置")

        # --- TAB 4: 发送 ---
        tab_tx = QWidget()
        tab_tx_layout = QVBoxLayout(tab_tx)
        tab_tx_layout.setContentsMargins(8, 8, 8, 8)
        self.txt_tx = QTextEdit()
        self.txt_tx.setPlaceholderText("在此输入向设备下发的数据...")
        tab_tx_layout.addWidget(self.txt_tx, stretch=1)
        self.chk_hex_tx = QCheckBox("按 HEX 发送")
        tab_tx_layout.addWidget(self.chk_hex_tx)
        self.btn_tx = QPushButton("立刻发送")
        self.btn_tx.setStyleSheet("background-color: #28a745; font-size: 14px; padding: 10px;")
        self.btn_tx.clicked.connect(self.send_tx_data)
        tab_tx_layout.addWidget(self.btn_tx)
        self.left_tabs.addTab(tab_tx, "发送")

        left_layout.addWidget(self.left_tabs, stretch=1)

        # ========== 右侧图表区域 ==========
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 创建 QMdiArea
        self.mdi_area = QMdiArea()
        self.mdi_area.setViewMode(QMdiArea.ViewMode.SubWindowView)
        try:
            self.mdi_area.setOption(QMdiArea.DontMaximizeSubWindowOnActivation, True)
        except AttributeError:
            pass
        self.mdi_area.setBackground(QColor('#121212'))
        # 禁用滚动条：子窗口已通过 _constrain_geometry 约束在视口内，
        # 无需滚动条，且滚动条的显隐判断在 resize 时会造成额外 layout 开销
        self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.splitter.splitterMoved.connect(self.on_mdi_resized)
        right_layout.addWidget(self.mdi_area)

        # 创建默认时域窗口并最大化
        default_time_widget = self.create_time_widget()
        default_time_sub = SnapMdiSubWindow()
        default_time_sub.setWidget(default_time_widget)
        default_time_sub.setWindowTitle("时域波形")
        default_time_sub.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        default_time_sub.setProperty('window_type', 'time')
        self.mdi_area.addSubWindow(default_time_sub)
        default_time_sub.showMaximized()
        self.main_time_sub = default_time_sub

        # 保存主窗口引用的 plot_widget 等以便兼容旧代码（暂时指向第一个时域窗口）
        self.plot_widget = default_time_widget.plot_widget
        self.vofa_timeline = default_time_widget.vofa_timeline
        self.spin_max_cache = default_time_widget.spin_max_cache
        self.spin_interval = default_time_widget.spin_interval
        self.spin_visible_points = default_time_widget.spin_visible_points
        self.lbl_buffer_status = default_time_widget.lbl_buffer_status
        self.btn_go_latest = default_time_widget.btn_go_latest
        self.time_hud_label = default_time_widget.time_hud_label
        # 测量线保留在主窗口
        self.meas_line_A = OscilloscopeCursor(angle=90, movable=True, label_text="A", pen=pg.mkPen('#ffcc00', width=1.5, style=Qt.PenStyle.SolidLine))
        self.meas_line_B = OscilloscopeCursor(angle=90, movable=True, label_text="B", pen=pg.mkPen('#00ffcc', width=1.5, style=Qt.PenStyle.SolidLine))
        self.plot_widget.addItem(self.meas_line_A, ignoreBounds=True)
        self.plot_widget.addItem(self.meas_line_B, ignoreBounds=True)
        self.meas_line_A.sigPositionChanged.connect(self.on_meas_line_A_dragged)
        self.meas_line_B.sigPositionChanged.connect(self.on_meas_line_B_dragged)
        self.plot_widget.plotItem.vb.sigXRangeChanged.connect(self.sync_cursors_to_screen)
        self.plot_widget.plotItem.vb.sigRangeChangedManually.connect(self.on_view_manually_changed)
        self.meas_hud_label = QLabel(self.plot_widget)
        self.meas_hud_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.meas_hud_label.setStyleSheet("background-color: rgba(25, 25, 25, 220); border: 1px solid #ffcc00; font-size: 11px; padding: 6px; font-family: 'Consolas'; border-radius: 4px;")
        self.meas_hud_label.hide()
        # 将测量线设为不可见，由 toggle_measurement_lines 控制

        # 频域相关引用（初始为 None，后续可能动态添加）
        self.fft_plot = None
        self.fft_hud_label = None

        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)
        left_container.setMinimumWidth(260)
        self.splitter.setSizes([260, 1140])
        self.splitter.setOpaqueResize(False)   # 拖拽时只显示预览线，松开后一次性应用
        # 初始隐藏 UDP/TCP 参数
        self.on_protocol_changed(0)

    def on_mdi_resized(self):
        """splitter / 窗口拖拽中：子窗口全屏化以保证 QMdiArea 渲染性能，
        半透明遮罩覆盖在全屏窗口上，避免视觉跳变。"""
        if not SnapMdiSubWindow._parent_resizing:
            SnapMdiSubWindow._parent_resizing = True
            self._temp_maxed = []
            self.mdi_area.setUpdatesEnabled(False)
            for sub in self.mdi_area.subWindowList():
                if not sub.isMaximized():
                    self._temp_maxed.append(sub)
                    sub.showMaximized()
            self._show_drag_overlay()
            self.mdi_area.setUpdatesEnabled(True)
        self.constrain_timer.start(80)
        # 遮罩跟随 resize 始终保持覆盖整个视口
        if hasattr(self, '_drag_overlay') and self._drag_overlay.isVisible():
            self._drag_overlay.setGeometry(self.mdi_area.viewport().rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not SnapMdiSubWindow._parent_resizing:
            SnapMdiSubWindow._parent_resizing = True
            self._temp_maxed = []
            self.mdi_area.setUpdatesEnabled(False)
            for sub in self.mdi_area.subWindowList():
                if not sub.isMaximized():
                    self._temp_maxed.append(sub)
                    sub.showMaximized()
            self._show_drag_overlay()
            self.mdi_area.setUpdatesEnabled(True)
        self.constrain_timer.start(80)
        if hasattr(self, '_drag_overlay') and self._drag_overlay.isVisible():
            self._drag_overlay.setGeometry(self.mdi_area.viewport().rect())

    def _show_drag_overlay(self):
        """在 MDI 区域上覆盖半透明遮罩，隐藏全屏化的窗口跳变"""
        if not hasattr(self, '_drag_overlay'):
            self._drag_overlay = QLabel(self.mdi_area.viewport())
            self._drag_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._drag_overlay.setStyleSheet(
                "background-color: rgba(18,18,18,200); color: #666; font-size: 13px;"
            )
            self._drag_overlay.setText("resizing...")
        self._drag_overlay.setGeometry(self.mdi_area.viewport().rect())
        self._drag_overlay.raise_()
        self._drag_overlay.show()

    def _hide_drag_overlay(self):
        if hasattr(self, '_drag_overlay'):
            self._drag_overlay.hide()

    def _constrain_all_windows(self):
        """拖拽/缩放结束：移除遮罩，恢复窗口状态，等比缩放定位"""
        self.mdi_area.setUpdatesEnabled(False)
        self._hide_drag_overlay()
        for sub in getattr(self, '_temp_maxed', []):
            try:
                sub.showNormal()
            except RuntimeError:
                pass
        self._temp_maxed = []
        SnapMdiSubWindow._parent_resizing = False
        for sub in self.mdi_area.subWindowList():
            if isinstance(sub, SnapMdiSubWindow) and not sub.isMaximized():
                sub.apply_frac_geometry()
        self.mdi_area.setUpdatesEnabled(True)

    def _restore_sidebar(self, state):
        """从配置恢复左侧栏宽度"""
        self.splitter.restoreState(state)

    def showEvent(self, event):
        """窗口首次显示后恢复侧栏宽度（此时布局已稳定）"""
        super().showEvent(event)
        if hasattr(self, '_pending_splitter_state') and self._pending_splitter_state is not None:
            state = self._pending_splitter_state
            self._pending_splitter_state = None
            QTimer.singleShot(0, lambda s=state: self._restore_sidebar(s))

    def create_time_widget(self):
        """创建时域波形内容（QWidget），包含完整的 plot、timeline、控制条"""
        left_axis = PrecisionAxisItem(orientation='left')
        left_axis.setStyle(autoExpandTextSpace=False, tickTextWidth=60)
        right_axis = PrecisionAxisItem(orientation='right')
        right_axis.setStyle(autoExpandTextSpace=False, tickTextWidth=60)
        bottom_axis = PrecisionAxisItem(orientation='bottom')

        tab_time = QWidget()
        tab_time_layout = QVBoxLayout(tab_time)
        tab_time_layout.setContentsMargins(2, 4, 2, 4)

        plot_widget = pg.PlotWidget(axisItems={'right': right_axis, 'bottom': bottom_axis, 'left': left_axis})
        plot_widget.showGrid(x=True, y=True, alpha=0.25)
        plot_widget.setMenuEnabled(False)
        plot_widget.getAxis('left').setStyle(showValues=False, tickLength=0)
        plot_widget.getAxis('right').setStyle(showValues=True, tickLength=-5)
        plot_widget.getAxis('bottom').setStyle(tickLength=-5)
        plot_widget.getAxis('bottom').setLabel('时间 (ms)')

        plot_widget.setDownsampling(ds=True, auto=True, mode='peak')
        plot_widget.setClipToView(True)
        plot_widget.plotItem.vb.setMouseEnabled(y=not self.auto_scale_y)

        # 十字线
        plot_widget.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.PenStyle.DashLine))
        plot_widget.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.PenStyle.DashLine))
        plot_widget.addItem(plot_widget.v_line, ignoreBounds=True)
        plot_widget.addItem(plot_widget.h_line, ignoreBounds=True)
        plot_widget.v_line.setVisible(False)
        plot_widget.h_line.setVisible(False)

        plot_widget.crosshair_dots = pg.ScatterPlotItem(size=8, pen=pg.mkPen('#FFFFFF', width=1))
        plot_widget.addItem(plot_widget.crosshair_dots, ignoreBounds=True)

        # 测量线（仅用于第一个时域窗口，这里我们不在每个窗口都添加，避免干扰）
        # 如果需要每个窗口独立测量，可扩展，这里省略

        # HUD 时间标签（每个窗口独立）
        time_hud_label = QLabel(plot_widget)
        time_hud_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        time_hud_label.setStyleSheet("background-color: rgba(45, 45, 45, 230); border: 1px solid #888888; color: #ffffff; font-size: 11px; padding: 2px 5px; font-family: 'Consolas'; font-weight: bold; border-radius: 3px;")
        time_hud_label.hide()

        # 鼠标移动事件（需要连接信号）
        plot_widget.scene().sigMouseMoved.connect(self.mouse_moved)
        plot_widget.leaveEvent = self.on_plot_mouse_leave

        tab_time_layout.addWidget(plot_widget, stretch=1)

        # 添加时间轴（VofaTimeline）和底部控制
        vofa_timeline = VofaTimeline()
        vofa_timeline.range_changed.connect(self.on_timeline_range_changed)  # 可能需要修改信号处理，因为多个窗口共用
        tab_time_layout.addWidget(vofa_timeline)

        timeline_layout = QHBoxLayout()

        spin_max_cache = QSpinBox()
        spin_max_cache.setRange(1000, 2000000)
        spin_max_cache.setSingleStep(10000)
        spin_max_cache.setValue(self.max_memory_points)
        spin_max_cache.setFixedWidth(120)
        spin_max_cache.valueChanged.connect(self.on_max_cache_changed)

        spin_interval = QDoubleSpinBox()
        spin_interval.setRange(0.001, 10000.0)
        spin_interval.setValue(1.000)
        spin_interval.setSingleStep(1.0)
        spin_interval.setDecimals(3)
        spin_interval.setFixedWidth(120)
        spin_interval.valueChanged.connect(self.on_interval_changed)

        spin_visible_points = QSpinBox()
        spin_visible_points.setRange(10, 500000)
        spin_visible_points.setValue(self.visible_points)
        spin_visible_points.setFixedWidth(120)
        spin_visible_points.valueChanged.connect(self.on_visible_points_changed)

        timeline_layout.addWidget(QLabel("缓存:"))
        timeline_layout.addWidget(spin_max_cache)
        timeline_layout.addWidget(QLabel("点间隔(ms):"))
        timeline_layout.addWidget(spin_interval)
        timeline_layout.addWidget(QLabel("显示点数:"))
        timeline_layout.addWidget(spin_visible_points)

        lbl_buffer_status = QLabel(" 缓存: 0 / 100000 | 帧率: 0 Hz | 间隔: 1.000 ms | 速率: 0.0 KB/s")
        lbl_buffer_status.setStyleSheet("color: #aaaaaa; font-family: 'Consolas'; font-size: 11px;")
        lbl_buffer_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        timeline_layout.addWidget(lbl_buffer_status, stretch=1)

        btn_go_latest = QPushButton("拉到最新")
        btn_go_latest.setProperty("active", "true")
        btn_go_latest.setStyleSheet("background-color: #28a745; min-width: 80px;")
        btn_go_latest.clicked.connect(self.force_go_latest)
        timeline_layout.addWidget(btn_go_latest)

        tab_time_layout.addLayout(timeline_layout)

        # 保存一些引用到 widget 以便外部访问
        tab_time.plot_widget = plot_widget
        tab_time.vofa_timeline = vofa_timeline
        tab_time.spin_max_cache = spin_max_cache
        tab_time.spin_interval = spin_interval
        tab_time.spin_visible_points = spin_visible_points
        tab_time.lbl_buffer_status = lbl_buffer_status
        tab_time.btn_go_latest = btn_go_latest
        tab_time.time_hud_label = time_hud_label

        # 存储曲线列表和 plot 引用，用于动态更新
        tab_time.curves = []
        tab_time.plot_widget = plot_widget
        return tab_time

    def create_fft_widget(self):
        """创建频域频谱内容（QWidget）"""
        fft_plot = pg.PlotWidget()
        fft_plot.showGrid(x=True, y=True, alpha=0.3)
        fft_plot.setLabel('bottom', '频率 (Hz)')
        fft_plot.setLabel('left', '幅值')
        fft_plot.setDownsampling(ds=True, auto=True, mode='subsample')
        fft_plot.plotItem.vb.setMouseEnabled(y=not self.auto_scale_y)

        # ---- 十字光标 ----
        fft_plot.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.PenStyle.DashLine))
        fft_plot.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.PenStyle.DashLine))
        fft_plot.addItem(fft_plot.v_line, ignoreBounds=True)
        fft_plot.addItem(fft_plot.h_line, ignoreBounds=True)
        fft_plot.v_line.setVisible(False)
        fft_plot.h_line.setVisible(False)

        fft_plot.crosshair_dots = pg.ScatterPlotItem(size=8, pen=pg.mkPen('#FFFFFF', width=1))
        fft_plot.addItem(fft_plot.crosshair_dots, ignoreBounds=True)

        fft_hud_label = QLabel(fft_plot)
        fft_hud_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        fft_hud_label.setStyleSheet("background-color: rgba(25, 25, 25, 220); border: 1px solid #777777; font-size: 11px; padding: 4px 6px; font-family: 'Consolas'; border-radius: 4px;")
        fft_hud_label.hide()

        # 频率十字光标标签
        freq_hud_label = QLabel(fft_plot)
        freq_hud_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        freq_hud_label.setStyleSheet("background-color: rgba(45, 45, 45, 230); border: 1px solid #888888; color: #ffffff; font-size: 11px; padding: 2px 5px; font-family: 'Consolas'; font-weight: bold; border-radius: 3px;")
        freq_hud_label.hide()

        btn_reset_fft = QPushButton("🔍 复位 (0~Nyquist)", fft_plot)
        btn_reset_fft.setStyleSheet("""
            QPushButton {
                background-color: rgba(40, 40, 40, 200);
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(80, 80, 80, 220); color: #ffffff; border: 1px solid #007acc; }
        """)
        btn_reset_fft.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_fft.move(10, 10)
        btn_reset_fft.clicked.connect(self.reset_fft_view)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(fft_plot)

        container.fft_plot = fft_plot
        container.fft_hud_label = fft_hud_label
        container.fft_freq_hud_label = freq_hud_label
        container.btn_reset_fft = btn_reset_fft
        container.fft_curves = []

        # 每窗口独立的十字光标状态
        container.fft_last_mouse_pos = None
        container.fft_last_bin_idx = -1
        container.fft_xf = None
        container.fft_mags = {}
        container.fft_channel_labels = []

        # 鼠标跟踪
        fft_plot.scene().sigMouseMoved.connect(
            lambda evt, c=container: setattr(c, 'fft_last_mouse_pos', evt)
        )
        # 鼠标离开时清理
        def _make_fft_leave(_fp, _c):
            def _handler(ev):
                _c.fft_last_mouse_pos = None
                try:
                    _fp.v_line.setVisible(False)
                    _fp.h_line.setVisible(False)
                    _fp.crosshair_dots.setVisible(False)
                    _c.fft_freq_hud_label.hide()
                    for lbl in _c.fft_channel_labels:
                        lbl.hide()
                except RuntimeError:
                    pass
                super(pg.PlotWidget, _fp).leaveEvent(ev)
            return _handler
        fft_plot.leaveEvent = _make_fft_leave(fft_plot, container)

        return container

    def create_imu_widget(self):
        """创建 IMU 姿态 3D 可视化模块"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # ---- 控制栏 ----
        ctrl = QWidget()
        ctrl_layout = QHBoxLayout(ctrl)
        ctrl_layout.setContentsMargins(4, 2, 4, 2)

        mode_label = QLabel("模式:")
        mode_combo = QComboBox()
        mode_combo.addItems(["四元数 (w,x,y,z)", "欧拉角 ZYX (deg)"])

        ctrl_layout.addWidget(mode_label)
        ctrl_layout.addWidget(mode_combo)
        ctrl_layout.addStretch()

        # 标签容器：四元数用4个，欧拉角用3个
        quat_labels = ["w:", "x:", "y:", "z:"]
        euler_labels = ["Roll:", "Pitch:", "Yaw:"]
        ch_selectors = []
        lbl_widgets = []

        for i in range(4):
            lbl = QLabel(quat_labels[i])
            ctrl_layout.addWidget(lbl)
            lbl_widgets.append(lbl)
        for i in range(4):
            sel = QComboBox()
            sel.setMinimumWidth(60)
            ctrl_layout.addWidget(sel)
            ch_selectors.append(sel)

        def on_mode_changed(idx):
            is_quat = (idx == 0)
            visible_count = 4 if is_quat else 3
            labels = quat_labels if is_quat else euler_labels
            for i in range(4):
                lbl_widgets[i].setVisible(i < visible_count)
                if i < visible_count:
                    lbl_widgets[i].setText(labels[i])
                ch_selectors[i].setVisible(i < visible_count)

        mode_combo.currentIndexChanged.connect(on_mode_changed)
        on_mode_changed(0)  # 默认四元数

        layout.addWidget(ctrl)

        # ---- 3D 视口 ----
        gl_view = gl.GLViewWidget()
        gl_view.setBackgroundColor(QColor('#1a1a1a'))
        gl_view.setCameraPosition(distance=5, elevation=25, azimuth=45)

        # 坐标轴（自定义彩色线条）
        axis_size = 2.0
        x_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [axis_size, 0, 0]]),
            color=(1, 0.3, 0.3, 1), width=2, antialias=True)
        y_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, axis_size, 0]]),
            color=(0.3, 1, 0.3, 1), width=2, antialias=True)
        z_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, 0, axis_size]]),
            color=(0.3, 0.5, 1, 1), width=2, antialias=True)
        gl_view.addItem(x_axis)
        gl_view.addItem(y_axis)
        gl_view.addItem(z_axis)

        # 参考网格（XY 水平面，+Z 向上）
        grid = gl.GLGridItem(color=(180, 180, 195, 160))
        grid.setSize(4, 4)
        grid.setSpacing(0.5, 0.5)
        gl_view.addItem(grid)

        # 重置视角按钮
        btn_reset_view = QPushButton("⟳ 重置视角", gl_view)
        btn_reset_view.setStyleSheet("""
            QPushButton {
                background-color: rgba(40, 40, 40, 200);
                color: #cccccc;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(80, 80, 80, 220); color: #fff; border: 1px solid #007acc; }
        """)
        btn_reset_view.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_view.move(10, 10)
        btn_reset_view.clicked.connect(
            lambda: gl_view.setCameraPosition(distance=5, elevation=25, azimuth=45))

        angle_label = QLabel(gl_view)
        angle_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        angle_label.setStyleSheet("""
            QLabel {
                background-color: rgba(20, 20, 20, 210);
                color: #f0f0f0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 8px;
                font-family: 'Consolas';
                font-size: 11px;
            }
        """)
        angle_label.move(10, 44)
        angle_label.setText("Roll:  +0.00°\nPitch: +0.00°\nYaw:   +0.00°")
        angle_label.adjustSize()
        angle_label.show()

        # ---- 3D 长方体：右手系 FLU，+X 前，+Y 左，+Z 上 ----
        hx, hy, hz = 0.75, 0.3, 0.5  # 半尺寸：长/宽/高
        verts = np.array([
            [-hx, -hy, -hz], [ hx, -hy, -hz], [ hx,  hy, -hz], [-hx,  hy, -hz],  # 底 (-Z)
            [-hx, -hy,  hz], [ hx, -hy,  hz], [ hx,  hy,  hz], [-hx,  hy,  hz],  # 顶 (+Z)
        ], dtype=np.float32)
        # 三角面片 (每面2个三角形，共12个面)
        faces = np.array([
            # -Z 面（底）
            [0, 2, 1], [0, 3, 2],
            # +Z 面（顶）
            [4, 5, 6], [4, 6, 7],
            # -X 面（后）
            [0, 4, 7], [0, 7, 3],
            # +X 面（前）
            [1, 2, 6], [1, 6, 5],
            # -Y 面（右）
            [0, 1, 5], [0, 5, 4],
            # +Y 面（左）
            [3, 7, 6], [3, 6, 2],
        ], dtype=np.int32)
        # 面颜色
        face_colors = np.array([
            [0.15, 0.25, 0.65, 0.85], [0.15, 0.25, 0.65, 0.85],  # -Z 底：暗蓝
            [0.35, 0.55, 1.00, 0.85], [0.35, 0.55, 1.00, 0.85],  # +Z 上：亮蓝
            [0.55, 0.15, 0.15, 0.85], [0.55, 0.15, 0.15, 0.85],  # -X 后：暗红
            [1.00, 0.25, 0.25, 0.85], [1.00, 0.25, 0.25, 0.85],  # +X 前：亮红
            [0.15, 0.55, 0.15, 0.85], [0.15, 0.55, 0.15, 0.85],  # -Y 右：暗绿
            [0.35, 1.00, 0.35, 0.85], [0.35, 1.00, 0.35, 0.85],  # +Y 左：亮绿
        ], dtype=np.float32)

        md = gl.MeshData(vertexes=verts, faces=faces, faceColors=face_colors)
        box_mesh = gl.GLMeshItem(meshdata=md, smooth=False, shader='shaded',
                                  drawEdges=True, edgeColor=(0.5, 0.5, 0.5, 0.5))
        gl_view.addItem(box_mesh)

        def axis_meshdata(axis, start, length, radius):
            md_axis = gl.MeshData.cylinder(rows=1, cols=28, radius=radius, length=length, offset=True)
            local = md_axis.vertexes()
            verts_axis = np.empty_like(local)
            if axis == 'x':
                verts_axis[:, 0] = start + local[:, 2]
                verts_axis[:, 1] = local[:, 0]
                verts_axis[:, 2] = local[:, 1]
            elif axis == 'y':
                verts_axis[:, 0] = local[:, 0]
                verts_axis[:, 1] = start + local[:, 2]
                verts_axis[:, 2] = local[:, 1]
            else:
                verts_axis[:, 0] = local[:, 0]
                verts_axis[:, 1] = local[:, 1]
                verts_axis[:, 2] = start + local[:, 2]
            return gl.MeshData(vertexes=verts_axis, faces=md_axis.faces())

        def make_axis_arrow(axis):
            specs = {
                'x': (hx + 0.05, 0.32, 0.22, 0.035, 0.11, (1.0, 0.12, 0.10, 1.0)),
                'y': (hy + 0.05, 0.28, 0.20, 0.030, 0.095, (0.15, 1.0, 0.15, 1.0)),
                'z': (hz + 0.05, 0.30, 0.21, 0.032, 0.10, (0.25, 0.55, 1.0, 1.0)),
            }
            start, shaft_len, head_len, shaft_r, head_r, color = specs[axis]
            shaft = gl.GLMeshItem(
                meshdata=axis_meshdata(axis, start, shaft_len, [shaft_r, shaft_r]),
                smooth=True, shader='shaded', color=color, drawEdges=False)
            head = gl.GLMeshItem(
                meshdata=axis_meshdata(axis, start + shaft_len, head_len, [head_r, 0.0]),
                smooth=True, shader='shaded', color=color, drawEdges=False)
            return [shaft, head]

        body_axis_items = []
        for axis_name in ('x', 'y', 'z'):
            body_axis_items.extend(make_axis_arrow(axis_name))
        for item in body_axis_items:
            gl_view.addItem(item)

        layout.addWidget(gl_view, stretch=1)

        # 挂在 widget 上的属性
        container.mode_combo = mode_combo
        container.ch_selectors = ch_selectors
        container.gl_view = gl_view
        container.box_mesh = box_mesh
        container.body_axis_items = body_axis_items
        container.imu_angle_label = angle_label
        container.curves = []  # 兼容 update 循环
        container.imu_channel_indices = [0, 1, 2, 3]
        for i, sel in enumerate(ch_selectors):
            sel.currentIndexChanged.connect(
                lambda idx, selector_idx=i, w=container: self._on_imu_channel_changed(w, selector_idx, idx)
            )

        # 初始化通道列表
        self._refresh_imu_channels(widget=container)
        return container

    def _refresh_all_imu_channels(self):
        """刷新所有 IMU 窗口的通道选择器"""
        for sub in self.mdi_area.subWindowList():
            if sub.property('window_type') == 'imu':
                w = sub.widget()
                if w and hasattr(w, 'ch_selectors'):
                    self._refresh_imu_channels(widget=w)

    def _refresh_imu_channels(self, widget):
        """刷新 IMU 窗口的通道选择器列表"""
        if not hasattr(widget, 'imu_channel_indices'):
            widget.imu_channel_indices = [sel.currentIndex() for sel in widget.ch_selectors]
        while len(widget.imu_channel_indices) < len(widget.ch_selectors):
            widget.imu_channel_indices.append(len(widget.imu_channel_indices))

        ch_names = []
        for i in range(len(self.data_history)):
            name = (self.channel_widgets[i]["name_edit"].text().strip()
                    if i < len(self.channel_widgets) else f"CH{i+1}")
            ch_names.append(f"CH{i+1}:{name}")
        if not ch_names:
            ch_names = ["(无通道)"]
        for selector_idx, sel in enumerate(widget.ch_selectors):
            saved_idx = widget.imu_channel_indices[selector_idx]
            current = sel.currentText()
            sel.blockSignals(True)
            sel.clear()
            sel.addItems(ch_names)
            if 0 <= saved_idx < len(ch_names):
                sel.setCurrentIndex(saved_idx)
            elif current in ch_names:
                sel.setCurrentText(current)
                widget.imu_channel_indices[selector_idx] = sel.currentIndex()
            sel.blockSignals(False)
        # 更新模式显示（可能通道数变了）
        widget.mode_combo.currentIndexChanged.emit(widget.mode_combo.currentIndex())

    def _on_imu_channel_changed(self, widget, selector_idx, channel_idx):
        if not hasattr(widget, 'imu_channel_indices'):
            widget.imu_channel_indices = [0, 1, 2, 3]
        while len(widget.imu_channel_indices) <= selector_idx:
            widget.imu_channel_indices.append(0)
        widget.imu_channel_indices[selector_idx] = int(channel_idx)

    def add_window(self):
        """根据下拉框选择添加新窗口"""
        window_type_name = self.combo_add_window.currentText()
        if window_type_name not in self.window_factories:
            return
        # 生成唯一标题
        base_name = window_type_name
        key = self.window_type_map[window_type_name]
        if not hasattr(self, 'window_counter'):
            self.window_counter = {'time': 0, 'fft': 0, 'imu': 0}
        self.window_counter[key] += 1
        if self.window_counter[key] > 1:
            title = f"{base_name} {self.window_counter[key]}"
        else:
            title = base_name

        # 创建内容
        widget = self.window_factories[window_type_name]()
        sub = SnapMdiSubWindow()
        sub.setWidget(widget)
        sub.setWindowTitle(title)
        sub.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        sub.setProperty('window_type', key)
        self.mdi_area.addSubWindow(sub)
        sub.resize(600, 400)  # 默认大小
        sub.show()
        # 如果是第一个频域窗口，将其设置为主频域引用（以便 create_channel_ui 等旧逻辑兼容）
        if key == 'fft' and self.fft_plot is None:
            self.fft_plot = widget.fft_plot
            self.main_fft_sub = sub

    # ========== 协议切换显示隐藏 ==========
    def on_protocol_changed(self, index):
        is_serial = (index == 0)  # 串口
        # 显示/隐藏串口控件（端口、波特率）
        self.port_combo.setVisible(is_serial)
        self.baud_combo.setVisible(is_serial)
        self.btn_refresh_ports.setVisible(is_serial)
        # 显示/隐藏 UDP/TCP 参数
        is_net = (index >= 1)
        self.edit_host.setVisible(is_net)
        self.spin_port.setVisible(is_net)

    # ========== 连接/断开统一入口 ==========
    def toggle_connection(self):
        if self.comm_thread and self.comm_thread.isRunning():
            self.close_connection()
        else:
            protocol = self.combo_protocol.currentIndex()
            if protocol == 0:  # 串口
                port = self.port_combo.currentText()
                if not port:
                    QMessageBox.warning(self, "错误", "请选择串口！")
                    return
                current_ports = [p.device for p in serial.tools.list_ports.comports()]
                if port not in current_ports:
                    QMessageBox.warning(self, "连接失败", f"找不到物理串口 {port}！")
                    self.refresh_ports()
                    return
                try:
                    baud = int(self.baud_combo.currentText().strip())
                except ValueError:
                    return
                if self.time_history.total_count > 0:
                    last_time = self.time_history.get_val_at_abs(self.time_history.total_count - 1)
                    if last_time is not None:
                        self.time_offset = last_time
                else:
                    self.time_offset = 0.0
                thread = SerialThread(port, baud)

            elif protocol == 1:  # UDP
                local_ip = '0.0.0.0'
                local_port = self.spin_port.value()
                remote_ip = self.edit_host.text().strip()
                remote_port = self.spin_port.value()
                thread = UDPThread(local_ip=local_ip, local_port=local_port,
                                   remote_ip=remote_ip, remote_port=remote_port)

            elif protocol == 2:  # TCP 客户端
                host = self.edit_host.text().strip()
                port = self.spin_port.value()
                thread = TCPThread(mode='client', host=host, port=port)

            elif protocol == 3:  # TCP 服务端
                host = '0.0.0.0'
                port = self.spin_port.value()
                thread = TCPThread(mode='server', host=host, port=port)

            else:
                return

            self._reset_dynamic_time_axis(keep_time=True)
            thread.data_received.connect(self.handle_batch_matrix)
            thread.connection_error.connect(self.handle_connection_exception)
            thread.start()
            self.comm_thread = thread

            self.btn_connect.setText("关闭连接")
            self.btn_connect.setStyleSheet("background-color: #d9534f;")
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.combo_protocol.setEnabled(False)

    def close_connection(self):
        if self.comm_thread:
            self.comm_thread.stop()
            self.comm_thread = None
        self.btn_connect.setText("打开连接")
        self.btn_connect.setStyleSheet("background-color: #007acc;")
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.combo_protocol.setEnabled(True)
        self.current_fps = 0.0
        self.current_kbps = 0.0

    def handle_connection_exception(self, error_msg):
        self.close_connection()
        QMessageBox.critical(self, "通信异常", error_msg)

    def refresh_ports(self):
        current_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.clear()
        self.port_combo.addItems(current_ports)

    def auto_check_ports(self):
        if self.comm_thread and self.comm_thread.isRunning():
            return
        current_ports = [port.device for port in serial.tools.list_ports.comports()]
        existing_ports = [self.port_combo.itemText(i) for i in range(self.port_combo.count())]
        if set(current_ports) != set(existing_ports):
            current_selection = self.port_combo.currentText()
            self.port_combo.clear()
            self.port_combo.addItems(current_ports)
            if current_selection in current_ports:
                self.port_combo.setCurrentText(current_selection)

    def update_stats_only(self):
        self.current_fps = float(self.total_frames_received - self.last_stat_frames)
        self.current_kbps = float(self.total_bytes_received - self.last_stat_bytes) / 1024.0
        self.last_stat_frames = self.total_frames_received
        self.last_stat_bytes = self.total_bytes_received

    def _reset_dynamic_time_axis(self, keep_time=True):
        """重置动态平均间隔估计器，不清除已有波形数据。"""
        self.dynamic_time_samples.clear()
        fallback_interval = self.configured_interval_ms
        self.dynamic_interval_ms = max(0.001, float(fallback_interval))
        self.dynamic_fps = 1000.0 / self.dynamic_interval_ms
        if keep_time and self.time_history.total_count > 0:
            last_time = self.time_history.get_val_at_abs(self.time_history.total_count - 1)
            self.dynamic_last_time_ms = float(last_time) if last_time is not None else 0.0
        else:
            self.dynamic_last_time_ms = 0.0

    def _make_dynamic_time_array(self, frames):
        """按最近 N 秒平均 FPS 生成等间隔时间轴，避免批量接收造成真实时间戳抖动。"""
        if frames <= 0:
            return np.array([], dtype=np.float64)

        now_ms = time.perf_counter() * 1000.0
        window_ms = max(0.2, float(self.dynamic_time_window_s)) * 1000.0
        self.dynamic_time_samples.append((now_ms, self.total_frames_received))
        while len(self.dynamic_time_samples) > 2 and now_ms - self.dynamic_time_samples[0][0] > window_ms:
            self.dynamic_time_samples.popleft()

        if len(self.dynamic_time_samples) >= 2:
            first_t, first_frames = self.dynamic_time_samples[0]
            last_t, last_frames = self.dynamic_time_samples[-1]
            elapsed_ms = last_t - first_t
            frame_delta = last_frames - first_frames
            if elapsed_ms > 1.0 and frame_delta > 0:
                self.dynamic_fps = frame_delta * 1000.0 / elapsed_ms
                self.dynamic_interval_ms = max(0.001, 1000.0 / self.dynamic_fps)

        if self.dynamic_last_time_ms is None:
            self._reset_dynamic_time_axis(keep_time=True)

        step = self.dynamic_interval_ms
        t_array = self.dynamic_last_time_ms + step * np.arange(1, frames + 1, dtype=np.float64)
        self.dynamic_last_time_ms = float(t_array[-1])
        if hasattr(self, 'combo_x_axis') and self.combo_x_axis.currentIndex() == 0:
            self._sync_interval_spinbox_to_mode()
        return t_array

    def send_tx_data(self):
        if not self.comm_thread or not self.comm_thread.running:
            QMessageBox.warning(self, "错误", "请先打开连接！")
            return
        data_str = self.txt_tx.toPlainText()
        if not data_str: return
        if self.chk_hex_tx.isChecked():
            try:
                data = bytes.fromhex(data_str)
            except ValueError:
                QMessageBox.warning(self, "错误", "HEX 数据格式不合法！")
                return
        else:
            data = data_str.encode('utf-8')
        self.comm_thread.send_data(data)

    def reset_fft_view(self):
        """一键将当前活跃的 FFT 视窗的 X 轴恢复至 0 ~ 奈奎斯特频率"""
        # 尝试获取当前激活的子窗口
        active_sub = self.mdi_area.activeSubWindow()
        if active_sub and active_sub.property('window_type') == 'fft':
            fft_widget = active_sub.widget()
            if hasattr(fft_widget, 'fft_plot'):
                fft_plot = fft_widget.fft_plot
            else:
                return
        else:
            # 否则找第一个可见的 FFT 窗口
            for sub in self.mdi_area.subWindowList():
                if sub.isVisible() and sub.property('window_type') == 'fft':
                    fft_widget = sub.widget()
                    if hasattr(fft_widget, 'fft_plot'):
                        fft_plot = fft_widget.fft_plot
                        break
            else:
                return

        # 计算奈奎斯特频率
        if not self.data_history or self.data_history[0].total_count < 2:
            return

        interval = self.spin_interval.value()
        use_real_time = (self.combo_x_axis.currentIndex() == 0)

        if use_real_time:
            live_len = self.data_history[0].total_count
            current_len = self.paused_length if self.is_display_paused else live_len
            earliest_abs = max(0, current_len - self.max_memory_points)
            if self.auto_follow_x and not self.is_display_paused:
                chunk_start = max(earliest_abs, current_len - self.visible_points)
                chunk_end = current_len
            else:
                chunk_start = max(earliest_abs, self.view_start_abs - self.visible_points)
                chunk_end = min(current_len, self.view_start_abs + self.visible_points * 2)
            t_slice = self.time_history.get_data_slice(chunk_start, chunk_end)
            n = len(t_slice)
            if n > 1:
                dt_ms = (t_slice[-1] - t_slice[0]) / (n - 1)
                if dt_ms <= 0:
                    dt_ms = interval
                fs = 1000.0 / dt_ms
            else:
                fs = 1000.0 / interval
        else:
            fs = 1000.0 / interval

        nyquist_freq = fs / 2.0
        # 用 disableAutoRange=False 设定范围但不锁定，用户仍可滚轮缩放，数据更新时自动跟随 Nyquist
        fft_plot.plotItem.vb.setRange(xRange=(0, nyquist_freq), padding=0.02, disableAutoRange=False)

    def refresh_ports(self):
        current_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.clear()
        self.port_combo.addItems(current_ports)

    def auto_check_ports(self):
        if self.comm_thread and self.comm_thread.isRunning():
            return
            
        current_ports = [port.device for port in serial.tools.list_ports.comports()]
        existing_ports = [self.port_combo.itemText(i) for i in range(self.port_combo.count())]
        
        if set(current_ports) != set(existing_ports):
            current_selection = self.port_combo.currentText()
            self.port_combo.clear()
            self.port_combo.addItems(current_ports)

            if current_selection in current_ports:
                self.port_combo.setCurrentText(current_selection)

    def update_stats_only(self):
        self.current_fps = float(self.total_frames_received - self.last_stat_frames)
        self.current_kbps = float(self.total_bytes_received - self.last_stat_bytes) / 1024.0
        self.last_stat_frames = self.total_frames_received
        self.last_stat_bytes = self.total_bytes_received

    def toggle_serial(self):
        if self.comm_thread and self.comm_thread.isRunning():
            self.close_serial_backend()
        else:
            port = self.port_combo.currentText()
            if not port: return
            current_ports = [p.device for p in serial.tools.list_ports.comports()]
            if port not in current_ports:
                QMessageBox.warning(self, "连接失败", f"找不到物理串口 {port}！\n设备可能已被拔出或不存在。")
                self.refresh_ports()
                return
            try: baud = int(self.baud_combo.currentText().strip())
            except ValueError: return
                
            if self.time_history.total_count > 0:
                last_time = self.time_history.get_val_at_abs(self.time_history.total_count - 1)
                if last_time is not None:
                    self.time_offset = last_time
            else:
                self.time_offset = 0.0
            
            self._reset_dynamic_time_axis(keep_time=True)
            self.comm_thread = SerialThread(port, baud)
            self.comm_thread.data_received.connect(self.handle_batch_matrix)
            self.comm_thread.serial_error.connect(self.handle_serial_exception)
            self.comm_thread.start()
            
            self.btn_connect.setText("关闭串口")
            self.btn_connect.setStyleSheet("background-color: #d9534f;")
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)

    def close_serial_backend(self):
        if self.comm_thread:
            self.comm_thread.stop()
            self.comm_thread = None
        self.btn_connect.setText("打开串口")
        self.btn_connect.setStyleSheet("background-color: #007acc;")
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.current_fps = 0.0
        self.current_kbps = 0.0

    def handle_serial_exception(self, error_msg):
        self.close_serial_backend()
        QMessageBox.critical(self, "串口异常", error_msg)
        
    def send_tx_data(self):
        if not self.comm_thread or not self.comm_thread.running:
            QMessageBox.warning(self, "错误", "请先打开串口！")
            return
        data_str = self.txt_tx.toPlainText()
        if not data_str: return
        if self.chk_hex_tx.isChecked():
            try:
                data = bytes.fromhex(data_str)
            except ValueError:
                QMessageBox.warning(self, "错误", "HEX 数据格式不合法！请检查是否包含非十六进制字符。")
                return
        else:
            data = data_str.encode('utf-8')
        self.comm_thread.send_data(data)

    def toggle_display_pause(self):
        self.is_display_paused = not self.is_display_paused
        if self.is_display_paused:
            self.btn_pause.setText("恢复显示")
            self.btn_pause.setStyleSheet("background-color: #ff9933; color: black;")
            self.paused_length = self.data_history[0].total_count if self.data_history else 0
        else:
            self.btn_pause.setText("暂停显示")
            self.btn_pause.setStyleSheet("background-color: #007acc; color: white;")

    def toggle_measurement_lines(self):
        self.is_meas_active = not self.is_meas_active
        if self.is_meas_active:
            self.btn_meas.setText("双线测量: 开")
            self.btn_meas.setStyleSheet("background-color: #28a745; color: white;")
            self.btn_meas.setProperty("active", "true")
            
            self.meas_frac_A = 0.33
            self.meas_frac_B = 0.66
            
            self.meas_line_A.setVisible(True)
            self.meas_line_B.setVisible(True)
            self.meas_hud_label.show()
            self.sync_cursors_to_screen()
        else:
            self.btn_meas.setText("双线测量: 关")
            self.btn_meas.setStyleSheet("background-color: #555555; color: white;")
            self.btn_meas.setProperty("active", "false")
            self.meas_line_A.setVisible(False)
            self.meas_line_B.setVisible(False)
            self.meas_hud_label.hide()
        self.btn_meas.style().unpolish(self.btn_meas)
        self.btn_meas.style().polish(self.btn_meas)

    def calculate_measurement_delta(self):
        if not self.is_meas_active: return
        pos_A = self.meas_line_A.getXPos()
        pos_B = self.meas_line_B.getXPos()
        
        left_pos, right_pos = (pos_A, pos_B) if pos_A <= pos_B else (pos_B, pos_A)
        delta_t = right_pos - left_pos 
        
        if delta_t > 0.0:
            freq = 1000.0 / delta_t  
            freq_str = f"{freq:.2f} Hz" if freq < 1000 else f"{freq/1000.0:.3f} kHz"
        else:
            freq_str = "N/A"
            
        html_text = "<b style='color:#ffcc00;'>双线测量结果</b><br/>"
        html_text += "<table style='border-collapse: collapse; margin-top: 4px; color:#e0e0e0;'>"
        html_text += f"<tr><td style='padding-right:10px;'>游标 A:</td><td>{pos_A:.2f} ms</td></tr>"
        html_text += f"<tr><td style='padding-right:10px;'>游标 B:</td><td>{pos_B:.2f} ms</td></tr>"
        html_text += f"<tr><td style='padding-right:10px;'>时间差 Δt:</td><td style='color:#00ffcc;'>{delta_t:.3f} ms</td></tr>"
        html_text += f"<tr><td style='padding-right:10px;'>频  率 f:</td><td style='color:#00ffcc;'>{freq_str}</td></tr>"
        html_text += "</table>"
        
        if self.data_history and self.data_history[0].total_count > 0:
            current_len = self.paused_length if self.is_display_paused else self.data_history[0].total_count
            earliest_abs = max(0, current_len - self.max_memory_points)
            use_real_time = (self.combo_x_axis.currentIndex() == 0)
            interval = self.spin_interval.value()
            prec = self.spin_precision.value()
            
            def get_idx_at_x(target_x):
                if use_real_time:
                    t_slice = self.time_history.get_data_slice(earliest_abs, current_len)
                    if len(t_slice) == 0: return -1
                    rel_idx = np.searchsorted(t_slice, target_x)
                    if rel_idx >= len(t_slice): rel_idx = len(t_slice) - 1
                    if rel_idx > 0 and abs(t_slice[rel_idx-1] - target_x) < abs(t_slice[rel_idx] - target_x):
                        rel_idx -= 1
                    return earliest_abs + rel_idx
                else:
                    return int(round(target_x / interval))

            idx_left = get_idx_at_x(left_pos)
            idx_right = get_idx_at_x(right_pos)
            
            if earliest_abs <= idx_left < current_len and earliest_abs <= idx_right < current_len:
                has_channel_data = False
                ch_html = "<table style='border-collapse: collapse; margin-top: 6px; border-top: 1px solid #555; padding-top: 6px;'>"
                ch_html += "<tr><td style='padding-right:12px; color:#aaa;'>通道</td>"
                ch_html += "<td style='padding-right:12px; color:#aaa;'>ΔY</td>"
                ch_html += "<td style='color:#aaa;'>斜率(Y/ms)</td></tr>"
                
                for ch_idx in range(len(self.data_history)):
                    if ch_idx >= len(self.channel_widgets):
                        break
                    if self.channel_widgets[ch_idx]["checkbox"].isChecked():
                        y_left = self.data_history[ch_idx].get_val_at_abs(idx_left)
                        y_right = self.data_history[ch_idx].get_val_at_abs(idx_right)
                        
                        if y_left is not None and y_right is not None:
                            has_channel_data = True
                            name = self.channel_widgets[ch_idx]["name_edit"].text().strip() or f"CH{ch_idx+1}"
                            color = self.channel_colors[ch_idx]
                            
                            delta_y = y_right - y_left
                            slope = delta_y / delta_t if delta_t > 0 else 0.0
                            
                            ch_html += f"<tr style='color:{color}; font-weight:bold;'>"
                            ch_html += f"<td style='padding-right:12px;'>{name}</td>"
                            ch_html += f"<td style='padding-right:12px;'>{delta_y:+.{prec}f}</td>"
                            ch_html += f"<td>{slope:+.{prec}f}</td>"
                            ch_html += "</tr>"
                ch_html += "</table>"
                if has_channel_data: html_text += ch_html

        self.meas_hud_label.setText(html_text)
        self.meas_hud_label.adjustSize()
        self.meas_hud_label.move(10, 10)

    def sync_cursors_to_screen(self):
        if not self.is_meas_active or self.plot_widget is None:return
        xr = self.plot_widget.plotItem.vb.viewRange()[0]
        span = xr[1] - xr[0]

        self.meas_frac_A = max(0.005, min(0.995, getattr(self, 'meas_frac_A', 0.33)))
        self.meas_frac_B = max(0.005, min(0.995, getattr(self, 'meas_frac_B', 0.66)))
        
        self.meas_line_A.blockSignals(True)
        self.meas_line_B.blockSignals(True)
        
        self.meas_line_A.setValue(xr[0] + self.meas_frac_A * span)
        self.meas_line_B.setValue(xr[0] + self.meas_frac_B * span)
            
        self.meas_line_A.blockSignals(False)
        self.meas_line_B.blockSignals(False)
        self.calculate_measurement_delta()
        
    def on_meas_line_A_dragged(self):
        if not self.is_meas_active: return
        xr = self.plot_widget.plotItem.vb.viewRange()[0]
        span = xr[1] - xr[0]
        if span > 0:
            raw_frac = (self.meas_line_A.getXPos() - xr[0]) / span
            # 限制比例在 0.5% 到 99.5% 之间
            self.meas_frac_A = max(0.005, min(0.995, raw_frac))
            
            if raw_frac < 0.005 or raw_frac > 0.995:
                self.meas_line_A.blockSignals(True)
                self.meas_line_A.setValue(xr[0] + self.meas_frac_A * span)
                self.meas_line_A.blockSignals(False)
                
        self.calculate_measurement_delta()

    def on_meas_line_B_dragged(self):
        if not self.is_meas_active: return
        xr = self.plot_widget.plotItem.vb.viewRange()[0]
        span = xr[1] - xr[0]
        if span > 0:
            raw_frac = (self.meas_line_B.getXPos() - xr[0]) / span
            self.meas_frac_B = max(0.005, min(0.995, raw_frac))
            
            if raw_frac < 0.005 or raw_frac > 0.995:
                self.meas_line_B.blockSignals(True)
                self.meas_line_B.setValue(xr[0] + self.meas_frac_B * span)
                self.meas_line_B.blockSignals(False)
                
        self.calculate_measurement_delta()

    def bulk_channel_checkbox(self, checked):
        for widgets in self.channel_widgets:
            widgets["checkbox"].setChecked(checked)

    def toggle_auto_scale_y(self):
        self.auto_scale_y = not self.auto_scale_y
        if self.auto_scale_y:
            self.plot_widget.enableAutoRange(axis='y', enable=True)
            self.plot_widget.plotItem.vb.setMouseEnabled(y=False)
            if self.fft_plot is not None:
                self.fft_plot.enableAutoRange(axis='y', enable=True)
                self.fft_plot.plotItem.vb.setMouseEnabled(y=False)
            self.btn_autoscale.setText("Y轴自适应: 开")
            self.btn_autoscale.setProperty("active", "true")
        else:
            self.plot_widget.disableAutoRange(axis='y')
            self.plot_widget.plotItem.vb.setMouseEnabled(y=True)
            if self.fft_plot is not None:
                self.fft_plot.disableAutoRange(axis='y')
                self.fft_plot.plotItem.vb.setMouseEnabled(y=True)
            self.btn_autoscale.setText("Y轴自适应: 关")
            self.btn_autoscale.setProperty("active", "false")
        self.btn_autoscale.style().unpolish(self.btn_autoscale)
        self.btn_autoscale.style().polish(self.btn_autoscale)

    def on_view_manually_changed(self, *args):
        if getattr(self, '_setting_range', False): return
        if not self.data_history: return
        interval = self.spin_interval.value()
        view_range = self.plot_widget.plotItem.vb.viewRange()
        current_len = self.data_history[0].total_count
        earliest_abs = max(0, current_len - self.max_memory_points)
        use_real_time = (self.combo_x_axis.currentIndex() == 0)
        
        if getattr(self.vofa_timeline, 'drag_mode', None) is not None: return
        
        if use_real_time:
            t_slice = self.time_history.get_data_slice(earliest_abs, current_len)
            if len(t_slice) > 0:
                idx_start = np.searchsorted(t_slice, view_range[0][0])
                idx_end = np.searchsorted(t_slice, view_range[0][1])
                actual_visible = max(10, idx_end - idx_start)
                new_start_abs = earliest_abs + idx_start
            else:
                actual_visible = self.visible_points
                new_start_abs = self.view_start_abs
        else:
            new_start_abs = max(earliest_abs, int(view_range[0][0] / interval))
            actual_visible = max(10, int((view_range[0][1] - view_range[0][0]) / interval))
            
        if self.auto_follow_x:
            if abs(actual_visible - self.visible_points) > 2:
                self.visible_points = actual_visible
                self.spin_visible_points.blockSignals(True)
                self.spin_visible_points.setValue(self.visible_points)
                self.spin_visible_points.blockSignals(False)
            elif new_start_abs < (current_len - 15):
                self.auto_follow_x = False
                self.btn_go_latest.setText("跟随已解")
                self.btn_go_latest.setStyleSheet("background-color: #555555; min-width: 80px;")
                self.view_start_abs = new_start_abs
        else:
            self.visible_points = actual_visible
            self.view_start_abs = new_start_abs
            self.spin_visible_points.blockSignals(True)
            self.spin_visible_points.setValue(self.visible_points)
            self.spin_visible_points.blockSignals(False)

    def on_timeline_range_changed(self, new_start, new_width):
        current_len = self.data_history[0].total_count if self.data_history else 0
        use_real_time = (self.combo_x_axis.currentIndex() == 0)
        
        if self.vofa_timeline.drag_mode == 'red_dot':
            self.visible_points = new_width
            if not self.auto_follow_x: self.view_start_abs = new_start
        else:
            is_pin_to_latest = (new_start + new_width >= current_len - 12)
            if is_pin_to_latest:
                self.force_go_latest()
            else:
                self.auto_follow_x = False
                self.btn_go_latest.setText("跟随已解")
                self.btn_go_latest.setStyleSheet("background-color: #555555; min-width: 80px;")
                self.view_start_abs = new_start
                self.visible_points = new_width
        
        self.spin_visible_points.blockSignals(True)
        self.spin_visible_points.setValue(self.visible_points)
        self.spin_visible_points.blockSignals(False)
        
        interval = self.spin_interval.value()
        self._setting_range = True
        if self.auto_follow_x:
            end_abs = current_len
            start_abs = max(0, current_len - self.visible_points)
        else:
            start_abs = self.view_start_abs
            end_abs = self.view_start_abs + self.visible_points
            
        if use_real_time:
            t_slice = self.time_history.get_data_slice(start_abs, end_abs)
            if len(t_slice) >= 2: self.plot_widget.setXRange(t_slice[0], t_slice[-1], padding=0)
        else:
            self.plot_widget.setXRange(start_abs * interval, end_abs * interval, padding=0)
        self._setting_range = False

    def on_max_cache_changed(self, value):
        self.max_memory_points = value
        self.time_history.resize_buffer(value)
        for buf in self.data_history: buf.resize_buffer(value)
        self.force_go_latest()

    def on_interval_changed(self, value):
        if self._updating_interval_display:
            return
        self.configured_interval_ms = float(value)
        self.dynamic_interval_ms = max(0.001, self.dynamic_interval_ms)

    def on_x_axis_mode_changed(self, _idx):
        self._sync_interval_spinbox_to_mode()
        self.force_go_latest()

    def _sync_interval_spinbox_to_mode(self):
        if not hasattr(self, 'spin_interval'):
            return
        use_dynamic = (self.combo_x_axis.currentIndex() == 0)
        display_value = self.dynamic_interval_ms if use_dynamic else self.configured_interval_ms
        self._updating_interval_display = True
        self.spin_interval.setEnabled(not use_dynamic)
        self.spin_interval.setValue(max(0.001, float(display_value)))
        self._updating_interval_display = False

    def on_dynamic_time_window_changed(self, value):
        self.dynamic_time_window_s = float(value)
        self.dynamic_time_samples.clear()

    def on_visible_points_changed(self, value):
        self.visible_points = value
        if not self.auto_follow_x:
            interval = self.spin_interval.value()
            use_real_time = (self.combo_x_axis.currentIndex() == 0)
            self._setting_range = True
            if use_real_time:
                end_abs = min(self.time_history.total_count, self.view_start_abs + self.visible_points)
                t_slice = self.time_history.get_data_slice(self.view_start_abs, end_abs)
                if len(t_slice) >= 2: self.plot_widget.setXRange(t_slice[0], t_slice[-1], padding=0)
            else:
                self.plot_widget.setXRange(self.view_start_abs * interval, (self.view_start_abs + self.visible_points) * interval, padding=0)
            self._setting_range = False

    def update_curves_style(self, force=False):
        mode = self.combo_draw_mode.currentIndex()
        width = self.spin_linewidth.value()
        stacked = self.cb_stacked_mode.isChecked()
        show_symbols = (self.visible_points <= 1500)
        
        if not force and mode == self.last_draw_mode and width == self.last_line_width and show_symbols == self.last_show_symbols and stacked == self.last_stacked_mode: return
            
        self.last_draw_mode = mode; self.last_line_width = width; self.last_show_symbols = show_symbols; self.last_stacked_mode = stacked
        
        for i, curve in enumerate(self.curves):
            if i >= len(self.channel_colors): break
            color = self.channel_colors[i]
            pen = pg.mkPen(color=color, width=width)
            
            if mode == 0 or mode == 1:  
                curve.setPen(pen)
                curve.setSymbol(None)
            elif mode == 2: 
                if show_symbols:
                    curve.setPen(None); curve.setSymbol('o'); curve.setSymbolSize(max(3, width * 2 + 1)); curve.setSymbolBrush(color); curve.setSymbolPen(None)
                else:
                    curve.setPen(pen); curve.setSymbol(None)
            elif mode == 3:  
                curve.setPen(pen)
                if show_symbols:
                    curve.setSymbol('o'); curve.setSymbolSize(max(3, width * 2 + 1)); curve.setSymbolBrush(color); curve.setSymbolPen(None)
                else:
                    curve.setSymbol(None)

    def mouse_moved(self, evt):
        self.last_mouse_pos = evt

    def on_plot_mouse_leave(self, event):
        """当鼠标彻底移出波形区域时，清理所有悬浮UI"""
        self.last_mouse_pos = None

        # 隐藏十字线
        if hasattr(self, 'plot_widget'):
            try:
                self.plot_widget.v_line.setVisible(False)
                self.plot_widget.h_line.setVisible(False)
                self.plot_widget.crosshair_dots.setVisible(False)
            except RuntimeError:
                pass

        # 隐藏所有悬浮标签
        try:
            self.time_hud_label.hide()
        except RuntimeError:
            pass
        for lbl in self.hud_labels:
            try:
                lbl.hide()
            except RuntimeError:
                pass

        # 调用父类 leaveEvent
        if hasattr(self, 'plot_widget'):
            try:
                super(pg.PlotWidget, self.plot_widget).leaveEvent(event)
            except RuntimeError:
                pass

    def create_channel_ui(self, ch_idx):
        def_color = self.default_colors[ch_idx % len(self.default_colors)]
        saved_color = self.settings.value(f"channel_color_{ch_idx}", def_color)
        if not isinstance(saved_color, str) or not saved_color.startswith('#') or len(saved_color) != 7:
            saved_color = def_color
            
        saved_name = self.settings.value(f"channel_name_{ch_idx}", f"CH {ch_idx + 1}")
        saved_checked = self.settings.value(f"channel_checked_{ch_idx}", "true") == "true"
        
        if ch_idx < len(self.channel_colors): 
            self.channel_colors[ch_idx] = saved_color
        else: 
            self.channel_colors.append(saved_color)

        # 时域曲线
        curve = self.plot_widget.plot()
        curve.setVisible(saved_checked)
        self.curves.append(curve)
        
        # 频域曲线
        if self.fft_plot is not None:
            fft_curve = self.fft_plot.plot(pen=pg.mkPen(color=saved_color, width=self.spin_linewidth.value()))
            fft_curve.setVisible(saved_checked)
        else:
            fft_curve = None
        self.fft_curves.append(fft_curve)
        
        # HUD 标签
        lbl = pg.TextItem(anchor=(0, 0.5))
        lbl.setZValue(100) 
        lbl.hide()
        self.plot_widget.addItem(lbl, ignoreBounds=True)
        self.hud_labels.append(lbl)
        
        grid = QGridLayout()
        grid.setSpacing(4); grid.setContentsMargins(0, 0, 0, 0)
        
        cb = QCheckBox(); cb.setChecked(saved_checked); cb.setFixedWidth(16)
        name_edit = QLineEdit(); name_edit.setText(saved_name); name_edit.setMinimumWidth(40)  
        color_btn = QPushButton(); color_btn.setFixedSize(16, 16); color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        val_label = QLabel("0.00"); val_label.setFont(pg.Qt.QtGui.QFont('Consolas', 10))
        val_label.setMinimumWidth(75)
        
        grid.addWidget(cb, 0, 0, Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(color_btn, 0, 1, Qt.AlignmentFlag.AlignVCenter)
        grid.setColumnStretch(2, 1); grid.setColumnStretch(3, 0)
        
        def adjust_layout_by_text():
            text = name_edit.text()
            metrics = name_edit.fontMetrics()
            if metrics.horizontalAdvance(text) > 75:
                grid.removeWidget(name_edit); grid.removeWidget(val_label)
                grid.addWidget(name_edit, 0, 2, 1, 2, Qt.AlignmentFlag.AlignVCenter)
                grid.addWidget(val_label, 1, 2, 1, 2, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                val_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            else:
                grid.removeWidget(name_edit); grid.removeWidget(val_label)
                grid.addWidget(name_edit, 0, 2, 1, 1, Qt.AlignmentFlag.AlignVCenter)
                grid.addWidget(val_label, 0, 3, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                val_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        name_edit.textChanged.connect(adjust_layout_by_text)
        adjust_layout_by_text() 
        self.channel_layout.addLayout(grid)
        
        cb.toggled.connect(lambda checked, c=curve, fc=fft_curve: [c.setVisible(checked), fc.setVisible(checked) if fc is not None else None])
        color_btn.clicked.connect(lambda checked, idx=ch_idx: self.open_color_picker(idx))
        
        self.channel_widgets.append({"checkbox": cb, "name_edit": name_edit, "color_btn": color_btn, "label": val_label})
        self.apply_channel_style(ch_idx, saved_color)
        self.update_curves_style(force=True)

    def open_color_picker(self, ch_idx):
        current_hex = self.channel_colors[ch_idx] if ch_idx < len(self.channel_colors) else '#FFFFFF'
        new_color = QColorDialog.getColor(QColor(current_hex), self, f"选择通道颜色")
        if new_color.isValid(): self.apply_channel_style(ch_idx, new_color.name())

    def apply_channel_style(self, ch_idx, hex_color):
        if ch_idx < len(self.channel_colors): 
            self.channel_colors[ch_idx] = hex_color
        self.update_curves_style(force=True)
        if ch_idx < len(self.fft_curves) and self.fft_curves[ch_idx] is not None:
            self.fft_curves[ch_idx].setPen(pg.mkPen(color=hex_color, width=max(1, self.spin_linewidth.value())))
        self.channel_widgets[ch_idx]["color_btn"].setStyleSheet(f"background-color: {hex_color}; border: 1px solid #ffffff;")
        self.channel_widgets[ch_idx]["label"].setStyleSheet(f"color: {hex_color}; font-weight: bold;")
        self.hud_labels[ch_idx].color_hex = hex_color
        # 同步颜色到所有 FFT 窗口的十字光标标签
        for sub in self.mdi_area.subWindowList():
            if sub.property('window_type') == 'fft':
                w = sub.widget()
                if hasattr(w, 'fft_channel_labels') and ch_idx < len(w.fft_channel_labels):
                    w.fft_channel_labels[ch_idx].color_hex = hex_color

    def handle_batch_matrix(self, matrix, t_array):
        num_signals = matrix.shape[0]
        frames = matrix.shape[1]
        self.total_frames_received += frames
        self.total_bytes_received += frames * (num_signals * 4 + 4)

        old_num_channels = len(self.data_history)
        while len(self.data_history) > num_signals:
            self.data_history.pop() # 移除数据缓存
            # 从时域图表中移除曲线
            curve = self.curves.pop()
            self.plot_widget.removeItem(curve)
            # 从频域图表中移除 FFT 曲线
            fft_curve = self.fft_curves.pop()
            if fft_curve is not None:
                self.fft_plot.removeItem(fft_curve)
            # 移除悬浮标签
            lbl = self.hud_labels.pop()
            self.plot_widget.removeItem(lbl)
            # 移除所有 FFT 窗口的十字光标标签和 mag 缓存
            for sub in self.mdi_area.subWindowList():
                if sub.property('window_type') == 'fft':
                    w = sub.widget()
                    if hasattr(w, 'fft_channel_labels') and w.fft_channel_labels:
                        fft_lbl = w.fft_channel_labels.pop()
                        if hasattr(w, 'fft_plot'):
                            w.fft_plot.removeItem(fft_lbl)
                    if hasattr(w, 'fft_mags'):
                        stale = [k for k in w.fft_mags if k >= len(self.data_history)]
                        for k in stale:
                            del w.fft_mags[k]
            # 销毁左侧面板的 UI 控件
            widgets = self.channel_widgets.pop()
            widgets["checkbox"].deleteLater()
            widgets["name_edit"].deleteLater()
            widgets["color_btn"].deleteLater()
            widgets["label"].deleteLater()

        # 当接收到的通道数增加时，创建新通道
        while len(self.data_history) < num_signals:
            self.data_history.append(CircularBuffer(self.max_memory_points))
            self.create_channel_ui(len(self.data_history) - 1)

        # 刷新 IMU 通道列表
        if len(self.data_history) != old_num_channels:
            self._refresh_all_imu_channels()

        self.time_history.extend(self._make_dynamic_time_array(frames))
        for i in range(num_signals): 
            self.data_history[i].extend(matrix[i])

    def force_go_latest(self):
        self.auto_follow_x = True
        self.btn_go_latest.setText("拉到最新")
        self.btn_go_latest.setStyleSheet("background-color: #28a745; min-width: 80px;")
                    
    def update_time_plot(self, plot_widget, curves_list, chunk_start, chunk_end, x_data_full, is_stacked, mode, is_text_frame, enable_hud=False):
        """更新时域波形图，指定 plot_widget 和曲线列表"""
        # ===== 确保 curves_list 长度与 data_history 一致 =====
        num_channels = len(self.data_history)
        while len(curves_list) < num_channels:
            color = self.channel_colors[len(curves_list)] if len(curves_list) < len(self.channel_colors) else '#FFFFFF'
            curve = plot_widget.plot(pen=pg.mkPen(color=color, width=self.spin_linewidth.value()))
            curves_list.append(curve)
        while len(curves_list) > num_channels:
            curve = curves_list.pop()
            plot_widget.removeItem(curve)

        # 应用当前绘图样式（线型、宽度、符号等）
        draw_mode = self.combo_draw_mode.currentIndex()
        line_width = self.spin_linewidth.value()
        show_symbols = (self.visible_points <= 1500)
        for i, curve in enumerate(curves_list):
            if i >= len(self.channel_colors):
                break
            try:
                color = self.channel_colors[i]
                pen = pg.mkPen(color=color, width=line_width)
                if draw_mode == 0 or draw_mode == 1:  # 阶梯线或曲线
                    curve.setPen(pen)
                    curve.setSymbol(None)
                elif draw_mode == 2:  # 散点
                    if show_symbols:
                        curve.setPen(None)
                        curve.setSymbol('o')
                        curve.setSymbolSize(max(3, line_width * 2 + 1))
                        curve.setSymbolBrush(color)
                        curve.setSymbolPen(None)
                    else:
                        curve.setPen(pen)
                        curve.setSymbol(None)
                elif draw_mode == 3:  # 连线+散点
                    curve.setPen(pen)
                    if show_symbols:
                        curve.setSymbol('o')
                        curve.setSymbolSize(max(3, line_width * 2 + 1))
                        curve.setSymbolBrush(color)
                        curve.setSymbolPen(None)
                    else:
                        curve.setSymbol(None)
            except RuntimeError:
                continue

        shared_x_step = None
        stacked_idx = 0

        for i in range(len(self.data_history)):
            if self.channel_widgets[i]["checkbox"].isChecked():
                y_data = self.data_history[i].get_data_slice(chunk_start, chunk_end)
                if len(x_data_full) > 0 and len(x_data_full) == len(y_data):
                    if is_stacked:
                        y_min, y_max = y_data.min(), y_data.max()
                        span = y_max - y_min if y_max != y_min else 1.0
                        y_draw = (y_data - y_min) / span - stacked_idx * 1.5
                        stacked_idx += 1
                    else:
                        y_draw = y_data

                    try:
                        curve = curves_list[i]
                        if mode == 0:  # 阶梯线
                            if shared_x_step is None or len(shared_x_step) != len(x_data_full) * 2:
                                shared_x_step = np.empty(2 * len(x_data_full), dtype=x_data_full.dtype)
                                shared_x_step[0::2] = x_data_full
                                if self.combo_x_axis.currentIndex() == 0:
                                    dt = (x_data_full[-1] - x_data_full[0]) / (len(x_data_full)-1) if len(x_data_full) > 1 else self.spin_interval.value()
                                    shared_x_step[1::2] = np.append(x_data_full[1:], x_data_full[-1] + dt)
                                else:
                                    interval = self.spin_interval.value()
                                    shared_x_step[1::2] = (np.arange(chunk_start + 1, chunk_end + 1, dtype=np.float32)) * interval
                            y_step = np.empty(2 * len(y_draw), dtype=np.float32)
                            y_step[0::2] = y_draw
                            y_step[1::2] = y_draw
                            curve.setData(x=shared_x_step, y=y_step, skipFiniteCheck=True)
                        else:
                            curve.setData(x=x_data_full, y=y_draw, skipFiniteCheck=True)
                    except RuntimeError:
                        continue
                else:
                    try:
                        curves_list[i].setData([], [], skipFiniteCheck=True)
                    except RuntimeError:
                        continue
            else:
                if i < len(curves_list):
                    try:
                        curves_list[i].setData([], [], skipFiniteCheck=True)
                    except RuntimeError:
                        continue

        # 如果启用 HUD，则更新主窗口的悬浮标签（仅主窗口）
        if enable_hud:
            self.render_independent_labels(is_text_frame)

    def update_fft_plot(self, fft_plot, fft_curves_list, chunk_start, chunk_end, x_data_full, interval, use_real_time, update_hud=False):
        """更新频域频谱图，指定 fft_plot 和曲线列表"""
        parent_widget = fft_plot.parent()  # container QWidget
        # ===== 确保 fft_curves_list 长度与 data_history 一致 =====
        num_channels = len(self.data_history)
        while len(fft_curves_list) < num_channels:
            color = self.channel_colors[len(fft_curves_list)] if len(fft_curves_list) < len(self.channel_colors) else '#FFFFFF'
            curve = fft_plot.plot(pen=pg.mkPen(color=color, width=max(1, self.spin_linewidth.value())))
            fft_curves_list.append(curve)
            # 为每个新通道创建对应的十字光标标签
            if parent_widget and hasattr(parent_widget, 'fft_channel_labels'):
                lbl = pg.TextItem(anchor=(0, 0.5))
                lbl.setZValue(100)
                lbl.hide()
                fft_plot.addItem(lbl, ignoreBounds=True)
                parent_widget.fft_channel_labels.append(lbl)
        while len(fft_curves_list) > num_channels:
            curve = fft_curves_list.pop()
            fft_plot.removeItem(curve)
            # 移除多余标签
            if parent_widget and hasattr(parent_widget, 'fft_channel_labels') and parent_widget.fft_channel_labels:
                lbl = parent_widget.fft_channel_labels.pop()
                fft_plot.removeItem(lbl)

        html_text = "<b style='color:#ffffff; font-size:11px;'>各通道频谱峰值:</b><br/>"
        html_text += "<table style='border-collapse: collapse; margin-top: 4px;'>"
        has_peaks = False

        for i in range(len(self.data_history)):
            if self.channel_widgets[i]["checkbox"].isChecked():
                y_data = self.data_history[i].get_data_slice(chunk_start, chunk_end)
                n = len(y_data)
                if n > 10:
                    y_centered = y_data - np.mean(y_data)
                    window = np.hanning(n)
                    yf = np.fft.rfft(y_centered * window)

                    if use_real_time and len(x_data_full) > 1:
                        dt_ms = (x_data_full[-1] - x_data_full[0]) / (n-1)
                        if dt_ms <= 0:
                            dt_ms = interval
                        fs = 1000.0 / dt_ms
                    else:
                        fs = 1000.0 / interval

                    xf = np.fft.rfftfreq(n, d=1.0/fs)
                    mag = np.abs(yf) / n * 2.0

                    if len(mag) > 1:
                        mag[0] = 0

                    # 缓存 FFT 数据供十字光标使用
                    if parent_widget and hasattr(parent_widget, 'fft_mags'):
                        parent_widget.fft_mags[i] = mag
                        if parent_widget.fft_xf is None or len(parent_widget.fft_xf) != len(xf):
                            parent_widget.fft_xf = xf

                    channel_peaks = []
                    if len(mag) > 2:
                        local_max_mask = (mag[1:-1] > mag[:-2]) & (mag[1:-1] > mag[2:])
                        local_max_idx = np.where(local_max_mask)[0] + 1
                        for idx in local_max_idx:
                            channel_peaks.append((mag[idx], xf[idx]))

                    channel_peaks.sort(key=lambda x: x[0], reverse=True)
                    top3_peaks = channel_peaks[:3]

                    name = self.channel_widgets[i]["name_edit"].text().strip() or f"CH{i+1}"
                    color = self.channel_colors[i]

                    if top3_peaks:
                        has_peaks = True
                        for p_idx, (m, f) in enumerate(top3_peaks):
                            html_text += f"<tr style='color:{color};'>"
                            if p_idx == 0:
                                html_text += f"<td style='padding: 1px 8px 1px 0; font-weight:bold;'>{name}</td>"
                            else:
                                html_text += f"<td style='padding: 1px 8px 1px 0;'></td>"
                            html_text += f"<td style='padding: 1px 8px 1px 0;'>[{p_idx+1}] {f: >7.2f} Hz</td>"
                            html_text += f"<td style='padding: 1px 0;'>Amp: {m:.3f}</td>"
                            html_text += "</tr>"
                        html_text += "<tr><td colspan='3' style='height:2px;'></td></tr>"

                    try:
                        fft_curves_list[i].setData(x=xf, y=mag)
                    except RuntimeError:
                        pass
                else:
                    try:
                        fft_curves_list[i].setData([], [])
                    except RuntimeError:
                        pass
            else:
                if i < len(fft_curves_list):
                    try:
                        fft_curves_list[i].setData([], [])
                    except RuntimeError:
                        pass

        html_text += "</table>"

        # 清理过期的 mag 缓存
        if parent_widget and hasattr(parent_widget, 'fft_mags'):
            stale = [k for k in parent_widget.fft_mags if k >= num_channels]
            for k in stale:
                del parent_widget.fft_mags[k]

        # 渲染十字光标
        self.render_fft_crosshair(fft_plot, parent_widget)

        # ===== 更新 HUD（仅当 update_hud=True） =====
        if update_hud:
            if parent_widget and hasattr(parent_widget, 'fft_hud_label'):
                if has_peaks:
                    parent_widget.fft_hud_label.setText(html_text)
                    parent_widget.fft_hud_label.adjustSize()
                    margin_right = 10
                    margin_top = 10
                    x_pos = fft_plot.width() - parent_widget.fft_hud_label.width() - margin_right
                    parent_widget.fft_hud_label.move(max(10, x_pos), margin_top)
                    parent_widget.fft_hud_label.show()
                else:
                    parent_widget.fft_hud_label.hide()

    # ==================== IMU 姿态计算 ====================
    def _get_channel_value(self, ch_idx):
        """读取指定通道的最新值"""
        if ch_idx < 0 or ch_idx >= len(self.data_history):
            return 0.0
        if self.data_history[ch_idx].total_count == 0:
            return 0.0
        val = self.data_history[ch_idx].get_val_at_abs(
            self.data_history[ch_idx].total_count - 1)
        return float(val) if val is not None else 0.0

    @staticmethod
    def _quat_to_matrix(w, x, y, z):
        """四元数 → FLU 右手系旋转矩阵。

        坐标定义：+X 前，+Y 左，+Z 上。与欧拉角模式保持一致：
        roll/pitch 输入反向映射，等价于四元数 x/y 分量取反。
        """
        n = np.sqrt(w*w + x*x + y*y + z*z)
        if n < 1e-12:
            return np.eye(3, dtype=np.float32)
        w, x, y, z = w/n, x/n, y/n, z/n
        x, y = -x, -y
        return np.array([
            [1-2*y*y-2*z*z, 2*x*y-2*w*z, 2*x*z+2*w*y],
            [2*x*y+2*w*z, 1-2*x*x-2*z*z, 2*y*z-2*w*x],
            [2*x*z-2*w*y, 2*y*z+2*w*x, 1-2*x*x-2*y*y],
        ], dtype=np.float32)

    @staticmethod
    def _euler_to_matrix(roll, pitch, yaw):
        """欧拉角 ZYX (yaw-pitch-roll, 度) → FLU 右手系旋转矩阵。

        坐标定义：+X 前，+Y 左，+Z 上。输入角按当前 IMU 输出习惯映射：
        roll/pitch 正值分别等价于绕 -X/-Y 旋转。
        """
        r, p, y = np.radians(-roll), np.radians(-pitch), np.radians(yaw)
        cr, sr = np.cos(r), np.sin(r)
        cp, sp = np.cos(p), np.sin(p)
        cy, sy = np.cos(y), np.sin(y)
        # R = Rz(yaw) * Ry(-pitch_input) * Rx(-roll_input)
        return np.array([
            [cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr],
            [sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr],
            [-sp,   cp*sr,            cp*cr],
        ], dtype=np.float32)

    @staticmethod
    def _matrix_to_display_euler(R):
        """从当前显示矩阵反算用户视角的 roll/pitch/yaw（度）。"""
        p = np.arcsin(np.clip(-R[2, 0], -1.0, 1.0))
        cp = np.cos(p)
        if abs(cp) > 1e-6:
            r = np.arctan2(R[2, 1], R[2, 2])
            y = np.arctan2(R[1, 0], R[0, 0])
        else:
            r = 0.0
            y = np.arctan2(-R[0, 1], R[1, 1])
        return -np.degrees(r), -np.degrees(p), np.degrees(y)

    def update_imu_window(self, widget):
        """更新单个 IMU 窗口的姿态"""
        if not self.data_history:
            return
        mode = widget.mode_combo.currentIndex()
        sel = widget.ch_selectors
        if mode == 0:  # 四元数
            w = self._get_channel_value(sel[0].currentIndex() if sel[0].count() > 0 else -1)
            x = self._get_channel_value(sel[1].currentIndex() if sel[1].count() > 0 else -1)
            y = self._get_channel_value(sel[2].currentIndex() if sel[2].count() > 0 else -1)
            z = self._get_channel_value(sel[3].currentIndex() if sel[3].count() > 0 else -1)
            R = self._quat_to_matrix(w, x, y, z)
        else:  # 欧拉角
            roll = self._get_channel_value(sel[0].currentIndex() if sel[0].count() > 0 else -1)
            pitch = self._get_channel_value(sel[1].currentIndex() if sel[1].count() > 0 else -1)
            yaw = self._get_channel_value(sel[2].currentIndex() if sel[2].count() > 0 else -1)
            R = self._euler_to_matrix(roll, pitch, yaw)

        disp_roll, disp_pitch, disp_yaw = self._matrix_to_display_euler(R)

        # 构建 4x4 齐次变换矩阵
        mat = QMatrix4x4(
            R[0,0], R[0,1], R[0,2], 0,
            R[1,0], R[1,1], R[1,2], 0,
            R[2,0], R[2,1], R[2,2], 0,
            0,      0,      0,      1,
        )
        widget.box_mesh.resetTransform()
        widget.box_mesh.setTransform(mat)
        for item in getattr(widget, 'body_axis_items', []):
            item.resetTransform()
            item.setTransform(mat)
        if hasattr(widget, 'imu_angle_label'):
            widget.imu_angle_label.setText(
                f"Roll:  {disp_roll:+7.2f}°\n"
                f"Pitch: {disp_pitch:+7.2f}°\n"
                f"Yaw:   {disp_yaw:+7.2f}°\n"
                f"+X 前  +Y 左  +Z 上"
            )
            widget.imu_angle_label.adjustSize()

    def update_plot_display(self):
        if not self.data_history:
            return
        if getattr(self, '_resizing', False):
            return

        live_len = self.data_history[0].total_count
        if self.is_display_paused:
            current_len = self.paused_length
        else:
            current_len = live_len

        if self.combo_x_axis.currentIndex() == 0:
            x_axis_info = f"动态: {self.dynamic_fps:.1f} Hz / {self.dynamic_interval_ms:.3f} ms"
        else:
            x_axis_info = f"间隔: {self.configured_interval_ms:.3f} ms"
        self.lbl_buffer_status.setText(
            f"缓存: {min(live_len, self.max_memory_points)}/{self.max_memory_points} | "
            f"帧率: {self.current_fps:.0f} Hz | {x_axis_info} | 速率: {self.current_kbps:.1f} KB/s"
        )

        self.render_frame_counter += 1
        is_text_frame = (self.render_frame_counter % 2 == 0)

        if is_text_frame:
            prec = self.spin_precision.value()
            for i in range(len(self.data_history)):
                if i < len(self.channel_widgets):
                    last_val = self.data_history[i].get_val_at_abs(current_len - 1)
                    if last_val is not None:
                        self.channel_widgets[i]["label"].setText(f"{last_val:>.{prec}f}")

        earliest_abs = max(0, current_len - self.max_memory_points)
        interval = self.spin_interval.value()
        use_real_time = (self.combo_x_axis.currentIndex() == 0)
        is_stacked = self.cb_stacked_mode.isChecked()

        # 设置视图边界（仅主窗口）
        if current_len >= 2:
            x_min_limit, x_max_limit = None, None
            if use_real_time:
                t_slice = self.time_history.get_data_slice(earliest_abs, current_len)
                if len(t_slice) >= 2:
                    x_min_limit, x_max_limit = t_slice[0], t_slice[-1]
            else:
                x_min_limit = earliest_abs * interval
                x_max_limit = current_len * interval
            if x_min_limit is not None and x_max_limit is not None and (x_max_limit - x_min_limit > 0.01):
                span = x_max_limit - x_min_limit
                self.plot_widget.plotItem.vb.setLimits(xMin=x_min_limit, xMax=x_max_limit, maxXRange=span)
        else:
            self.plot_widget.plotItem.vb.setLimits(xMin=None, xMax=None, maxXRange=None)

        prec = self.spin_precision.value()
        if prec != self.last_precision:
            self.plot_widget.getAxis('left').precision = min(prec, 4)
            self.plot_widget.getAxis('right').precision = min(prec, 4)
            self.plot_widget.getAxis('bottom').precision = min(prec, 3)
            self.last_precision = prec

        self._setting_range = True
        if self.auto_follow_x and not self.is_display_paused:
            self.view_start_abs = max(earliest_abs, current_len - self.visible_points)
            if use_real_time:
                t_slice = self.time_history.get_data_slice(self.view_start_abs, current_len)
                if len(t_slice) >= 2:
                    self.plot_widget.setXRange(t_slice[0], t_slice[-1], padding=0)
            else:
                self.plot_widget.setXRange(self.view_start_abs * interval, current_len * interval, padding=0)
        self._setting_range = False

        self.vofa_timeline.update_state(
            total_count=current_len,
            view_start=self.view_start_abs,
            view_width=self.visible_points,
            auto_follow=self.auto_follow_x if not self.is_display_paused else False,
            max_len=self.max_memory_points
        )

        if self.auto_follow_x and not self.is_display_paused:
            chunk_start, chunk_end = self.view_start_abs, current_len
        else:
            chunk_start = max(earliest_abs, self.view_start_abs - self.visible_points)
            chunk_end = min(current_len, self.view_start_abs + self.visible_points * 2)

        if use_real_time:
            x_data_full = self.time_history.get_data_slice(chunk_start, chunk_end)
        else:
            x_data_full = np.arange(chunk_start, chunk_end, dtype=np.float32) * interval

        mode = self.combo_draw_mode.currentIndex()

        # ---- 更新主时域窗口 ----
        if self.plot_widget.isVisible():
            self.update_time_plot(self.plot_widget, self.curves, chunk_start, chunk_end, x_data_full, is_stacked, mode, is_text_frame, enable_hud=True)

        # ---- 更新其他时域子窗口 ----
        for sub in self.mdi_area.subWindowList():
            if sub is self.main_time_sub:
                continue  # 已更新
            if sub.property('window_type') == 'time' and sub.isVisible():
                widget = sub.widget()
                if hasattr(widget, 'plot_widget') and hasattr(widget, 'curves'):
                    self.update_time_plot(widget.plot_widget, widget.curves, chunk_start, chunk_end, x_data_full, is_stacked, mode, is_text_frame, enable_hud=False)

        # ---- 更新频域窗口 ----
        for sub in self.mdi_area.subWindowList():
            if sub.property('window_type') == 'fft' and sub.isVisible():
                widget = sub.widget()
                if hasattr(widget, 'fft_plot') and hasattr(widget, 'fft_curves'):
                    # 更新频谱数据，不更新HUD（HUD只有第一个频域窗口需要，但这里简化）
                    self.update_fft_plot(widget.fft_plot, widget.fft_curves, chunk_start, chunk_end, x_data_full, interval, use_real_time, update_hud=False)

        # ---- 更新 IMU 窗口 ----
        for sub in self.mdi_area.subWindowList():
            if sub.property('window_type') == 'imu' and sub.isVisible():
                widget = sub.widget()
                if hasattr(widget, 'box_mesh') and self.data_history:
                    self.update_imu_window(widget)

        # ---- 统计表格 ----
        active_left_tab = self.left_tabs.currentIndex()
        if active_left_tab == 1 and is_text_frame:
            active_channels = [i for i in range(len(self.data_history)) if self.channel_widgets[i]["checkbox"].isChecked()]
            self.table_stats.setRowCount(len(active_channels))
            row = 0
            for i in active_channels:
                y_data = self.data_history[i].get_data_slice(chunk_start, chunk_end)
                if len(y_data) > 0:
                    ymax, ymin = np.max(y_data), np.min(y_data)
                    vpp = ymax - ymin
                    mean = np.mean(y_data)
                    rms = np.sqrt(np.mean(y_data**2))
                    name = self.channel_widgets[i]["name_edit"].text().strip() or f"CH{i+1}"
                    color_hex = self.channel_colors[i]
                    brush = pg.mkBrush(color_hex)
                    vals = [name, f"{ymax:.{prec}f}", f"{ymin:.{prec}f}", f"{vpp:.{prec}f}", f"{mean:.{prec}f}", f"{rms:.{prec}f}"]
                    for col, text in enumerate(vals):
                        item = self.table_stats.item(row, col)
                        if not item:
                            item = QTableWidgetItem()
                            if col > 0:
                                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                            else:
                                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                            self.table_stats.setItem(row, col, item)
                        item.setText(text)
                        item.setForeground(brush)
                    row += 1

    def render_independent_labels(self, is_text_frame=False):
        if not hasattr(self, 'plot_widget'):
            return
            
        if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:
            self.plot_widget.v_line.setVisible(False)
            self.plot_widget.h_line.setVisible(False)
            self.time_hud_label.hide()
            self.plot_widget.crosshair_dots.setVisible(False)
            for lbl in self.hud_labels:
                try: lbl.hide()
                except RuntimeError: pass
            return

        if self.last_mouse_pos is not None and self.plot_widget.sceneBoundingRect().contains(self.last_mouse_pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(self.last_mouse_pos)
            x_val = mouse_point.x()
            interval = self.spin_interval.value()
            prec = self.spin_precision.value()
            use_real_time = (self.combo_x_axis.currentIndex() == 0)
            is_stacked = self.cb_stacked_mode.isChecked()

            if len(self.data_history) > 0:
                live_len = self.data_history[0].total_count
                current_len = self.paused_length if self.is_display_paused else live_len
                earliest_abs = max(0, current_len - self.max_memory_points)
                
                if use_real_time:
                    t_slice = self.time_history.get_data_slice(earliest_abs, current_len)
                    if len(t_slice) > 0:
                        rel_idx = np.searchsorted(t_slice, x_val)
                        if rel_idx >= len(t_slice):
                            rel_idx = len(t_slice) - 1
                        if rel_idx > 0 and abs(t_slice[rel_idx-1] - x_val) < abs(t_slice[rel_idx] - x_val):
                            rel_idx -= 1
                        
                        actual_start_abs = max(earliest_abs, max(0, self.time_history.total_count - self.time_history.max_len))
                        idx = actual_start_abs + rel_idx
                        current_time_ms = t_slice[rel_idx]
                    else:
                        return
                else:
                    idx = int(round(x_val / interval))
                    current_time_ms = idx * interval
                    if idx < earliest_abs or idx >= current_len:
                        return
                
                if earliest_abs <= idx < current_len:
                    if idx == getattr(self, 'last_crosshair_idx', -1) and not is_text_frame:
                        return
                    self.last_crosshair_idx = idx
                    self.plot_widget.v_line.setPos(current_time_ms)
                    self.plot_widget.v_line.setVisible(True)
                    self.plot_widget.h_line.setVisible(True)
                    
                    vb = self.plot_widget.plotItem.vb
                    view_range = vb.viewRange()

                    time_prec = min(prec, 4) if min(prec, 4) > 2 else 2
                    self.time_hud_label.setText(f"时间: {current_time_ms:.{time_prec}f} ms")
                    self.time_hud_label.adjustSize()
                    
                    scene_pos_top = vb.mapViewToScene(QPointF(float(current_time_ms), view_range[1][1]))
                    widget_pos_top = self.plot_widget.mapFromScene(scene_pos_top)
                    
                    lx_time, ly_time = widget_pos_top.x() + 10, 0
                    if lx_time + self.time_hud_label.width() > self.plot_widget.width():
                        lx_time = widget_pos_top.x() - self.time_hud_label.width() - 10
                    self.time_hud_label.move(int(lx_time), int(ly_time))
                    self.time_hud_label.show()

                    x_dots, y_dots, brush_dots = [], [], []
                    first_y_val = None
                    stacked_idx = 0
                    
                    for ch_idx in range(len(self.data_history)):
                        val = self.data_history[ch_idx].get_val_at_abs(idx)
                        is_visible = self.channel_widgets[ch_idx]["checkbox"].isChecked()
                        
                        if ch_idx < len(self.hud_labels):
                            lbl = self.hud_labels[ch_idx]
                            if is_visible and val is not None:
                                try:
                                    draw_val = val
                                    if is_stacked:
                                        y_data = self.data_history[ch_idx].get_data_slice(max(earliest_abs, current_len - self.visible_points), current_len)
                                        if len(y_data) > 0:
                                            ymin, ymax = y_data.min(), y_data.max()
                                            span = ymax - ymin if ymax != ymin else 1.0
                                            draw_val = (val - ymin) / span - stacked_idx * 1.5
                                    stacked_idx += 1

                                    x_dots.append(current_time_ms)
                                    y_dots.append(draw_val)
                                    brush_dots.append(pg.mkBrush(self.channel_colors[ch_idx]))

                                    custom_name = self.channel_widgets[ch_idx]["name_edit"].text().strip() or f"CH {ch_idx+1}"
                                    hex_color = getattr(lbl, 'color_hex', '#FFFFFF')
                                    plain_text = f"{custom_name}: {val:.{prec}f}"
                                    html_str = f'<div style="background-color: rgba(22,22,22,0.9); border: 1px solid {hex_color}; color: {hex_color}; font-size:11px; padding:2px; font-family: Consolas;">{plain_text}</div>'
                                    lbl.setHtml(html_str)

                                    view_range = vb.viewRange()
                                    span_x = view_range[0][1] - view_range[0][0]
                                    x_offset = span_x * 0.015

                                    fm = pg.Qt.QtGui.QFontMetrics(pg.Qt.QtGui.QFont('Consolas', 11))
                                    lbl_pixel_width = fm.horizontalAdvance(plain_text) + 0

                                    vb_width = vb.width()
                                    lbl_data_width = (lbl_pixel_width / vb_width) * span_x if vb_width > 0 else (span_x * 0.1)

                                    if current_time_ms + x_offset + lbl_data_width > view_range[0][1]:
                                        lbl.setAnchor((1, 0.5))
                                        lbl.setPos(current_time_ms - x_offset, draw_val)
                                    else:
                                        lbl.setAnchor((0, 0.5))
                                        lbl.setPos(current_time_ms + x_offset, draw_val)

                                    lbl.show()
                                except RuntimeError:
                                    pass

                    if x_dots:
                        self.plot_widget.crosshair_dots.setData(x=x_dots, y=y_dots, brush=brush_dots)
                        self.plot_widget.crosshair_dots.setVisible(True)
                    else:
                        self.plot_widget.crosshair_dots.setVisible(False)
                        
                    if first_y_val is not None:
                        self.plot_widget.h_line.setPos(first_y_val)
                    return
        self.plot_widget.v_line.setVisible(False)
        self.plot_widget.h_line.setVisible(False)
        self.time_hud_label.hide()
        self.plot_widget.crosshair_dots.setVisible(False)
        for lbl in self.hud_labels:
            try: lbl.hide()
            except RuntimeError: pass

    def render_fft_crosshair(self, fft_plot, widget):
        """渲染 FFT 频域图的十字光标和通道幅值标签（镜像时域 render_independent_labels）"""
        if widget is None:
            return

        if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:
            fft_plot.v_line.setVisible(False)
            fft_plot.h_line.setVisible(False)
            widget.fft_freq_hud_label.hide()
            fft_plot.crosshair_dots.setVisible(False)
            for lbl in widget.fft_channel_labels:
                try: lbl.hide()
                except RuntimeError: pass
            return

        if (widget.fft_last_mouse_pos is not None
                and fft_plot.sceneBoundingRect().contains(widget.fft_last_mouse_pos)):
            mouse_point = fft_plot.plotItem.vb.mapSceneToView(widget.fft_last_mouse_pos)
            freq_val = mouse_point.x()

            xf = widget.fft_xf
            if xf is None or len(xf) < 2:
                return

            # 限制在 Nyquist 范围内
            if freq_val < 0:
                freq_val = 0
            if freq_val > xf[-1]:
                freq_val = xf[-1]

            # 找最近的频率 bin
            bin_idx = int(np.searchsorted(xf, freq_val))
            if bin_idx >= len(xf):
                bin_idx = len(xf) - 1
            if bin_idx > 0 and abs(xf[bin_idx - 1] - freq_val) < abs(xf[bin_idx] - freq_val):
                bin_idx -= 1

            actual_freq = xf[bin_idx]

            # 与上一帧同一 bin → 跳过
            if bin_idx == getattr(widget, 'fft_last_bin_idx', -1):
                return
            widget.fft_last_bin_idx = bin_idx

            # 竖线
            fft_plot.v_line.setPos(actual_freq)
            fft_plot.v_line.setVisible(True)
            fft_plot.h_line.setVisible(True)

            # 频率标签（widget 坐标，顶部）
            widget.fft_freq_hud_label.setText(f"频率: {actual_freq:.2f} Hz")
            widget.fft_freq_hud_label.adjustSize()

            vb = fft_plot.plotItem.vb
            view_range = vb.viewRange()
            scene_pos_top = vb.mapViewToScene(QPointF(float(actual_freq), view_range[1][1]))
            widget_pos_top = fft_plot.mapFromScene(scene_pos_top)

            lx_freq, ly_freq = widget_pos_top.x() + 10, 0
            if lx_freq + widget.fft_freq_hud_label.width() > fft_plot.width():
                lx_freq = widget_pos_top.x() - widget.fft_freq_hud_label.width() - 10
            widget.fft_freq_hud_label.move(int(lx_freq), int(ly_freq))
            widget.fft_freq_hud_label.show()

            # 各通道幅值标签 + crosshair 圆点
            x_dots, y_dots, brush_dots = [], [], []
            first_y_val = None
            prec = self.spin_precision.value()

            for ch_idx in range(len(self.data_history)):
                is_visible = self.channel_widgets[ch_idx]["checkbox"].isChecked()

                if ch_idx < len(widget.fft_channel_labels):
                    lbl = widget.fft_channel_labels[ch_idx]
                    try:
                        if is_visible and ch_idx in widget.fft_mags:
                            mag = widget.fft_mags[ch_idx]
                            if bin_idx < len(mag):
                                mag_val = float(mag[bin_idx])

                                x_dots.append(actual_freq)
                                y_dots.append(mag_val)
                                brush_dots.append(pg.mkBrush(self.channel_colors[ch_idx]))

                                if first_y_val is None:
                                    first_y_val = mag_val

                                custom_name = self.channel_widgets[ch_idx]["name_edit"].text().strip() or f"CH {ch_idx+1}"
                                hex_color = self.channel_colors[ch_idx]
                                lbl.color_hex = hex_color
                                plain_text = f"{custom_name}: {mag_val:.{prec}f}"
                                html_str = f'<div style="background-color: rgba(22,22,22,0.9); border: 1px solid {hex_color}; color: {hex_color}; font-size:11px; padding:2px; font-family: Consolas;">{plain_text}</div>'
                                lbl.setHtml(html_str)

                                span_x = view_range[0][1] - view_range[0][0]
                                x_offset = span_x * 0.015
                                fm = pg.Qt.QtGui.QFontMetrics(pg.Qt.QtGui.QFont('Consolas', 11))
                                lbl_pixel_width = fm.horizontalAdvance(plain_text)
                                vb_width = vb.width()
                                lbl_data_width = (lbl_pixel_width / vb_width) * span_x if vb_width > 0 else (span_x * 0.1)

                                if actual_freq + x_offset + lbl_data_width > view_range[0][1]:
                                    lbl.setAnchor((1, 0.5))
                                    lbl.setPos(actual_freq - x_offset, mag_val)
                                else:
                                    lbl.setAnchor((0, 0.5))
                                    lbl.setPos(actual_freq + x_offset, mag_val)

                                lbl.show()
                            else:
                                lbl.hide()
                        else:
                            lbl.hide()
                    except RuntimeError:
                        pass

            # 更新 crosshair 圆点
            if x_dots:
                fft_plot.crosshair_dots.setData(x=x_dots, y=y_dots, brush=brush_dots)
                fft_plot.crosshair_dots.setVisible(True)
            else:
                fft_plot.crosshair_dots.setVisible(False)

            # 横线定位在第一个可见通道的幅值
            if first_y_val is not None:
                fft_plot.h_line.setPos(first_y_val)

            return

        # 鼠标不在绘图区域：全部隐藏
        fft_plot.v_line.setVisible(False)
        fft_plot.h_line.setVisible(False)
        widget.fft_freq_hud_label.hide()
        fft_plot.crosshair_dots.setVisible(False)
        for lbl in widget.fft_channel_labels:
            try: lbl.hide()
            except RuntimeError: pass

    def clear_data(self):
        for i in range(len(self.data_history)):
            self.data_history[i].clear()
            self.curves[i].setData([], [])
            if i < len(self.channel_widgets): 
                self.channel_widgets[i]["label"].setText("0.00")
            if i < len(self.fft_curves) and self.fft_curves[i] is not None:
                self.fft_curves[i].setData([], [])
        self.time_history.clear()
        self._reset_dynamic_time_axis(keep_time=False)
        for lbl in self.hud_labels:
            try: lbl.hide()
            except RuntimeError: pass
        self.time_hud_label.hide()
        self.plot_widget.crosshair_dots.setData([], [])
        
        self.table_stats.clearContents()
        self.table_stats.setRowCount(0)
        
        self.force_go_latest()

    def export_to_csv(self):
        if not self.data_history or self.data_history[0].total_count == 0:
            QMessageBox.warning(self, "导出失败", "当前缓存内没有任何波形数据！")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出波形数据", "", "CSV Files (*.csv)")
        if not file_path: return
        
        try:
            current_len = self.data_history[0].total_count
            earliest_abs = max(0, current_len - self.max_memory_points)
            total_points = current_len - earliest_abs
            num_channels = len(self.data_history)
            use_real_time = (self.combo_x_axis.currentIndex() == 0)
            
            all_y_data = []
            for i in range(num_channels):
                y = self.data_history[i].get_data_slice(earliest_abs, current_len)
                all_y_data.append(y)
                
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if use_real_time:
                    headers = ["Time_ms"] + [self.channel_widgets[i]["name_edit"].text().strip() or f"CH_{i+1}" for i in range(num_channels)]
                    time_data = self.time_history.get_data_slice(earliest_abs, current_len)
                else:
                    headers = ["Sample_Index"] + [self.channel_widgets[i]["name_edit"].text().strip() or f"CH_{i+1}" for i in range(num_channels)]
                    time_data = np.arange(earliest_abs, current_len) * self.spin_interval.value()

                writer.writerow(headers)
                for idx in range(total_points):
                    row = [time_data[idx]] + [all_y_data[ch][idx] for ch in range(num_channels)]
                    writer.writerow(row)
            QMessageBox.information(self, "导出成功", f"成功将 {total_points} 个数据点导出至:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"导出失败: {e}")

    def import_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入波形数据", "", "CSV Files (*.csv)")
        if not file_path: return
        
        try:
            self.clear_data()
            self.close_serial_backend() 
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if not headers or len(headers) < 2:
                    raise ValueError("CSV 文件格式不正确")
                
                num_channels = len(headers) - 1
                rows = list(reader)
                total_points = len(rows)
                
                if total_points == 0: return
                
                matrix = np.zeros((num_channels, total_points), dtype=np.float32)
                time_array = np.zeros(total_points, dtype=np.float64)
                
                for row_idx, row in enumerate(rows):
                    time_array[row_idx] = float(row[0])
                    for ch_idx in range(num_channels):
                        matrix[ch_idx, row_idx] = float(row[ch_idx + 1])
                
                if headers[0] == "Time_ms": self.combo_x_axis.setCurrentIndex(0)
                else: self.combo_x_axis.setCurrentIndex(1)
                
                while len(self.data_history) < num_channels:
                    self.data_history.append(CircularBuffer(self.max_memory_points))
                    self.create_channel_ui(len(self.data_history) - 1)
                
                self.time_history.extend(time_array)
                self._reset_dynamic_time_axis(keep_time=True)
                for i in range(num_channels):
                    self.channel_widgets[i]["name_edit"].setText(headers[i+1])
                    self.data_history[i].resize_buffer(self.max_memory_points)
                    self.data_history[i].extend(matrix[i])
                    
            self.auto_follow_x = False
            self.btn_go_latest.setText("静态复现")
            self.btn_go_latest.setStyleSheet("background-color: #555555; min-width: 80px;")
            self.view_start_abs = 0
            
            interval = self.spin_interval.value()
            use_real_time = (self.combo_x_axis.currentIndex() == 0)
            
            if use_real_time: self.plot_widget.setXRange(time_array[0], time_array[min(total_points - 1, self.visible_points)], padding=0)
            else: self.plot_widget.setXRange(0, min(total_points, self.visible_points) * interval, padding=0)
                
            QMessageBox.information(self, "导入成功", f"CSV波形复现完成！共计导入 {num_channels} 个通道，{total_points} 个数据点。")
        except Exception as e:
            QMessageBox.critical(self, "导入错误", f"加载失败: {e}")

    def load_saved_configurations(self):
        try:
            # 加载通用设置
            if self.settings.contains("x_axis_mode"):
                self.combo_x_axis.setCurrentIndex(int(self.settings.value("x_axis_mode")))
            if self.settings.contains("dynamic_time_window"):
                self.spin_dynamic_time_window.setValue(float(self.settings.value("dynamic_time_window")))
            if self.settings.contains("draw_mode"):
                self.combo_draw_mode.setCurrentIndex(int(self.settings.value("draw_mode")))
            if self.settings.contains("baudrate"):
                self.baud_combo.setCurrentText(str(self.settings.value("baudrate")))
            if self.settings.contains("precision"):
                self.spin_precision.setValue(int(self.settings.value("precision")))
            if self.settings.contains("linewidth"):
                self.spin_linewidth.setValue(float(self.settings.value("linewidth")))
            if self.settings.contains("interval"):
                self.configured_interval_ms = float(self.settings.value("interval"))
                self._updating_interval_display = True
                self.spin_interval.setValue(self.configured_interval_ms)
                self._updating_interval_display = False
            else:
                self.configured_interval_ms = self.spin_interval.value()
            self._sync_interval_spinbox_to_mode()
            if self.settings.contains("max_cache"):
                self.spin_max_cache.setValue(int(self.settings.value("max_cache")))
                self.max_memory_points = int(self.settings.value("max_cache"))
            if self.settings.contains("visible_points"):
                self.spin_visible_points.setValue(int(self.settings.value("visible_points")))
                self.visible_points = int(self.settings.value("visible_points"))
            if self.settings.contains("geometry"):
                self.restoreGeometry(self.settings.value("geometry"))
            if self.settings.contains("splitter_state"):
                self._pending_splitter_state = self.settings.value("splitter_state")

            # 恢复波形缓冲区数据（必须在窗口恢复前，以填充通道列表）
            self._load_buffer_data()

            # 加载通信配置
            if self.settings.contains("protocol_index"):
                idx = int(self.settings.value("protocol_index"))
                self.combo_protocol.setCurrentIndex(idx)
                self.on_protocol_changed(idx)
            if self.settings.contains("port"):
                self.port_combo.setCurrentText(self.settings.value("port"))
            if self.settings.contains("baudrate"):
                self.baud_combo.setCurrentText(str(self.settings.value("baudrate")))
            if self.settings.contains("host"):
                self.edit_host.setText(self.settings.value("host"))
            if self.settings.contains("port_num"):
                self.spin_port.setValue(int(self.settings.value("port_num")))

            # 加载窗口配置（清空现有窗口，根据保存重建）
            if self.settings.contains("window_list"):
                window_list = self.settings.value("window_list")
                if window_list and isinstance(window_list, list) and len(window_list) > 0:
                    # 清除所有现有子窗口（包括默认的时域窗口）
                    for sub in self.mdi_area.subWindowList():
                        self.mdi_area.removeSubWindow(sub)
                        sub.deleteLater()
                    # 重置主窗口引用
                    self.main_time_sub = None
                    self.main_fft_sub = None
                    self.fft_plot = None
                    self.fft_hud_label = None

                    # 重建保存的窗口
                    for win_data in window_list:
                        title = win_data.get('title', '')
                        win_type = win_data.get('type', 'time')
                        x = win_data.get('x', 0)
                        y = win_data.get('y', 0)
                        width = win_data.get('width', 400)
                        height = win_data.get('height', 300)
                        maximized = win_data.get('maximized', False)

                        # 根据类型创建 widget
                        if win_type == 'time':
                            widget = self.create_time_widget()
                        elif win_type == 'fft':
                            widget = self.create_fft_widget()
                        elif win_type == 'imu':
                            widget = self.create_imu_widget()
                        else:
                            continue

                        sub = SnapMdiSubWindow()
                        sub.setWidget(widget)
                        sub.setWindowTitle(title)
                        sub.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
                        sub.setProperty('window_type', win_type)
                        self.mdi_area.addSubWindow(sub)

                        # 如果保存了比例坐标，优先使用（可适配当前窗口大小）
                        has_frac = all(k in win_data for k in ('x_frac', 'y_frac', 'w_frac', 'h_frac'))
                        if has_frac and not maximized:
                            sub.set_frac_geometry(
                                win_data['x_frac'], win_data['y_frac'],
                                win_data['w_frac'], win_data['h_frac']
                            )

                        # 先显示，再设置几何（必须显示后 setGeometry 才有效）
                        sub.show()
                        if maximized:
                            sub.showMaximized()
                        elif has_frac:
                            # 用比例坐标计算当前视口下的绝对位置（延迟到布局完成）
                            QTimer.singleShot(0, lambda s=sub: s.apply_frac_geometry())
                        else:
                            sub.setGeometry(x, y, width, height)

                        # 恢复 IMU 窗口配置（模式 + 通道映射）
                        if win_type == 'imu' and 'imu_mode' in win_data:
                            widget.mode_combo.setCurrentIndex(win_data['imu_mode'])
                            saved_ch = win_data.get('imu_channels', [])
                            widget.imu_channel_indices = list(saved_ch[:len(widget.ch_selectors)])
                            while len(widget.imu_channel_indices) < len(widget.ch_selectors):
                                widget.imu_channel_indices.append(len(widget.imu_channel_indices))
                            self._refresh_imu_channels(widget=widget)

                        # 如果是频域窗口且还没有设置主频域，则设置
                        if win_type == 'fft' and self.fft_plot is None:
                            self.fft_plot = widget.fft_plot
                            self.main_fft_sub = sub

                    print(f"[加载配置] 已加载 {len(window_list)} 个窗口")

                    # 重建完成后，更新主时域窗口引用（第一个时域窗口）
                    for sub in self.mdi_area.subWindowList():
                        if sub.property('window_type') == 'time':
                            widget = sub.widget()
                            if hasattr(widget, 'plot_widget'):
                                self.plot_widget = widget.plot_widget
                                self.main_time_sub = sub
                                self.vofa_timeline = widget.vofa_timeline
                                self.spin_max_cache = widget.spin_max_cache
                                self.spin_interval = widget.spin_interval
                                self.spin_visible_points = widget.spin_visible_points
                                self.lbl_buffer_status = widget.lbl_buffer_status
                                self.btn_go_latest = widget.btn_go_latest
                                self.time_hud_label = widget.time_hud_label

                                # 重新添加测量线（因为新建了 plot_widget）
                                self.meas_line_A = OscilloscopeCursor(angle=90, movable=True, label_text="A", pen=pg.mkPen('#ffcc00', width=1.5, style=Qt.PenStyle.SolidLine))
                                self.meas_line_B = OscilloscopeCursor(angle=90, movable=True, label_text="B", pen=pg.mkPen('#00ffcc', width=1.5, style=Qt.PenStyle.SolidLine))
                                self.plot_widget.addItem(self.meas_line_A, ignoreBounds=True)
                                self.plot_widget.addItem(self.meas_line_B, ignoreBounds=True)
                                self.meas_line_A.sigPositionChanged.connect(self.on_meas_line_A_dragged)
                                self.meas_line_B.sigPositionChanged.connect(self.on_meas_line_B_dragged)
                                self.plot_widget.plotItem.vb.sigXRangeChanged.connect(self.sync_cursors_to_screen)
                                self.plot_widget.plotItem.vb.sigRangeChangedManually.connect(self.on_view_manually_changed)
                                self.meas_hud_label = QLabel(self.plot_widget)
                                self.meas_hud_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                                self.meas_hud_label.setStyleSheet("background-color: rgba(25, 25, 25, 220); border: 1px solid #ffcc00; font-size: 11px; padding: 6px; font-family: 'Consolas'; border-radius: 4px;")
                                self.meas_hud_label.hide()
                                # 根据测量状态显示
                                if self.is_meas_active:
                                    self.meas_line_A.setVisible(True)
                                    self.meas_line_B.setVisible(True)
                                    self.meas_hud_label.show()
                                else:
                                    self.meas_line_A.setVisible(False)
                                    self.meas_line_B.setVisible(False)
                                    self.meas_hud_label.hide()
                                break  # 只处理第一个时域窗口

                    # 更新频域引用（如果有多个，取第一个）
                    for sub in self.mdi_area.subWindowList():
                        if sub.property('window_type') == 'fft':
                            widget = sub.widget()
                            if hasattr(widget, 'fft_plot'):
                                self.fft_plot = widget.fft_plot
                                self.fft_hud_label = widget.fft_hud_label
                                break

        except Exception as e:
            print(f"加载配置时出错: {e}")
            import traceback
            traceback.print_exc()

    def closeEvent(self, event):
        if self.comm_thread:
            self.comm_thread.stop()
        self.plot_timer.stop()

        # 安全获取控件值的辅助函数
        def safe_get(control, default=None):
            try:
                if hasattr(control, 'value'):
                    return control.value()
                elif hasattr(control, 'currentIndex'):
                    return control.currentIndex()
                elif hasattr(control, 'currentText'):
                    return control.currentText()
                elif hasattr(control, 'text'):
                    return control.text()
                return default
            except RuntimeError:
                return default

        # 保存通用设置（所有访问控件的调用都用 safe_get 包装）
        self.settings.setValue("x_axis_mode", safe_get(self.combo_x_axis, 0))
        self.settings.setValue("dynamic_time_window", safe_get(self.spin_dynamic_time_window, 1000))
        self.settings.setValue("draw_mode", safe_get(self.combo_draw_mode, 0))
        self.settings.setValue("baudrate", safe_get(self.baud_combo, ""))
        self.settings.setValue("precision", safe_get(self.spin_precision, 0))
        self.settings.setValue("linewidth", safe_get(self.spin_linewidth, 1))
        self.settings.setValue("interval", self.configured_interval_ms)
        self.settings.setValue("max_cache", safe_get(self.spin_max_cache, 10000))
        self.settings.setValue("visible_points", safe_get(self.spin_visible_points, 1000))
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitter_state", self.splitter.saveState())

        # 保存通信配置
        self.settings.setValue("protocol_index", safe_get(self.combo_protocol, 0))
        self.settings.setValue("port", safe_get(self.port_combo, ""))
        self.settings.setValue("host", safe_get(self.edit_host, ""))
        self.settings.setValue("port_num", safe_get(self.spin_port, 0))

        # 保存窗口列表
        window_list = []
        for sub in self.mdi_area.subWindowList():
            if sub.isVisible():
                try:
                    geo = sub.geometry()
                    frac = sub.get_frac_geometry() if isinstance(sub, SnapMdiSubWindow) else None
                    win_data = {
                        'title': sub.windowTitle(),
                        'type': sub.property('window_type'),
                        'x': geo.x(),
                        'y': geo.y(),
                        'width': geo.width(),
                        'height': geo.height(),
                        'maximized': sub.isMaximized(),
                    }
                    if frac is not None:
                        win_data['x_frac'] = frac[0]
                        win_data['y_frac'] = frac[1]
                        win_data['w_frac'] = frac[2]
                        win_data['h_frac'] = frac[3]
                    # 保存 IMU 窗口配置
                    if sub.property('window_type') == 'imu':
                        w = sub.widget()
                        if w and hasattr(w, 'mode_combo'):
                            win_data['imu_mode'] = safe_get(w.mode_combo, 0)
                            win_data['imu_channels'] = [
                                int(w.imu_channel_indices[i]) if hasattr(w, 'imu_channel_indices') and i < len(w.imu_channel_indices)
                                else safe_get(sel, 0)
                                for i, sel in enumerate(w.ch_selectors)
                            ]
                    window_list.append(win_data)
                except RuntimeError:
                    continue
        self.settings.setValue("window_list", window_list)
        print(f"[保存配置] 已保存 {len(window_list)} 个窗口")

        # 保存通道配置
        for i, widgets in enumerate(self.channel_widgets):
            try:
                self.settings.setValue(f"channel_name_{i}", safe_get(widgets["name_edit"], ""))
                self.settings.setValue(f"channel_checked_{i}", "true" if widgets["checkbox"].isChecked() else "false")
                if i < len(self.channel_colors):
                    self.settings.setValue(f"channel_color_{i}", self.channel_colors[i])
            except RuntimeError:
                continue

        # 保存波形缓冲区数据到 scope_data.npz
        self._save_buffer_data()

        event.accept()

    def _save_buffer_data(self):
        """将 data_history 和 time_history 保存到 scope_data.npz"""
        if not self.data_history:
            return
        try:
            save_dict = {
                'num_channels': len(self.data_history),
                'time_total': self.time_history.total_count,
                'time_head': self.time_history.head,
                'time_max': self.time_history.max_len,
                'time_buffer': self.time_history.buffer,
            }
            for i, buf in enumerate(self.data_history):
                save_dict[f'ch{i}_total'] = buf.total_count
                save_dict[f'ch{i}_head'] = buf.head
                save_dict[f'ch{i}_max'] = buf.max_len
                save_dict[f'ch{i}_buffer'] = buf.buffer
            np.savez_compressed('scope_data.npz', **save_dict)
            print(f"[保存数据] 已保存 {len(self.data_history)} 通道的波形数据到 scope_data.npz")
        except Exception as e:
            print(f"[保存数据] 失败: {e}")

    def _load_buffer_data(self):
        """从 scope_data.npz 恢复波形缓冲区数据"""
        import os
        if not os.path.exists('scope_data.npz'):
            return
        try:
            data = np.load('scope_data.npz', allow_pickle=False)
            num_channels = int(data['num_channels'])

            # 恢复时间轴
            self.time_history.max_len = int(data['time_max'])
            self.time_history.buffer = data['time_buffer']
            self.time_history.head = int(data['time_head'])
            self.time_history.total_count = int(data['time_total'])

            # 恢复每个通道
            while len(self.data_history) < num_channels:
                self.data_history.append(CircularBuffer(self.max_memory_points))
                self.create_channel_ui(len(self.data_history) - 1)
            for i in range(num_channels):
                buf = self.data_history[i]
                buf.max_len = int(data[f'ch{i}_max'])
                buf.buffer = data[f'ch{i}_buffer']
                buf.head = int(data[f'ch{i}_head'])
                buf.total_count = int(data[f'ch{i}_total'])

            # 对齐 time_history 和 data_history 的 max_len
            self.max_memory_points = max(
                self.max_memory_points,
                self.time_history.max_len,
                *(buf.max_len for buf in self.data_history)
            )
            self.spin_max_cache.setValue(self.max_memory_points)

            print(f"[加载数据] 已从 scope_data.npz 恢复 {num_channels} 通道波形数据")
        except Exception as e:
            print(f"[加载数据] 失败: {e}")

if __name__ == "__main__":
    import traceback
    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print("未捕获的异常:")
        traceback.print_exc()
        input("按回车键退出...")
