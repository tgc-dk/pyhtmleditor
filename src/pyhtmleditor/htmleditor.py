# -*- coding: utf-8 -*-
# Author: Milan Nikolic <gen2brain@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtWebEngineWidgets, QtWidgets, QtWebChannel

from pyhtmleditor.highlighter import Highlighter
from pyhtmleditor.ui.htmleditor_ui import Ui_MainWindow
from pyhtmleditor.ui.inserthtmldialog_ui import Ui_Dialog

class HtmlDialog(QDialog, Ui_Dialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)


class HtmlEditor(QMainWindow, Ui_MainWindow):

    def __init__(self):
        QMainWindow.__init__(self, None)
        self.setupUi(self)
        self.sourceDirty = True
        self.highlighter = None
        self.insertHtmlDialog = None
        self.tabWidget.setTabText(0, "Normal View")
        self.tabWidget.setTabText(1, "HTML Source")
        self.tabWidget.currentChanged.connect(self.changeTab)
        self.resize(800, 600)

        self.highlighter = Highlighter(self.plainTextEdit.document())

        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.standardToolBar.insertWidget(self.actionZoomOut, spacer)

        self.zoomLabel = QLabel()
        self.standardToolBar.insertWidget(self.actionZoomOut, self.zoomLabel)

        self.zoomSlider = QSlider(self)
        self.zoomSlider.setOrientation(Qt.Horizontal)
        self.zoomSlider.setMaximumWidth(150)
        self.zoomSlider.setRange(25, 400)
        self.zoomSlider.setSingleStep(25)
        self.zoomSlider.setPageStep(100)
        self.zoomSlider.valueChanged.connect(self.changeZoom)
        self.standardToolBar.insertWidget(self.actionZoomIn, self.zoomSlider)

        self.actionFileNew.triggered.connect(self.fileNew)
        self.actionFileOpen.triggered.connect(self.fileOpen)
        self.actionFileSave.triggered.connect(self.fileSave)
        self.actionFileSaveAs.triggered.connect(self.fileSaveAs)
        self.actionExit.triggered.connect(self.close)
        self.actionInsertImage.triggered.connect(self.insertImage)
        self.actionCreateLink.triggered.connect(self.createLink)
        self.actionInsertHtml.triggered.connect(self.insertHtml)
        self.actionZoomOut.triggered.connect(self.zoomOut)
        self.actionZoomIn.triggered.connect(self.zoomIn)

        # these are forward to internal QWebView
        self._forward_action(self.actionEditUndo, QtWebEngineWidgets.QWebEnginePage.Undo)
        self._forward_action(self.actionEditRedo, QtWebEngineWidgets.QWebEnginePage.Redo)
        self._forward_action(self.actionEditCut, QtWebEngineWidgets.QWebEnginePage.Cut)
        self._forward_action(self.actionEditCopy, QtWebEngineWidgets.QWebEnginePage.Copy)
        self._forward_action(self.actionEditPaste, QtWebEngineWidgets.QWebEnginePage.Paste)
        self._forward_action(self.actionFormatBold, QtWebEngineWidgets.QWebEnginePage.ToggleBold)
        self._forward_action(self.actionFormatItalic, QtWebEngineWidgets.QWebEnginePage.ToggleItalic)
        self._forward_action(self.actionFormatUnderline, QtWebEngineWidgets.QWebEnginePage.ToggleUnderline)

        # Qt 4.5.0 has a bug: always returns 0 for QWebPage::SelectAll
        self.actionEditSelectAll.triggered.connect(self.editSelectAll)

        self.actionStyleParagraph.triggered.connect(self.styleParagraph)
        self.actionStyleHeading1.triggered.connect(self.styleHeading1)
        self.actionStyleHeading2.triggered.connect(self.styleHeading2)
        self.actionStyleHeading3.triggered.connect(self.styleHeading3)
        self.actionStyleHeading4.triggered.connect(self.styleHeading4)
        self.actionStyleHeading5.triggered.connect(self.styleHeading5)
        self.actionStyleHeading6.triggered.connect(self.styleHeading6)
        self.actionStylePreformatted.triggered.connect(self.stylePreformatted)
        self.actionStyleAddress.triggered.connect(self.styleAddress)
        self.actionFormatFontName.triggered.connect(self.formatFontName)
        self.actionFormatFontSize.triggered.connect(self.formatFontSize)
        self.actionFormatTextColor.triggered.connect(self.formatTextColor)
        self.actionFormatBackgroundColor.triggered.connect(self.formatBackgroundColor)

        # no page action exists yet for these, so use execCommand trick
        self.actionFormatStrikethrough.triggered.connect(self.formatStrikeThrough)
        self.actionFormatAlignLeft.triggered.connect(self.formatAlignLeft)
        self.actionFormatAlignCenter.triggered.connect(self.formatAlignCenter)
        self.actionFormatAlignRight.triggered.connect(self.formatAlignRight)
        self.actionFormatAlignJustify.triggered.connect(self.formatAlignJustify)
        self.actionFormatDecreaseIndent.triggered.connect(self.formatDecreaseIndent)
        self.actionFormatIncreaseIndent.triggered.connect(self.formatIncreaseIndent)
        self.actionFormatNumberedList.triggered.connect(self.formatNumberedList)
        self.actionFormatBulletedList.triggered.connect(self.formatBulletedList)

        # enable pasting
        self.webView.settings().setAttribute(QtWebEngineWidgets.QWebEngineSettings.JavascriptCanAccessClipboard, True)
        self.webView.settings().setAttribute(QtWebEngineWidgets.QWebEngineSettings.JavascriptCanPaste, True)
        self.webView.page().settings().setAttribute(QtWebEngineWidgets.QWebEngineSettings.JavascriptCanAccessClipboard, True)
        self.webView.page().settings().setAttribute(QtWebEngineWidgets.QWebEngineSettings.JavascriptCanPaste, True)

        # necessary to sync our actions
        self.webView.page().selectionChanged.connect(self.adjustActions)

        self.webView.setFocus()

        self.setCurrentFileName('')

        self.webchannel = QtWebChannel.QWebChannel(self)
        self.webView.page().setWebChannel(self.webchannel)
        self.webchannel.registerObject('MyChannel', self)

        initialFile = str("./src/pyhtmleditor/ui/example.html")
        args = QCoreApplication.arguments()
        if (len(args) == 2):
            initialFile = args[1]

        if not self.load(initialFile):
            self.fileNew()

        self.adjustActions()
        self.adjustSource()
        self.setWindowModified(False)
        self.changeZoom(100)

    def _forward_action(self, action1, action2):
        action1.triggered.connect(self.webView.pageAction(action2).trigger)
        self.webView.pageAction(action2).changed.connect(self.adjustActions)

    def _follow_enable(self, a1, a2):
        a1.setEnabled(self.webView.pageAction(a2).isEnabled())

    def _follow_check(self, a1, a2):
        a1.setChecked(self.webView.pageAction(a2).isChecked())

    def maybeSave(self):
        if not self.isWindowModified():
            return True
        ret = QMessageBox.warning(self, self.tr("HTML Editor"),
                self.tr("The document has been modified.\nDo you want to save your changes?"),
                QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel)
        if ret == QMessageBox.Save:
            return self.fileSave()
        elif ret == QMessageBox.Cancel:
            return False
        return True

    def fileNew(self):
        if self.maybeSave():
            self.webView.setHtml("<p></p>")
            self.webView.setFocus()
            #self.webView.page().setContentEditable(True)
            #self.run_javascript("document.designMode = true;")
            #self.webView.page().runJavaScript("document.body.contentEditable = true;");
            self.setCurrentFileName('')
            self.setWindowModified(False)

            # quirk in QWebView: need an initial mouse click to show the cursor
            mx = self.webView.width() / 2
            my = self.webView.height() / 2
            center = QPoint(mx, my)
            e1 = QMouseEvent(QEvent.MouseButtonPress, center, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            e2 = QMouseEvent(QEvent.MouseButtonRelease, center, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            QApplication.postEvent(self.webView, e1)
            QApplication.postEvent(self.webView, e2)

    def fileOpen(self):
        fn,file_type = QFileDialog.getOpenFileName(self, self.tr("Open File..."),
                '', self.tr("HTML-Files (*.htm *.html);;All Files (*)"))
        if not fn:
            self.load(fn)

    def fileSave(self):
        if not self.fileName or self.fileName.startswith(str(":/")):
            return self.fileSaveAs()

        fd = QFile(self.fileName)
        success = fd.open(QIODevice.WriteOnly)
        if success:
            content = self.webView.page().toHtml()
            data = content.toUtf8()
            c = fd.write(data)
            success = (c >= data.length())

        self.setWindowModified(False)
        return success

    def fileSaveAs(self):
        fn,file_type = QFileDialog.getSaveFileName(self, self.tr("Save as..."),
                '', self.tr("HTML-Files (*.htm *.html);;All Files (*)"))
        if not fn:
            return False
        if not fn.endswith(".htm", Qt.CaseInsensitive) or not fn.endswith(".html", Qt.CaseInsensitive):
            fn += ".htm"
        self.setCurrentFileName(fn)
        return self.fileSave()

    def insertImage(self):
        filters = self.tr("Common Graphics (*.png *.jpg *.jpeg *.gif);;");
        filters += self.tr("Portable Network Graphics (PNG) (*.png);;");
        filters += self.tr("JPEG (*.jpg *.jpeg);;");
        filters += self.tr("Graphics Interchange Format (*.gif);;");
        filters += self.tr("All Files (*)");

        fn,file_type = QFileDialog.getOpenFileName(self,
                self.tr("Open image..."), '', filters)
        if not fn:
            return
        if not QFile.exists(fn):
            return

        url = QUrl.fromLocalFile(fn)
        self.execCommand("insertImage", url.toString())

    def guessUrlFromString(self, string):
        urlStr = string.trimmed()
        test = QRegExp(str("^[a-zA-Z]+\\:.*"))

        hasSchema = test.exactMatch(urlStr)
        if hasSchema:
            url = QUrl(urlStr, QUrl.TolerantMode)
            if url.isValid():
                return url

        # Might be a file.
        if QFile.exists(urlStr):
            return QUrl.fromLocalFile(urlStr)

        # Might be a shorturl - try to detect the schema.
        if not hasSchema:
            dotIndex = urlStr.indexOf('.')
            if dotIndex != -1:
                prefix = urlStr.left(dotIndex).toLower()
                schema = prefix if prefix == "ftp" else "http"
                url = QUrl(schema + "://" + urlStr, QUrl.TolerantMode)
                if url.isValid():
                    return url

        # Fall back to QUrl's own tolerant parser.
        return QUrl(string, QUrl.TolerantMode)

    def createLink(self):
        link = QInputDialog.getText(self, self.tr("Create link"), "Enter URL")[0]
        if not link.isEmpty():
            url = self.guessUrlFromString(link)
            if url.isValid():
                self.execCommand("createLink", url.toString())

    def insertHtml(self):
        if not self.insertHtmlDialog:
            self.insertHtmlDialog = HtmlDialog()
            self.insertHtmlDialog.buttonBox.accepted.connect(self.insertHtmlDialog.accept)
            self.insertHtmlDialog.buttonBox.rejected.connect(self.insertHtmlDialog.reject)

        self.insertHtmlDialog.plainTextEdit.clear()
        self.insertHtmlDialog.plainTextEdit.setFocus()
        hilite = Highlighter(self.insertHtmlDialog.plainTextEdit.document())

        if self.insertHtmlDialog.exec_() == QDialog.Accepted:
            self.execCommand("insertHTML", self.insertHtmlDialog.plainTextEdit.toPlainText())

        del hilite

    def zoomOut(self):
        percent = self.webView.zoomFactor() * 100
        if percent > 25:
            percent -= 25
            percent = 25 * ((percent + 25 - 1) // 25)
            factor = percent / 100
            self.webView.setZoomFactor(factor)
            self.actionZoomOut.setEnabled(percent > 25)
            self.actionZoomIn.setEnabled(True)
            self.zoomSlider.setValue(percent)

    def zoomIn(self):
        percent = self.webView.zoomFactor() * 100
        if percent < 400:
            percent += 25
            percent = 25 * (percent // 25)
            factor = percent / 100
            self.webView.setZoomFactor(factor)
            self.actionZoomIn.setEnabled(percent < 400)
            self.actionZoomOut.setEnabled(True)
            self.zoomSlider.setValue(percent)

    def editSelectAll(self):
        self.webView.triggerPageAction(QtWebEngineWidgets.QWebEnginePage.SelectAll)

    def execCommand(self, cmd, arg=None):
        if arg:
            js = 'document.execCommand("{cmd}", false, "{arg}");'.format(cmd=cmd,arg=arg)
        else:
            js = 'document.execCommand("{cmd}", false, null);'.format(cmd=cmd)
        self.run_javascript(js)

    def queryCommandState(self, cmd):
        js = 'document.queryCommandState("{cmd}") + ":{cmd}";'.format(cmd=cmd)
        result = self.run_javascript(js, self.js_callback)
        return str(result).strip().lower() == "true"

    def styleParagraph(self):
        self.execCommand("formatBlock", "p")

    def styleHeading1(self):
        self.execCommand("formatBlock", "h1")

    def styleHeading2(self):
        self.execCommand("formatBlock", "h2")

    def styleHeading3(self):
        self.execCommand("formatBlock", "h3")

    def styleHeading4(self):
        self.execCommand("formatBlock", "h4")

    def styleHeading5(self):
        self.execCommand("formatBlock", "h5")

    def styleHeading6(self):
        self.execCommand("formatBlock", "h6")

    def stylePreformatted(self):
        self.execCommand("formatBlock", "pre")

    def styleAddress(self):
        self.execCommand("formatBlock", "address")

    def formatStrikeThrough(self):
        self.execCommand("strikeThrough")

    def formatAlignLeft(self):
        self.execCommand("justifyLeft")

    def formatAlignCenter(self):
        self.execCommand("justifyCenter")

    def formatAlignRight(self):
        self.execCommand("justifyRight")

    def formatAlignJustify(self):
        self.execCommand("justifyFull")

    def formatIncreaseIndent(self):
        self.execCommand("indent")

    def formatDecreaseIndent(self):
        self.execCommand("outdent")

    def formatNumberedList(self):
        self.execCommand("insertOrderedList")

    def formatBulletedList(self):
        self.execCommand("insertUnorderedList")

    def formatFontName(self):
        families = QFontDatabase().families()
        family = QInputDialog.getItem(self, self.tr("Font"), self.tr("Select font:"),
                families, 0, False)[0]
        self.execCommand("fontName", family)

    def formatFontSize(self):
        sizes = ["xx-small","x-small","small","medium","large","x-large","xx-large"]
        size = QInputDialog.getItem(self, self.tr("Font Size"), self.tr("Select font size:"),
                list(sizes), list(sizes).indexOf("medium"), False)[0]

        self.execCommand("fontSize", int(list(sizes).indexOf(size)))

    def formatTextColor(self):
        color = QColorDialog.getColor(Qt.black, self)
        if color.isValid():
            self.execCommand("foreColor", color.name())

    def formatBackgroundColor(self):
        color = QColorDialog.getColor(Qt.white, self)
        if color.isValid():
            self.execCommand("hiliteColor", color.name())

    def adjustActions(self):
        self._forward_action(self.actionEditUndo, QtWebEngineWidgets.QWebEnginePage.Undo)
        self._forward_action(self.actionEditRedo, QtWebEngineWidgets.QWebEnginePage.Redo)
        self._forward_action(self.actionEditCut, QtWebEngineWidgets.QWebEnginePage.Cut)
        self._forward_action(self.actionEditCopy, QtWebEngineWidgets.QWebEnginePage.Copy)
        self._forward_action(self.actionEditPaste, QtWebEngineWidgets.QWebEnginePage.Paste)
        self._forward_action(self.actionFormatBold, QtWebEngineWidgets.QWebEnginePage.ToggleBold)
        self._forward_action(self.actionFormatItalic, QtWebEngineWidgets.QWebEnginePage.ToggleItalic)
        self._forward_action(self.actionFormatUnderline, QtWebEngineWidgets.QWebEnginePage.ToggleUnderline)

        self.queryCommandState("bold")
        self.queryCommandState("italic")
        self.queryCommandState("underLine")
        self.queryCommandState("strikeThrough")
        self.queryCommandState("alignLeft")
        self.queryCommandState("alignCenter")
        self.queryCommandState("alignRight")
        self.queryCommandState("alignJustify")
        self.queryCommandState("orderedList")
        self.queryCommandState("unorderedList")

    def adjustSource(self):
        self.setWindowModified(True)
        self.sourceDirty = True

        if self.tabWidget.currentIndex() == 1:
            self.changeTab(1)

    def changeTab(self, index):
        if self.sourceDirty and index == 1:
            self.webView.page().toHtml(self.changeTabCallback)

    def changeTabCallback(self, html):
        self.plainTextEdit.setPlainText(html)
        self.sourceDirty = False

    def openLink(self, url):
        msg = "Open {url} ?".format(url=str(url))
        if (QMessageBox.question(self, self.tr("Open link"), msg,
            QMessageBox.Open|QMessageBox.Cancel)) == QMessageBox.Open:
            QDesktopServices.openUrl(url)

    @pyqtSlot(int)
    def changeZoom(self, percent):
        self.actionZoomOut.setEnabled(percent > 25)
        self.actionZoomIn.setEnabled(percent < 400)
        factor = float(percent) / 100
        self.webView.setZoomFactor(factor)

        self.zoomLabel.setText(" Zoom: {percent}% ".format(percent=percent))
        self.zoomSlider.setValue(percent)

    def closeEvent(self, event):
        if self.maybeSave():
            event.accept()
        else:
            event.ignore()

    def load(self, f):
        if not QFile.exists(f):
            return False
        fd = QFile(f)
        if not fd.open(QFile.ReadOnly):
            return False

        data = fd.readAll()
        self.webView.setContent(data, "text/html")

        self.setCurrentFileName(f)
        return True

    def setCurrentFileName(self, fileName):
        self.fileName = fileName
        if not fileName:
            shownName = str("Untitled")
        else:
            shownName = str(QFileInfo(fileName).fileName())

        self.setWindowTitle("{shownName}[*] - {app_name}".format(shownName=shownName,app_name="HTML Editor"))
        self.setWindowModified(False)

        allowSave = True
        if not fileName or fileName.startswith(str(":/")):
            allowSave = False
        self.actionFileSave.setEnabled(allowSave)

    @QtCore.pyqtSlot(str)
    def js_new_pos(self, pos):
        self.adjustActions()

    def js_callback(self, result):
        # Result is formated like this: <true|false>:<formatting>
        results = result.split(':')
        if len(results) != 2:
            print('unexpected result: %s' % result)
            return
        status = results[0]
        formatting = results[1]
        status = True if status == 'true' else False
        format_action_map = { 'bold' : self.actionFormatBold,
                              'italic' : self.actionFormatItalic,
                              'underLine' : self.actionFormatUnderline,
                              'strikeThrough' : self.actionFormatStrikethrough,
                              'alignLeft' : self.actionFormatAlignLeft,
                              'alignCenter' : self.actionFormatAlignCenter,
                              'alignRight' : self.actionFormatAlignRight,
                              'alignJustify' : self.actionFormatAlignJustify,
                              'unorderedList' : self.actionFormatBulletedList,
                              'orderedList' : self.actionFormatNumberedList }
        action_to_set = format_action_map[formatting]
        action_to_set.setChecked(status)

    def run_javascript(self, script, callback=None):
        """
        Run some Javascript in the WebView

        :param script: The script to run, a string
        :param callback: Use callback to handle result. Defaults to None
        """
        if not callback:
            self.webView.page().runJavaScript(script)
        else:
            self.webView.page().runJavaScript(script, callback)
            return False
