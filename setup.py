from pathlib import Path
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop


def _run_bootstrap():
    try:
        from src.todoctl.bootstrap import install_for_current_shell
        install_for_current_shell(silent=True)
    except Exception:
        # Keep installation resilient. The CLI still contains a runtime fallback.
        pass


class InstallCommand(install):
    def run(self):
        super().run()
        _run_bootstrap()


class DevelopCommand(develop):
    def run(self):
        super().run()
        _run_bootstrap()


setup(cmdclass={"install": InstallCommand, "develop": DevelopCommand})
