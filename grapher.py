#!/usr/bin/python

from pyggy import lexer, glr, srgram, pylly, pyggy, util
from tempfile import NamedTemporaryFile, mkdtemp
from shutil import rmtree
import pydot
import getopt
import sys
import os

def main():
    try:
        options, args = getopt.getopt(sys.argv[1:], 'p:a:i:ho:', ['help'])
        out_filename = None
        out_format = None
        instring = None
        frame_delay = None
        animated = False
        prefix = get_prefix()
        for option, arg in options:
            if option == '-o':
                out_filename = arg
            elif option == '-p':
                if not os.path.exists(arg):
                    raise geopt.GetoptError("Dot prefix file doesn't exist: "+arg)
                prefix = file(arg, "r").read() 
            elif option in ('-h', '--help'):
                usage()
                sys.exit(0)
            elif option == '-i':
                instring = arg
            elif option == '-a':
               animated = True 
               frame_delay = float(arg)
            else:
                raise getopt.GetoptError("Invalid option: %s" % option)

        grammar_filename = filter(lambda f: f[-4:] == ".pyg", args)
        lex_filename = filter(lambda f: f[-4:] == ".pyl", args)
        if not grammar_filename:
            raise getopt.GetoptError("No input grammar file given")
        if not lex_filename:
            raise getopt.GetoptError("No input lexical spec file given")
        grammar_filename = grammar_filename[0]
        lex_filename = lex_filename[0]

        if animated and not out_filename:
            # default filename = <grammar>_graph.gif
            base_index = grammar_filename.index(".pyg")
            out_filename = "%s_graph.gif" % grammar_filename[:base_index]
        if out_filename:
            out_format = out_filename[-3:]
        if animated and out_format != "gif":
            raise getopt.GetoptError("Output filename must end in .gif with -a option")
        if out_filename and out_format not in pydot.Dot.formats:
            raise getopt.GetoptError("Format not supported: "+out_format)

    except getopt.GetoptError, e:
       print str(e)
       sys.exit(2)

    # pyyl.sanity() prints out stuff and it doesn't look like I can shut it up, 
    # so wrap it in /* */ so any output is ignored by Dot
    print "/*",
    parser = get_parser(grammar_filename)
    lexer = get_lexer(lex_filename)
    print "*/",
    if not instring:
        lexer.setinput("-")
    else:
        lexer.setinputstr(instring)
    parser.setlexer(lexer)
    tree = parser.parse()
    dot_list = get_dot_list(tree)

    if not animated:
        dot = pydot.graph_from_dot_data(prefix+'\n'.join(dot_list)+"}")
        if not out_filename:
            print dot.to_string()
        else:
            dot.write(path = out_filename, format = out_format)
    else:
        image_sequence = []
        #temporary directory for storing frames of the to-be animation
        dir_name = mkdtemp()
        path = ""
        for i in range(len(dot_list)+1):
            dot = pydot.graph_from_dot_data(prefix+'\n'.join(dot_list[1:i])+"}")
            path = "%s/%s%i.gif" % (dir_name, i < 10 and "0" or "", i)
            dot.write(path = path, format = "gif")
        # get the size of the largest image to use as size argument for animation
        cmd = "identify -format '%wx%h' "+path
        size = os.popen(cmd).read().strip()
        # assemble frames into animation with ImageMagick
        cmd = "convert -dispose 2 -extent %s -delay %d -loop 0 %s/*.gif %s" % (size, frame_delay, dir_name, out_filename)
        os.system(cmd)
        # clean-up
        rmtree(dir_name)

def get_prefix():
    return """
digraph "parse_tree" {
        node [
                fontsize = "12"
                fontname = "Courier"
                fontcolor = "black"
                shape = "ellipse"
                color = "black"
                style = "solid"
        ];
    """


def usage():
    print """usage: grapher.py [options] <grammar> <lexicalspec>

Where <grammar> is a .pyg file containing a CFG grammar, <lexicalspec> is a .pyl containing
the lexical specifications, and [options] is taken from the following list:
  -p <file>     Override default prefix for dot files with given file.
  -a <delay>    If set, write an animated GIF showing the construction of the parse tree
                from top to bottom, with <delay> ms delay between each frame.
  -o <outfile>  Write to given file. Extension determines format. If not specified, dot file 
                will be printed to stdout.
  -i <instring> String to parse. If not provided, input will be taken from STDIN.
  -h, --help    Print this message"""

def get_parser(filename):
    #create temporary file for the machine-generated Python stuff
    prefix = os.path.basename(filename)[:-4]
    temp = NamedTemporaryFile(prefix = prefix, suffix = "_gramtab.py")
    pyggy.parsespec(filename, temp.name)
    gram = {}
    exec temp.read() in gram
    g = srgram.SRGram(gram['gramspec'])
    p = glr.GLR(g)
    #don't need this anymore ~desu
    temp.close()
    return p

def get_lexer(filename):
    prefix = os.path.basename(filename)[:-4]
    temp = NamedTemporaryFile(prefix = prefix, suffix = "lextab.py")
    lex = {}
    pylly.parsespec(filename, temp.name)
    exec temp.read() in lex
    temp.close()
    return lexer.lexer(lex['lexspec'])

def get_dot_list(tree):
    #mostly taken from pyggy.glr.dottree. Rewritten to stop using dumb dot object.
    level_list = []
    level_list.append("start -> sym_%s;" % hash(tree))
    dot_list_rec(level_list, tree, {}, {})
    return level_list

def dot_list_rec(level_list, sym, rules, syms):
    #mostly taken from pyggy.glt.dottree_rec
    "helper for dottree()"
    if syms.has_key(sym) :
        return
    syms[sym] = 1

    name = util.printable(str(sym.sym), 1, 0)
    string = 'sym_%d [label="%s", color=red];\n' % (hash(sym), name)
    for p in sym.possibilities :
        #string += "sym_%d -> rule_%d;\n" % (hash(sym), hash(p))
        if not rules.has_key(p):
            rules[p] = 1
            name = util.printable(str(p.rule), 1, 0)
            #string += 'rule_%d [label="%s"];\n' % (hash(p), name)
            for e in p.elements:
                if isinstance(e.sym, tuple):
                    string += 'sym_%d [label="%s"];\n' % (hash(e), e.sym[1])
                string += "sym_%d -> sym_%d;\n" % (hash(sym), hash(e))
                dot_list_rec(level_list, e, rules, syms)
        level_list.append(string)

if __name__ == '__main__':
    main()
