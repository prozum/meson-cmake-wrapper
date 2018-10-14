import os
import subprocess


class NinjaBackend:
    """
    Class that handles interaction with Ninja.
    """

    def __init__(self, meson, path='ninja'):
        self.meson = meson
        self.path = path

    def call(self, args, show=False):
        child = subprocess.Popen([self.path] + args, stdout=subprocess.PIPE)
        fulloutput = b''
        while True:
            output = child.stdout.readline()
            if output == b'' and child.poll() is not None:
                break
            if output:
                if show:
                    print(output.decode("utf-8"), end='')
                fulloutput += output
        fulloutput = fulloutput.decode("utf-8")
        if child.poll() != 0:
            raise RuntimeError(fulloutput)
        return fulloutput

    def setup(self):
        ninja_file = os.path.join(self.meson.build_dir, 'build.ninja')
        if os.path.exists(ninja_file):
            return True
        return False

    def reconfigure(self):
        self.call(['-C', self.meson.build_dir, 'reconfigure'], True)

    def build(self, target):
        self.call(['-C', self.meson.build_dir, self.get_target(target)], True)

    def get_target(self, target_name):
        target = next((t for t in self.meson.get_targets() if t['name'] == target_name), None)
        if target:
            return target['filename']

        return target_name
