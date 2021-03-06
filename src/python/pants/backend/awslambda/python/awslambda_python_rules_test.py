# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import textwrap
from io import BytesIO
from typing import Tuple
from zipfile import ZipFile

from pants.backend.awslambda.common.awslambda_common_rules import CreatedAWSLambda
from pants.backend.awslambda.python.awslambda_python_rules import PythonAwsLambdaFieldSet
from pants.backend.awslambda.python.awslambda_python_rules import rules as awslambda_python_rules
from pants.backend.awslambda.python.target_types import PythonAWSLambda
from pants.backend.python.target_types import PythonLibrary
from pants.engine.addresses import Address
from pants.engine.fs import DigestContents
from pants.engine.rules import RootRule
from pants.engine.target import WrappedTarget
from pants.testutil.engine.util import Params
from pants.testutil.external_tool_test_base import ExternalToolTestBase
from pants.testutil.option.util import create_options_bootstrapper


class TestPythonAWSLambdaCreation(ExternalToolTestBase):
    @classmethod
    def rules(cls):
        return (
            *super().rules(),
            *awslambda_python_rules(),
            RootRule(PythonAwsLambdaFieldSet),
        )

    @classmethod
    def target_types(cls):
        return [PythonAWSLambda, PythonLibrary]

    def create_python_awslambda(self, addr: str) -> Tuple[str, bytes]:
        bootstrapper = create_options_bootstrapper(
            args=[
                "--backend-packages=pants.backend.awslambda.python",
                "--source-root-patterns=src/python",
            ]
        )
        target = self.request_single_product(
            WrappedTarget, Params(Address.parse(addr), bootstrapper)
        ).target
        created_awslambda = self.request_single_product(
            CreatedAWSLambda, Params(PythonAwsLambdaFieldSet.create(target), bootstrapper)
        )
        created_awslambda_digest_contents = self.request_single_product(
            DigestContents, created_awslambda.digest
        )
        assert len(created_awslambda_digest_contents) == 1
        return created_awslambda.zip_file_relpath, created_awslambda_digest_contents[0].content

    def test_create_hello_world_lambda(self) -> None:
        self.create_file(
            "src/python/foo/bar/hello_world.py",
            textwrap.dedent(
                """
                def handler(event, context):
                    print('Hello, World!')
                """
            ),
        )

        self.create_file(
            "src/python/foo/bar/BUILD",
            textwrap.dedent(
                """
                python_library(
                  name='hello_world',
                  sources=['hello_world.py']
                )

                python_awslambda(
                  name='hello_world_lambda',
                  dependencies=[':hello_world'],
                  handler='foo.bar.hello_world',
                  runtime='python3.7'
                )
                """
            ),
        )

        zip_file_relpath, content = self.create_python_awslambda(
            "src/python/foo/bar:hello_world_lambda"
        )
        assert "hello_world_lambda.zip" == zip_file_relpath
        zipfile = ZipFile(BytesIO(content))
        names = set(zipfile.namelist())
        assert "lambdex_handler.py" in names
        assert "foo/bar/hello_world.py" in names
