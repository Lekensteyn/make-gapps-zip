#!/usr/bin/env python
# Scans for library dependencies and plot a graph between those.
#
# Usage: scanlibs.py [-plot] files...
#
# Print all libraries and its dependencies (paths followed by zero or more
# dynamically linked libraries, optionally followed by a dot and one or more
# runtime dependencies. Non-ELF input files are prepended with '#'):
#
#   find system/ -type f -exec ./scanlibs.py {} +
#
# Draws a plot for all libraries and its dependencies (orange edges mark runtime
# dependencies that are not dynamically linked, bisque nodes are files that were
# passed as argument):
#
#   find system/ -type f -exec ./scanlibs.py -plot {} +
#
# Copyright (C) 2015 Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license, see LICENSE for details.

import re, sys

# For parsing binaries (programs and libraries).
from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFError

# For -plot
import networkx as nx

# Library dependencies that are ignored. These common libraries are
# likely not interesting but makes the plot unreadable.
exclude_libs = [
# Core libraries
'libc.so',
'libm.so',
'libdl.so',
'libstdc++.so',
#'libc++.so', # LLVM C++ library
# Other common libraries
#'libcrypto.so',
#'libz.so',
# Android-specific core libraries
'libutils.so',
'libcutils.so',
'liblog.so',
]


class SetList(list):
    def add(self, item):
        '''Adds an item to the list only if it did not occur before.'''
        if item not in self:
            list.append(self, item)

def get_needed_libs(filename):
    '''
    Returns a list of library names that are needed by the given file.

    Names might be duplicated, use set() to eliminate those.
    :raises ELFError: for bad binaries.
    :returns: A list of dynamic libraries and another list of possible runtime
    libraries. The former is fully correct, the latter may contain false
    matches.
    :rtype: (list, list)
    '''
    dyn_libs = SetList()
    runtime_libs = SetList()

    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        # Libraries that are directly linked. Comparable to this command:
        # readelf -d libloc_core.so | grep NEEDED
        dynamic_section = elffile.get_section_by_name(b'.dynamic')
        if dynamic_section:
            for tags in dynamic_section.iter_tags(type='DT_NEEDED'):
                dyn_libs.add(tags.needed)

        # Other libraries, possibly loaded via dlopen("libfoo.so").
        # Assume that strings are NUL-terminated. It cannot be assumed that the
        # preceding data is a NUL-terinated string though.
        # Assume const char*, not char[] (those could end up in .text).
        rodata = elffile.get_section_by_name(b'.rodata')
        if rodata:
            # Optional directory components ("/system/lib/")
            libpath_pattern = br'(?:[\w.-/]+/)?'
            # "libfoo.so"
            libpath_pattern += br'lib[\w.-]+\.so(?=\0)'
            other_libs = re.findall(libpath_pattern, rodata.data())
            for name in other_libs:
                runtime_libs.add(name)

    # Return a list of (unicode) strings, not bytes (in Python 3).
    return tuple([name.decode('utf8') for name in libs]
            for libs in (dyn_libs, runtime_libs))

def iter_files(filenames):
    '''
    Yields a filename and its libraries (a tuple of dynamic and runtime
    libraries). If an existing file could not be parsed as ELF file, then None
    is given instead of this tuple.
    '''
    for filename in filenames:
        try:
            dyn_libs, runtime_libs = get_needed_libs(filename)

            # Remove common libraries
            for libname in exclude_libs:
                for libs in dyn_libs, runtime_libs:
                    if libname in libs:
                        libs.remove(libname)

            yield filename, (dyn_libs, runtime_libs)
        except ELFError as e:
            yield filename, None

def dump_libs(filenames):
    for filename, libs in iter_files(filenames):
        if not libs:
            print('# %s' % filename)
            continue

        dyn_libs, runtime_libs = libs
        print(filename)
        # Note that these outputs can be empty if there are no unignored libs.
        for lib in dyn_libs:
            print('  %s' % lib)
        if runtime_libs:
            print('  .')
            for lib in runtime_libs:
                print('  %s' % lib)

def _filename_to_node_label(filename):
    #return filename
    return filename.split('/')[-1]

def plot_libs(filenames):
    G = nx.DiGraph()
    for filename, libs in iter_files(filenames):
        source_node = _filename_to_node_label(filename)

        # Color nodes which are located on the filesystem
        source_node_attr = {
            'fillcolor': 'bisque',
            'style': 'filled',
        }
        if not libs:
            # Add a red border for non-ELF files
            source_node_attr['color'] = 'red'
        G.add_node(source_node, **source_node_attr)

        # Library lists can be None, so skip processing if the lists are empty.
        if not libs:
            continue

        dyn_libs, runtime_libs = libs
        for libname in set(dyn_libs + runtime_libs):
            dest_node = _filename_to_node_label(libname)

            # Color edges which are not dynamically linked (that is, these are
            # only referenced at runtime).
            edge_attr = {}
            if libname not in dyn_libs:
                edge_attr['color'] = 'orange'

            G.add_edge(source_node, dest_node, **edge_attr)

    # Use pygraphviz for better node sizes.
    A = nx.to_agraph(G)

    # See http://www.graphviz.org/doc/info/attrs.html#d:rankdir
    A.graph_attr.update(
        rankdir='LR',
        overlap=False,
    )

    # 'neato' is default, but edges overlap nodes. Try 'dot' instead.
    A.layout(prog='dot')

    # Possible formats are at http://www.graphviz.org/doc/info/output.html
    A.draw(format='xlib')

if __name__ == '__main__':
    args = sys.argv[1:]
    if '-plot' in args:
        args.remove('-plot')
        plot_libs(args)
    else:
        dump_libs(args)
