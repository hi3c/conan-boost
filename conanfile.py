from conans import ConanFile, CMake, tools
import os


class BoostConan(ConanFile):
    name = "boost"
    version = "1.64.0"
    license = "BSL"
    url = "http://boost.org"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = "shared=False"
    generators = "cmake"

    def source(self):
        tools.download("https://dl.bintray.com/boostorg/release/1.64.0/source/boost_1_64_0.tar.bz2",
                       "boost.tar.bz2")
        tools.unzip("boost.tar.bz2")

    def build(self):
        self.run("cd boost_1_64_0 && ./bootstrap.sh")
        self.run("cd boost_1_64_0 && ./b2 --with-filesystem --with-system -j{}".format(tools.cpu_count()))

    def package(self):
        self.copy("*.lib", dst="lib", keep_path=False)
        self.copy("*.a", dst="lib", keep_path=False)

        if self.options.shared:
            self.copy("*.dll", dst="bin", keep_path=False)
            self.copy("*.so", dst="lib", keep_path=False)
            self.copy("*.dylib", dst="lib", keep_path=False)

        self.copy("*.hpp", src=os.path.join("boost_1_64_0", "boost"), dst="include/boost", keep_path=True)
        self.copy("*.h", src=os.path.join("boost_1_64_0", "boost"), dst="include/boost", keep_path=True)
        self.copy("*.ipp", src=os.path.join("boost_1_64_0", "boost"), dst="include/boost", keep_path=True)

    def package_info(self):
        self.cpp_info.libs = ["boost_filesystem", "boost_system"]
