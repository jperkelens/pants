# Copyright 2018 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from pants.init.options_initializer import BuildConfigInitializer
from pants.option.options_bootstrapper import OptionsBootstrapper
from pants.option.scope import GLOBAL_SCOPE, Scope, ScopedOptions
from pants.testutil.engine.util import Params
from pants.testutil.test_base import TestBase
from pants.util.logging import LogLevel


class TestEngineOptionsParsing(TestBase):
    def _ob(self, args=tuple(), env=None):
        self.create_file("pants.toml")
        options_bootstrap = OptionsBootstrapper.create(
            args=tuple(args), env=env or {}, allow_pantsrc=False,
        )
        # NB: BuildConfigInitializer has sideeffects on first-run: in actual usage, these
        # sideeffects will happen during setup. We force them here.
        BuildConfigInitializer.get(options_bootstrap)
        return options_bootstrap

    def test_options_parse_scoped(self):
        options_bootstrapper = self._ob(
            args=(
                "./pants",
                "-ldebug",
                "--backend-packages=pants.backend.python",
                "binary",
                "src/python::",
            ),
            env=dict(PANTS_PANTSD="True", PANTS_BUILD_IGNORE='["ignoreme/"]'),
        )

        global_options_params = Params(Scope(str(GLOBAL_SCOPE)), options_bootstrapper)
        python_setup_options_params = Params(Scope(str("python-setup")), options_bootstrapper)
        global_options, python_setup_options = self.scheduler.product_request(
            ScopedOptions, [global_options_params, python_setup_options_params],
        )

        self.assertEqual(global_options.options.level, LogLevel.DEBUG)
        self.assertEqual(global_options.options.pantsd, True)
        self.assertEqual(global_options.options.build_ignore, ["ignoreme/"])

        self.assertEqual(python_setup_options.options.platforms, ["current"])

    def test_options_parse_memoization(self):
        # Confirm that re-executing with a new-but-identical Options object results in memoization.
        def ob():
            return self._ob(args=("./pants", "-ldebug", "binary", "src/python::"))

        def parse(ob):
            params = Params(Scope(str(GLOBAL_SCOPE)), ob)
            return self.request_single_product(ScopedOptions, params)

        # If two OptionsBootstrapper instances are not equal, memoization will definitely not kick in.
        one_opts = ob()
        two_opts = ob()
        self.assertEqual(one_opts, two_opts)
        self.assertEqual(hash(one_opts), hash(two_opts))

        # If they are equal, executing parsing on them should result in a memoized object.
        one = parse(one_opts)
        two = parse(two_opts)
        self.assertEqual(one, two)
        self.assertIs(one, two)
