# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Support for Python.

See https://www.pantsbuild.org/docs/python-backend.
"""

from pants.backend.python.dependency_inference import rules as dependency_inference_rules
from pants.backend.python.pants_requirement import PantsRequirement
from pants.backend.python.python_artifact import PythonArtifact
from pants.backend.python.python_requirements import PythonRequirements
from pants.backend.python.rules import (
    ancestor_files,
    coverage,
    create_python_binary,
    pex,
    pex_cli,
    pex_environment,
    pex_from_targets,
    pytest_runner,
    python_sources,
    repl,
    run_python_binary,
    run_setup_py,
)
from pants.backend.python.subsystems import python_native_code, subprocess_environment
from pants.backend.python.target_types import (
    PythonBinary,
    PythonDistribution,
    PythonLibrary,
    PythonRequirementLibrary,
    PythonRequirementsFile,
    PythonTests,
)
from pants.build_graph.build_file_aliases import BuildFileAliases
from pants.python.python_requirement import PythonRequirement


def build_file_aliases():
    return BuildFileAliases(
        objects={
            "python_requirement": PythonRequirement,
            "python_artifact": PythonArtifact,
            "setup_py": PythonArtifact,
        },
        context_aware_object_factories={
            "python_requirements": PythonRequirements,
            PantsRequirement.alias: PantsRequirement,
        },
    )


def rules():
    return (
        *coverage.rules(),
        *ancestor_files.rules(),
        *python_sources.rules(),
        *dependency_inference_rules.rules(),
        *pex.rules(),
        *pex_cli.rules(),
        *pex_environment.rules(),
        *pex_from_targets.rules(),
        *pytest_runner.rules(),
        *create_python_binary.rules(),
        *python_native_code.rules(),
        *repl.rules(),
        *run_python_binary.rules(),
        *run_setup_py.rules(),
        *subprocess_environment.rules(),
    )


def target_types():
    return [
        PythonBinary,
        PythonDistribution,
        PythonLibrary,
        PythonRequirementLibrary,
        PythonRequirementsFile,
        PythonTests,
    ]
