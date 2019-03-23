"""Generate top-level subtree filters for modules.
"""
import optparse

from pyang import plugin
from pyang import statements
from lxml import etree
from lxml import objectify
import sys

def pyang_plugin_init():
    plugin.register_plugin(NSConvPlugin())


class NSConvPlugin(plugin.PyangPlugin):
    def add_output_format(self, fmts):
        self.multiple_modules = True
        fmts['nsconv'] = self

    def add_opts(self, optparser):
        optlist = [
            optparse.make_option("--xml",
                                 metavar="XMLDOC",
                                 dest="xml",
                                 default=None,
                                 type="str",
                                 help="XML document to convert"),
            ]
        optparser.add_options(optlist)

    def setup_fmt(self, ctx):
        ctx.implicit_errors = False

    def emit(self, ctx, modules, fd):
        if not ctx.opts.xml:
            fd.write('No XML file!\n')
            sys.exit(1)
        try:
            doc = etree.parse(open(ctx.opts.xml, 'rb'))
            native = doc.xpath('//*[local-name()="native"]')
            if not native:
                print('No node \'native\'!!')
                sys.exit(1)

            # find the Cisco-IOS-XE-native module
            module_native = None
            for m in modules:
                if m.i_modulename == 'Cisco-IOS-XE-native':
                    module_native = m
                    break
            if not module_native:
                print('Cisco-IOS-XE-native not loaded!')
                sys.exit(1)

            # replace all namespaces from XML doc
            replace_namespaces(module_native, [], native[0])

            # cleanup the namespaces for display
            etree.cleanup_namespaces(doc)

            # print the modified doc
            fd.write(etree.tostring(doc, pretty_print=True).decode())
            fd.write('\n')
        except:
            fd.write('\n')
            fd.write('Failed to process file\n')
        

def strip_namespaces(path, e):
    '''
    Strip XML namespace from every node.
    '''
    path_elem = etree.QName(e.tag).localname
    e.tag = '{%s}%s' % ('myuri:widget', path_elem)
    new_path = path + [path_elem]
    for child in e.getchildren():
        strip_namespaces(new_path, child)


def find_by_path(children, path):
    '''
    Try to find the next schema node down from the first element in
    the path passed in.
    '''
    for c in children:
        
        # if it's a choice or a case node, we need to skip over and
        # look at its children, but don't break out if we don't find
        # something; go on to look at other children, if any
        if c.keyword == 'choice' or c.keyword == 'case':
            choice_case = find_by_path(c.i_children, path)
            if choice_case:
                return choice_case

        # else we can do the simple comparison on this node
        elif c.arg == path[0]:
            if len(path) == 1:
                return c
            else:
                return find_by_path(c.i_children, path[1:])

    return None

    
def replace_namespaces(module_native, path, e):
    '''
    Replace XML namespaces
    '''
    
    path_elem = etree.QName(e.tag).localname
    new_path = path + [path_elem]
    # print(new_path)
    node = find_by_path(module_native.i_children, new_path)
    if node:
        ns = [s.arg for s in node.i_module.substmts if s.keyword=='namespace'][0]
        e.tag = '{%s}%s' % (ns, path_elem)
    else:
        e.tag = '{NOTFOUND}%s' % path_elem
    for child in e.getchildren():
        replace_namespaces(module_native, new_path, child)

        
if __name__ == '__main__':

    #
    # let's do some testing!
    #
    TEST_FILE = '/Users/einarnn/scratch/sample.xml'

    doc = etree.parse(open(TEST_FILE, 'rb'))
    native = doc.xpath('//*[local-name()="native"]')
    if not native:
        print('No node \'native\'!!')
        sys.exit(1)

    strip_namespaces([], native[0])
    # objectify.deannotate(doc, cleanup_namespaces=True)
    etree.cleanup_namespaces(doc)
    print(etree.tostring(doc, pretty_print=True).decode())
