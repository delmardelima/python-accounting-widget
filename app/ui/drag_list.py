"""
Lista com suporte a drag-and-drop interno.
"""
from PyQt6.QtWidgets import QListWidget, QAbstractItemView
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QDrag, QPixmap, QPainter


class DragListWidget(QListWidget):
    """QListWidget que permite reordenar itens arrastando."""

    order_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.viewport().setStyleSheet("background: transparent;")

    def dropEvent(self, event):
        super().dropEvent(event)
        self.order_changed.emit()

    def startDrag(self, supportedActions):
        items = self.selectedItems()
        if not items:
            return

        item = items[0]
        mimeData = self.mimeData(items)
        if mimeData is None:
            return

        drag = QDrag(self)
        drag.setMimeData(mimeData)

        widget = self.itemWidget(item)
        if widget:
            pixmap = QPixmap(widget.size())
            pixmap.fill(Qt.GlobalColor.transparent)
            widget.render(pixmap)

            transparent_pixmap = QPixmap(pixmap.size())
            transparent_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(transparent_pixmap)
            painter.setOpacity(0.65)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            drag.setPixmap(transparent_pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        drag.exec(supportedActions, Qt.DropAction.MoveAction)
