#!/usr/bin/env python
# Scans for library dependencies and plot a graph between those.
#
# Copyright (C) 2015 Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license, see LICENSE for details.
#
# Invoke `scanlibs.py --help` for usage. Examples:
#
# Print all libraries and its dependencies (paths followed by zero or more
# dynamically linked libraries, optionally followed by a dot and one or more
# runtime dependencies. Non-ELF input files are prepended with '#'):
#
#   find system/ -type f -exec ./scanlibs.py {} + > dependencies.txt
#
# Draws a plot for all libraries and its dependencies (orange edges mark runtime
# dependencies that are not dynamically linked, bisque nodes are files that were
# passed as argument):
#
#   find system/ -type f -exec ./scanlibs.py --plot {} +
#
# Draws a plot given a previous dependencies file:
#
#   ./scanlibs.py --plot --deps-file dependencies.txt

import argparse, re

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

def dump_libs(dependencies):
    for filename, libs in dependencies:
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

# Template for HTML outputs
_html_header = '''
<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="user-scalable=no,width=device-width,initial-scale=1,maximum-scale=1">
<style>html,body{overflow:hidden;margin:0;padding:0;width:100vw;height:100vh;}</style>
<script src="https://ariutta.github.io/svg-pan-zoom/dist/svg-pan-zoom.min.js"></script>
<script>self.onload=function(){svgPanZoom(document.querySelector('svg'),{minZoom:.1,maxZoom:2});};</script>
'''.strip()

def plot_libs(dependencies, plot_path=None, plot_format=None):
    G = nx.DiGraph()
    for filename, libs in dependencies:
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
    if not plot_format:
        if not plot_path:
            plot_format = 'xlib'
        elif plot_path.endswith('.html'):
            plot_format = 'html'
    if plot_format == 'html':
        svg = A.draw(format='svg').decode('utf8')
        html = re.sub(r'<\?xml[^>]+>\n<!DOCTYPE.+\n[^>]+>', '', svg, count=1)
        with open(plot_path, 'w') as f:
            f.write(_html_header)
            f.write(html)
    else:
        A.draw(path=plot_path, format=plot_format)

def parse_inputs(deps_filename, filenames):
    if deps_filename:
        with open(deps_filename) as f:
            filename, dyn_libs, runtime_libs = None, None, None
            libs = None
            for line in f:
                line = line.rstrip()

                # Detect end of dependencies list for previous program or lib.
                if not line.startswith('  '):
                    if filename:
                        yield filename, (dyn_libs, runtime_libs)
                    filename = None

                if line.startswith('# '):
                    # Could not be parsed as ELF file
                    yield line[2:], None
                elif line.startswith('  '):
                    # Dependencies for previous program or library.
                    dep_filename = line[2:]
                    assert filename
                    if dep_filename == '.': # Marker for begin of runtime libs.
                        libs = runtime_libs
                    else:
                        libs.append(dep_filename)
                else:
                    # Begin of library name
                    filename = line
                    dyn_libs, runtime_libs = [], []
                    libs = dyn_libs
            if filename:
                yield filename, (dyn_libs, runtime_libs)
    if filenames:
        for item in iter_files(filenames):
            yield item

_parser = argparse.ArgumentParser()
_parser.add_argument('--plot', action='store_true',
        help='Draw a plot instead of generating output')
_parser.add_argument('--plot-output', metavar='FILENAME',
        help='''
        Outputs a plot to the given file. The extension dictates the output
        format (e.g. dot (default), svg, png, html (special)). Implies --plot.
        ''')
_parser.add_argument('--plot-format', metavar='FORMAT',
        help='''
        Overrides the default plot format (the extension or "dot" for
        --plot-output, xlib otherwise). Implies --plot.
        See http://www.graphviz.org/doc/info/output.html for a list of formats.
        The special "html" format will result in a SVG-based HTML file.
        ''')
_parser.add_argument('--deps-file', metavar='FILENAME',
        help='Read dependencies from file')
_parser.add_argument('files', nargs='*',
        help='Files to be parsed in addition to the (optional) dependencies file.')

if __name__ == '__main__':
    args = _parser.parse_args()
    if args.files:
        # For parsing binaries (programs and libraries).
        from elftools.elf.elffile import ELFFile
        from elftools.common.exceptions import ELFError
    if args.plot_output or args.plot_format:
        args.plot = True
    if args.plot:
        import networkx as nx

    dependencies = parse_inputs(args.deps_file, args.files)

    if args.plot:
        plot_libs(
            dependencies,
            plot_path=args.plot_output,
            plot_format=args.plot_format
        )
    else:
        dump_libs(dependencies)
