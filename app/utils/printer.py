def beautify_print(level, message):
    if level == 'INFO':
        print('\033[1;34m' + 'INFO: ' + '\033[0m', end='')
    else:
        print('\033[1;31m' + 'ERROR: ' + '\033[0m', end='')

    print('\033[1;31m' + message + '\033[0m')
