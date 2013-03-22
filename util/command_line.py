#
# command_line.py
#
#  Copyright (C) 2013 Diamond Light Source
#
#  Author: James Parkhurst
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
from __future__ import division

def parse_range_list_string(string):
    """Parse a string in the following ways:
    string: 1, 2, 3        -> [1, 2, 3]
    string: 1 - 6          -> [1, 2, 3, 4, 5, 6]
    string: 1 - 6, 7, 8, 9 -> [1, 2, 3, 4, 5, 6, 7, 8, 9]
    """
    items = string.split(',')
    for i in range(len(items)):
        items[i] = items[i].split("-")
        if len(items[i]) == 1:
            items[i] = [int(items[i][0])]
        elif len(items[i]) == 2:
            items[i] = range(int(items[i][0]), int(items[i][1]) + 1)
        else:
            raise SyntaxError
    items = [item for sublist in items for item in sublist]
    return set(items)

def interactive_console(namespace):
    """ Enter an interactive console session. """
    try:
        from IPython import embed
        embed(user_ns = namespace)
    except ImportError:
        print "IPython not available"

class ProgressBar:
    """ A command line progress bar. """

    def __init__(self, spinner=True, bar=True, length=50):
        """ Init the progress bar parameters. """

        # Set the parameters
        self._spinner = spinner
        self._bar = bar
        self._length = length
        
        # Print 0 percent
        self.update(0)

    def update(self, percent):
        """ Update the progress bar with a percentage. """
        import sys
        
        # Get integer percentage
        percent = int(percent)
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        
        # Add a percentage counter
        progress_str = '\r'
        progress_str += '{0: >3}%'.format(percent)
        
        # Add a spinner
        if self._spinner:
            progress_str += ' '
            progress_str += '[ {0} ]'.format('-\|/'[percent % 4])
        
        # Add a bar
        if self._bar:
            n_char = int(percent * self._length / 100)
            n_space = self._length - n_char
            progress_str += ' '
            progress_str += '[ {0}>{1} ]'.format('=' * n_char, ' ' * n_space)
        
        # Print progress string to stdout
        sys.stdout.write(progress_str)
        sys.stdout.flush()
        
    def finished(self):
        """ The progress bar is finished. """
        self.update(100)        
        print ""
