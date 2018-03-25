"""Load RediSearch for YANG module searching. Derived from JSTree plugin.
"""
import logging
import optparse
import sys

from pyang import plugin
from pyang import statements
from collections import defaultdict

logger = logging.getLogger(__name__)

index_module_keywords = [
    'module',
    'revision',
    'description',
    'organization',
    'contact',
    'import',
    'include',
]
node_module_keywords = [
    ('module', 2.0),
    ('path', 5.0),
    ('name', 2.0),
    ('keyword', 1.0),
    ('type', 1.0),
    ('description', 1.0),
]

MODULE_INDEX_NAME = 'yang_module_index'
NODE_INDEX_NAME = 'yang_node_index'


def pyang_plugin_init():
    plugin.register_plugin(RediSearchPlugin())


class RediSearchPlugin(plugin.PyangPlugin):

    rs = None
    module_index = None
    node_index = None
    
    def add_output_format(self, fmts):
        self.multiple_modules = True
        fmts['redisearch'] = self

    def add_opts(self, optparser):
        optlist = [
            optparse.make_option("--redis-recreate",
                                 dest="redis_recreate",
                                 action="store_true",
                                 help="Recreate the document index"),
            optparse.make_option("--redis-skip-modules",
                                 dest="redis_skip_modules",
                                 action="store_true",
                                 default=False,
                                 help="Skip module indexing"),
            optparse.make_option("--redis-skip-nodes",
                                 dest="redis_skip_nodes",
                                 action="store_true",
                                 default=False,
                                 help="Skip full node indexing"),
            optparse.make_option("--redis-verbose",
                                 dest="redis_verbose",
                                 action="store_true",
                                 help="Log a bunch of stuff about redis indexing"),
            ]
        optparser.add_options(optlist)

    def setup_fmt(self, ctx):
        ctx.implicit_errors = False
        if ctx.opts.redis_verbose:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)


    def emit(self, ctx, modules, fd):
        #
        # Open up the index or indices required, optionally forcing
        # recreation.
        #
        self.open_index(recreate=ctx.opts.redis_recreate)

        #
        # Index modules
        #
        if ctx.opts.redis_skip_modules is False:
            self.index_modules(modules, fd, ctx)

        #
        # Index all nodes in all modules
        #
        if ctx.opts.redis_skip_nodes is False:
            self.index_tree(modules, fd, ctx)


    def open_index(self, recreate=False):

        logger.debug('opening indices, index recreate=%s' % recreate)
        
        #
        # Not sure yet why I have to do this; standard module imports
        # seemed to not work...
        #
        import importlib
        self.rs = importlib.import_module('redisearch')
        self.redis_except = importlib.import_module('redis.exceptions')
        self.module_index = self.rs.Client(MODULE_INDEX_NAME)
        self.node_index = self.rs.Client(NODE_INDEX_NAME)

        #
        # Check if the index info is there
        #
        try:
            info = self.module_index.info()
        except self.redis_except.ResponseError as e:
            logger.debug('document index not present, will create')
            recreate = True

        #
        # If either not there or forced recreate, create the indices.
        #
        if recreate:
            logger.debug('creating indices')
            try:
                self.module_index.drop_index()
                self.node_index.drop_index()
            except:
                pass
            self.module_index.create_index([
                self.rs.TextField(kw) for kw in index_module_keywords
            ])
            self.node_index.create_index([
                self.rs.TextField(kw, weight=w) for kw, w in node_module_keywords
            ])
            
        
    def index_modules(self, modules, fd, ctx):
        logger.debug('start indexing modules')
        for module in modules:
            versioned_modulename = '%s@%s' % (module.i_modulename,
                                              module.i_latest_revision)
            logger.debug(
                'creating module index for %s' % versioned_modulename)
            kw = defaultdict(list)
            kw['module'].append(module.i_modulename)
            for modsub in module.substmts:
                if modsub.keyword in index_module_keywords:
                    kw[modsub.keyword].append(modsub.arg)
            for k, v in kw.iteritems():
                kw[k] = ' '.join(v)
            self.module_index.add_document(versioned_modulename, replace=True, **kw)
        logger.debug('end indexing modules')


    def index_tree(self, modules, fd, ctx):
        logger.debug('start indexing tree')
        for module in modules:
            chs = [ch for ch in module.i_children
                   if ch.keyword in statements.data_definition_keywords]
            self.index_children(chs, module, fd, ' ', ctx, 2)
        logger.debug('end indexing tree')


    def index_children(self, i_children, module, fd, prefix, ctx, level=0):
        for ch in i_children:
            self.index_node(ch, module, fd, prefix, ctx, level)


    def index_node(self, s, module, fd, prefix, ctx, level=0):

        name = ''
        nodetype = ''
        if s.i_module.i_modulename == module.i_modulename:
            name = s.arg
        else:
            name = s.i_module.i_prefix + ':' + s.arg

        if s.keyword == 'choice':
            m = s.search_one('mandatory')
            if m is None or m.arg == 'false':
                name = '(' + s.arg + ')'
            else:
                name = '(' + s.arg + ')'
        elif s.keyword == 'case':
            name = ':(' + s.arg + ')'
        else:
            nodetype = get_typename(s)

        if s.keyword == 'list' and s.search_one('key') is not None:
            name += '[' + s.search_one('key').arg + ']'

        versioned_module_name = '%s@%s' % (s.i_module.arg, s.i_module.i_latest_revision)
        
        pathstr = statements.mk_path_str(s, True)

        keyword = s.keyword

        description = get_description(s)
        if description:
            description = description.replace('\n', ' ')

        #
        # Log attributes we will be indexing
        #
        logger.debug('path=%s' % pathstr)
        logger.debug('name=%s' % name)
        logger.debug('keyword=%s' % s.keyword)
        logger.debug('type=%s' % nodetype)
        logger.debug('module=%s' % versioned_module_name)
        logger.debug('description="%s"' % description)

        #
        # Populate the keywords for indexing and then index the
        # document. We will use the full path as the document id and
        # also include the full path as an indexable key.
        #
        kw = {
            'path': pathstr,
            'name': name,
            'keyword': s.keyword,
            'module': versioned_module_name,
        }
        if len(nodetype) > 0:
            kw['type'] = nodetype
        if description:
            kw['description'] = description
        logger.debug('indexing %s' % pathstr)
        self.node_index.add_document(pathstr, replace=True, **kw)
        
        #
        # See if we need to recurse
        #
        if hasattr(s, 'i_children'):
            level += 1
            if s.keyword in ['choice', 'case']:
                self.index_children(s.i_children, module, fd, prefix, ctx, level)
            else:
                self.index_children(s.i_children, module, fd, prefix, ctx, level)


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


def get_description(s):
    for sub in s.substmts:
        if sub.keyword == 'description':
            return sub.arg
    return None


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
