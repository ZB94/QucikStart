# coding: utf-8
import sys
import os
from os import path
import json
from configparser import ConfigParser

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import keyboard


class Item():
    name = None
    path = None
    icon = None

    def __init__(self, name: str, path: str, icon: str=None):
        self.name = name
        self.path = path
        self.icon = icon

    def toDict(self):
        return {
            "name": self.name,
            "path": self.path,
            "icon": self.icon
        }

    @staticmethod
    def fromDict(item: dict):
        return Item(item.get("name", ""), item.get("path", ""), item.get("icon", None))


class Data():
    name = None
    items = None

    def __init__(self, name):
        self.name = name
        self.items = []

    def toDict(self):
        items = [i.toDict() for i in self.items]
        return {
            "name": self.name,
            "items": items
        }

    @staticmethod
    def fromDict(data: dict):
        _data = Data(data.get("name", ""))
        _data.items = [Item.fromDict(i) for i in data.get("items", [])]
        return _data


class MainWindow(QTabWidget):

    icon_provider = QFileIconProvider()
    icon = None
    item_actions = None
    data_actions = None
    __data = None
    __data_path = None
    __position_path = None
    __icon_path = None
    __hotkey = None
    __name = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.loadConfig()
        self.loadData()
        self.initUi()
        keyboard.add_hotkey(self.__hotkey, lambda: self.showNormal() if self.isHidden() else self.hide())

    def initUi(self):
        try:
            if not self.__icon_path:
                raise Exception()
            self.icon = QIcon(self.__icon_path)
        except:
            self.icon = self.icon_provider.icon(QFileInfo(sys.argv[0]))

        self.setWindowTitle(self.__name)
        self.setWindowIcon(self.icon)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setAcceptDrops(True)
        self.dragEnterEvent = self.dragMoveEvent = lambda e: e.accept() if e.mimeData().hasUrls() else e.ignore()

        # 选中项右键菜单
        self.item_actions = []
        self.item_actions.append(QAction("修改...", self, triggered=self.updateItem))
        self.item_actions.append(QAction("设置图标...", self, triggered=self.updateItemIcon))
        self.item_actions.append(QAction("打开所在文件夹...", self, triggered=self.openItemPath))
        self.item_actions.append(QAction(self))
        self.item_actions[-1].setSeparator(True)
        self.item_actions.append(QAction("删除", self, triggered=self.deleteItem))

        # tab 右键菜单
        self.data_actions = []
        self.data_actions.append(QAction("新增...", self, triggered=self.newTab))
        self.data_actions.append(QAction("修改...", self, triggered=self.updateTab))
        self.data_actions.append(QAction(self))
        self.data_actions[-1].setSeparator(True)
        self.data_actions.append(QAction("删除", self, triggered=self.deleteTab))

        def event(pos):
            tab = self.childAt(pos)
            if tab:
                self.setCurrentIndex(tab.tabAt(pos))
                menu = QMenu(self)
                menu.addActions(self.data_actions)
                menu.exec_(QCursor.pos())

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(event)

        # 托盘&托盘菜单
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.icon)
        self.tray.setToolTip(self.__name)
        menu = QMenu(self)
        menu.addAction(QAction("显示", self, triggered=self.showNormal))
        menu.addAction(QAction("隐藏", self, triggered=self.hide))
        menu.addSeparator()
        menu.addAction(QAction("退出", self, triggered=self.close))
        self.tray.setContextMenu(menu)
        self.tray.show()

        def double_event(event: int):
            if event == QSystemTrayIcon.DoubleClick:
                self.showNormal()

        self.tray.activated.connect(double_event)

        # 加载数据
        for data in self.__data:
            self.showTab(data)

        # 加载位置
        try:
            with open(self.__position_path, "rb") as fp:
                data = fp.read()
                self.restoreGeometry(data)
        except:
            pass

    def dropEvent(self, event: QDropEvent):
        mimedata = event.mimeData()
        urls = mimedata.urls()
        for url in urls:
            p = url.toLocalFile()
            self.addItem(p)

    def closeEvent(self, event: QCloseEvent):
        self.tray.hide()
        self.saveData()

        try:
            with open(self.__position_path, "wb") as fp:
                fp.write(self.saveGeometry())
        except:
            pass

    def changeEvent(self, event: QEvent):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            self.setHidden(True)

    def showTab(self, data: Data):
        widget = QListWidget(self)
        # widget.setViewMode(QListWidget.IconMode)
        # widget.setGridSize(QSize(60, 60))
        widget.setIconSize(QSize(32, 32))
        widget.setFrameShape(QListWidget.NoFrame)
        widget.setResizeMode(QListWidget.Adjust)
        widget.setDragDropMode(QListWidget.NoDragDrop)
        widget.setContextMenuPolicy(Qt.CustomContextMenu)

        def double_event(idx):
            idx = idx.row()
            item = widget.item(idx).data(Qt.UserRole)
            QDesktopServices.openUrl(QUrl(item.path))

        def menu_event(pos):
            if widget.itemAt(pos):
                menu = QMenu(self)
                menu.addActions(self.item_actions)
                menu.exec_(QCursor.pos())

        widget.customContextMenuRequested.connect(menu_event)
        widget.doubleClicked.connect(double_event)

        dataitem = QListWidgetItem(widget)
        dataitem.setHidden(True)
        dataitem.setData(Qt.UserRole, data)
        widget.addItem(dataitem)

        for i in data.items:
            self.showItem(widget, i)

        self.addTab(widget, data.name)

    def newTab(self):
        name, ret = QInputDialog.getText(self, "请输入名称", "新增项的名称：", text="默认")
        if ret:
            data = Data(name)
            self.__data.append(data)
            self.showTab(data)
            self.saveData()

    def updateTab(self):
        tab = self.currentWidget()
        idx = self.currentIndex()
        data = tab.item(0).data(Qt.UserRole)
        name, ret = QInputDialog.getText(self, "请输入新名称", "新名称", text=data.name)
        if ret:
            data.name = name
            self.setTabText(idx, name)
            self.saveData()

    def deleteTab(self):
        if not QMessageBox.question(self, "询问", "确认删除吗？") == QMessageBox.Yes:
            return
        data = self.currentWidget().item(0).data(Qt.UserRole)
        idx = self.currentIndex()

        del self.__data[self.__data.index(data)]
        self.removeTab(idx)

        if not self.__data:
            data = Data("默认")
            self.__data.append(data)
            self.showTab(data)

    def showItem(self, parent: QListWidget, item: Item):
        _item = QListWidgetItem(parent)
        _item.setData(Qt.DisplayRole, item.name)
        _item.setData(Qt.UserRole, item)
        if item.icon:
            _item.setIcon(QIcon(item.icon))
        else:
            _item.setIcon(self.icon_provider.icon(QFileInfo(item.path)))
        _item.setToolTip(item.name)

        parent.addItem(_item)

    def addItem(self, p: str):
        n = path.splitext(path.basename(p))[0]
        p = QFileInfo(p)
        p = p.canonicalFilePath()
        icon = None
        if p.endswith(".url"):
            parse = ConfigParser()
            parse.read(p)
            p = parse.get("InternetShortcut", "URL")
            icon = parse.get("InternetShortcut", "IconFile", fallback=None)

        item = Item(n, p, icon)

        widget = self.currentWidget()
        data = widget.item(0).data(Qt.UserRole)

        if not [i for i in data.items if i.path == item.path]:
            data.items.append(item)
            self.showItem(widget, item)
            self.saveData()

    def __getItemData(self):
        widget = self.currentWidget()
        item = widget.currentItem()
        _item = item.data(Qt.UserRole)
        return widget, item, _item

    def updateItem(self):
        widget, item, _item = self.__getItemData()

        name, ret = QInputDialog.getText(self, "请输入新名称", "新名称：", text=_item.name)
        if ret:
            _item.name = name
            item.setData(Qt.DisplayRole, name)
            self.saveData()

    def updateItemIcon(self):
        widget, item, _item = self.__getItemData()

        icon = QFileDialog.getOpenFileName(self, "选择图标", path.split(_item.path)[0], "图标文件(*.ico)")[0]

        if icon:
            icon = QFileInfo(icon).canonicalFilePath()
            _item.icon = icon
            item.setIcon(QIcon(icon))
            self.saveData()

    def openItemPath(self):
        widget, item, _item = self.__getItemData()
        if path.exists(_item.path):
            QDesktopServices.openUrl(QUrl(path.split(_item.path)[0]))

    def deleteItem(self):
        widget, item, _item = self.__getItemData()
        idx = widget.currentIndex().row()

        data = widget.item(0).data(Qt.UserRole)

        del data.items[data.items.index(_item)]
        widget.takeItem(idx)
        widget.removeItemWidget(item)

        self.saveData()

    def loadData(self):
        try:
            with open(self.__data_path, encoding="utf-8") as fp:
                data = json.load(fp)
                self.__data = [Data.fromDict(i) for i in data]
        except Exception as e:
            self.__data = [Data("默认")]

    def saveData(self):
        try:
            with open(self.__data_path, "w", encoding="utf-8") as fp:
                data = [i.toDict() for i in self.__data]
                json.dump(data, fp)
        except Exception as e:
            pass

    def loadConfig(self):
        section = "QuickStart"
        try:
            parse = ConfigParser()
            parse.read("config.ini", encoding="utf-8")
            self.__name = parse.get(section, "name")
            self.__data_path = parse.get(section, "data_path")
            self.__position_path = parse.get(section, "position_path")
            self.__icon_path = parse.get(section, "icon_path")
            self.__hotkey = parse.get(section, "hotkey")
        except Exception as e:
            self.__name = "快速启动"
            self.__data_path = "./data.json"
            self.__position_path = "./position.dat"
            self.__icon_path = None
            self.__hotkey = "alt+q"


app = QApplication(sys.argv)
main = MainWindow()
main.show()
sys.exit(app.exec_())
