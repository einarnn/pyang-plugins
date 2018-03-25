"""Generate CSV file of xpaths. Derived from JSTree plugin.
"""
import optparse

from pyang import plugin
from pyang import statements


def pyang_plugin_init():
    plugin.register_plugin(XPathPlugin())


class XPathPlugin(plugin.PyangPlugin):
    def add_output_format(self, fmts):
        self.multiple_modules = True
        fmts['xpath'] = self

    def add_opts(self, optparser):
        optlist = [
            optparse.make_option("--foo",
                                 dest="foo",
                                 action="store_true",
                                 help="no arg"),
            ]
        optparser.add_options(optlist)

    def setup_fmt(self, ctx):
        ctx.implicit_errors = False

    def emit(self, ctx, modules, fd):
        emit_tree(modules, fd, ctx)


def emit_tree(modules, fd, ctx):
    for module in modules:
        chs = [ch for ch in module.i_children
               if ch.keyword in statements.data_definition_keywords]
        print_children(chs, module, fd, ' ', ctx, 2)


def print_children(i_children, module, fd, prefix, ctx, level=0):
    for ch in i_children:
        print_node(ch, module, fd, prefix, ctx, level)


def print_node(s, module, fd, prefix, ctx, level=0):

    fontstarttag = ""
    fontendtag = ""
    nodetype = ''
    options = ''
    folder = False
    if s.i_module.i_modulename == module.i_modulename:
        name = s.arg
    else:
        name = s.i_module.i_prefix + ':' + s.arg

    if s.keyword == 'list':
        folder = True
    elif s.keyword == 'container':
        folder = True
        p = s.search_one('presence')
        if p is not None:
            pr_str = p.arg
            options = "<abbr title=\"" + pr_str + "\">Presence</abbr>"
    elif s.keyword == 'choice':
        folder = True
        m = s.search_one('mandatory')
        if m is None or m.arg == 'false':
            name = '(' + s.arg + ')'
            options = 'Choice'
        else:
            name = '(' + s.arg + ')'
    elif s.keyword == 'case':
        folder = True
        # fd.write(':(' + s.arg + ')')
        name = ':(' + s.arg + ')'
    elif s.keyword == 'input':
        folder = True
    elif s.keyword == 'output':
        folder = True
    elif s.keyword == 'rpc':
        folder = True
    elif s.keyword == 'notification':
        folder = True
    else:
        if s.keyword == 'leaf-list':
            options = '*'
        elif s.keyword == 'leaf' and not hasattr(s, 'i_is_key'):
            m = s.search_one('mandatory')
            if m is None or m.arg == 'false':
                options = '?'
        nodetype = get_typename(s)

    if s.keyword == 'list' and s.search_one('key') is not None:
        name += '[' + s.search_one('key').arg + ']'

    pathstr = ""
    if not ctx.opts.jstree_no_path:
        pathstr = statements.mk_path_str(s, True)

    keyword = s.keyword

    #
    # Just print path string
    #
    print("%s,%s,%s" % (pathstr, s.keyword, nodetype))

    if hasattr(s, 'i_children'):
        level += 1
        if s.keyword in ['choice', 'case']:
            print_children(s.i_children, module, fd, prefix, ctx, level)
        else:
            print_children(s.i_children, module, fd, prefix, ctx, level)


def get_status_str(s):
    status = s.search_one('status')
    if status is None or status.arg == 'current':
        return 'current'
    else:
        return status


def get_flags_str(s):
    if s.keyword == 'rpc':
        return ''
    elif s.keyword == 'notification':
        return ''
    elif s.i_config is True:
        return 'config'
    else:
        return 'no config'


def get_typename(s):
    t = s.search_one('type')
    if t is not None:
        return t.arg
    else:
        return ''


def typestring(node):

    def get_nontypedefstring(node):
        s = ""
        found = False
        t = node.search_one('type')
        if t is not None:
            s = t.arg + '\n'
            if t.arg == 'enumeration':
                found = True
                s = s + ' : {'
                for enums in t.substmts:
                    s = s + enums.arg + ','
                s = s + '}'
            elif t.arg == 'leafref':
                found = True
                s = s + ' : '
                p = t.search_one('path')
                if p is not None:
                    s = s + p.arg

            elif t.arg == 'identityref':
                found = True
                b = t.search_one('base')
                if b is not None:
                    s = s + ' {' + b.arg + '}'

            elif t.arg == 'union':
                found = True
                uniontypes = t.search('type')
                s = s + '{' + uniontypes[0].arg
                for uniontype in uniontypes[1:]:
                    s = s + ', ' + uniontype.arg
                s = s + '}'

            typerange = t.search_one('range')
            if typerange is not None:
                found = True
                s = s + ' [' + typerange.arg + ']'
            length = t.search_one('length')
            if length is not None:
                found = True
                s = s + ' {length = ' + length.arg + '}'

            pattern = t.search_one('pattern')
            if pattern is not None:  # truncate long patterns
                found = True
                s = s + ' {pattern = ' + pattern.arg + '}'
        return s

    s = get_nontypedefstring(node)

    if s != "":
        t = node.search_one('type')
        # chase typedef
        name = t.arg
        if name.find(":") == -1:
            prefix = None
        else:
            [prefix, name] = name.split(':', 1)
        if prefix is None or t.i_module.i_prefix == prefix:
            # check local typedefs
            pmodule = node.i_module
            typedef = statements.search_typedef(t, name)
        else:
            # this is a prefixed name, check the imported modules
            err = []
            pmodule = statements.prefix_to_module(
                t.i_module, prefix, t.pos, err)
            if pmodule is None:
                return
            typedef = statements.search_typedef(pmodule, name)
        if typedef is not None:
            s = s + get_nontypedefstring(typedef)
    return s


def action_params(action):
    s = ""
    for params in action.substmts:

        if params.keyword == 'input':
            inputs = params.search('leaf')
            inputs += params.search('leaf-list')
            inputs += params.search('list')
            inputs += params.search('container')
            inputs += params.search('anyxml')
            inputs += params.search('uses')
            for i in inputs:
                s += ' in: ' + i.arg + "\n"

        if params.keyword == 'output':
            outputs = params.search('leaf')
            outputs += params.search('leaf-list')
            outputs += params.search('list')
            outputs += params.search('container')
            outputs += params.search('anyxml')
            outputs += params.search('uses')
            for o in outputs:
                s += ' out: ' + o.arg + "\n"
    return s
