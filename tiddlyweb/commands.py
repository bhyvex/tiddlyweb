"""
A collection of routines for doing things like starting
a server, creating a user. Command line tools.
"""

import sys

from tiddlyweb.store import Store, NoBagError
from tiddlyweb.serializer import Serializer
from tiddlyweb.model.user import User

from tiddlyweb.manage import make_command, usage

from tiddlyweb import __version__ as VERSION


config = None


def init(config_in):
    """
    Set the config, via plugin init scheme.
    """
    global config
    config = config_in


@make_command()
def info(args):
    """Display info about TiddlyWeb."""
    print """This is TiddlyWeb version %s.
The current store is: %s.""" % (VERSION, config['server_store'][0])
    if config['system_plugins']:
        print 'System Plugins:'
        for plugin in config['system_plugins']:
            module = __import__(plugin)
            print '\t%s (%s)' % (plugin,
                    getattr(module, '__version__', 'unknown'))


@make_command()
def server(args):
    """Start the server using config settings. Provide <host name or IP number> <port> to override."""
    hostname = port = ''
    try:
        hostname, port = args[0:2]
    except(IndexError, ValueError), exc:
        if 0 < len(args) < 2:
            usage('you must include both a hostname or ip '
                'number and a port if using arguments: %s' % exc)
        else:
            pass

    if hostname and port:
        config['server_host'] = {
                'scheme': 'http',
                'host': hostname,
                'port': port,
                }

    from tiddlyweb.web import serve
    serve.start_cherrypy()


@make_command()
def userpass(args):
    """Change the password of an existing user. <username> <password>"""
    try:
        username, password = args[0:2]
    except (IndexError, ValueError), exc:
        usage('you must provide both a user and a password')

    try:
        store = _store()
        user = User(username)
        user = store.get(user)
        user.set_password(password)
        store.put(user)
    except Exception, exc:
        usage('unable to set password for user: %s' % exc)

    return True


@make_command()
def addrole(args):
    """Add a role to an existing user. <username> [role] [role] [role]"""
    try:
        username = args.pop(0)
        roles = args[0:]
    except (IndexError, ValueError), exc:
        usage('you must provide a user and at least one '
            'role: %s' % exc)

    try:
        store = _store()
        user = User(username)
        user = store.get(user)
        for role in roles:
            user.add_role(role)
        store.put(user)
    except Exception, exc:
        usage('unable to add role to user: %s' % exc)

    return True


@make_command()
def adduser(args):
    """Add or update a user to the database: <username> <password> [[role] [role] ...]"""
    try:
        username, password = args[0:2]
    except (IndexError, ValueError), exc:
        usage('you must include at least a username and password')

    try:
        roles = args[2:]
    except IndexError:
        roles = []

    # this will raise an except to be caught by the handler
    store = _store()
    user = User(username)
    user.set_password(password)
    for role in roles:
        user.add_role(role)
    store.put(user)

    return True


@make_command()
def recipe(args):
    """Create or update a recipe with the recipe text on stdin: <recipe>"""
    try:
        recipe_name = args[0]
    except IndexError, exc:
        usage('you must include a recipe name')

    from tiddlyweb.model.recipe import Recipe

    new_recipe = Recipe(recipe_name)

    content = sys.stdin.read()
    _put(new_recipe, unicode(content, 'UTF-8'), 'text')


@make_command()
def bag(args):
    """Create or update a bag with the json text on stdin: <bag>"""
    try:
        bag_name = args[0]
    except IndexError, exc:
        usage('you must include a bag name')

    from tiddlyweb.model.bag import Bag

    new_bag = Bag(bag_name)

    content = sys.stdin.read()
    if not len(content):
        content = '{"policy":{}}'
    _put(new_bag, unicode(content, 'UTF-8'), 'json')


@make_command()
def tiddler(args):
    """Import a single tiddler into an existing bag from stdin: <bag> <tiddler>"""
    try:
        bag_name, tiddler_name = args[0:3]
    except (IndexError, ValueError), exc:
        usage('you must include a tiddler and bag name')

    from tiddlyweb.model.tiddler import Tiddler

    new_tiddler = Tiddler(tiddler_name)
    new_tiddler.bag = bag_name

    content = sys.stdin.read()
    _put(new_tiddler, unicode(content, 'UTF-8'), 'text')


@make_command()
def lusers(args):
    """List all the users on the system"""
    store = _store()
    users = store.list_users()
    for user in users:
        user = store.get(user)
        print user.usersign, user.list_roles()


@make_command()
def lbags(args):
    """List all the bags on the system. [<bag> <bag> <bag>] to limit."""
    from tiddlyweb.model.bag import Bag
    store = _store()
    bags = [Bag(name) for name in args]
    if not bags:
        bags = store.list_bags()
    serializer = Serializer('json')
    for listed_bag in bags:
        listed_bag = store.get(listed_bag)
        serializer.object = listed_bag
        print 'Name: %s' % listed_bag.name
        print serializer.to_string()
        print


@make_command()
def lrecipes(args):
    """List all the recipes on the system. [<recipe> <recipe> <recipe>] to limit."""
    from tiddlyweb.model.recipe import Recipe
    store = _store()
    recipes = [Recipe(name) for name in args]
    if not recipes:
        recipes = store.list_recipes()
    for listed_recipe in recipes:
        listed_recipe = store.get(listed_recipe)
        print listed_recipe.name, listed_recipe.policy.owner
        for recipe_bag, recipe_filter in listed_recipe.get_recipe():
            print '\t', recipe_bag, recipe_filter


@make_command()
def ltiddlers(args):
    """List all the tiddlers on the system. [<bag> <bag> <bag>] to limit."""
    from tiddlyweb.model.bag import Bag
    store = _store()
    bags = [Bag(name) for name in args]
    if not bags:
        bags = store.list_bags()
    try:
        for listed_bag in bags:
            listed_bag = store.get(listed_bag)
            print listed_bag.name, listed_bag.policy.owner
            tiddlers = listed_bag.list_tiddlers()
            for listed_tiddler in tiddlers:
                listed_tiddler = store.get(listed_tiddler)
                print '  ', listed_tiddler.title, listed_tiddler.modifier
    except NoBagError, exc:
        usage('unable to inspect bag %s: %s' % (listed_bag.name, exc))


def _put(entity, content, serialization):
    """
    Put entity to store, by serializing content
    using the named serialization.
    """
    serializer = Serializer(serialization)
    serializer.object = entity
    serializer.from_string(content)
    _store().put(entity)


def _store():
    """Get our Store from config."""
    return Store(config['server_store'][0],
            environ={'tiddlyweb.config': config})