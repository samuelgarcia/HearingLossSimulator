 
import sys
from hearinglosssimulator.gui.myqt import QT, mkQApp, QT_MODE
print('QT_MODE', QT_MODE)

import  hearinglosssimulator.gui.icons

#~ print(dir(hearinglosssimulator.gui.icons))
if __name__ == '__main__' :
	app = mkQApp()
	
	w = QT.QWidget()
	w.show()
	w.setWindowIcon(QT.QIcon(':/bypass.png'))
	
	app.exec_()
	
	
