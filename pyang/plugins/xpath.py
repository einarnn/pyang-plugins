"""Generate CSV file of xpaths, types abd something else.
"""

import optparse
import sys

from pyang import plugin
from pyang import statements

def pyang_plugin_init():
    plugin.register_plugin(XPathPlugin())

class XPathPlugin(plugin.PyangPlugin):
    def add_output_format(self, fmts):
        self.multiple_modules = True
        fmts['xpath'] = self

    def add_opts(self, optparser):
        pass
        # optlist = [
        #     optparse.make_option("--jstree-no-path",
        #                          dest="jstree_no_path",
        #                          action="store_true",
        #                          help="""Do not include paths to make
        #                                page less wide"""),
        #     ]

        # g = optparser.add_option_group("JSTree output specific options")
        # g.add_options(optlist)

    def setup_fmt(self, ctx):
        ctx.implicit_errors = False

    def emit(self, ctx, modules, fd):
        emit_tree(modules, fd, ctx)

levelcnt = [0]*100

def emit_tree(modules, fd, ctx):
    global levelcnt
    for module in modules:
        bstr = ""
        b = module.search_one('belongs-to')
        if b is not None:
            bstr = " (belongs-to %s)" % b.arg
        ns = module.search_one('namespace')
        if ns is not None:
            nsstr = ns.arg
        pr = module.search_one('prefix')
        if pr is not None:
            prstr = pr.arg
        else:
            prstr = ""

        temp_mod_arg = module.arg
        # html plugin specific changes
        if hasattr(ctx, 'html_plugin_user'):
           from pyang.plugins.html import force_link
           temp_mod_arg = force_link(ctx,module,module)

        levelcnt[1] += 1
        # fd.write("""<tr id="%s" class="a">
        #              <td id="p1">
        #                 <div id="p2" class="tier1">
        #                    <a href="#" id="p3"
        #                       onclick="toggleRows(this);return false;"
        #                       class="folder">&nbsp;
        #                    </a>
        #                    <font color=blue>%s</font>
        #                 </div>
        #              </td> \n""" %(levelcnt[1], temp_mod_arg))
        # fd.write("""<td>%s</td><td></td><td></td><td></td><td>
        #             </td></tr>\n""" %module.keyword)
        #fd.write("<td>module</td><td></td><td></td><td></td><td></td></tr>\n")

        chs = [ch for ch in module.i_children
               if ch.keyword in statements.data_definition_keywords]
        print_children(chs, module, fd, ' ', ctx, 2)

        rpcs = module.search('rpc')
        levelcnt[1] += 1
        if len(rpcs) > 0:
            fd.write("""<tr id="%s" class="a">
                         <td nowrap id="p1000">
                            <div id="p2000" class="tier1">
                               <a href="#" id="p3000"
                                  onclick="toggleRows(this);
                                  return false;" class="folder">&nbsp;
                               </a>
                               %s:rpcs
                            </div>
                         </td> \n""" %(levelcnt[1],prstr))
            fd.write("<td></td><td></td><td></td><td></td><td></td></tr>\n")
            print_children(rpcs, module, fd, ' ', ctx, 2)

        notifs = module.search('notification')
        levelcnt[1] += 1
        if len(notifs) > 0:
            fd.write("""<tr id="%s" class="a">
                        <td nowrapid="p4000">
                           <div id="p5000" class="tier1">
                              <a href="#" id="p6000"
                                 onclick="toggleRows(this);return false;"
                                 class="folder">&nbsp;
                              </a>%s:notifs
                           </div>
                        </td> \n""" %(levelcnt[1],prstr))
            fd.write("<td></td><td></td><td></td><td></td><td></td></tr>\n")
            print_children(notifs, module, fd, ' ', ctx, 2)

def print_children(i_children, module, fd, prefix, ctx, level=0):
    for ch in i_children:
        print_node(ch, module, fd, prefix, ctx, level)

def print_node(s, module, fd, prefix, ctx, level=0):

    global levelcnt
    fontstarttag = ""
    fontendtag = ""
    status = get_status_str(s)
    nodetype = ''
    options = ''
    folder = False
    if s.i_module.i_modulename == module.i_modulename:
        name = s.arg
    else:
        name = s.i_module.i_prefix + ':' + s.arg

    pr = module.search_one('prefix')
    if pr is not None:
        prstr = pr.arg
    else:
        prstr = ""

    descr = s.search_one('description')
    descrstring = "No description"
    if descr is not None:
        descrstring = descr.arg
    flags = get_flags_str(s)
    if s.keyword == 'list':
        folder = True
    elif s.keyword == 'container':
        folder = True
        p = s.search_one('presence')
        if p is not None:
            pr_str = p.arg
            options = "<abbr title=\"" + pr_str + "\">Presence</abbr>"
    elif s.keyword  == 'choice':
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
        name += '[' + s.search_one('key').arg +  ']'

    descr = s.search_one('description')
    if descr is not None:
        descrstring = ''.join([x for x in descr.arg if ord(x) < 128])
    else:
        descrstring = "No description";
    levelcnt[level] += 1
    idstring = str(levelcnt[1])

    for i in range(2,level+1):
        idstring += '-' + str(levelcnt[i])

    pathstr = ""
    if not ctx.opts.jstree_no_path:
        pathstr = statements.mk_path_str(s, True)

    if '?' in options:
        fontstarttag = "<em>"
        fontendtag = "</em>"
    keyword = s.keyword

    #
    # Just print path string
    #
    print("%s,%s,%s" % (pathstr,s.keyword,nodetype))
    
    # if folder:
    #     # html plugin specific changes
    #     if hasattr(ctx, 'html_plugin_user'):
    #        from pyang.plugins.html import force_link
    #        name = force_link(ctx,s,module,name)
    #     fd.write("""<tr id="%s" class="a">
    #                    <td nowrap id="p4000">
    #                       <div id="p5000" class="tier%s">
    #                          <a href="#" id="p6000"
    #                             onclick="toggleRows(this);return false"
    #                             class="folder">&nbsp;
    #                          </a>
    #                          <abbr title="%s">%s</abbr>
    #                       </div>
    #                    </td> \n""" %(idstring, level, descrstring, name))
    #     fd.write("""<td nowrap>%s</td>
    #                 <td nowrap>%s</td>
    #                 <td nowrap>%s</td>
    #                 <td>%s</td>
    #                 <td>%s</td>
    #                 <td nowrap>%s</td>
    #                 </tr> \n""" %(s.keyword,
    #                               nodetype,
    #                               flags,
    #                               options,
    #                               status,
    #                               pathstr))
    # else:
    #     if s.keyword in ['action', ('tailf-common', 'action')]:
    #         classstring = "action"
    #         typeinfo = action_params(s)
    #         typename = "parameters"
    #         keyword = "action"
    #     elif s.keyword == 'rpc' or s.keyword == 'notification':
    #         classstring = "folder"
    #         typeinfo = action_params(s)
    #         typename = "parameters"
    #     else:
    #         classstring = s.keyword
    #         typeinfo = typestring(s)
    #         typename = nodetype
    #     fd.write("""<tr id="%s" class="a">
    #                    <td nowrap>
    #                       <div id=9999 class=tier%s>
    #                          <a class="%s">&nbsp;</a>
    #                          <abbr title="%s"> %s %s %s</abbr>
    #                       </div>
    #                    </td>
    #                    <td>%s</td>
    #                    <td nowrap><abbr title="%s">%s</abbr></td>
    #                    <td nowrap>%s</td>
    #                    <td>%s</td>
    #                    <td>%s</td>
    #                    <td nowrap>%s</td</tr> \n""" %(idstring,
    #                                                   level,
    #                                                   classstring,
    #                                                   descrstring,
    #                                                   fontstarttag,
    #                                                   name,
    #                                                   fontendtag,
    #                                                   keyword,
    #                                                   typeinfo,
    #                                                   typename,
    #                                                   flags,
    #                                                   options,
    #                                                   status,
    #                                                   pathstr))

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
    elif s.i_config == True:
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
        found  = False
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
            if pattern is not None: # truncate long patterns
                found = True
                s = s + ' {pattern = ' + pattern.arg + '}'
        return s

    s = get_nontypedefstring(node)

    if s != "":
        t = node.search_one('type')
        # chase typedef
        type_namespace = None
        i_type_name = None
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
            pmodule = statements.prefix_to_module(t.i_module,prefix,t.pos,err)
            if pmodule is None:
                return
            typedef = statements.search_typedef(pmodule, name)
        if typedef != None:
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

