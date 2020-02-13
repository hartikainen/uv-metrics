"""Reader implementation that relies on the PyFilesystem2 abstraction for
filesystems. See https://github.com/PyFilesystem/pyfilesystem2 for more
information on the library.

"""

import json
from typing import Iterable, List, Union

import fs as pyfs
from fs.base import FS

import uv.types as t
from uv.reader.base import AbstractReader, IterableReader
import uv.fs.util as u


class FSReader(AbstractReader, IterableReader):
  """AbstractReader implementation backed by an instance of pyfilesystem2's FS
  abstraction.

  Args:
    fs: Either an fs URI string, or an actual fs.base.FS object.

  """

  def __init__(self, fs: Union[FS, str]):
    self._fs = u.load_fs(fs)

  def keys(self) -> Iterable[t.Metric]:
    """Returns all files in the filesystem that plausibly contains metrics in jsonl
    format.

    """
    for p in self._fs.walk.files(filter=['*.jsonl']):
      base = pyfs.path.basename(p)
      k, _ = pyfs.path.splitext(base)
      yield k

  def read(self, k: t.MetricKey) -> List[t.Metric]:
    try:
      abs_path = u.jsonl_path(k)
      with self._fs.open(abs_path, mode='rb') as handle:
        lines = handle.read().splitlines()
        return [json.loads(s.decode("utf-8")) for s in lines]

    except pyfs.errors.ResourceNotFound:
      return []

  def close(self) -> None:
    self._fs.close()
