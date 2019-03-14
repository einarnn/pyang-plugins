"""Generate top-level subtree filters for modules.
"""
import optparse

from pyang import plugin
from pyang import statements

filter_template_full = '''<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
  <get>
    <filter>
      <{NODE} xmlns="{NS}"/>
    </filter>
  </get>
</rpc>'''

filter_template_minimal = '''<{NODE} xmlns="{NS}"/>'''

def pyang_plugin_init():
    plugin.register_plugin(FilterPlugin())


class FilterPlugin(plugin.PyangPlugin):
    def add_output_format(self, fmts):
        self.multiple_modules = True
        fmts['filter'] = self

    def add_opts(self, optparser):
        optlist = [
            optparse.make_option("--filter-minimal",
                                 dest="filter_minimal",
                                 action="store_true",
                                 help="Display a minimal filter"),
            ]
        optparser.add_options(optlist)

    def setup_fmt(self, ctx):
        ctx.implicit_errors = False

    def emit(self, ctx, modules, fd):
        emit_tree(modules, fd, ctx)


def emit_tree(modules, fd, ctx):
    for module in modules:
        ns = [s.arg for s in module.substmts if s.keyword=='namespace'][0]
        chs = [ch for ch in module.i_children
               if ch.keyword in statements.data_definition_keywords]
        print_children(chs, ns, fd, ctx)


def print_children(i_children, ns, fd, ctx):
    for ch in i_children:
        if ctx.opts.filter_minimal:
            fd.write(filter_template_minimal.format(NODE=ch.arg, NS=ns))
        else:
            fd.write(filter_template_full.format(NODE=ch.arg, NS=ns))
        fd.write('\n')


