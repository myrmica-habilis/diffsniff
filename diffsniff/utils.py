from collections import namedtuple, UserDict
from datetime import datetime
import filecmp
import os
from pathlib import Path
import shutil

ItemInfo = namedtuple(
    'ItemInfo',
    'equal unique mtimes left_to_right sizes other_name'
)


class CaseInsensitiveMembershipDict(UserDict):
    """Subclass of dictionary that performs a case-insensitive key
       membership test.

       Example:
       >>> d = CaseInsensitiveMembershipDict({'File.txt': None})
       >>> 'file.txt' in d
       True
    """
    def __contains__(self, item):
        return item.lower() in (key.lower() for key in self)


def diff_items(this_path, other_path, ignore_dirs=(), ignore_files=()):
    """Run two passes of `compare_one_way` and return the result."""

    result = CaseInsensitiveMembershipDict()
    compare_one_way(this_path, other_path, ignore_dirs, ignore_files, result)
    compare_one_way(other_path, this_path, ignore_dirs, ignore_files, result,
                    reverse=True)

    return result


def compare_one_way(this_path, other_path, ignore_dirs, ignore_files, result,
                    reverse=False):
    """Walk all files in `this_path` recursively and check for
       existence of the file names in `other_path`. If a file is found
       in both paths, check if the files are equal. Add results to the
       `result` mapping, modifying it in-place.
    """
    dirs_to_prune = shutil.ignore_patterns(*ignore_dirs)
    files_to_prune = shutil.ignore_patterns(*ignore_files)

    # walk `this_path` and compare files with `other_path`
    for this_abspath, subdirs, files in os.walk(this_path):

        # prune list of subdirs and list of files
        for subdir in dirs_to_prune(this_abspath, subdirs):
            subdirs.remove(subdir)
        for file in files_to_prune(this_abspath, files):
            files.remove(file)

        # relative path of the currently walked dir to the root of walk
        rel_path = os.path.relpath(this_abspath, this_path)

        for filename in files:
            # file relative path (this is the string used as a key in `result`)
            item_name = Path(filename if rel_path == '.'
                             else os.path.join(rel_path,
                                               filename)).as_posix()

            if item_name in result:
                # skip items processed in the first pass
                continue

            # absolute paths of files
            file_this = os.path.join(this_abspath, filename)
            file_other = os.path.join(other_path, item_name)

            if not os.path.exists(file_other):
                # try to find a non-matching-case version of the same filename
                file_other = match_case_insensitive(file_other)

            if file_other is None or not os.path.isfile(file_other):
                # unique file (only in this branch can `reverse` be True)
                result[item_name] = ItemInfo(
                    equal=False, unique=True, mtimes=None,
                    left_to_right=not reverse, sizes=None, other_name=None
                )
                continue

            other_basename = os.path.basename(file_other)
            other_name = os.path.join(
                os.path.dirname(item_name),
                other_basename
            ) if other_basename != os.path.basename(item_name) else None

            if not filecmp.cmp(file_this, file_other, shallow=False):
                # unequal files of the same name
                mtime_this = os.path.getmtime(file_this)
                mtime_other = os.path.getmtime(file_other)
                size_this = os.path.getsize(file_this)
                size_other = os.path.getsize(file_other)

                result[item_name] = ItemInfo(
                    equal=False, unique=False, mtimes=(mtime_this, mtime_other),
                    left_to_right=mtime_this > mtime_other,
                    sizes=(size_this, size_other), other_name=other_name
                )
            else:
                # equal files
                result[item_name] = None


def match_case_insensitive(absolute_path):
    dirname, basename = os.path.split(absolute_path)
    if not os.path.exists(dirname):
        return

    for item in os.listdir(dirname):
        if item.lower() == basename.lower():
            return os.path.join(dirname, item)


def short_stats(mtime: float, size: int) -> str:
    mtime_iso = datetime.fromtimestamp(mtime).isoformat(' ', 'seconds')
    return f'{mtime_iso}, {size:,} Bytes'


def set_fg_color(widget, color):
    palette = widget.palette()
    palette.setColor(palette.WindowText, color)
    widget.setPalette(palette)
