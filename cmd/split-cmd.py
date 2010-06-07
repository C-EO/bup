#!/usr/bin/env python
import sys, time, struct
from bup import hashsplit, git, options, client
from bup.helpers import *
from subprocess import PIPE


optspec = """
bup split [-tcb] [-n name] [--bench] [filenames...]
--
r,remote=  remote repository path
b,blobs    output a series of blob ids
t,tree     output a tree id
c,commit   output a commit id
n,name=    name of backup set to update (if any)
N,noop     don't actually save the data anywhere
q,quiet    don't print progress messages
v,verbose  increase log output (can be used more than once)
copy       just copy input to output, hashsplitting along the way
bench      print benchmark timings to stderr
max-pack-size=  maximum bytes in a single pack
max-pack-objects=  maximum number of objects in a single pack
fanout=    maximum number of blobs in a single tree
bwlimit=   maximum bytes/sec to transmit to server
"""
o = options.Options('bup split', optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

git.check_repo_or_die()
if not (opt.blobs or opt.tree or opt.commit or opt.name or
        opt.noop or opt.copy):
    o.fatal("use one or more of -b, -t, -c, -n, -N, --copy")
if (opt.noop or opt.copy) and (opt.blobs or opt.tree or 
                               opt.commit or opt.name):
    o.fatal('-N is incompatible with -b, -t, -c, -n')

if opt.verbose >= 2:
    git.verbose = opt.verbose - 1
    opt.bench = 1
if opt.max_pack_size:
    hashsplit.max_pack_size = parse_num(opt.max_pack_size)
if opt.max_pack_objects:
    hashsplit.max_pack_objects = parse_num(opt.max_pack_objects)
if opt.fanout:
    hashsplit.fanout = parse_num(opt.fanout)
if opt.blobs:
    hashsplit.fanout = 0
if opt.bwlimit:
    client.bwlimit = parse_num(opt.bwlimit)

is_reverse = os.environ.get('BUP_SERVER_REVERSE')
if is_reverse and opt.remote:
    o.fatal("don't use -r in reverse mode; it's automatic")
start_time = time.time()

refname = opt.name and 'refs/heads/%s' % opt.name or None
if opt.noop or opt.copy:
    cli = pack_writer = oldref = None
elif opt.remote or is_reverse:
    cli = client.Client(opt.remote)
    oldref = refname and cli.read_ref(refname) or None
    pack_writer = cli.new_packwriter()
else:
    cli = None
    oldref = refname and git.read_ref(refname) or None
    pack_writer = git.PackWriter()

files = extra and (open(fn) for fn in extra) or [sys.stdin]
if pack_writer:
    shalist = hashsplit.split_to_shalist(pack_writer, files)
    tree = pack_writer.new_tree(shalist)
else:
    last = 0
    for (blob, bits) in hashsplit.hashsplit_iter(files):
        hashsplit.total_split += len(blob)
        if opt.copy:
            sys.stdout.write(str(blob))
        megs = hashsplit.total_split/1024/1024
        if not opt.quiet and last != megs:
            progress('%d Mbytes read\r' % megs)
            last = megs
    progress('%d Mbytes read, done.\n' % megs)

if opt.verbose:
    log('\n')
if opt.blobs:
    for (mode,name,bin) in shalist:
        print bin.encode('hex')
if opt.tree:
    print tree.encode('hex')
if opt.commit or opt.name:
    msg = 'bup split\n\nGenerated by command:\n%r' % sys.argv
    ref = opt.name and ('refs/heads/%s' % opt.name) or None
    commit = pack_writer.new_commit(oldref, tree, msg)
    if opt.commit:
        print commit.encode('hex')

if pack_writer:
    pack_writer.close()  # must close before we can update the ref

if opt.name:
    if cli:
        cli.update_ref(refname, commit, oldref)
    else:
        git.update_ref(refname, commit, oldref)

if cli:
    cli.close()

secs = time.time() - start_time
size = hashsplit.total_split
if opt.bench:
    log('\nbup: %.2fkbytes in %.2f secs = %.2f kbytes/sec\n'
        % (size/1024., secs, size/1024./secs))
