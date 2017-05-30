"""
Basic command line for HearingLossSimulator
"""




import sys
import os
import argparse



comand_list =[
    'audiodevice',
    'wifidevice',
    
]
txt_command_list = ', '.join(comand_list)


def open_mainwindow():
    import PyQt5
    import pyqtgraph as pg
    from hearinglosssimulator.gui.mainwindow import MainWindow
    
    app = pg.mkQApp()
    win = MainWindow()
    win.show()
    app.exec_()


def open_hls_wifi():
    print('TODO GUI wifi')
    
def hls():
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='hearinglosssimulator')
    parser.add_argument('command', help='command in [{}]'.format(txt_command_list), default='audiodevice', nargs='?')
    
    parser.add_argument('-i', '--input', help='working directory', default=None)
    parser.add_argument('-o', '--output', type=int, help='channel group index', default=None)
    parser.add_argument('-p', '--parameters', help='JSON parameter file', default=None)
    
    
    args = parser.parse_args(argv)
    #~ print(sys.argv)
    #~ print(args)
    #~ print(args.command)
    
    command = args.command
    if not command in comand_list:
        print('command should be in [{}]'.format(txt_command_list))
        exit()
    
    if command=='audiodevice':
        open_mainwindow()
    
    elif command=='wifidevice':
        open_hls_wifi()



if __name__=='__main__':
    open_mainwindow()





    
