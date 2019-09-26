# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import logging
import os

from pants.backend.python.rules.download_pex_bin import DownloadedPexBin
from pants.backend.python.subsystems.python_native_code import PexBuildEnvironment, PythonNativeCode
from pants.backend.python.subsystems.python_repos import PythonRepos
from pants.backend.python.subsystems.python_setup import PythonSetup
from pants.engine.isolated_process import ExecuteProcessRequest, ExecuteProcessResult
from pants.engine.fs import EMPTY_DIRECTORY_DIGEST, Digest, DirectoriesToMerge
from pants.engine.rules import optionable_rule, rule
from pants.engine.selectors import Get
from pants.util.objects import Exactly, datatype, hashable_string_list, string_optional, string_type
from pants.util.strutil import create_path_env_var


logger = logging.getLogger(__name__)


class MakePexRequest(datatype([
  ('output_filename', string_type),
  ('requirements', hashable_string_list),
  ('interpreter_constraints', hashable_string_list),
  ('entry_point', string_optional),
  ('input_files_digest', Exactly(Digest, type(None))),
  ('source_dirs', hashable_string_list),
])):

  def __new__(cls, output_filename, requirements, interpreter_constraints, entry_point,
              input_files_digest=None, source_dirs=()):
    return super().__new__(cls, output_filename, requirements, interpreter_constraints, entry_point,
                           input_files_digest=input_files_digest, source_dirs=source_dirs)


class RequirementsPex(datatype([('directory_digest', Digest)])):
  pass


def containing_dir_if_exe(path):
  if not os.path.isdir(path):
    return os.path.dirname(path)
  return path


# TODO: This is non-hermetic because the requirements will be resolved on the fly by
# pex, where it should be hermetically provided in some way.
@rule(RequirementsPex, [MakePexRequest, DownloadedPexBin, PythonSetup, PythonRepos, PexBuildEnvironment])
def create_requirements_pex(request, pex_bin, python_setup, python_repos, pex_build_environment):
  """Returns a PEX with the given requirements, optional entry point, and optional
  interpreter constraints."""

  interpreter_search_paths = create_path_env_var([
    containing_dir_if_exe(p) for p in
    python_setup.interpreter_search_paths
  ])
  env = {"PATH": interpreter_search_paths, **pex_build_environment.invocation_environment_dict}

  interpreter_constraint_args = []
  for constraint in request.interpreter_constraints:
    interpreter_constraint_args.extend(["--interpreter-constraint", constraint])

  # NB: we use the hardcoded and generic bin name `python`, rather than something dynamic like
  # `sys.executable`, to ensure that the interpreter may be discovered both locally and in remote
  # execution (so long as `env` is populated with a `PATH` env var and `python` is discoverable
  # somewhere on that PATH). This is only used to run the downloaded PEX tool; it is not
  # necessarily the interpreter that PEX will use to execute the generated .pex file.
  # TODO(#7735): Set --python-setup-interpreter-search-paths differently for the host and target
  # platforms, when we introduce platforms in https://github.com/pantsbuild/pants/issues/7735.
  argv = [
    "python",
    f"./{pex_bin.executable}",
    "--output-file",
    request.output_filename,
    # FIXME: interpreter constraints don't play well with pexrc configuration in some internal
    # repos!
    '--python=python3.6',
  ]

  # argv.append('--no-index')
  argv.extend(
    f'--index-url={python_index}'
    for python_index in python_repos.indexes
  )
  argv.extend(
    f'--repo={repo_url}'
    for repo_url in python_repos.repos
  )

  if request.entry_point is not None:
    argv.extend(["--entry-point", request.entry_point])

  # FIXME: interpreter constraints don't play well with pexrc configuration in some internal repos!
  # argv.extend(interpreter_constraint_args)
  argv.extend(request.requirements)

  argv.extend(
    f'--sources-directory={src_dir}'
    for src_dir in request.source_dirs
  )

  all_inputs = (pex_bin.directory_digest,) + ((request.input_files_digest,) if request.input_files_digest else ())
  merged_digest = yield Get(Digest, DirectoriesToMerge(directories=all_inputs))

  execute_process_request = ExecuteProcessRequest(
    argv=tuple(argv),
    env=env,
    input_files=merged_digest,
    description=f"Create a PEX with sources and requirements: {', '.join(request.requirements)}",
    output_files=(f'./{request.output_filename}',),
  )

  result = yield Get(ExecuteProcessResult, ExecuteProcessRequest, execute_process_request)
  yield RequirementsPex(directory_digest=result.output_directory_digest)


def rules():
  return [
    create_requirements_pex,
    optionable_rule(PythonSetup),
    optionable_rule(PythonNativeCode),
    optionable_rule(PythonRepos),
  ]
