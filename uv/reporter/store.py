"""AbstractReporter implementations that live at the bottom of the reporter
stack. These reporters aren't combinators; they're responsible for persisting
metrics into underlying store or mechanism.

"""

import sys
from typing import Callable, Dict, List, Optional

import uv.reader.base as rb
import uv.reader.store as rs
import uv.types as t
import uv.util as u
from uv.reporter.base import AbstractReporter


class NullReporter(AbstractReporter):
  """Reporter that does nothing with the metrics passed to its various methods.
  reader() returns an instance of rs.EmptyReader.

  """

  def report_all(self, step, m):
    return None

  def report(self, step, k, v):
    return None

  def reader(self) -> Optional[rb.AbstractReader]:
    return rs.EmptyReader()


class LambdaReporter(AbstractReporter):
  """AbstractReporter implementation that defers to a supplied lambda for its
  persistence ability. This allows you to escape the object-oriented
  programming paradigm, if you so choose.

  Args:
    report: Function called whenever reporter.report(step, k, v) is called.
    report_all: Function called whenever reporter.reporter_all(step, m) is
                called.
    close: If supplied, this no-arg function will get called by this instance's
           `close` method.

  """

  def __init__(self,
               report: Optional[Callable[[int, t.MetricKey, t.Metric],
                                         None]] = None,
               report_all: Optional[Callable[[int, Dict[t.MetricKey, t.Metric]],
                                             None]] = None,
               close: Optional[Callable[[], None]] = None):
    if report is None and report_all is None:
      raise ValueError(
          f"Must supply one of `report` and `report_all` to `LambdaReporter`.")

    self._report = report
    self._reportall = report_all
    self._close = close

  def report_all(self, step, m):
    if self._reportall is None:
      super().report_all(step, m)
    else:
      self._reportall(step, m)

  def report(self, step, k, v):
    if self._report is None:
      super().report(step, k, v)
    else:
      self._report(step, k, v)

  def close(self) -> None:
    if self._close is not None:
      self._close()


class LoggingReporter(AbstractReporter):
  """Reporter that logs all data to the file handle you pass in using a fairly
  sane format. Compatible with tqdm, the python progress bar.

  """

  @staticmethod
  def tqdm():  # pragma: no cover
    """Returns a logging reporter that will work with a tqdm progress bar."""
    return LoggingReporter(u.TqdmFile(sys.stderr))

  def __init__(self, file=sys.stdout):
    self._file = file

  def _format(self, v: t.Metric) -> str:
    """Formats the value into something appropriate for logging."""
    if u.is_number(v):
      return f"{v:.3f}"

    return str(v)

  def report_all(self, step: int, m: Dict[t.MetricKey, t.Metric]) -> None:
    s = ", ".join([f"{k} = {self._format(v)}" for k, v in m.items()])
    f = self._file
    print(f"Step {step}: {s}", file=f)


class MemoryReporter(AbstractReporter):
  """Reporter that stores metrics in a Python dictionary, keyed by t.MetricKey.
  Metrics are stored as a list.

  Args:
    m: Optional dictionary mapping metric keys to a list of accumulated metric
       values. If supplied, this dictionary will be mutated as new metrics
       arrive.

  """

  def __init__(self, m: Optional[Dict[str, List[t.Metric]]] = None):
    if m is None:
      m = {}

    self._m = m

  def report_all(self, step: int, m: Dict[t.MetricKey, t.Metric]) -> None:
    for k, v in m.items():
      self._m.setdefault(k, []).append(v)

  def clear(self):
    """Erase all key-value pairs in the backing store."""
    self._m.clear()

  def reader(self) -> Optional[rb.AbstractReader]:
    return rs.MemoryReader(self._m)