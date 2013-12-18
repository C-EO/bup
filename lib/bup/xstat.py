"""Enhanced stat operations for bup."""
import os
import stat as pystat
from bup import _helpers

try:
    _bup_utimensat = _helpers.bup_utimensat
except AttributeError, e:
    _bup_utimensat = False

try:
    _bup_utimes = _helpers.bup_utimes
except AttributeError, e:
    _bup_utimes = False

try:
    _bup_lutimes = _helpers.bup_lutimes
except AttributeError, e:
    _bup_lutimes = False


def timespec_to_nsecs((ts_s, ts_ns)):
    # c.f. _helpers.c: timespec_vals_to_py_ns()
    if ts_ns < 0 or ts_ns > 999999999:
        raise Exception('invalid timespec nsec value')
    return ts_s * 10**9 + ts_ns


def nsecs_to_timespec(ns):
    """Return (s, ns) where ns is always non-negative
    and t = s + ns / 10e8""" # metadata record rep (and libc rep)
    ns = int(ns)
    return (ns / 10**9, ns % 10**9)


def nsecs_to_timeval(ns):
    """Return (s, us) where ns is always non-negative
    and t = s + us / 10e5"""
    ns = int(ns)
    return (ns / 10**9, (ns % 10**9) / 1000)


def fstime_floor_secs(ns):
    """Return largest integer not greater than ns / 10e8."""
    return int(ns) / 10**9;


def fstime_to_timespec(ns):
    return nsecs_to_timespec(ns)


def fstime_to_sec_str(fstime):
    (s, ns) = fstime_to_timespec(fstime)
    if(s < 0):
        s += 1
    if ns == 0:
        return '%d' % s
    else:
        return '%d.%09d' % (s, ns)


if _bup_utimensat:
    def utime(path, times):
        """Times must be provided as (atime_ns, mtime_ns)."""
        atime = nsecs_to_timespec(times[0])
        mtime = nsecs_to_timespec(times[1])
        _bup_utimensat(_helpers.AT_FDCWD, path, (atime, mtime), 0)
    def lutime(path, times):
        """Times must be provided as (atime_ns, mtime_ns)."""
        atime = nsecs_to_timespec(times[0])
        mtime = nsecs_to_timespec(times[1])
        _bup_utimensat(_helpers.AT_FDCWD, path, (atime, mtime),
                       _helpers.AT_SYMLINK_NOFOLLOW)
else: # Must have these if utimensat isn't available.
    def utime(path, times):
        """Times must be provided as (atime_ns, mtime_ns)."""
        atime = nsecs_to_timeval(times[0])
        mtime = nsecs_to_timeval(times[1])
        _bup_utimes(path, (atime, mtime))
    def lutime(path, times):
        """Times must be provided as (atime_ns, mtime_ns)."""
        atime = nsecs_to_timeval(times[0])
        mtime = nsecs_to_timeval(times[1])
        _bup_lutimes(path, (atime, mtime))


class stat_result:
    @staticmethod
    def from_xstat_rep(st):
        result = stat_result()
        (result.st_mode,
         result.st_ino,
         result.st_dev,
         result.st_nlink,
         result.st_uid,
         result.st_gid,
         result.st_rdev,
         result.st_size,
         result.st_atime,
         result.st_mtime,
         result.st_ctime) = st
        result.st_atime = timespec_to_nsecs(result.st_atime)
        result.st_mtime = timespec_to_nsecs(result.st_mtime)
        result.st_ctime = timespec_to_nsecs(result.st_ctime)
        return result


def stat(path):
    return stat_result.from_xstat_rep(_helpers.stat(path))


def fstat(path):
    return stat_result.from_xstat_rep(_helpers.fstat(path))


def lstat(path):
    return stat_result.from_xstat_rep(_helpers.lstat(path))


def mode_str(mode):
    result = ''
    if pystat.S_ISREG(mode):
        result += '-'
    elif pystat.S_ISDIR(mode):
        result += 'd'
    elif pystat.S_ISCHR(mode):
        result += 'c'
    elif pystat.S_ISBLK(mode):
        result += 'b'
    elif pystat.S_ISFIFO(mode):
        result += 'p'
    elif pystat.S_ISLNK(mode):
        result += 'l'
    elif pystat.S_ISSOCK(mode):
        result += 's'
    else:
        result += '?'

    result += 'r' if (mode & pystat.S_IRUSR) else '-'
    result += 'w' if (mode & pystat.S_IWUSR) else '-'
    result += 'x' if (mode & pystat.S_IXUSR) else '-'
    result += 'r' if (mode & pystat.S_IRGRP) else '-'
    result += 'w' if (mode & pystat.S_IWGRP) else '-'
    result += 'x' if (mode & pystat.S_IXGRP) else '-'
    result += 'r' if (mode & pystat.S_IROTH) else '-'
    result += 'w' if (mode & pystat.S_IWOTH) else '-'
    result += 'x' if (mode & pystat.S_IXOTH) else '-'
    return result
