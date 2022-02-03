import pickle
from operator import itemgetter
import json
import os # for Silence and environ
from os import path
import collections
import string
from datetime import datetime, timedelta
import time
from simplerandom import random
from hashids import Hashids
from hashlib import md5
import base64
import uuid
import bisect
from anonymizeip import anonymize_ip

hashids = Hashids(salt='hello i am a salt',
                  alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
                  min_length=6)

def my_hash(s):
    # [:-2] removes the superfluous '==' at end
    return base64.urlsafe_b64encode(md5(s).digest())[:-2].decode('utf-8')

def unix_timestamp_to_str(t=None):
    if t is None:
        t = time.time()
    return "{:%Y-%m-%d %H:%M:%S}".format(datetime.fromtimestamp(t))

def process_IP_address(IPaddress):
    anon_IP = anonymize_ip(IPaddress,
                           ipv4_mask="255.255.0.0",
                           ipv6_mask="ffff:ffff:ffff:::"
                           )
    hash_IP = uuid.uuid5(uuid.NAMESPACE_OID, IPaddress).hex[:16]
    return anon_IP, hash_IP


# ------------------------------------------

COLOR_RED = (0xff, 0x15, 0x45)
COLOR_DARKRED = (0x90, 0x50, 0x30)
COLOR_DEEPGREEN = (0x05, 0x30, 0x05)
COLOR_DEEPBLUE = (0x05, 0x05, 0x30)
COLOR_WHITE = (0xee, 0xff, 0xff)
COLOR_YELLOW = (0xee, 0xee, 0x30)
COLOR_ORANGE = (0xff, 0x9f, 0x10)
COLOR_GREEN = (0x22, 0xff, 0x05)
COLOR_BLACK = (0x05, 0x05, 0x15)
COLOR_GREY = (0xb5, 0xd5, 0xe5)  # tinge of blue
COLOR_DARKGREY = (0x75, 0x95, 0x95)


ASCII_chars = ''.join(chr(x) for x in range(128))

"""
# ISSUE: US keyboard mapping only!
NUMERIC_ASCII_SHIFT_MAP = {
    48: 41, # 0 -> )
    49: 33, # 1 -> !
    50: 64, # 2 -> @
    51: 35, # 3 -> #
    52: 36, # 4 -> $
    53: 37, # 5 -> %
    54: 94, # 6 -> ^
    55: 38, # 7 -> &
    56: 42, # 8 -> *
    57: 40, # 9 -> (
    47: 63, # / -> ?
    61: 43, # = -> +
    45: 95, # - -> _
    59: 58, # ; -> :
    44: 60, # , -> <
    46: 62, # . -> >
    39: 34, # ' -> "
    91: 123, # [ -> {
    93: 125, # ] -> }
    92: 124, # \ -> |
    96: 126, # ` -> ~
    }
NUMERIC_CHARS_ASCII = set(NUMERIC_ASCII_SHIFT_MAP.keys())

LEGAL_ASCII_CODES = set([pygame.K_BACKSPACE, pygame.K_ESCAPE,
                     pygame.K_SPACE, pygame.K_RETURN] + \
    range(48,58) + range(65, 91) + range(97, 123) + [44,45,46,47,59,61])
# 44 = ,
# 45 = -
# 46 = .
# 47 = /
# 59 = ;
# 61 = =

LEGAL_ASCII_CODES_EXTENDED = set([pygame.K_BACKSPACE, pygame.K_ESCAPE,
                     pygame.K_SPACE, pygame.K_RETURN] + range(33,126))
# no tilde

IN_MENU_EVTS = (pygame.USEREVENT,)

INV_MAX_ITEMS = 17
"""

# ------------------------------------------

# two instances to control when things get re-seeded or not
rand_level = random.KISS() # will be re-seeded
#rand_items = random.KISS() # UNUSED
rand_always = random.KISS() # will not be seeded


class Silence(object):
    """Context manager which uses low-level file descriptors to suppress
    output to stdout/stderr, optionally redirecting to the named file(s).

    https://code.activestate.com/recipes/577564-context-manager-for-low-level-redirection-of-stdou/

    >>> import sys, numpy.f2py
    >>> # build a test fortran extension module with F2PY
    ...
    >>> with open('hellofortran.f', 'w') as f:
    ...     f.write('''\
    ...       integer function foo (n)
    ...           integer n
    ...           print *, "Hello from Fortran!"
    ...           print *, "n = ", n
    ...           foo = n
    ...       end
    ...       ''')
    ...
    >>> sys.argv = ['f2py', '-c', '-m', 'hellofortran', 'hellofortran.f']
    >>> with Silence():
    ...     # assuming this succeeds, since output is suppressed
    ...     numpy.f2py.main()
    ...
    >>> import hellofortran
    >>> foo = hellofortran.foo(1)
     Hello from Fortran!
     n =  1
    >>> print "Before silence"
    Before silence
    >>> with Silence(stdout='output.txt', mode='w'):
    ...     print "Hello from Python!"
    ...     bar = hellofortran.foo(2)
    ...     with Silence():
    ...         print "This will fall on deaf ears"
    ...         baz = hellofortran.foo(3)
    ...     print "Goodbye from Python!"
    ...
    ...
    >>> print "After silence"
    After silence
    >>> # ... do some other stuff ...
    ...
    >>> with Silence(stderr='output.txt', mode='a'):
    ...     # appending to existing file
    ...     print >> sys.stderr, "Hello from stderr"
    ...     print "Stdout redirected to os.devnull"
    ...
    ...
    >>> # check the redirected output
    ...
    >>> with open('output.txt', 'r') as f:
    ...     print "=== contents of 'output.txt' ==="
    ...     print f.read()
    ...     print "================================"
    ...
    === contents of 'output.txt' ===
    Hello from Python!
     Hello from Fortran!
     n =  2
    Goodbye from Python!
    Hello from stderr

    ================================
    >>> foo, bar, baz
    (1, 2, 3)
    >>>

    """
    def __init__(self, stdout=os.devnull, stderr=os.devnull, mode='w'):
        self.outfiles = stdout, stderr
        self.combine = (stdout == stderr)
        self.mode = mode

    def __enter__(self):
        import sys
        self.sys = sys
        # save previous stdout/stderr
        self.saved_streams = saved_streams = sys.__stdout__, sys.__stderr__
        self.fds = fds = [s.fileno() for s in saved_streams]
        self.saved_fds = map(os.dup, fds)
        # flush any pending output
        for s in saved_streams: s.flush()

        # open surrogate files
        if self.combine:
            null_streams = [open(self.outfiles[0], self.mode, 0)] * 2
            if self.outfiles[0] != os.devnull:
                # disable buffering so output is merged immediately
                sys.stdout, sys.stderr = map(os.fdopen, fds, ['w']*2, [0]*2)
        else: null_streams = [open(f, self.mode, 0) for f in self.outfiles]
        self.null_fds = null_fds = [s.fileno() for s in null_streams]
        self.null_streams = null_streams

        # overwrite file objects and low-level file descriptors
        map(os.dup2, null_fds, fds)

    def __exit__(self, *args):
        sys = self.sys
        # flush any pending output
        for s in self.saved_streams: s.flush()
        # restore original streams and file descriptors
        map(os.dup2, self.saved_fds, self.fds)
        sys.stdout, sys.stderr = self.saved_streams
        # clean up
        for s in self.null_streams: s.close()
        for fd in self.saved_fds: os.close(fd)
        return False


class TimeOrderedQ(object):
    """
    Used for future game-level events and assumes the queue contents are TimerEvent objects
    with a `time` attribute.
    """
    def __init__(self, limit=None):
        self.q = []
        self.times = []
        self.limit = limit

    def test(self, game):
        while True:
            if self.times == []:
                break
            else:
                if game.t > self.times[0]:
                    ev = self.get()
                    ev.do(game)
                    if not ev.one_shot:
                        # ev reset itself with next time
                        self.insert(ev)
                    # keep checking
                else:
                    break

    def get(self):
        try:
            val = self.q.pop(0)
        except IndexError:
            return None
        else:
            # discard first time
            self.times.pop(0)
            return val

    def read(self):
        """Non-destructive read from queue.
        """
        return self.q, self.times

    def insert(self, ev):
        ix = bisect.bisect(self.times, ev.time)
        self.q.insert(ix, ev)
        self.times.insert(ix, ev.time)
        if self.limit:
            if len(self.q) > self.limit:
                self.q.pop(-1)
                self.times.pop(-1)


class Struct(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, x):
        return x in self.__dict__

# not needed in python 3
class OrderedSet(collections.MutableSet):
    """
    From http://code.activestate.com/recipes/576694/
    """

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def update(self, keys):
        for key in keys:
            self.add(key)

    def remove(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    discard = remove  # for compatibility with abstract methods

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


class CycleTimeTester(object):
    def __init__(self, repeat):
        """
        repeat time in seconds
        """
        self.last_time = -1
        self.repeat = repeat

    def __call__(self, time, repeat=None):
        if repeat is None:
            repeat = self.repeat
        if time > self.last_time + repeat*1000:
            self.last_time = time
            return True
        else:
            return False

    def reset(self, time):
        self.last_time = time


class CounterUtil(object):
    def __init__(self):
        # will start at 1 when used
        self.n = 0

    def get_count(self):
        self.n += 1
        return self.n


class Unique_id(object):
    def __init__(self, types=None):
        if types is None:
            types = ['']
        self.known_types = []
        self.counters = {}
        self.add_types(types)

    def add_types(self, types):
        new_types = [t for t in types if
                           t not in self.known_types]
        self.known_types.extend(new_types)
        for kt in new_types:
            self.counters[kt] = CounterUtil()

    def get(self, objtype=''):
        return self.counters[objtype].get_count()

class ItemIDManager(object):
    # all items created in game are permanent!
    def __init__(self):
        # reset used when reloading
        self.reset()

    def reset(self):
        self.item_lookup = {}
        self.eqid_item_lookup = {}
        self.uID = Unique_id()

    def dump_log(self, prefix=''):
        from logger import log
        for idval, item in self.item_lookup.items():
            log.info("{} - Item {} = {} {}".format(prefix, type(item), idval, item.equipment_id))

    def declare(self, item):
        from logger import log #, do_log
        try:
            idval = item.item_id
        except AttributeError:
            # new item, not declared yet
            #_type = item.__class__.__name__
            idval = self.uID.get()
            eq_idval = hashids.encode(idval).upper()
            self.item_lookup[idval] = item
            assert eq_idval not in self.eqid_item_lookup, "hash clash on eq_idval"
            assert idval not in self.item_lookup, "hash clash on idval"
            self.eqid_item_lookup[eq_idval] = item
            return idval, eq_idval
        else:
            if idval in self.item_lookup:
                # already declared it, duh ...
                return idval, hashids.encode(idval).upper()
            else:
                # Item ID was not issued in this instance of the server
                # but was loaded from a previous
                #log.info(type(item))
                #log.info(idval)
                if idval is None:
                    idval = self.uID.get()
                try:
                    eq_idval = item.equipment_id
                    #log.info("Recovered {} ({})".format(eq_idval, type(item)))
                except AttributeError:
                    eq_idval = hashids.encode(idval).upper()
                    #log.info("Made {} ({})".format(eq_idval, type(item)))
                #assert eq_idval not in self.eqid_item_lookup, "hash clash on eq_idval"
                #if eq_idval in self.eqid_item_lookup:
                    #old_item = self.eqid_item_lookup[eq_idval]
                    #print(type(old_item))
                    #print(type(item))
                assert idval not in self.item_lookup, "hash clash on idval"
                self.item_lookup[idval] = item
                self.eqid_item_lookup[eq_idval] = item
                return idval, eq_idval

    def __getitem__(self, idval):
        try:
            return self.item_lookup[idval]
        except KeyError:
            raise KeyError(f"Not an item: {idval}")

##    def lookup_equipment_id(self, eq_idval):
##        try:
##            return self.eqid_item_lookup[eq_idval]
##        except KeyError:
##            raise KeyError(f"Not an item: {idval}")

    def format(self, id_or_item):
        try:
            # convenience functionality
            idval = id_or_item.item_id
        except AttributeError:
            # integer!
            idval = id_or_item
        # ISSUE: Change from 4 to 6 digits when game is large
        return "{0:04d}".format(idval)



def argmax_key(pairs):
    "given an iterable of pairs return the key corresponding to the greatest value"
    return max(pairs, key=itemgetter(1))[0]

def argmax_index(values):
    "given an iterable of values return the index of the greatest value"
    return argmax_key(enumerate(values))

def argmin_key(pairs):
    "given an iterable of pairs return the key corresponding to the smallest value"
    return min(pairs, key=itemgetter(1))[0]

def argmin_index(values):
    "given an iterable of values return the index of the smallest value"
    return argmin_key(enumerate(values))

def argsort(values):
    return sorted(range(len(values)), key=values.__getitem__)


class simpleFIFO(object):
    def __init__(self):
        self.q = []

    def put(self, v):
        self.q.append(v)

    def get(self):
        try:
            return self.q.pop(0)
        except IndexError:
            return None

def dict_list_add(d, k, v):
    """
    Convenience function to create empty list in dictionary if not
    already present under that key
    """
    if k in d:
        d[k].append(v)
    else:
        d[k] = [v]

def dict_list_add_unique(d, k, v):
    """
    Convenience function to create empty list in dictionary if not
    already present under that key. Only add to the list if the list
    does not already contain the value.
    """
    if k in d and v not in d[k]:
        d[k].append(v)
    else:
        d[k] = [v]

def dict_list_remove(d, k, v):
    if k in d:
        try:
            d[k].remove(v)
        except ValueError:
            # v not in list
            pass
        if d[k] == []:
            del(d[k])


class BuildWrappedLines(object):
    """Simple rule: add to line one "item" at a time and wrap
    when next item + line exceeds line length
    """
    def __init__(self, line_length=70):
        self.lines = ['']
        self.line_length = line_length

    def append(self, item):
        if len(self.lines[-1]) + len(item) > self.line_length:
            self.lines.append(item)
        else:
            self.lines[-1] += item


class VirtualLog(object):
    """
    Abstraction to provide a rolling log of string entries with
    a finite number of entries.
    """
    def __init__(self, size=400, input=None):
        self.log = {}
        self.cursor = 0
        self.size = size
        if input is not None:
            for line in input:
                self.append(line)

    def append(self, entry_str):
        self.log[self.cursor] = entry_str
        self.cursor += 1
        if self.cursor == self.size:
            self.cursor = 0

    def read_lines(self):
        out = []
        for i in range(self.size):
            try:
                out.append(self.log[(self.cursor-1-i)%self.size])
            except KeyError:
                break
        return out[::-1]


class Timer(object):
    def __init__(self, delay, with_over=False):
        # delay in seconds
        # with_over checks for excess and continues to trigger
        self.delay = delay
        self.state = False
        self.t_next = -1
        self.with_over = with_over
        self.over_count = 0

    def reset(self, remain=0):
        self.state = not self.state
        if self.with_over and remain < 0:
            while remain < 0:
                self.over_count += 1
                remain += self.delay
            self.t_next = time.time() + remain
        else:
            self.t_next = self.delay + time.time()

    def __call__(self):
        # poll
        remain = self.t_next - time.time()
        if remain <= 0:
            self.reset(remain)
            return True
        else:
            self.over_count = 0
            return False

class Timer_OneShot(object):
    def __init__(self, delay):
        # delay in seconds
        self.delay = delay
        self.state = False # on / off
        self.t_next = -1
        # override this with a function
        self.activate_fn = lambda : None

    def reset(self):
        # manual reset
        self.state = True
        self.t_next = self.delay + time.time()

    def __call__(self):
        # poll
        if self.state:
            remain = self.t_next - time.time()
            if remain <= 0:
                self.state = False
                self.activate_fn()
                return 0
            else:
                return remain
        else:
            raise ValueError("Timer not running")


# These will be overwritten if game level loaded in Game.new
global unique_item_ids, item_id_man
try:
    fl = open("saveIDs.sav", "rb")
    unique_item_ids, item_id_man = pickle.load(fl)
except:
    unique_item_ids = Unique_id()
    item_id_man = ItemIDManager()
else:
    fl.close()

# def load_saved_level():
#     level = None
#     try:
#         fl = open("savelevel.sav", "rb")
#     except:
#         rebuild = True
#     else:
#         try:
#             level = pickle.load(fl)
#         except:
#             rebuild = True
#             import game_items
#             game_items.register_ID_types()
#         fl.close()
#     if level is not None:
#         print("Reloaded level")
#     return level


def add_to_item_tree(item_host_list, tree):
    """Tree must have one exact root. Updates *in place*
    """
    if len(item_host_list) == 2:
        # base case
        host, item = item_host_list
        if host in tree:
            if item not in tree[host]:
                tree[host][item] = {}
            # else already there so nothing to do
        else:
            tree[host] = {item: {}}
    else:
        # len > 2
        top_host = item_host_list[0]
        if top_host not in tree:
            tree[top_host] = {}
        add_to_item_tree(item_host_list[1:], tree[top_host])

# BORKED
#def _sort_by_short_txt(ditem):
#    k, v = ditem
#    return (desc, k, v)

def intersect(a, b):
    """Find intersection of two lists, sequences, etc.
    Returns a list that includes repetitions if they occur in the inputs."""
    return [e for e in a if e in set(b)]

def remain(a, b):
    """Find remainder of two lists, sequences, etc., after intersection.
    Returns a list that includes repetitions if they occur in the inputs."""
    return list(set(a)-set(b))


def item_tree_visual_struct(tree, i=0, engrams_dict=None, filter_items=None,
                            sortby=None):
    """
    tree expected to be of form:
    {SolidItem_a: {SolidItem_b: {}, SolidItem_c: {SolidItem_d: {}}}}
    where there is only one root.

    For efficiency, filter_items should always be passed so that it's never
    None.
    """
    struct_list = []
    for k, v in tree.items():
        if i == 0 and not hasattr(k, 'attributes'):
            # keep same i, as we don't include root map LocMan
            struct_list = item_tree_visual_struct(v, i, engrams_dict,
                                           filter_items=filter_items)
            # only sort the outermost level
            return sorted(struct_list, key=itemgetter('sortby'))
        else:
            try:
                engram = engrams_dict[k]
            except KeyError:
                # ISSUE: Maybe a hack, but if player is interior to a container
                # that is closed, k may not be in the engrams dict
                pass
            else:
                new_struct = {}
                new_struct['viewport'] = False  # default
                new_struct['dirnstr'] = engram.dirnstr
                new_struct['item_id'] = k.item_id
                if k.item_id in filter_items:
                    new_struct['kind'] = '  +  ' # extra space to compensate for non-mono font
                else:
                    new_struct['kind'] = engram.kind
                desc = k.attributes.visuals.short_txt
                if engram.kind == 'see':
                    new_struct['description'] = "  "*i + desc
                else:
                    # so as to not include item ID in compass viewer
                    new_struct['description'] = "  "*i + desc + \
                        ' #'+str(k.item_id)
                if i == 0:
                    # use a darker color for less important root items
                    new_struct['color'] = COLOR_DARKGREY
                    new_struct['sortby'] = desc
                    sortby = desc
                else:
                    if i == 1 and engram.dirnstr == '=':
                        new_struct['viewport'] = True
                    new_struct['color'] = COLOR_WHITE
                    new_struct['sortby'] = sortby
                struct_list.append(new_struct)
            if k.item_id not in filter_items:
                # don't extend tree for filtered items (but include that
                # item, itself)
                struct_list.extend(item_tree_visual_struct(v, i+1, engrams_dict,
                                         filter_items=filter_items, sortby=sortby))
    return struct_list


def LRjustify_text(ltext, rtext, width):
    l = len(ltext)
    r = len(rtext)
    if l+r < width:  # strictly less, to allow for space
        return ltext + ' '*(width-l-r)+rtext
    else:
        # must truncate
        maxlen = len(ltext) + 2
        return ltext + ' ' + rtext[:width-maxlen]


_norm=str.maketrans(dict(zip('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', \
                       '5678901234nopqrstuvwxyzabcdefghijklmNOPQRSTUVWXYZABCDEFGHIJKLM')))

def rot13ish(message):
    return message.translate(_norm)
